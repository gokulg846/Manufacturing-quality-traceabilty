# Manufacturing Quality Traceability Lakehouse

A local data lakehouse portfolio project for automotive manufacturing quality traceability. It simulates four realistic shop-floor and supplier data sources, lands them as daily Bronze Parquet files, transforms them with dbt into Silver and Gold quality marts in DuckDB, and serves a Streamlit dashboard for defect analytics and part-level traceability.

## Business problem

Automotive OEMs and Tier 1 suppliers need fast containment when a quality issue appears in production or warranty. A single defective e-axle carrier, battery tray bracket, or machined housing can involve multiple signals:

- CMM inspection results showing a critical dimension drifting out of tolerance.
- CNC process parameters such as spindle speed, feed rate, coolant temperature, or cycle time.
- Torque audit logs for bolted joints that can fail due to tool, material, or process issues.
- Supplier material certificates proving whether an incoming batch met hardness and tensile specifications.

In many plants these records live in separate quality, MES, machine-log, and supplier systems. This project demonstrates how a data engineer can build a local traceability lakehouse that joins those signals into one part-level record for containment, root-cause analysis, and executive reporting.

## Why this matters for OEMs

- **Containment speed:** identify every part sharing a failed dimension, torque issue, machine, batch, or supplier material deviation.
- **Warranty risk reduction:** connect upstream process drift to downstream inspection and audit failures before escapes reach customers.
- **Launch and ramp support:** monitor quality score and process correlations while new lines stabilize.
- **Supplier accountability:** tie part failures to certified material properties and incoming batch evidence.
- **Auditability:** preserve raw Bronze source records while publishing governed Silver and Gold tables.

## Architecture

```text
Synthetic source generators
  |-- simulators/cmm_inspection.py
  |-- simulators/process_parameters.py
  |-- simulators/torque_audit.py
  `-- simulators/material_certs.py
          |
          v
Prefect / Python ingestion
  pipelines/ingest.py or orchestration/flow.py
          |
          v
Local Parquet Bronze layer
  lakehouse/bronze/cmm_inspection/YYYY-MM-DD/*.parquet
  lakehouse/bronze/process_parameters/YYYY-MM-DD/*.parquet
  lakehouse/bronze/torque_audit/YYYY-MM-DD/*.parquet
  lakehouse/bronze/supplier_material_certs/YYYY-MM-DD/*.parquet
          |
          v
dbt-duckdb transformations and tests
  dbt/models/bronze  -> typed views over Parquet
  dbt/models/silver  -> cleaned joins and quality flags
  dbt/models/gold    -> mart_part_quality_summary
          |
          v
DuckDB database
  lakehouse/quality_traceability.duckdb
          |
          v
Streamlit dashboard
  app.py
```

The default lakehouse root is `./lakehouse` so the project runs without elevated privileges. To write to an absolute `/lakehouse` root, set:

```bash
export LAKEHOUSE_ROOT=/lakehouse
export DUCKDB_PATH=/lakehouse/quality_traceability.duckdb
```

## Data sources simulated

### CMM inspection results

Grain: one row per part and critical dimension.

Fields include `part_id`, `dimension_name`, `measured_value`, `nominal`, `tolerance`, lower/upper spec limits, inspection timestamp, and `pass_fail`.

The generator models machine-specific dimensional drift, tool wear through the shift, and rare outlier events.

### CNC process parameters

Grain: one row per part.

Fields include `part_id`, `machine_id`, `spindle_speed`, `feed_rate`, `coolant_temp`, `cycle_time`, plus `batch_id`, line, shift, part model, and process timestamp.

`batch_id` provides the traceability bridge from each machined part to supplier material certificates.

### Torque audit logs

Grain: one row per part and bolted joint.

Fields include `part_id`, `joint_id`, `target_torque`, `actual_torque`, `angle`, torque/angle limits, audit timestamp, and `pass_fail`.

The generator models line/tool bias and occasional torque outliers.

### Supplier material certificates

Grain: one row per incoming material batch.

Fields include `batch_id`, `supplier_id`, `hardness`, `tensile_strength`, `cert_date`, spec limits, and material deviation flag.

The generator creates mostly conforming batches with a small number of hardness or tensile deviations.

## Gold mart

`gold.mart_part_quality_summary` has one row per part with:

- All CNC process parameters: machine, spindle speed, feed rate, coolant temperature, and cycle time.
- Material traceability: batch, supplier, hardness, tensile strength, and cert date.
- Quality outcomes: failed dimension count, failing dimension names, failed torque joint count, failing joint IDs, material deviation flag.
- `defect_flag`: true when the part has any out-of-tolerance dimension, torque failure, material deviation, or missing traceability.
- `defect_root_cause`: `dimension`, `torque`, `material`, `unknown`, or `none`.
- `composite_quality_score`: 0-100 score penalizing dimensional failures, torque failures, material deviations, and high-risk process conditions.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Generate one day of synthetic Bronze data:

```bash
python -m pipelines.ingest --date 2026-06-11 --parts 500
```

Or run the Prefect flow:

```bash
python -m orchestration.flow --date 2026-06-11 --parts 500
```

Build and test the lakehouse:

```bash
dbt --profiles-dir . run
dbt --profiles-dir . test
```

Launch the dashboard:

```bash
streamlit run app.py
```

## Multi-day demo data

Run ingestion for several dates, then rerun dbt:

```bash
python -m pipelines.ingest --date 2026-06-08 --parts 450
python -m pipelines.ingest --date 2026-06-09 --parts 475
python -m pipelines.ingest --date 2026-06-10 --parts 525
python -m pipelines.ingest --date 2026-06-11 --parts 500
dbt --profiles-dir . run
dbt --profiles-dir . test
```

## Dashboard capabilities

The Streamlit app provides:

1. Defect rate trend by production day.
2. Top failing dimensions.
3. Process parameter correlation heatmap against the defect flag.
4. Drill-down by `part_id` showing the Gold summary plus raw CMM, torque, CNC process, and supplier cert records.

Sidebar filters support production date range, machine, and root cause.

## Data quality coverage

dbt tests cover:

- Referential integrity from CMM and torque part records to the CNC part population.
- Referential integrity from CNC `batch_id` to supplier material certificates.
- Completeness checks on keys, dates, source measurements, and Gold outputs.
- Range checks for CMM measurements, tolerance values, torque, angle, CNC parameters, material properties, and composite quality score.
- Accepted values for pass/fail and root-cause classifications.

## Repository layout

```text
.
|-- app.py
|-- dbt_project.yml
|-- profiles.yml
|-- requirements.txt
|-- simulators/
|   |-- cmm_inspection.py
|   |-- common.py
|   |-- material_certs.py
|   |-- process_parameters.py
|   `-- torque_audit.py
|-- pipelines/
|   `-- ingest.py
|-- orchestration/
|   `-- flow.py
`-- dbt/
    |-- macros/
    |-- models/
    |   |-- bronze/
    |   |-- silver/
    |   `-- gold/
    `-- tests/
```

## Notes for portfolio presentation

This project is intentionally local and reproducible. It demonstrates data engineering skills that map directly to real manufacturing analytics programs: synthetic source creation, partitioned Parquet ingestion, lakehouse layering, dbt modeling and testing, traceability joins, defect scoring, and dashboard delivery.
