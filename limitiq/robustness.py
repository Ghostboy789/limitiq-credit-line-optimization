"""Development-only calibration/challenger evidence and inference support checks."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from limitiq.behavioral import (
    BEHAVIORAL_HGB_ITERATIONS,
    CANDIDATE_MODEL_PATH,
    _paired_bootstrap,
    boosting_configuration,
    load_behavioral_source,
)
from limitiq.config import REPORT_DIR, SEED
from limitiq.features import FEATURE_NAMES, FeatureBuilder, engineer_features
from limitiq.splits import frozen_split

REPORT_PATH = REPORT_DIR / "model_robustness.json"
MONOTONIC_CONSTRAINTS = [
    0,  # limit_bal
    1,
    1,
    1,
    1,
    -1,
    -1,
    -1,
    1,
    1,
    1,
    1,
    -1,
    0,
    0,
    1,
    0,
]


def development_partition() -> tuple[pd.DataFrame, pd.Series, dict[str, Any]]:
    """Reconstruct the original 80% development partition without evaluating test labels."""
    features, target, provenance = load_behavioral_source()
    (train_x, train_y), (validation_x, validation_y), (_test_x, _test_y) = frozen_split(
        features, target
    )
    return pd.concat([train_x, validation_x]), pd.concat([train_y, validation_y]), provenance


def _candidates(iterations: int) -> dict[str, CalibratedClassifierCV]:
    logistic = Pipeline(
        [
            ("behavior", FeatureBuilder()),
            ("scale", StandardScaler()),
            ("model", LogisticRegression(C=0.5, max_iter=2_000, random_state=SEED)),
        ]
    )

    def boosted(monotonic: bool = False) -> Pipeline:
        return Pipeline(
            [
                ("behavior", FeatureBuilder()),
                (
                    "model",
                    HistGradientBoostingClassifier(
                        learning_rate=0.06,
                        max_iter=iterations,
                        max_leaf_nodes=15,
                        l2_regularization=1.0,
                        monotonic_cst=MONOTONIC_CONSTRAINTS if monotonic else None,
                        random_state=SEED,
                    ),
                ),
            ]
        )

    return {
        "Logistic + sigmoid": CalibratedClassifierCV(logistic, method="sigmoid", cv=3),
        "HGB + sigmoid": CalibratedClassifierCV(boosted(), method="sigmoid", cv=3),
        "HGB + isotonic": CalibratedClassifierCV(boosted(), method="isotonic", cv=3),
        "Monotonic HGB + sigmoid": CalibratedClassifierCV(
            boosted(monotonic=True), method="sigmoid", cv=3
        ),
    }


def _calibration_diagnostics(truth: np.ndarray, probability: np.ndarray) -> dict[str, float]:
    clipped = np.clip(probability, 1e-6, 1 - 1e-6)
    logit = np.log(clipped / (1 - clipped)).reshape(-1, 1)
    recalibration = LogisticRegression(penalty=None, max_iter=1_000).fit(logit, truth)
    bins = pd.qcut(probability, q=min(10, len(np.unique(probability))), duplicates="drop")
    grouped = pd.DataFrame({"truth": truth, "probability": probability, "bin": bins}).groupby(
        "bin", observed=True
    )
    gap = sum(
        len(group) * abs(float(group["truth"].mean() - group["probability"].mean()))
        for _, group in grouped
    ) / len(truth)
    return {
        "calibration_intercept": float(recalibration.intercept_[0]),
        "calibration_slope": float(recalibration.coef_[0, 0]),
        "expected_calibration_error": float(gap),
    }


def development_benchmark(
    features: pd.DataFrame,
    target: pd.Series,
    *,
    folds: int = 3,
    iterations: int = BEHAVIORAL_HGB_ITERATIONS,
    bootstrap_repeats: int = 500,
) -> dict[str, Any]:
    """Compare a frozen, small candidate set with out-of-fold development predictions."""
    if len(features) < 200 or target.nunique() != 2:
        raise ValueError("Robustness benchmark requires at least 200 rows and both outcomes")
    splitter = StratifiedKFold(n_splits=folds, shuffle=True, random_state=SEED + 4_300)
    split_indexes = list(splitter.split(features, target))
    truth = target.to_numpy(dtype=int)
    probabilities: dict[str, np.ndarray] = {}
    candidates = _candidates(iterations)
    evidence: dict[str, Any] = {}
    for name, estimator in candidates.items():
        probability = np.zeros(len(target), dtype=float)
        fold_rows = []
        for fold, (train_index, validation_index) in enumerate(split_indexes, start=1):
            model = clone(estimator)
            model.fit(features.iloc[train_index], target.iloc[train_index])
            score = model.predict_proba(features.iloc[validation_index])[:, 1]
            probability[validation_index] = score
            fold_rows.append(
                {
                    "fold": fold,
                    "roc_auc": float(roc_auc_score(target.iloc[validation_index], score)),
                    "brier_score": float(brier_score_loss(target.iloc[validation_index], score)),
                }
            )
        probabilities[name] = probability
        evidence[name] = {
            "roc_auc": float(roc_auc_score(truth, probability)),
            "pr_auc": float(average_precision_score(truth, probability)),
            "brier_score": float(brier_score_loss(truth, probability)),
            "log_loss": float(log_loss(truth, probability)),
            **_calibration_diagnostics(truth, probability),
            "folds": fold_rows,
        }
    best_auc = max(item["roc_auc"] for item in evidence.values())
    eligible = {name: item for name, item in evidence.items() if item["roc_auc"] >= best_auc - 0.02}
    preferred = min(eligible, key=lambda name: (eligible[name]["brier_score"], name))
    reference = "HGB + sigmoid"
    candidate = "HGB + isotonic"
    paired = _paired_bootstrap(
        target,
        probabilities[candidate],
        probabilities[reference],
        bootstrap_repeats,
    )
    loss_differences = {}
    for metric in ("brier_score", "log_loss"):
        values = paired[metric]
        loss_differences[metric] = {
            "candidate_minus_reference": values["candidate_minus_v3"],
            "lower_95": values["lower_95"],
            "upper_95": values["upper_95"],
            "repeats": values["repeats"],
            "method": values["method"],
            "higher_is_better": values["higher_is_better"],
        }
    interval_rule_met = all(values["upper_95"] < 0 for values in loss_differences.values())
    return {
        "selection_rule": "Lowest out-of-fold Brier score within 0.02 ROC-AUC of the best",
        "calibrator_decision_rule": (
            "Adopt a new calibrator only if its paired 95% candidate-minus-reference "
            "Brier and log-loss intervals both exclude zero in its favor"
        ),
        "candidates": evidence,
        "development_preference": preferred,
        "paired_calibrator_comparison": {
            "candidate": candidate,
            "reference": reference,
            "metrics": loss_differences,
            "development_interval_rule_met": interval_rule_met,
        },
    }


def support_bounds(features: pd.DataFrame) -> dict[str, dict[str, float]]:
    engineered = engineer_features(features, clip=False)
    return {
        name: {
            "lower": float(engineered[name].quantile(0.005)),
            "upper": float(engineered[name].quantile(0.995)),
        }
        for name in FEATURE_NAMES
    }


def behavioral_support_flags(
    frame: pd.DataFrame,
    bounds: dict[str, dict[str, float]],
    *,
    minimum_breaches: int = 3,
) -> pd.DataFrame:
    """Flag histories outside multiple development-support bounds for manual review."""
    engineered = engineer_features(frame, clip=False)
    breached = pd.DataFrame(
        {
            name: (engineered[name] < limit["lower"]) | (engineered[name] > limit["upper"])
            for name, limit in bounds.items()
        },
        index=engineered.index,
    )
    return pd.DataFrame(
        {
            "support_breach_count": breached.sum(axis=1).astype(int),
            "outside_model_support": breached.sum(axis=1) >= minimum_breaches,
            "support_breaches": breached.apply(
                lambda row: "|".join(row.index[row].tolist()), axis=1
            ),
        },
        index=engineered.index,
    )


def build_report(*, folds: int = 3) -> dict[str, Any]:
    features, target, provenance = development_partition()
    payload = {
        "classification": "Development-only robustness study; frozen v4 test was not reread",
        "generated_at": datetime.now(UTC).isoformat(),
        "development_rows": len(features),
        "source": provenance,
        "boosting_configuration": {
            "iterations": BEHAVIORAL_HGB_ITERATIONS,
            "deployed_iterations": BEHAVIORAL_HGB_ITERATIONS,
            "matches_deployed_configuration": True,
            **boosting_configuration(joblib.load(CANDIDATE_MODEL_PATH)),  # noqa: S301
        },
        **development_benchmark(
            features.reset_index(drop=True),
            target.reset_index(drop=True),
            folds=folds,
            iterations=BEHAVIORAL_HGB_ITERATIONS,
        ),
        "support_bounds": support_bounds(features),
        "promotion_status": "No promotion; a new untouched or current-vintage external gate is required",
        "limitations": [
            "All candidates use the same 2005 Taiwan development population.",
            "Out-of-fold evidence supports engineering choices but is not new external validation.",
            "Support-bound flags are conservative routing controls, not evidence of default.",
            "Support bounds use unclipped engineered values; estimator inputs remain clipped.",
        ],
    }
    REPORT_PATH.write_text(
        json.dumps(payload, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Build development-only robustness evidence")
    parser.add_argument("--folds", type=int, default=3)
    args = parser.parse_args()
    print(json.dumps(build_report(folds=args.folds), indent=2))


if __name__ == "__main__":
    main()
