"""Streamlit dashboard for manufacturing quality traceability."""

from __future__ import annotations

import os
from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st


DEFAULT_DUCKDB_PATH = Path(os.getenv("DUCKDB_PATH", "lakehouse/quality_traceability.duckdb"))


@st.cache_resource
def connect_duckdb(database_path: str) -> duckdb.DuckDBPyConnection:
    return duckdb.connect(database_path, read_only=True)


@st.cache_data(ttl=60)
def load_gold_summary(database_path: str) -> pd.DataFrame:
    con = connect_duckdb(database_path)
    return con.execute(
        """
        select *
        from gold.mart_part_quality_summary
        order by production_date, part_id
        """
    ).df()


@st.cache_data(ttl=60)
def load_source_rows(database_path: str, part_id: str) -> dict[str, pd.DataFrame]:
    con = connect_duckdb(database_path)
    return {
        "cmm": con.execute(
            """
            select *
            from bronze.bronze_cmm_inspection
            where part_id = ?
            order by dimension_name
            """,
            [part_id],
        ).df(),
        "torque": con.execute(
            """
            select *
            from bronze.bronze_torque_audit
            where part_id = ?
            order by joint_id
            """,
            [part_id],
        ).df(),
        "process": con.execute(
            """
            select *
            from bronze.bronze_process_parameters
            where part_id = ?
            """,
            [part_id],
        ).df(),
    }


@st.cache_data(ttl=60)
def load_material_cert(database_path: str, batch_id: str) -> pd.DataFrame:
    con = connect_duckdb(database_path)
    return con.execute(
        """
        select *
        from bronze.bronze_supplier_material_certs
        where batch_id = ?
        """,
        [batch_id],
    ).df()


def show_setup_error(database_path: Path, error: Exception) -> None:
    st.error("The DuckDB mart is not available yet.")
    st.code(
        "\n".join(
            [
                "python -m pipelines.ingest --date 2026-06-11 --parts 500",
                "dbt --profiles-dir . run",
                "dbt --profiles-dir . test",
                "streamlit run app.py",
            ]
        ),
        language="bash",
    )
    st.caption(f"Expected database: {database_path}")
    st.exception(error)


def render_metric_row(summary: pd.DataFrame) -> None:
    total_parts = len(summary)
    defect_parts = int(summary["defect_flag"].sum())
    defect_rate = defect_parts / total_parts if total_parts else 0
    avg_score = summary["composite_quality_score"].mean() if total_parts else 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Parts traced", f"{total_parts:,}")
    col2.metric("Defect parts", f"{defect_parts:,}")
    col3.metric("Defect rate", f"{defect_rate:.1%}")
    col4.metric("Avg quality score", f"{avg_score:.1f}")


def render_defect_trend(summary: pd.DataFrame) -> None:
    st.subheader("Defect rate trend by day")
    trend = (
        summary.assign(defect_int=summary["defect_flag"].astype(int))
        .groupby("production_date", as_index=False)
        .agg(defect_rate=("defect_int", "mean"), parts=("part_id", "count"))
    )
    trend["defect_rate_pct"] = trend["defect_rate"] * 100
    st.line_chart(trend, x="production_date", y="defect_rate_pct")
    st.dataframe(trend, use_container_width=True, hide_index=True)


def render_top_failing_dimensions(summary: pd.DataFrame) -> None:
    st.subheader("Top failing dimensions")
    exploded = (
        summary.loc[summary["failing_dimension_names"].fillna("") != "", ["part_id", "failing_dimension_names"]]
        .assign(dimension_name=lambda df: df["failing_dimension_names"].str.split(", "))
        .explode("dimension_name")
    )
    if exploded.empty:
        st.success("No dimensional failures in the selected population.")
        return

    top_dims = (
        exploded.groupby("dimension_name", as_index=False)
        .agg(failing_parts=("part_id", "nunique"))
        .sort_values("failing_parts", ascending=False)
    )
    st.bar_chart(top_dims, x="dimension_name", y="failing_parts")
    st.dataframe(top_dims, use_container_width=True, hide_index=True)


