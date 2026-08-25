from __future__ import annotations

import pandas as pd

from limitiq.behavioral import synthetic_behavioral_profiles
from limitiq.robustness import behavioral_support_flags, development_benchmark, support_bounds


def test_support_flags_route_multiple_out_of_range_features() -> None:
    raw = synthetic_behavioral_profiles(60)
    bounds = support_bounds(raw)
    extreme = raw.iloc[[0]].copy()
    extreme[[f"BILL_AMT{i}" for i in range(1, 7)]] = [[float(extreme["LIMIT_BAL"].iloc[0]) * 2] * 6]
    flags = behavioral_support_flags(extreme, bounds, minimum_breaches=2)
    assert bool(flags.iloc[0]["outside_model_support"])
    assert flags.iloc[0]["support_breach_count"] >= 2


def test_development_benchmark_returns_calibration_evidence() -> None:
    raw = synthetic_behavioral_profiles(240).reset_index(drop=True)
    target = pd.Series(([0, 1] * 120), dtype=int)
    report = development_benchmark(raw, target, folds=2, iterations=5)
    assert set(report["candidates"]) == {
        "Logistic + sigmoid",
        "HGB + sigmoid",
        "HGB + isotonic",
        "Monotonic HGB + sigmoid",
    }
    assert report["development_preference"] in report["candidates"]
    assert all("calibration_slope" in evidence for evidence in report["candidates"].values())
