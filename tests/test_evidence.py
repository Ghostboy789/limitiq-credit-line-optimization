import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from limitiq.evidence import (
    _calibrated,
    _monitoring_baseline,
    _partial_dependence,
    _permutation_importance,
    _vintage_split,
)
from limitiq.multisource import HARMONIZED_FEATURES


def test_vintage_split_partitions_in_time_order() -> None:
    dates = np.arange("2015-01-01", "2020-01-01", dtype="datetime64[D]")
    train, validation, test = _vintage_split(dates)
    assert (train | validation | test).all()
    assert not ((train & validation) | (train & test) | (validation & test)).any()
    assert dates[train].max() < dates[validation].min()
    assert dates[validation].max() < dates[test].min()
    assert train.sum() > test.sum()


def test_variants_fit_and_score_on_synthetic_rows() -> None:
    rng = np.random.default_rng(0)
    frame = pd.DataFrame(rng.random((160, len(HARMONIZED_FEATURES))), columns=HARMONIZED_FEATURES)
    frame["region"] = rng.choice(["asia", "europe", "north_america"], 160)
    y = pd.Series(rng.integers(0, 2, 160))
    for use_region, use_features in ((True, True), (False, True), (True, False)):
        model = _calibrated(use_region, use_features)
        model.fit(frame, y)
        probability = model.predict_proba(frame)[:, 1]
        assert probability.shape == (160,)
        assert ((probability >= 0) & (probability <= 1)).all()


def test_feature_diagnostics_preserve_source_structure() -> None:
    rng = np.random.default_rng(4)
    rows = 240
    frame = pd.DataFrame(rng.random((rows, len(HARMONIZED_FEATURES))), columns=HARMONIZED_FEATURES)
    frame["region"] = np.repeat(["asia", "europe"], rows // 2)
    source = pd.Series(np.repeat(["source_a", "source_b"], rows // 2), index=frame.index)
    y = pd.Series((frame["utilization"] + rng.normal(0, 0.2, rows) > 0.5).astype(int))
    model = _calibrated()
    model.fit(frame, y)
    probability = model.predict_proba(frame)[:, 1]
    importance = _permutation_importance(
        model,
        frame,
        y,
        roc_auc_score(y, probability),
        ["utilization", "region"],
        source,
        repeats=2,
    )
    by_feature = {item["feature"]: item for item in importance}
    assert by_feature["utilization"]["mean_roc_auc_drop"] > 0
    assert abs(by_feature["region"]["mean_roc_auc_drop"]) < 1e-9
    curve = _partial_dependence(model, frame, source, "utilization", points=5)
    assert curve["sources"] == ["source_a", "source_b"]
    assert len(curve["points"]) == 5
    assert all("value" in point and 0 <= point["y"] <= 1 for point in curve["points"])


def test_monitoring_missingness_uses_training_test_cohorts_only() -> None:
    sources = [
        "taiwan_credit",
        "south_german_credit",
        "give_me_some_credit",
        "fico_heloc",
        "lending_club_full",
        "home_credit",
    ]
    payload = {
        "test_rows": 60,
        "per_source": [
            {
                "source": source,
                "accounts": 10,
                "risk_rate": 0.2,
                "mean_score": 0.2,
                "roc_auc": 0.7,
                "gini": 0.4,
                "ks": 0.3,
                "calibration_gap": 0.02,
            }
            for source in sources
        ],
        "missingness": [
            {"source": source, **{column: 0.0 for column in HARMONIZED_FEATURES}}
            for source in sources
        ],
    }
    baseline = _monitoring_baseline(payload)
    assert {item["source"] for item in baseline["missingness"]} == set(sources)
    assert "german_credit" not in {item["source"] for item in baseline["missingness"]}
    assert "illustrative" in baseline["evidence_boundary"].lower()
