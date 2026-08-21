"""Separate 36-month Lending Club vintage-validation track.

This is loan-domain temporal evidence only.  It never feeds the credit-card decision engine.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.frozen import FrozenEstimator
from sklearn.impute import SimpleImputer
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score
from sklearn.pipeline import Pipeline

from limitiq.config import MODEL_DIR, RAW_DIR, REPORT_DIR, SEED
from limitiq.pipeline import _sha256, _write_json

FEATURES = [
    "loan_amnt",
    "annual_inc",
    "dti",
    "delinq_2yrs",
    "fico_mean",
    "inq_last_6mths",
    "open_acc",
    "pub_rec",
    "revol_bal",
    "revol_util",
    "total_acc",
]
USE_COLUMNS = [
    "id",
    "term",
    "issue_d",
    "loan_status",
    "fico_range_low",
    "fico_range_high",
    *[name for name in FEATURES if name != "fico_mean"],
]
ADVERSE = {"Charged Off", "Default"}
BENIGN = {"Fully Paid"}


def prepare_vintages(path: Path, *, max_rows: int = 400_000) -> pd.DataFrame:
    """Read application-time fields and retain seasoned terminal 36-month loans."""
    chunks: list[pd.DataFrame] = []
    for chunk in pd.read_csv(path, usecols=USE_COLUMNS, chunksize=150_000, low_memory=False):
        chunk["issue_date"] = pd.to_datetime(chunk["issue_d"], format="%b-%Y", errors="coerce")
        chunk["term_months"] = pd.to_numeric(
            chunk["term"].astype(str).str.extract(r"(\d+)")[0], errors="coerce"
        )
        chunk = chunk.loc[
            (chunk["term_months"] == 36)
            & (chunk["issue_date"] <= "2015-12-31")
            & chunk["loan_status"].isin(ADVERSE | BENIGN)
        ].copy()
        if chunk.empty:
            continue
        chunk["target"] = chunk["loan_status"].isin(ADVERSE).astype(int)
        chunk["vintage"] = chunk["issue_date"].dt.year.astype(int)
        chunk["fico_mean"] = (
            pd.to_numeric(chunk["fico_range_low"], errors="coerce")
            + pd.to_numeric(chunk["fico_range_high"], errors="coerce")
        ) / 2
        for feature in FEATURES:
            chunk[feature] = pd.to_numeric(chunk[feature], errors="coerce")
        chunks.append(chunk[["id", "vintage", *FEATURES, "target"]])
    if not chunks:
        raise ValueError("No eligible terminal 36-month Lending Club records found")
    frame = pd.concat(chunks, ignore_index=True)
    if len(frame) > max_rows:
        total = len(frame)
        frame = pd.concat(
            [
                group.sample(
                    min(len(group), max(1, round(max_rows * len(group) / total))),
                    random_state=SEED + int(vintage),
                )
                for vintage, group in frame.groupby("vintage", sort=True)
            ],
            ignore_index=True,
        )
    return frame


def _metrics(target: pd.Series, probability: np.ndarray) -> dict[str, float | int]:
    return {
        "rows": int(len(target)),
        "event_rate": float(target.mean()),
        "mean_score": float(probability.mean()),
        "roc_auc": float(roc_auc_score(target, probability)),
        "pr_auc": float(average_precision_score(target, probability)),
        "brier_score": float(brier_score_loss(target, probability)),
        "log_loss": float(log_loss(target, probability, labels=[0, 1])),
    }


def train_temporal_track(
    frame: pd.DataFrame,
    *,
    model_dir: Path = MODEL_DIR,
    report_dir: Path = REPORT_DIR,
    iterations: int = 160,
) -> dict[str, Any]:
    """Train on <=2013, calibrate on 2014 and evaluate once on 2015."""
    train = frame[frame["vintage"] <= 2013]
    validation = frame[frame["vintage"] == 2014]
    test = frame[frame["vintage"] == 2015]
    if min(map(len, (train, validation, test))) < 100 or any(
        cohort["target"].nunique() != 2 for cohort in (train, validation, test)
    ):
        raise ValueError("Temporal track requires both classes and at least 100 rows per period")
    base = Pipeline(
        [
            ("impute", SimpleImputer(strategy="median", add_indicator=True)),
            (
                "model",
                HistGradientBoostingClassifier(
                    max_iter=iterations,
                    max_leaf_nodes=15,
                    learning_rate=0.06,
                    l2_regularization=1.0,
                    random_state=SEED,
                ),
            ),
        ]
    )
    base.fit(train[FEATURES], train["target"])
    model = CalibratedClassifierCV(FrozenEstimator(base), method="sigmoid")
    model.fit(validation[FEATURES], validation["target"])
    test_probability = model.predict_proba(test[FEATURES])[:, 1]
    global_metadata_path = MODEL_DIR / "global_metadata.json"
    source = {}
    if global_metadata_path.exists():
        source = json.loads(global_metadata_path.read_text(encoding="utf-8"))["datasets"][
            "lending_club_full"
        ]
    model_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    model_path = model_dir / "temporal_champion.joblib"
    joblib.dump(model, model_path, compress=3)
    per_vintage = []
    for vintage, cohort in test.groupby("vintage"):
        probability = model.predict_proba(cohort[FEATURES])[:, 1]
        per_vintage.append({"vintage": int(vintage), **_metrics(cohort["target"], probability)})
    payload = {
        "classification": "Separate US installment-loan temporal validation; research only",
        "generated_at": datetime.now(UTC).isoformat(),
        "source": {
            "dataset": source.get("name", "Lending Club accepted loans 2007-2018Q4"),
            "source_url": source.get("source_url"),
            "mirror_url": source.get("mirror_url"),
            "file_sha256": source.get("file_sha256"),
            "terms_status": source.get("license_status"),
        },
        "target_definition": "Terminal charged-off/default outcome for seasoned 36-month loans",
        "horizon_boundary": (
            "Common 36-month contractual term; status timing inside the term is not available and "
            "this is not a credit-card next-month PD"
        ),
        "split": {"train_through": 2013, "validation": 2014, "untouched_test": 2015},
        "rows": {"train": len(train), "validation": len(validation), "test": len(test)},
        "sampling": (
            "Deterministic proportional-by-vintage sample capped by --max-rows after terminal "
            "36-month eligibility filtering"
        ),
        "features": FEATURES,
        "test_metrics": _metrics(test["target"], test_probability),
        "per_vintage_test": per_vintage,
        "model_checksum": _sha256(model_path),
        "prohibited_use": "Never feeds LimitIQ card recommendations or claims India portability",
    }
    payload["model_version"] = f"limitiq-temporal-4.0.0-{payload['model_checksum'][:12]}"
    _write_json(report_dir / "temporal_validation.json", payload)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Build separate Lending Club vintage evidence")
    parser.add_argument("--max-rows", type=int, default=400_000)
    args = parser.parse_args()
    frame = prepare_vintages(RAW_DIR / "lending_club_full.csv", max_rows=args.max_rows)
    print(json.dumps(train_temporal_track(frame), indent=2))


if __name__ == "__main__":
    main()
