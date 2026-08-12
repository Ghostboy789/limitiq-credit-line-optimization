from __future__ import annotations

import argparse
import hashlib
import json
import math
import urllib.request
import zipfile
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    log_loss,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from limitiq.config import (
    CURRENCY_RATE_DATE,
    CURRENCY_RATE_SOURCES,
    DATASET_DOI,
    DATASET_LICENSE,
    DATASET_PAGE,
    DATASET_URL,
    DISPLAY_CURRENCY,
    MODEL_DIR,
    PROCESSED_DIR,
    RAW_DIR,
    REPORT_DIR,
    SEED,
    SOURCE_CURRENCY,
    TWD_TO_INR,
    PolicyAssumptions,
)
from limitiq.features import (
    BILL_COLUMNS,
    DEMOGRAPHIC_COLUMNS,
    FEATURE_NAMES,
    ID_COLUMN,
    PAYMENT_COLUMNS,
    TARGET,
    FeatureBuilder,
    clean_source,
    engineer_features,
)
from limitiq.features import (
    TAIWAN_MODEL_INPUT_COLUMNS as MODEL_INPUT_COLUMNS,
)
from limitiq.optimizer import portfolio_sensitivity, recommend_portfolio, summarize_portfolio


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_dataset(force: bool = False) -> Path:
    """Download the official UCI ZIP and safely extract its single XLS data file."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    output = RAW_DIR / "default_of_credit_card_clients.xls"
    if output.exists() and not force:
        return output
    source = urlparse(DATASET_URL)
    if source.scheme != "https" or source.hostname != "archive.ics.uci.edu":
        raise ValueError("Dataset source must be the approved UCI HTTPS host")
    request = urllib.request.Request(  # noqa: S310 — constant official HTTPS source.
        DATASET_URL, headers={"User-Agent": "LimitIQ/1.0"}
    )
    with urllib.request.urlopen(request, timeout=60) as response:  # nosec B310  # noqa: S310
        payload = response.read(10 * 1024 * 1024 + 1)
    if len(payload) > 10 * 1024 * 1024:
        raise ValueError("Dataset archive exceeds expected 10 MB safety limit")
    with zipfile.ZipFile(BytesIO(payload)) as archive:
        members = [name for name in archive.namelist() if name.lower().endswith(".xls")]
        if len(members) != 1 or Path(members[0]).name != members[0]:
            raise ValueError("Unexpected or unsafe UCI archive structure")
        data = archive.read(members[0])
    output.write_bytes(data)
    _write_json(
        RAW_DIR / "source_metadata.json",
        {
            "dataset": "Default of Credit Card Clients",
            "publisher": "I-Cheng Yeh / UCI Machine Learning Repository",
            "source_page": DATASET_PAGE,
            "download_url": DATASET_URL,
            "doi": DATASET_DOI,
            "license": DATASET_LICENSE,
            "retrieved_at": datetime.now(UTC).isoformat(),
            "file_sha256": _sha256(output),
        },
    )
    return output


def load_source(path: Path | None = None) -> tuple[pd.DataFrame, dict[str, Any]]:
    path = path or download_dataset()
    raw = pd.read_excel(path, sheet_name="Data", header=1)
    clean, quality = clean_source(raw)
    monetary_columns = ["LIMIT_BAL", *BILL_COLUMNS, *PAYMENT_COLUMNS]
    clean[monetary_columns] = clean[monetary_columns] * TWD_TO_INR
    quality.update(
        {
            "dataset_sha256": _sha256(path),
            "dataset_version": f"uci-350-{_sha256(path)[:12]}-inr297",
            "source": DATASET_PAGE,
            "license": DATASET_LICENSE,
            "source_currency": SOURCE_CURRENCY,
            "model_currency": DISPLAY_CURRENCY,
            "twd_to_inr": TWD_TO_INR,
            "currency_rate_date": CURRENCY_RATE_DATE,
            "currency_rate_sources": list(CURRENCY_RATE_SOURCES),
            "currency_note": (
                "Observed TWD monetary fields are deterministically converted to INR before "
                "modelling and simulation; the conversion is presentation localization, not "
                "evidence about Indian borrowers."
            ),
        }
    )
    return clean, quality


def build_data() -> tuple[pd.DataFrame, dict[str, Any]]:
    frame, quality = load_source()
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    frame.to_csv(PROCESSED_DIR / "clean_source.csv", index=False)
    engineered = engineer_features(frame[MODEL_INPUT_COLUMNS])
    eda = {
        "classification": "Observed behavior with fixed TWD-to-INR currency conversion",
        "accounts": len(frame),
        "default_rate": float(frame[TARGET].mean()),
        "limit": {
            "mean": float(frame["LIMIT_BAL"].mean()),
            "median": float(frame["LIMIT_BAL"].median()),
            "p10": float(frame["LIMIT_BAL"].quantile(0.1)),
            "p90": float(frame["LIMIT_BAL"].quantile(0.9)),
        },
        "current_utilization": {
            "mean": float(engineered["current_utilization"].mean()),
            "median": float(engineered["current_utilization"].median()),
            "p90": float(engineered["current_utilization"].quantile(0.9)),
        },
        "delinquent_accounts": int((engineered["delinquent_month_count"] > 0).sum()),
        "target_by_sex": {
            str(key): float(value) for key, value in frame.groupby("SEX")[TARGET].mean().items()
        },
        "notes": [
            "Demographic attributes are observed but excluded from all model and optimizer inputs.",
            "Source TWD monetary fields are deterministically converted to INR at 2.97 INR per TWD.",
            "Negative bill amounts can represent credits and are clipped to zero only for behavioral ratios.",
            "No limit-increase response or economics outcome is present in the source dataset.",
        ],
    }
    _write_json(REPORT_DIR / "data_quality.json", quality)
    _write_json(REPORT_DIR / "eda.json", eda)
    return frame, quality


def _model_candidates() -> dict[str, CalibratedClassifierCV]:
    baseline = Pipeline(
        [
            ("features", FeatureBuilder()),
            ("scale", StandardScaler()),
            (
                "model",
                LogisticRegression(
                    C=0.5,
                    max_iter=2_000,
                    random_state=SEED,
                ),
            ),
        ]
    )
    challenger = Pipeline(
        [
            ("features", FeatureBuilder()),
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
    )
    return {
        "Regularized logistic regression": CalibratedClassifierCV(baseline, method="sigmoid", cv=3),
        "Histogram gradient boosting": CalibratedClassifierCV(challenger, method="sigmoid", cv=3),
    }


def _threshold(y_true: pd.Series, probability: np.ndarray) -> float:
    candidates = np.linspace(0.05, 0.60, 112)
    costs = []
    for threshold in candidates:
        prediction = probability >= threshold
        false_positive = int(((prediction == 1) & (y_true.to_numpy() == 0)).sum())
        false_negative = int(((prediction == 0) & (y_true.to_numpy() == 1)).sum())
        costs.append((5 * false_negative + false_positive, float(threshold)))
    return min(costs)[1]


def _metrics(y_true: pd.Series, probability: np.ndarray, threshold: float) -> dict[str, Any]:
    prediction = (probability >= threshold).astype(int)
    fraction_positive, mean_predicted = calibration_curve(
        y_true, probability, n_bins=10, strategy="quantile"
    )
    matrix = confusion_matrix(y_true, prediction).tolist()
    return {
        "roc_auc": float(roc_auc_score(y_true, probability)),
        "pr_auc": float(average_precision_score(y_true, probability)),
        "brier_score": float(brier_score_loss(y_true, probability)),
        "log_loss": float(log_loss(y_true, probability)),
        "precision": float(precision_score(y_true, prediction, zero_division=0)),
        "recall": float(recall_score(y_true, prediction, zero_division=0)),
        "f1": float(f1_score(y_true, prediction, zero_division=0)),
        "threshold": float(threshold),
        "confusion_matrix": matrix,
        "calibration": [
            {"mean_predicted": float(x), "observed_rate": float(y)}
            for x, y in zip(mean_predicted, fraction_positive, strict=True)
        ],
    }


def _risk_table(y_true: pd.Series, probability: np.ndarray) -> list[dict[str, Any]]:
    bands = pd.cut(
        probability,
        bins=[-math.inf, 0.05, 0.15, 0.30, math.inf],
        labels=["Low", "Moderate", "High", "Very high"],
        right=False,
    )
    table = pd.DataFrame({"band": bands, "target": y_true.to_numpy(), "pd": probability})
    result = []
    for band, group in table.groupby("band", observed=False):
        result.append(
            {
                "band": str(band),
                "accounts": int(len(group)),
                "mean_pd": float(group["pd"].mean()) if len(group) else 0.0,
                "observed_default_rate": float(group["target"].mean()) if len(group) else 0.0,
            }
        )
    return result


def _segment_metrics(
    audit: pd.DataFrame, y_true: pd.Series, probability: np.ndarray, threshold: float
) -> list[dict[str, Any]]:
    work = audit[["SEX", "AGE"]].copy()
    work["target"] = y_true.to_numpy()
    work["pd"] = probability
    work["prediction"] = probability >= threshold
    work["age_band"] = pd.cut(
        work["AGE"], [0, 29, 39, 49, 59, math.inf], labels=["<30", "30-39", "40-49", "50-59", "60+"]
    )
    rows = []
    for dimension, labels in (
        ("sex", work["SEX"].map({1: "Group 1", 2: "Group 2"})),
        ("age_band", work["age_band"]),
    ):
        for label, group in work.groupby(labels, observed=False):
            if not len(group):
                continue
            positives = group["target"] == 1
            negatives = ~positives
            rows.append(
                {
                    "dimension": dimension,
                    "segment": str(label),
                    "accounts": int(len(group)),
                    "observed_default_rate": float(group["target"].mean()),
                    "mean_pd": float(group["pd"].mean()),
                    "tpr": float(group.loc[positives, "prediction"].mean())
                    if positives.any()
                    else None,
                    "fpr": float(group.loc[negatives, "prediction"].mean())
                    if negatives.any()
                    else None,
                    "roc_auc": float(roc_auc_score(group["target"], group["pd"]))
                    if group["target"].nunique() > 1
                    else None,
                }
            )
    return rows


def _permutation_importance(
    model: Any, X: pd.DataFrame, y: pd.Series, sample_size: int = 1_500
) -> list[dict[str, float | str]]:  # noqa: N803
    sample = X.sample(min(sample_size, len(X)), random_state=SEED)
    target = y.loc[sample.index]
    result = permutation_importance(
        model,
        sample,
        target,
        scoring="neg_brier_score",
        n_repeats=5,
        random_state=SEED,
        n_jobs=1,
    )
    positive = np.maximum(result.importances_mean, 0)
    total = float(positive.sum()) or 1.0
    values = [
        {
            "feature": name,
            "importance": float(value / total),
            "brier_degradation": float(raw),
        }
        for name, value, raw in zip(sample.columns, positive, result.importances_mean, strict=True)
    ]
    return sorted(values, key=lambda item: item["importance"], reverse=True)


def _drift_indicators(reference: pd.DataFrame, comparison: pd.DataFrame) -> list[dict[str, Any]]:
    reference_features = engineer_features(reference)
    comparison_features = engineer_features(comparison)
    rows = []
    for name in FEATURE_NAMES:
        expected = reference_features[name].to_numpy()
        actual = comparison_features[name].to_numpy()
        edges = np.unique(np.quantile(expected, np.linspace(0, 1, 11)))
        if len(edges) < 3:
            psi = 0.0
        else:
            edges[0], edges[-1] = -np.inf, np.inf
            expected_share = np.histogram(expected, bins=edges)[0] / len(expected)
            actual_share = np.histogram(actual, bins=edges)[0] / len(actual)
            expected_share = np.clip(expected_share, 1e-6, None)
            actual_share = np.clip(actual_share, 1e-6, None)
            psi = float(
                np.sum((actual_share - expected_share) * np.log(actual_share / expected_share))
            )
        status = "Stable" if psi < 0.10 else "Monitor" if psi < 0.25 else "Investigate"
        rows.append({"feature": name, "psi": psi, "status": status})
    return sorted(rows, key=lambda item: item["psi"], reverse=True)


def _save_model_ready_splits(
    splits: dict[str, tuple[pd.DataFrame, pd.Series]],
    dataset_version: str,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    directory = output_dir or (PROCESSED_DIR / "splits")
    directory.mkdir(parents=True, exist_ok=True)
    files: dict[str, Any] = {}
    for name, (features, target) in splits.items():
        output = features.copy()
        output[TARGET] = target
        path = directory / f"{name}.csv"
        output.reset_index(drop=True).to_csv(path, index=False)
        files[name] = {"rows": len(output), "sha256": _sha256(path)}
    metadata = {
        "dataset_version": dataset_version,
        "random_seed": SEED,
        "stratified": True,
        "columns": [*MODEL_INPUT_COLUMNS, TARGET],
        "files": files,
    }
    _write_json(directory / "metadata.json", metadata)
    return metadata


def train_models() -> dict[str, Any]:
    frame, quality = build_data()
    X = frame[MODEL_INPUT_COLUMNS]  # noqa: N806
    y = frame[TARGET].astype(int)
    train_x, holdout_x, train_y, holdout_y = train_test_split(
        X, y, test_size=0.4, stratify=y, random_state=SEED
    )
    validation_x, test_x, validation_y, test_y = train_test_split(
        holdout_x, holdout_y, test_size=0.5, stratify=holdout_y, random_state=SEED
    )
    split_metadata = _save_model_ready_splits(
        {
            "train": (train_x, train_y),
            "validation": (validation_x, validation_y),
            "test": (test_x, test_y),
        },
        quality["dataset_version"],
    )
    audit_test = frame.loc[test_x.index, DEMOGRAPHIC_COLUMNS]
    validation_results: dict[str, Any] = {}
    fitted: dict[str, Any] = {}
    for name, model in _model_candidates().items():
        model.fit(train_x, train_y)
        probability = model.predict_proba(validation_x)[:, 1]
        selected_threshold = _threshold(validation_y, probability)
        validation_results[name] = _metrics(validation_y, probability, selected_threshold)
        fitted[name] = model
    best_auc = max(value["roc_auc"] for value in validation_results.values())
    eligible = {
        name: value
        for name, value in validation_results.items()
        if value["roc_auc"] >= best_auc - 0.02
    }
    champion_name = min(eligible, key=lambda name: (eligible[name]["brier_score"], name))
    validation_probability = fitted[champion_name].predict_proba(validation_x)[:, 1]
    selected_threshold = _threshold(validation_y, validation_probability)
    # Champion type and threshold are frozen before this refit and the single untouched-test read.
    champion = _model_candidates()[champion_name]
    combined_x = pd.concat([train_x, validation_x])
    combined_y = pd.concat([train_y, validation_y])
    champion.fit(combined_x, combined_y)
    test_probability = champion.predict_proba(test_x)[:, 1]
    test_metrics = _metrics(test_y, test_probability, selected_threshold)
    test_metrics["risk_bands"] = _risk_table(test_y, test_probability)
    test_metrics["segments"] = _segment_metrics(
        audit_test, test_y, test_probability, selected_threshold
    )
    test_metrics["feature_importance"] = _permutation_importance(champion, test_x, test_y)
    test_metrics["drift_indicators"] = _drift_indicators(combined_x, test_x)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    model_path = MODEL_DIR / "champion.joblib"
    joblib.dump(champion, model_path, compress=3)
    model_checksum = _sha256(model_path)
    metadata = {
        "model_version": f"limitiq-1.0.0-{model_checksum[:12]}",
        "champion": champion_name,
        "selection_rule": "Lowest validation Brier score among models within 0.02 ROC-AUC of the best",
        "threshold_rule": "Minimize validation cost with false negatives weighted 5x false positives",
        "selected_threshold": selected_threshold,
        "trained_at": datetime.now(UTC).isoformat(),
        "random_seed": SEED,
        "dataset_version": quality["dataset_version"],
        "dataset_checksum": quality["dataset_sha256"],
        "model_checksum": model_checksum,
        "decision_features": FEATURE_NAMES,
        "excluded_from_decisioning": [ID_COLUMN, TARGET, *DEMOGRAPHIC_COLUMNS],
        "split": {"train": len(train_x), "validation": len(validation_x), "test": len(test_x)},
        "split_artifacts": split_metadata,
        "validation_models": validation_results,
        "test_metrics": test_metrics,
        "audit_note": "Sex and age are used only for offline test diagnostics, never model inference.",
        "feature_importance_method": "Five-repeat permutation importance on untouched test data using Brier-score degradation; descriptive, not causal.",
        "drift_method": "PSI comparing development train+validation engineered features with the untouched test split; a development reference, not production monitoring.",
    }
    _write_json(MODEL_DIR / "metadata.json", metadata)
    _write_json(
        MODEL_DIR / "feature_schema.json",
        {
            "raw_required": MODEL_INPUT_COLUMNS,
            "engineered": FEATURE_NAMES,
            "target": TARGET,
            "protected_audit_only": DEMOGRAPHIC_COLUMNS,
        },
    )
    generate_demo(frame.loc[test_x.index], champion, PolicyAssumptions())
    _write_json(REPORT_DIR / "model_performance.json", metadata)
    return metadata


def synthetic_account_id(source_id: int | float | str) -> str:
    token = hashlib.sha256(f"limitiq-v1|{int(float(source_id))}".encode()).hexdigest()[:10].upper()
    return f"LIQ-{token}"


def generate_demo(
    frame: pd.DataFrame, model: Any, assumptions: PolicyAssumptions
) -> dict[str, Any]:
    probabilities = model.predict_proba(frame[MODEL_INPUT_COLUMNS])[:, 1]
    account_ids = [synthetic_account_id(value) for value in frame[ID_COLUMN]]
    decisions = recommend_portfolio(frame, probabilities, account_ids, assumptions)
    rows = []
    decision_by_id = {item.account_id: item for item in decisions}
    for (_, source), account_id in zip(frame.iterrows(), account_ids, strict=True):
        decision = decision_by_id[account_id]
        row = {"account_id": account_id, **{key: float(source[key]) for key in MODEL_INPUT_COLUMNS}}
        row.update(
            {
                "action": decision.action,
                "increase_pct": decision.increase_pct,
                "proposed_limit": decision.proposed_limit,
                "pd": decision.pd,
                "risk_band": decision.risk_band,
                "current_ead": decision.current_ead,
                "proposed_ead": decision.proposed_ead,
                "current_expected_loss": decision.current_expected_loss,
                "proposed_expected_loss": decision.proposed_expected_loss,
                "incremental_contribution": decision.incremental_contribution,
                "risk_adjusted_return": decision.risk_adjusted_return,
                "reason_codes": "|".join(decision.reason_codes),
                "policy_checks": json.dumps(decision.policy_checks, separators=(",", ":")),
            }
        )
        rows.append(row)
    demo = pd.DataFrame(rows)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    demo.to_csv(PROCESSED_DIR / "demo_portfolio.csv", index=False)
    summary = summarize_portfolio(decisions)
    payload = {
        "classification": "Simulated portfolio outcome",
        "assumptions": assumptions.to_dict(),
        "summary": summary,
        "sensitivity": portfolio_sensitivity(
            frame[MODEL_INPUT_COLUMNS], probabilities, account_ids, assumptions
        ),
        "limitations": [
            "Limit response, drawdown, revenue, costs, LGD and CCF are transparent assumptions.",
            "No simulated outcome is an observed or causal production result.",
            "PD is model-estimated from a 2005 Taiwan dataset; portability is unproven.",
        ],
    }
    _write_json(REPORT_DIR / "policy_simulation.json", payload)
    return payload


def resimulate_existing(assumptions: PolicyAssumptions | None = None) -> dict[str, Any]:
    """Reapply the pure policy layer without retraining or changing model-estimated PD."""
    assumptions = assumptions or PolicyAssumptions()
    path = PROCESSED_DIR / "demo_portfolio.csv"
    demo = pd.read_csv(path)
    decisions = recommend_portfolio(
        demo[MODEL_INPUT_COLUMNS],
        demo["pd"].to_numpy(),
        demo["account_id"].tolist(),
        assumptions,
    )
    decision_by_id = {item.account_id: item for item in decisions}
    for index, account_id in demo["account_id"].items():
        item = decision_by_id[account_id]
        demo.loc[
            index,
            [
                "action",
                "increase_pct",
                "proposed_limit",
                "current_ead",
                "proposed_ead",
                "current_expected_loss",
                "proposed_expected_loss",
                "incremental_contribution",
                "risk_adjusted_return",
                "reason_codes",
                "policy_checks",
            ],
        ] = [
            item.action,
            item.increase_pct,
            item.proposed_limit,
            item.current_ead,
            item.proposed_ead,
            item.current_expected_loss,
            item.proposed_expected_loss,
            item.incremental_contribution,
            item.risk_adjusted_return,
            "|".join(item.reason_codes),
            json.dumps(item.policy_checks, separators=(",", ":")),
        ]
    demo.to_csv(path, index=False)
    payload = {
        "classification": "Simulated portfolio outcome",
        "assumptions": assumptions.to_dict(),
        "summary": summarize_portfolio(decisions),
        "sensitivity": portfolio_sensitivity(
            demo[MODEL_INPUT_COLUMNS],
            demo["pd"].to_numpy(),
            demo["account_id"].tolist(),
            assumptions,
        ),
        "limitations": [
            "Limit response is a simulated monthly elasticity annualized over 12 periods; drawdown, revenue, costs, LGD and CCF are also assumptions.",
            "No simulated outcome is an observed or causal production result.",
            "PD is model-estimated from a 2005 Taiwan dataset; portability is unproven.",
        ],
    }
    _write_json(REPORT_DIR / "policy_simulation.json", payload)
    return payload


def generate_reports() -> None:
    from limitiq.reporting import build_reports

    build_reports()


def build_all(force_download: bool = False) -> dict[str, Any]:
    download_dataset(force_download)
    metadata = train_models()
    generate_reports()
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description="LimitIQ reproducible build pipeline")
    parser.add_argument(
        "command", choices=["download", "data", "train", "simulate", "reports", "all"]
    )
    parser.add_argument("--force-download", action="store_true")
    args = parser.parse_args()
    if args.command == "download":
        print(download_dataset(args.force_download))
    elif args.command == "data":
        _, quality = build_data()
        print(json.dumps(quality, indent=2))
    elif args.command == "train":
        print(json.dumps(train_models(), indent=2))
    elif args.command == "simulate":
        print(json.dumps(resimulate_existing(), indent=2))
    elif args.command == "reports":
        generate_reports()
        print(REPORT_DIR)
    else:
        print(json.dumps(build_all(args.force_download), indent=2))


if __name__ == "__main__":
    main()
