"""Synthetic supplier material certificate generator."""

from __future__ import annotations

from datetime import timedelta

import numpy as np
import pandas as pd

from simulators.common import (
    HARDNESS_MAX,
    HARDNESS_MIN,
    TENSILE_MAX,
    TENSILE_MIN,
    SimulationContext,
    batch_deviation_batches,
    daily_seed,
)


def generate_material_certs(context: SimulationContext) -> pd.DataFrame:
    """Generate incoming material certificate rows at supplier batch grain."""

    rng = np.random.default_rng(daily_seed(context.production_date, salt=404))
    deviating_batches = batch_deviation_batches(context.batch_plan["batch_id"], rng)
    rows = []

    for batch in context.batch_plan.itertuples(index=False):
        hardness = rng.normal(205, 8)
        tensile_strength = rng.normal(670, 28)

        if batch.batch_id in deviating_batches:
            if rng.random() < 0.55:
                hardness = rng.choice([rng.uniform(168, 178), rng.uniform(232, 246)])
            else:
                tensile_strength = rng.choice([rng.uniform(540, 575), rng.uniform(770, 815)])

        cert_date = context.production_date - timedelta(days=int(rng.integers(1, 12)))
        material_deviation = (
            hardness < HARDNESS_MIN
            or hardness > HARDNESS_MAX
            or tensile_strength < TENSILE_MIN
            or tensile_strength > TENSILE_MAX
        )

        rows.append(
            {
                "batch_id": batch.batch_id,
                "supplier_id": batch.supplier_id,
                "hardness": round(float(hardness), 1),
                "tensile_strength": round(float(tensile_strength), 1),
                "cert_date": cert_date.isoformat(),
                "hardness_min_spec": HARDNESS_MIN,
                "hardness_max_spec": HARDNESS_MAX,
                "tensile_min_spec": TENSILE_MIN,
                "tensile_max_spec": TENSILE_MAX,
                "material_deviation": bool(material_deviation),
            }
        )

    return pd.DataFrame(rows)
