from __future__ import annotations

import numpy as np
import pandas as pd

from limitiq.temporal import FEATURES, train_temporal_track


def test_temporal_track_uses_ordered_vintages(tmp_path) -> None:
    rng = np.random.default_rng(42)
    rows = []
    for vintage in (2013, 2014, 2015):
        for index in range(240):
            risk = rng.uniform()
            row = {feature: rng.normal() for feature in FEATURES}
            row.update(
                {
                    "id": f"{vintage}-{index}",
                    "vintage": vintage,
                    "target": int(risk > 0.65),
                    "fico_mean": 800 - risk * 150,
                }
            )
            rows.append(row)
    payload = train_temporal_track(
        pd.DataFrame(rows),
        model_dir=tmp_path / "models",
        report_dir=tmp_path / "reports",
        iterations=20,
    )
    assert payload["split"]["untouched_test"] == 2015
    assert payload["test_metrics"]["rows"] == 240
    assert "Never feeds" in payload["prohibited_use"]
