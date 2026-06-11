"""Prefect flow for daily manufacturing quality traceability ingestion."""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from prefect import flow, get_run_logger, task

from pipelines.ingest import IngestionResult, run_ingestion
from simulators.common import coerce_production_date


@task(name="generate-and-ingest-bronze-sources")
def ingest_bronze_sources(
    production_date: str | date | None = None,
    part_count: int = 500,
    seed: int | None = None,
    lakehouse_root: str | Path | None = None,
) -> list[IngestionResult]:
    return run_ingestion(
        production_date=production_date,
        part_count=part_count,
        seed=seed,
        lakehouse_root=lakehouse_root,
    )


@flow(name="manufacturing-quality-traceability-daily", log_prints=True)
def daily_quality_traceability_flow(
    production_date: str | date | None = None,
    part_count: int = 500,
    seed: int | None = None,
    lakehouse_root: str | Path | None = None,
) -> list[dict[str, str | int]]:
    """Generate all source extracts and land them in the Bronze layer."""

    logger = get_run_logger()
    prod_date = coerce_production_date(production_date)
    logger.info("Starting daily ingestion for %s with %,d parts", prod_date, part_count)
    results = ingest_bronze_sources(prod_date, part_count, seed, lakehouse_root)

    serializable_results = []
    for result in results:
        logger.info("Wrote %s rows for %s to %s", result.rows, result.source, result.output_path)
        serializable_results.append(
            {
                "source": result.source,
                "rows": result.rows,
                "output_path": str(result.output_path),
            }
        )
    return serializable_results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Prefect daily ingestion flow.")
    parser.add_argument("--date", dest="production_date", default=None, help="Production date YYYY-MM-DD.")
    parser.add_argument("--parts", dest="part_count", type=int, default=500, help="Parts to simulate.")
    parser.add_argument("--seed", dest="seed", type=int, default=None, help="Optional deterministic seed.")
    parser.add_argument("--lakehouse-root", dest="lakehouse_root", default=None)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    daily_quality_traceability_flow(
        production_date=args.production_date,
        part_count=args.part_count,
        seed=args.seed,
        lakehouse_root=args.lakehouse_root,
    )