def render_correlation_heatmap(summary: pd.DataFrame) -> None:
    st.subheader("Process parameter correlation heatmap vs defect flag")
    numeric_cols = [
        "spindle_speed",
        "feed_rate",
        "coolant_temp",
        "cycle_time",
        "hardness",
        "tensile_strength",
        "failed_dimension_count",
        "failed_joint_count",
        "composite_quality_score",
    ]
    corr_input = summary[numeric_cols].copy()
    corr_input["defect_flag"] = summary["defect_flag"].astype(int)
    corr = corr_input.corr(numeric_only=True).round(3)

    st.dataframe(
        corr.style.background_gradient(cmap="RdBu_r", axis=None, vmin=-1, vmax=1),
        use_container_width=True,
    )
    st.caption("Positive values indicate parameters moving with the defect flag in the selected data.")


def render_part_drilldown(database_path: str, summary: pd.DataFrame) -> None:
    st.subheader("Part traceability drill-down")
    part_options = summary["part_id"].sort_values().tolist()
    default_index = 0
    defect_parts = summary.loc[summary["defect_flag"], "part_id"].sort_values().tolist()
    if defect_parts:
        default_index = part_options.index(defect_parts[0])

    selected_part = st.selectbox("Select part_id", part_options, index=default_index)
    selected_summary = summary.loc[summary["part_id"] == selected_part].iloc[0]

    st.write("Gold summary")
    st.dataframe(selected_summary.to_frame(name="value"), use_container_width=True)

    source_rows = load_source_rows(database_path, selected_part)
    material_cert = load_material_cert(database_path, str(selected_summary["batch_id"]))

    tab1, tab2, tab3, tab4 = st.tabs(["CMM", "Torque", "CNC process", "Material cert"])
    with tab1:
        st.dataframe(source_rows["cmm"], use_container_width=True, hide_index=True)
    with tab2:
        st.dataframe(source_rows["torque"], use_container_width=True, hide_index=True)
    with tab3:
        st.dataframe(source_rows["process"], use_container_width=True, hide_index=True)
    with tab4:
        st.dataframe(material_cert, use_container_width=True, hide_index=True)


def main() -> None:
    st.set_page_config(page_title="Manufacturing Quality Traceability", layout="wide")
    st.title("Manufacturing Quality Traceability Lakehouse")
    st.caption("CMM inspection + CNC process + torque audit + supplier material certificates")

    database_path = Path(
        st.sidebar.text_input("DuckDB path", value=str(DEFAULT_DUCKDB_PATH))
    )
    try:
        summary = load_gold_summary(str(database_path))
    except Exception as exc:  # pragma: no cover - dashboard runtime guard
        show_setup_error(database_path, exc)
        return

    if summary.empty:
        st.warning("No quality summary rows found.")
        return

    summary["production_date"] = pd.to_datetime(summary["production_date"]).dt.date
    min_date = min(summary["production_date"])
    max_date = max(summary["production_date"])
    selected_dates = st.sidebar.date_input(
        "Production date range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )
    if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
        start_date, end_date = selected_dates
        summary = summary[
            (summary["production_date"] >= start_date) & (summary["production_date"] <= end_date)
        ]

    machines = ["All"] + sorted(summary["machine_id"].dropna().unique().tolist())
    selected_machine = st.sidebar.selectbox("Machine", machines)
    if selected_machine != "All":
        summary = summary[summary["machine_id"] == selected_machine]

    root_causes = ["All"] + sorted(summary["defect_root_cause"].dropna().unique().tolist())
    selected_root_cause = st.sidebar.selectbox("Root cause", root_causes)
    if selected_root_cause != "All":
        summary = summary[summary["defect_root_cause"] == selected_root_cause]

    if summary.empty:
        st.warning("No parts match the selected filters.")
        return

    render_metric_row(summary)
    render_defect_trend(summary)

    left, right = st.columns([1, 1])
    with left:
        render_top_failing_dimensions(summary)
    with right:
        render_correlation_heatmap(summary)

    render_part_drilldown(str(database_path), summary)


if __name__ == "__main__":
    main()
