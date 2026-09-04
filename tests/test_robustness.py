from __future__ import annotations

import hashlib

import joblib
import numpy as np
import pandas as pd

from limitiq.behavioral import (
    BEHAVIORAL_HGB_ITERATIONS,
    CANDIDATE_MODEL_PATH,
    synthetic_behavioral_profiles,
)
from limitiq.features import (
    BILL_COLUMNS,
    PAY_COLUMNS,
    PAYMENT_COLUMNS,
    TAIWAN_MODEL_INPUT_COLUMNS,
    engineer_features,
)
from limitiq.robustness import behavioral_support_flags, development_benchmark, support_bounds
from limitiq.splits import frozen_split


def _index_digest(index: pd.Index) -> str:
    return hashlib.sha256(",".join(map(str, index)).encode()).hexdigest()


def test_frozen_split_is_exact_sized_and_test_disjoint() -> None:
    features = pd.DataFrame({"row": np.arange(30_000)})
    target = pd.Series(np.tile([0, 1], 15_000))

    (train_x, _), (validation_x, _), (test_x, _) = frozen_split(features, target)
    development_index = set(train_x.index) | set(validation_x.index)

    assert (len(train_x), len(validation_x), len(test_x)) == (18_000, 6_000, 6_000)
    assert len(development_index) == 24_000
    assert development_index.isdisjoint(test_x.index)
    assert (
        _index_digest(train_x.index),
        _index_digest(validation_x.index),
        _index_digest(test_x.index),
    ) == (
        "86f84bdae2cde9c8f290dea5d1a6f569ad8f9ddc427d0a863d03444311bc216f",
        "1a6d5df5a0ae36164081ff2e0c5c3406a670421a7e4a8fce0eb6e89761b0b8f4",
        "9dc0129a23aa9a13b1e3b986e09fefa41cadc12f587131e257ddbc4edd5fe9a6",
    )


def test_support_flags_route_multiple_out_of_range_features() -> None:
    raw = synthetic_behavioral_profiles(60)
    bounds = support_bounds(raw)
    extreme = raw.iloc[[0]].copy()
    extreme[[f"BILL_AMT{i}" for i in range(1, 7)]] = [[float(extreme["LIMIT_BAL"].iloc[0]) * 2] * 6]
    flags = behavioral_support_flags(extreme, bounds, minimum_breaches=2)
    assert bool(flags.iloc[0]["outside_model_support"])
    assert flags.iloc[0]["support_breach_count"] >= 2


def test_support_flags_use_preclip_engineered_values() -> None:
    raw = pd.DataFrame({"LIMIT_BAL": np.arange(1_000, 1_100, dtype=float)})
    for name in PAY_COLUMNS:
        raw[name] = -1
    for name in BILL_COLUMNS:
        raw[name] = raw["LIMIT_BAL"] / 2
    for name in PAYMENT_COLUMNS:
        raw[name] = raw["LIMIT_BAL"] / 4

    extreme = raw.iloc[[0]].copy()
    amount_columns = ["LIMIT_BAL", *BILL_COLUMNS, *PAYMENT_COLUMNS]
    extreme[amount_columns] *= 1_000

    pd.testing.assert_frame_equal(
        engineer_features(extreme),
        engineer_features(raw.iloc[[0]]),
    )
    flags = behavioral_support_flags(extreme, support_bounds(raw), minimum_breaches=1)
    assert bool(flags.iloc[0]["outside_model_support"])
    assert flags.iloc[0]["support_breaches"] == "limit_bal"


def test_deployed_iterations_and_in_range_predictions_are_unchanged() -> None:
    model = joblib.load(CANDIDATE_MODEL_PATH)
    assert {
        calibrated.estimator.named_steps["model"].max_iter
        for calibrated in model.calibrated_classifiers_
    } == {BEHAVIORAL_HGB_ITERATIONS}

    raw = synthetic_behavioral_profiles(5)[TAIWAN_MODEL_INPUT_COLUMNS]
    expected = np.asarray(
        [
            0.16702904464121768,
            0.3813832588883867,
            0.09331231097274707,
            0.15188978572209078,
            0.10343865528799094,
        ]
    )
    np.testing.assert_allclose(
        model.predict_proba(raw)[:, 1], expected, rtol=0, atol=np.finfo(np.float64).eps
    )


def test_development_benchmark_returns_calibration_evidence() -> None:
    raw = synthetic_behavioral_profiles(240).reset_index(drop=True)
    target = pd.Series(([0, 1] * 120), dtype=int)
    report = development_benchmark(raw, target, folds=2, iterations=5, bootstrap_repeats=20)
    assert set(report["candidates"]) == {
        "Logistic + sigmoid",
        "HGB + sigmoid",
        "HGB + isotonic",
        "Monotonic HGB + sigmoid",
    }
    assert report["development_preference"] in report["candidates"]
    assert all("calibration_slope" in evidence for evidence in report["candidates"].values())
    comparison = report["paired_calibrator_comparison"]
    assert comparison["candidate"] == "HGB + isotonic"
    assert comparison["reference"] == "HGB + sigmoid"
    assert set(comparison["metrics"]) == {"brier_score", "log_loss"}
    assert comparison["development_interval_rule_met"] is all(
        values["upper_95"] < 0 for values in comparison["metrics"].values()
    )
    assert report["calibrator_decision_rule"].startswith("Adopt a new calibrator only if")
    assert all(values["repeats"] == 20 for values in comparison["metrics"].values())
