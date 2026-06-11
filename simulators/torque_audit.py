"""Synthetic bolted-joint torque audit generator."""

from __future__ import annotations

import numpy as np
import pandas as pd

from simulators.common import TORQUE_SPECS, SimulationContext, daily_seed


def generate_torque_audits(context: SimulationContext) -> pd.DataFrame:
    """Generate torque and angle audit data for critical bolted joints."""

    rng = np.random.default_rng(daily_seed(context.production_date, salt=303))
    rows = []

    for part in context.part_plan.itertuples(index=False):
        audit_ts = part.machining_ts + pd.to_timedelta(int(rng.integers(2, 6)), unit="h")
        shift_b_coolant_effect = 0.0
        if part.machine_id == "CNC-07" and part.shift == "B":
            shift_b_coolant_effect = -1.5

        for spec in TORQUE_SPECS:
            target_torque = float(spec["target_torque"])
            target_angle = float(spec["target_angle"])
            tool_bias = -0.8 if part.line_id == "LINE-C" else 0.0
            actual_torque = target_torque + rng.normal(0, target_torque * 0.018) + tool_bias
            actual_torque += shift_b_coolant_effect

            if rng.random() < 0.015:
                actual_torque += rng.choice([-1, 1]) * target_torque * rng.uniform(0.06, 0.11)

            angle = target_angle + rng.normal(0, 2.5) + (actual_torque - target_torque) * 0.45
            torque_low = target_torque * 0.95
            torque_high = target_torque * 1.05
            angle_low = target_angle - 8.0
            angle_high = target_angle + 8.0
            pass_fail = (
                "PASS"
                if torque_low <= actual_torque <= torque_high and angle_low <= angle <= angle_high
                else "FAIL"
            )

            rows.append(
                {
                    "audit_ts": audit_ts,
                    "production_date": part.production_date,
                    "part_id": part.part_id,
                    "joint_id": spec["joint_id"],
                    "target_torque": round(target_torque, 1),
                    "actual_torque": round(float(actual_torque), 2),
                    "angle": round(float(angle), 1),
                    "torque_lower_limit": round(torque_low, 2),
                    "torque_upper_limit": round(torque_high, 2),
                    "angle_lower_limit": round(angle_low, 1),
                    "angle_upper_limit": round(angle_high, 1),
                    "pass_fail": pass_fail,
                }
            )

    return pd.DataFrame(rows)
