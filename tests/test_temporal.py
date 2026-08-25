from __future__ import annotations

import numpy as np
import pandas as pd

from limitiq.temporal import FEATURES, rolling_vintage_evidence, train_temporal_track


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
    assert payload["rolling_windows"][-1]["test"] == 2015
    assert payload["stress_segments"]
    assert "Never feeds" in payload["prohibited_use"]


def test_rolling_vintage_evidence_skips_incomplete_windows() -> None:
    rows = []
    for year in (2012, 2013, 2014):
        for index in range(20):
            rows.append(
                {
                    **{feature: float(index + 1) for feature in FEATURES},
                    "vintage": year,
                    "target": index % 2,
                }
            )
    evidence = rolling_vintage_evidence(pd.DataFrame(rows), iterations=5, minimum_rows=10)
    assert evidence[-1]["test"] == 2014
