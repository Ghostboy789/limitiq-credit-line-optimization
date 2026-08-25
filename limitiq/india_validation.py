"""Forward validation for governed Indian account-month outcomes.

No public substitute is generated: this runner operates only on an operator-supplied,
tokenized file that satisfies the India data contract.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.frozen import FrozenEstimator
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from limitiq.config import SEED
from limitiq.india import INDIA_REQUIRED_FIELDS, validate_india_contract
from limitiq.pipeline import _metrics, _threshold

TARGET = "default_within_12m"
OUTCOME_DATE = "outcome_end_date"
MODEL_FEATURES = [
    "bureau_dpd_30_12m",
    "bureau_dpd_90_24m",
    "open_trades",
    "foir_proxy",
    "utilization",
    "aggregate_credit_limit_inr",
    "aggregate_limit_to_annual_income",
    "statement_months",
]
VALIDATION_REQUIRED_FIELDS = (*INDIA_REQUIRED_FIELDS, OUTCOME_DATE, TARGET)


def validate_account_months(frame: pd.DataFrame, *, minimum_rows: int = 1_000) -> pd.DataFrame:
    """Validate and derive a model-ready, identifier-free account-month table."""
    missing = [name for name in VALIDATION_REQUIRED_FIELDS if name not in frame]
    if missing:
        raise ValueError(f"India validation data missing columns: {', '.join(missing)}")
    if len(frame) < minimum_rows:
        raise ValueError(f"India validation requires at least {minimum_rows:,} account-months")
    if frame[["customer_reference", "as_of_date"]].duplicated().any():
        raise ValueError("India validation customer/month pairs must be unique")
    target = pd.to_numeric(frame[TARGET], errors="coerce")
    if target.isna().any() or not target.isin([0, 1]).all():
        raise ValueError(f"{TARGET} must contain only 0 and 1")

    derived = pd.DataFrame([validate_india_contract(row) for row in frame.to_dict("records")])
    snapshot = pd.to_datetime(frame["as_of_date"], utc=True, errors="coerce")
    outcome = pd.to_datetime(frame[OUTCOME_DATE], utc=True, errors="coerce")
    if snapshot.isna().any() or outcome.isna().any():
        raise ValueError("India validation dates must be valid timezone-aware timestamps")
    if ((outcome - snapshot).dt.days < 365).any():
        raise ValueError("Every India validation outcome window must cover at least 365 days")
    model_ready = frame[
        ["bureau_dpd_30_12m", "bureau_dpd_90_24m", "open_trades", "statement_months"]
    ].apply(pd.to_numeric, errors="raise")
    model_ready = model_ready.join(
        derived[
            [
                "foir_proxy",
                "utilization",
                "aggregate_credit_limit_inr",
                "aggregate_limit_to_annual_income",
            ]
        ]
    )
    model_ready["customer_reference"] = frame["customer_reference"].astype(str).to_numpy()
    model_ready["snapshot_month"] = snapshot.dt.tz_convert("Asia/Kolkata").dt.strftime("%Y-%m")
    model_ready[TARGET] = target.astype(int).to_numpy()
    return model_ready


def forward_splits(
    frame: pd.DataFrame, *, strict_account_holdout: bool = True
) -> dict[str, pd.DataFrame]:
    """Create chronological train/calibration/selection/test slices."""
    months = sorted(frame["snapshot_month"].unique())
    if len(months) < 4:
        raise ValueError("India forward validation requires at least four snapshot months")
    split = {
        "train": frame[frame["snapshot_month"].isin(months[:-3])].copy(),
        "calibration": frame[frame["snapshot_month"] == months[-3]].copy(),
        "selection": frame[frame["snapshot_month"] == months[-2]].copy(),
        "test": frame[frame["snapshot_month"] == months[-1]].copy(),
    }
    if strict_account_holdout:
        held_out = set(pd.concat([split["selection"], split["test"]])["customer_reference"])
        split["train"] = split["train"][~split["train"]["customer_reference"].isin(held_out)]
        split["calibration"] = split["calibration"][
            ~split["calibration"]["customer_reference"].isin(held_out)
        ]
    for name, part in split.items():
        if part.empty or part[TARGET].nunique() != 2:
            raise ValueError(f"India {name} slice must be non-empty and contain both outcomes")
    return split


def _candidates() -> dict[str, Any]:
    impute = ("impute", SimpleImputer(strategy="median"))
    return {
        "Regularized logistic regression": Pipeline(
            [
                impute,
                ("scale", StandardScaler()),
                ("model", LogisticRegression(C=0.5, max_iter=2_000, random_state=SEED)),
            ]
        ),
        "Histogram gradient boosting": Pipeline(
            [
                impute,
                (
                    "model",
                    HistGradientBoostingClassifier(
                        learning_rate=0.06,
                        max_iter=180,
                        max_leaf_nodes=15,
                        l2_regularization=1.0,
                        random_state=SEED,
                    ),
                ),
            ]
        ),
    }


def train_forward_validation(
    frame: pd.DataFrame, *, output_dir: Path | None = None
) -> dict[str, Any]:
    """Select on a forward slice and read the final month once."""
    splits = forward_splits(frame)
    fitted: dict[str, Any] = {}
    selection_metrics: dict[str, Any] = {}
    thresholds: dict[str, float] = {}
    for name, base in _candidates().items():
        base.fit(splits["train"][MODEL_FEATURES], splits["train"][TARGET])
        calibrated = CalibratedClassifierCV(FrozenEstimator(base), method="sigmoid")
        calibrated.fit(splits["calibration"][MODEL_FEATURES], splits["calibration"][TARGET])
        probability = calibrated.predict_proba(splits["selection"][MODEL_FEATURES])[:, 1]
        threshold = _threshold(splits["selection"][TARGET], probability)
        selection_metrics[name] = _metrics(splits["selection"][TARGET], probability, threshold)
        thresholds[name] = threshold
        fitted[name] = calibrated
    best_auc = max(item["roc_auc"] for item in selection_metrics.values())
    eligible = {
        name: item for name, item in selection_metrics.items() if item["roc_auc"] >= best_auc - 0.02
    }
    champion_name = min(eligible, key=lambda name: (eligible[name]["brier_score"], name))
    champion = fitted[champion_name]
    test_probability = champion.predict_proba(splits["test"][MODEL_FEATURES])[:, 1]
    test_metrics = _metrics(splits["test"][TARGET], test_probability, thresholds[champion_name])
    source_bytes = frame.to_csv(index=False, lineterminator="\n").encode()
    payload: dict[str, Any] = {
        "classification": "Operator-supplied Indian account-month forward validation",
        "generated_at": datetime.now(UTC).isoformat(),
        "target_definition": "Default within the complete 12 months after each snapshot",
        "split_method": "Chronological train/calibration/selection/test with held-out accounts",
        "split_months": {
            name: sorted(part["snapshot_month"].unique().tolist()) for name, part in splits.items()
        },
        "split_rows": {name: len(part) for name, part in splits.items()},
        "champion": champion_name,
        "selection_metrics": selection_metrics,
        "untouched_final_month_metrics": test_metrics,
        "selected_threshold": thresholds[champion_name],
        "model_features": MODEL_FEATURES,
        "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "limitations": [
            "This validates only the population, period and outcome definition supplied by the operator.",
            "Legal, compliance and independent model-validation approval remain external gates.",
            "A limit offer still requires explicit customer acceptance before activation.",
        ],
    }
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        model_path = output_dir / "india_forward_champion.joblib"
        report_path = output_dir / "india_forward_validation.json"
        joblib.dump(champion, model_path, compress=3)
        payload["model_sha256"] = hashlib.sha256(model_path.read_bytes()).hexdigest()
        report_path.write_text(
            json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8"
        )
    return payload


def readiness_report() -> dict[str, Any]:
    return {
        "classification": "Blocked deployment gate; no representative Indian outcomes supplied",
        "generated_at": datetime.now(UTC).isoformat(),
        "required_contract": list(VALIDATION_REQUIRED_FIELDS),
        "implemented_checks": [
            "Complete 12-month outcomes",
            "Chronological four-way split",
            "Account-disjoint selection and test holdout",
            "Dedicated calibration window",
            "Logistic baseline and histogram-gradient challenger",
            "Checksum-bound model and report outputs",
        ],
        "status": "awaiting_governed_operator_data",
        "prohibited_claim": "The public Taiwan or multi-source benchmarks are not Indian validation.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run governed India forward validation")
    parser.add_argument("input", type=Path, nargs="?", help="Tokenized account-month CSV")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--readiness-output", type=Path)
    args = parser.parse_args()
    if args.readiness_output:
        args.readiness_output.parent.mkdir(parents=True, exist_ok=True)
        args.readiness_output.write_text(
            json.dumps(readiness_report(), indent=2, allow_nan=False) + "\n", encoding="utf-8"
        )
        print(args.readiness_output)
        return
    if not args.input or not args.output_dir:
        parser.error("Provide input and --output-dir, or use --readiness-output")
    raw = pd.read_csv(args.input)
    clean = validate_account_months(raw)
    print(json.dumps(train_forward_validation(clean, output_dir=args.output_dir), indent=2))


if __name__ == "__main__":
    main()
