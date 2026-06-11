"""Daily Bronze ingestion for the manufacturing quality traceability lakehouse."""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd

from simulators.cmm_inspection import generate_cmm_inspections
from simulators.common import build_simulation_context, coerce_production_date
from simulators.material_certs import generate_material_certs
from simulators.process_parameters import generate_process_parameters
from simulators.torque_audit import generate_torque_audits


SOURCE_GENERATORS = {
    "cmm_inspection": generate_cmm_inspections,
    "process_parameters": generate_process_parameters,
    "torque_audit": generate_torque_audits,
    "supplier_material_certs": generate_material_certs,
}


@dataclass(frozen=True)
class IngestionResult:
    """Metadata returned for one written Bronze source."""

    source: str
    rows: int
    output_path: Path


def get_lakehouse_root() -> Path:
    """Resolve the lakehouse root.

    The repo defaults to a project-local lakehouse for easy demos. Set
    LAKEHOUSE_ROOT=/lakehouse when an absolute root is preferred.
    """

    return Path(os.getenv("LAKEHOUSE_ROOT", "lakehouse")).expanduser().resolve()


def bronze_source_path(lakehouse_root: Path, source: str, production_date: date) -> Path:
    """Return /lakehouse/bronze/source/date style storage path."""

    return lakehouse_root / "bronze" / source / production_date.isoformat()


def write_bronze_parquet(
    frame: pd.DataFrame,
    source: str,
    production_date: date,
    lakehouse_root: Path | None = None,
) -> IngestionResult:
    """Write a source dataframe to a daily Bronze Parquet file."""

    root = lakehouse_root or get_lakehouse_root()
    output_dir = bronze_source_path(root, source, production_date)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{source}_{production_date:%Y%m%d}.parquet"
    frame.to_parquet(output_file, index=False)
    return IngestionResult(source=source, rows=len(frame), output_path=output_file)


def run_ingestion(
    production_date: str | date | None = None,
    part_count: int = 500,
    seed: int | None = None,
    lakehouse_root: str | Path | None = None,
) -> list[IngestionResult]:
    """Generate and ingest all synthetic daily sources into Bronze."""

    prod_date = coerce_production_date(production_date)
    root = Path(lakehouse_root).expanduser().resolve() if lakehouse_root else get_lakehouse_root()
    context = build_simulation_context(prod_date, part_count=part_count, seed=seed)

    results = []
    for source, generator in SOURCE_GENERATORS.items():
        frame = generator(context)
        results.append(write_bronze_parquet(frame, source, prod_date, root))

    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate and ingest daily manufacturing source data.")
    parser.add_argument("--date", dest="production_date", default=None, help="Production date YYYY-MM-DD.")
    parser.add_argument("--parts", dest="part_count", type=int, default=500, help="Parts to simulate.")
    parser.add_argument("--seed", dest="seed", type=int, default=None, help="Optional deterministic seed.")
    parser.add_argument(
        "--lakehouse-root",
        dest="lakehouse_root",
        default=None,
        help="Override lakehouse root. Defaults to LAKEHOUSE_ROOT or ./lakehouse.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    results = run_ingestion(
        production_date=args.production_date,
        part_count=args.part_count,
        seed=args.seed,
        lakehouse_root=args.lakehouse_root,
    )
    for result in results:
        print(f"{result.source}: wrote {result.rows:,} rows to {result.output_path}")


if __name__ == "__main__":
    main()
