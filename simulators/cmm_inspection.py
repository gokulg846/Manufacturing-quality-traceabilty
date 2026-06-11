"""Synthetic coordinate measuring machine inspection generator."""

from __future__ import annotations

import numpy as np
import pandas as pd

from simulators.common import DIMENSION_SPECS, SimulationContext, daily_seed, weighted_machine_bias


def generate_cmm_inspections(context: SimulationContext) -> pd.DataFrame:
    """Generate dimensional inspection rows for each part and critical feature."""

    rng = np.random.default_rng(daily_seed(context.production_date, salt=202))
    rows = []
    total_parts = max(len(context.part_plan), 1)

    for part in context.part_plan.itertuples(index=False):
        machine_bias = weighted_machine_bias(part.machine_id)
        tool_wear_factor = part.sequence_no / total_parts
        inspection_ts = part.machining_ts + pd.to_timedelta(int(rng.integers(18, 75)), unit="m")

        for spec in DIMENSION_SPECS:
            tolerance = float(spec["tolerance"])
            sigma = tolerance / 3.8
            drift = machine_bias * tolerance * 0.55 + tool_wear_factor * tolerance * 0.30

            if part.machine_id == "CNC-07" and spec["dimension_name"] in {
                "bore_diameter_mm",
                "bolt_circle_dia_mm",
            }:
                drift += tolerance * 0.72
            if part.machine_id == "CNC-08" and spec["dimension_name"] == "locator_slot_width_mm":
                drift -= tolerance * 0.62

            rare_event = rng.random() < 0.018
            if rare_event:
                drift += rng.choice([-1, 1]) * tolerance * rng.uniform(1.05, 1.65)

            measured_value = float(spec["nominal"]) + drift + rng.normal(0, sigma)
            lower_spec = float(spec["nominal"]) - tolerance
            upper_spec = float(spec["nominal"]) + tolerance
            pass_fail = "PASS" if lower_spec <= measured_value <= upper_spec else "FAIL"

            rows.append(
                {
                    "inspection_ts": inspection_ts,
                    "production_date": part.production_date,
                    "part_id": part.part_id,
                    "dimension_name": spec["dimension_name"],
                    "measured_value": round(measured_value, 4),
                    "nominal": round(float(spec["nominal"]), 4),
                    "tolerance": round(tolerance, 4),
                    "lower_spec_limit": round(lower_spec, 4),
                    "upper_spec_limit": round(upper_spec, 4),
                    "pass_fail": pass_fail,
                }
            )

    return pd.DataFrame(rows)
