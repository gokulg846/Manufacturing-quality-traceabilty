"""Synthetic CNC process parameter generator."""

from __future__ import annotations

import numpy as np
import pandas as pd

from simulators.common import SimulationContext, daily_seed, weighted_machine_bias


def generate_process_parameters(context: SimulationContext) -> pd.DataFrame:
    """Generate one CNC machine-log row per produced part."""

    rng = np.random.default_rng(daily_seed(context.production_date, salt=101))
    rows = []

    for part in context.part_plan.itertuples(index=False):
        machine_bias = weighted_machine_bias(part.machine_id)
        tool_wear_factor = part.sequence_no / max(len(context.part_plan), 1)
        spindle_speed = 10500 + rng.normal(0, 260) + machine_bias * 140
        feed_rate = 620 + rng.normal(0, 35) - machine_bias * 18
        coolant_temp = 27.5 + rng.normal(0, 1.8) + tool_wear_factor * 2.3

        if part.machine_id == "CNC-07" and part.shift == "B":
            coolant_temp += 2.8
            feed_rate += 28
        if part.machine_id == "CNC-08":
            spindle_speed -= 180

        cycle_time = 92 + rng.normal(0, 5) + (620 - feed_rate) * 0.035 + tool_wear_factor * 3

        rows.append(
            {
                "process_ts": part.machining_ts,
                "production_date": part.production_date,
                "part_id": part.part_id,
                "part_model": part.part_model,
                "line_id": part.line_id,
                "shift": part.shift,
                "machine_id": part.machine_id,
                "batch_id": part.batch_id,
                "spindle_speed": round(float(spindle_speed), 0),
                "feed_rate": round(float(feed_rate), 1),
                "coolant_temp": round(float(coolant_temp), 1),
                "cycle_time": round(float(cycle_time), 1),
            }
        )

    return pd.DataFrame(rows)
