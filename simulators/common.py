"""Common manufacturing simulation primitives.

The generators intentionally share a daily production plan so the lakehouse can
trace a part across machining, inspection, torque audit, and material data.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Iterable

import numpy as np
import pandas as pd
from faker import Faker


MACHINES = [f"CNC-{idx:02d}" for idx in range(1, 9)]
SUPPLIERS = [f"SUP-{idx:03d}" for idx in range(101, 109)]
LINES = ["LINE-A", "LINE-B", "LINE-C"]
PART_MODELS = ["EV_GEAR_HOUSING", "BATTERY_TRAY_BRACKET", "E-AXLE_CARRIER"]

DIMENSION_SPECS = [
    {"dimension_name": "bore_diameter_mm", "nominal": 50.000, "tolerance": 0.030},
    {"dimension_name": "deck_height_mm", "nominal": 120.000, "tolerance": 0.050},
    {"dimension_name": "bolt_circle_dia_mm", "nominal": 86.000, "tolerance": 0.040},
    {"dimension_name": "oil_port_dia_mm", "nominal": 8.000, "tolerance": 0.015},
    {"dimension_name": "locator_slot_width_mm", "nominal": 12.000, "tolerance": 0.020},
]

TORQUE_SPECS = [
    {"joint_id": "J-AXLE-CAP-01", "target_torque": 65.0, "target_angle": 70.0},
    {"joint_id": "J-AXLE-CAP-02", "target_torque": 65.0, "target_angle": 70.0},
    {"joint_id": "J-MOUNT-BRACKET-01", "target_torque": 42.0, "target_angle": 55.0},
    {"joint_id": "J-MOUNT-BRACKET-02", "target_torque": 42.0, "target_angle": 55.0},
]

HARDNESS_MIN = 180.0
HARDNESS_MAX = 230.0
TENSILE_MIN = 580.0
TENSILE_MAX = 760.0


@dataclass(frozen=True)
class SimulationContext:
    """Shared daily production inputs for all source simulators."""

    production_date: date
    part_plan: pd.DataFrame
    batch_plan: pd.DataFrame
    seed: int


def coerce_production_date(value: str | date | datetime | None) -> date:
    """Convert CLI/Python date inputs into a date object."""

    if value is None:
        return date.today()
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return datetime.strptime(value, "%Y-%m-%d").date()


def daily_seed(production_date: date, salt: int = 0) -> int:
    """Make deterministic daily data while allowing per-source variation."""

    return int(production_date.strftime("%Y%m%d")) + salt


def production_timestamp(
    rng: np.random.Generator, production_date: date, sequence: int, total_parts: int
) -> datetime:
    """Spread part events through two ten-hour shifts."""

    seconds_per_shift_day = 20 * 60 * 60
    base_seconds = int(sequence / max(total_parts, 1) * seconds_per_shift_day)
    jitter = int(rng.integers(-240, 241))
    seconds = min(max(base_seconds + jitter, 0), seconds_per_shift_day - 1)
    return datetime.combine(production_date, time(5, 30)) + pd.to_timedelta(seconds, unit="s")


def build_simulation_context(
    production_date: str | date | datetime | None = None,
    part_count: int = 500,
    seed: int | None = None,
) -> SimulationContext:
    """Create a realistic daily part and material batch population."""

    prod_date = coerce_production_date(production_date)
    base_seed = seed if seed is not None else daily_seed(prod_date)
    rng = np.random.default_rng(base_seed)
    fake = Faker()
    Faker.seed(base_seed)

    batch_count = max(8, min(24, int(np.ceil(part_count / 45))))
    batch_rows = []
    for batch_idx in range(1, batch_count + 1):
        supplier_id = rng.choice(SUPPLIERS)
        batch_rows.append(
            {
                "batch_id": f"MAT-{prod_date:%Y%m%d}-{batch_idx:03d}",
                "supplier_id": supplier_id,
                "supplier_lot": fake.bothify(text="LOT-????-#####").upper(),
                "mill_heat": fake.bothify(text="HEAT-####??").upper(),
            }
        )
    batch_plan = pd.DataFrame(batch_rows)

    machine_weights = np.array([0.13, 0.14, 0.12, 0.13, 0.11, 0.13, 0.12, 0.12])
    supplier_batch_weights = np.ones(batch_count) / batch_count
    part_rows = []
    for idx in range(1, part_count + 1):
        batch = batch_plan.iloc[int(rng.choice(batch_count, p=supplier_batch_weights))]
        machine_id = str(rng.choice(MACHINES, p=machine_weights))
        shift = "A" if idx <= part_count / 2 else "B"
        part_rows.append(
            {
                "part_id": f"PART-{prod_date:%Y%m%d}-{idx:05d}",
                "production_date": prod_date.isoformat(),
                "sequence_no": idx,
                "part_model": str(rng.choice(PART_MODELS, p=[0.45, 0.30, 0.25])),
                "line_id": str(rng.choice(LINES, p=[0.40, 0.35, 0.25])),
                "shift": shift,
                "machine_id": machine_id,
                "batch_id": batch["batch_id"],
                "supplier_id": batch["supplier_id"],
                "machining_ts": production_timestamp(rng, prod_date, idx, part_count),
            }
        )
    part_plan = pd.DataFrame(part_rows)
    part_plan["machining_ts"] = pd.to_datetime(part_plan["machining_ts"])

    return SimulationContext(
        production_date=prod_date,
        part_plan=part_plan,
        batch_plan=batch_plan,
        seed=base_seed,
    )


def weighted_machine_bias(machine_id: str) -> float:
    """Represent known machine tendencies seen in real machining cells."""

    return {
        "CNC-02": -0.15,
        "CNC-05": 0.10,
        "CNC-07": 0.35,
        "CNC-08": -0.25,
    }.get(machine_id, 0.0)


def batch_deviation_batches(batch_ids: Iterable[str], rng: np.random.Generator) -> set[str]:
    """Select a small number of batches likely to be material outliers."""

    unique_batches = sorted(set(batch_ids))
    if not unique_batches:
        return set()
    outlier_count = max(1, int(round(len(unique_batches) * 0.12)))
    return set(rng.choice(unique_batches, size=outlier_count, replace=False))
