"""Source-coherent next-month default model for the LimitIQ v3 decision track.

The model is trained only on UCI 350 (Taiwan) and therefore has one observed
target: default payment in the following month.  The separate global model
remains a transportability benchmark because its source labels are not a
common-horizon probability of default.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    log_loss,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from limitiq.config import (
    DATASET_DOI,
    DATASET_LICENSE,
    DATASET_PAGE,
    MODEL_DIR,
    PROCESSED_DIR,
    RAW_DIR,
    REPORT_DIR,
    SEED,
    PolicyAssumptions,
)
from limitiq.features import PAY_COLUMNS
from limitiq.multisource import MODEL_FEATURES, TARGET
from limitiq.pipeline import _metrics, _sha256, _threshold, _write_json, load_source

ACTIVE_FEATURES = ["delinquency_count", "utilization"]
UNAVAILABLE_FEATURES = sorted(set(MODEL_FEATURES) - {*ACTIVE_FEATURES, "region"})
PRIMARY_MODEL_PATH = MODEL_DIR / "primary_champion.joblib"
PRIMARY_METADATA_PATH = MODEL_DIR / "primary_metadata.json"
PRIMARY_SCHEMA_PATH = MODEL_DIR / "primary_feature_schema.json"
PRIMARY_REPORT_PATH = REPORT_DIR / "primary_model.json"
PRIMARY_DEMO_PATH = PROCESSED_DIR / "primary_demo_portfolio.csv"
PRIMARY_SIMULATION_PATH = REPORT_DIR / "primary_policy_simulation.json"
BOOTSTRAP_SEED = SEED + 3_000


def _canonical_sha256(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def _frame_sha256(frame: pd.DataFrame) -> str:
    normalized = frame.to_csv(index=False, lineterminator="\n", na_rep="").encode()
    return hashlib.sha256(normalized).hexdigest()


def _text_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_text(encoding="utf-8").encode()).hexdigest()


def synthetic_primary_profiles(rows: int = 1_200) -> pd.DataFrame:
    """Generate fixed-distribution profiles matching the Taiwan field-availability contract."""
    if not 1 <= rows <= 10_000:
        raise ValueError("Synthetic profile rows must be between 1 and 10,000")
    rng = np.random.default_rng(SEED)
    frame = pd.DataFrame(index=range(rows), columns=MODEL_FEATURES, dtype=float)
    frame["delinquency_count"] = rng.poisson(0.35, rows).clip(0, 6)
    frame["utilization"] = (rng.beta(2.2, 2.8, rows) * 1.35).clip(0, 1.4)
    frame["region"] = "asia"
    frame["source_dataset"] = "taiwan_credit"
    frame["current_limit_inr"] = (
        rng.lognormal(np.log(350_000), 0.65, rows).clip(50_000, 2_500_000).round(-3)
    )
    frame["current_balance_inr"] = (frame["current_limit_inr"] * frame["utilization"]).round(-2)
    frame["account_id"] = [f"LIQ-{index + 1:06d}" for index in range(rows)]
    return frame


def _smoke_training_frame(rows: int = 1_200) -> tuple[pd.DataFrame, dict[str, Any]]:
    profiles = synthetic_primary_profiles(rows)
    rng = np.random.default_rng(SEED + 1)
    probability = 1 / (
        1 + np.exp(-(-2.5 + 0.65 * profiles["delinquency_count"] + profiles["utilization"]))
    )
    frame = profiles[MODEL_FEATURES].copy()
    frame[TARGET] = rng.binomial(1, probability)
    return frame, {
        "dataset": "Deterministic synthetic smoke fixture",
        "target_definition": "Synthetic binary adverse event for pipeline verification",
        "prediction_horizon": "Synthetic one-period horizon",
    }


def load_primary_source() -> tuple[pd.DataFrame, dict[str, Any]]:
    """Load the cached UCI source and map only semantically compatible fields."""
    raw_path = RAW_DIR / "default_of_credit_card_clients.xls"
    if not raw_path.exists():
        raise FileNotFoundError(
            "Cached UCI Taiwan source is required at data/raw/"
            "default_of_credit_card_clients.xls; this command never downloads data"
        )
    source, quality = load_source(raw_path)
    frame = pd.DataFrame(index=source.index)
    frame["delinquency_count"] = (source[PAY_COLUMNS] > 0).sum(axis=1).astype(float)
    frame["utilization"] = (
        source["BILL_AMT1"].clip(lower=0) / source["LIMIT_BAL"].clip(lower=1)
    ).clip(upper=5)
    for name in UNAVAILABLE_FEATURES:
        frame[name] = np.nan
    frame["region"] = "asia"
    frame[TARGET] = source["default_next_month"].astype(int)
    frame = frame[[*MODEL_FEATURES, TARGET]].reset_index(drop=True)
    provenance = {
        "dataset": "Default of Credit Card Clients",
        "publisher": "I-Cheng Yeh / UCI Machine Learning Repository",
        "source_page": DATASET_PAGE,
        "doi": DATASET_DOI,
        "license": DATASET_LICENSE,
        "source_file": raw_path.name,
        "source_sha256": quality["dataset_sha256"],
        "source_rows": int(quality["clean_rows"]),
        "event_rate": float(frame[TARGET].mean()),
        "geography": "Taiwan",
        "target_definition": "Default payment in the following month",
        "prediction_horizon": "One month",
        "monetary_conversion_note": quality["currency_note"],
    }
    return frame, provenance


def _candidate_models(challenger_iterations: int) -> dict[str, CalibratedClassifierCV]:
    baseline = Pipeline(
        [
            (
                "active_features",
                ColumnTransformer(
                    [("scale", StandardScaler(), ACTIVE_FEATURES)],
                    remainder="drop",
                    verbose_feature_names_out=False,
                ),
            ),
            ("model", LogisticRegression(C=0.5, max_iter=2_000, random_state=SEED)),
        ]
    )
    challenger = Pipeline(
        [
            (
                "active_features",
                ColumnTransformer(
                    [("select", "passthrough", ACTIVE_FEATURES)],
                    remainder="drop",
                    verbose_feature_names_out=False,
                ),
            ),
            (
                "model",
                HistGradientBoostingClassifier(
                    learning_rate=0.06,
                    max_iter=challenger_iterations,
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


def _bootstrap_intervals(
    target: pd.Series, probability: np.ndarray, repeats: int
) -> dict[str, dict[str, float | int | str]]:
    """Deterministic percentile intervals on the untouched test population."""
    truth = target.to_numpy(dtype=int)
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    functions = {
        "roc_auc": roc_auc_score,
        "pr_auc": average_precision_score,
        "brier_score": brier_score_loss,
        "log_loss": lambda y, p: log_loss(y, p, labels=[0, 1]),
    }
    samples: dict[str, list[float]] = {name: [] for name in functions}
    while len(samples["roc_auc"]) < repeats:
        indexes = rng.integers(0, len(truth), size=len(truth))
        boot_truth = truth[indexes]
        if np.unique(boot_truth).size != 2:
            continue
        boot_probability = probability[indexes]
        for name, function in functions.items():
            samples[name].append(float(function(boot_truth, boot_probability)))
    result: dict[str, dict[str, float | int | str]] = {}
    for name, values in samples.items():
        lower, upper = np.quantile(values, [0.025, 0.975])
        result[name] = {
            "lower_95": float(lower),
            "upper_95": float(upper),
            "repeats": repeats,
            "method": "seeded nonparametric percentile bootstrap",
        }
    return result


def _test_diagnostics(
    features: pd.DataFrame, target: pd.Series, probability: np.ndarray
) -> dict[str, Any]:
    """Emit compact, source-coherent governance evidence for the untouched test."""
    truth = target.to_numpy(dtype=int)
    fpr, tpr, _ = roc_curve(truth, probability)
    if len(fpr) > 201:
        indexes = np.unique(np.linspace(0, len(fpr) - 1, 201).astype(int))
        fpr, tpr = fpr[indexes], tpr[indexes]
    edges = np.linspace(0, 1, 21)
    counts, _ = np.histogram(probability, bins=edges)
    bands = {
        "Low": int((probability < 0.05).sum()),
        "Moderate": int(((probability >= 0.05) & (probability < 0.15)).sum()),
        "High": int(((probability >= 0.15) & (probability < 0.30)).sum()),
        "Very high": int((probability >= 0.30).sum()),
    }

    rng = np.random.default_rng(SEED + 4_000)
    baseline_auc = float(roc_auc_score(truth, probability))
    importance = []
    for feature in ACTIVE_FEATURES:
        shuffled = features.copy()
        shuffled[feature] = rng.permutation(shuffled[feature].to_numpy())
        # This diagnostic is populated after the champion is fitted in train_primary.
        importance.append({"feature": feature, "roc_auc_drop": None, "_frame": shuffled})

    segment_masks = {
        "Utilization <30%": features["utilization"] < 0.30,
        "Utilization 30–70%": features["utilization"].between(0.30, 0.70, inclusive="left"),
        "Utilization ≥70%": features["utilization"] >= 0.70,
        "No reported delinquency": features["delinquency_count"] == 0,
        "One delinquent month": features["delinquency_count"] == 1,
        "Two or more delinquent months": features["delinquency_count"] >= 2,
    }
    segments = []
    for name, mask in segment_masks.items():
        segment_truth = truth[mask.to_numpy()]
        segment_probability = probability[mask.to_numpy()]
        segments.append(
            {
                "segment": name,
                "accounts": int(mask.sum()),
                "event_rate": float(segment_truth.mean()),
                "mean_probability": float(segment_probability.mean()),
                "roc_auc": (
                    float(roc_auc_score(segment_truth, segment_probability))
                    if np.unique(segment_truth).size == 2
                    else None
                ),
            }
        )

    return {
        "roc_points": {"fpr": fpr.tolist(), "tpr": tpr.tolist()},
        "probability_summary": {
            "histogram": [
                {"lower": float(edges[i]), "upper": float(edges[i + 1]), "count": int(count)}
                for i, count in enumerate(counts)
            ],
            "risk_bands": bands,
        },
        "segments": segments,
        "feature_summary": [
            {
                "feature": feature,
                "p01": float(features[feature].quantile(0.01)),
                "median": float(features[feature].median()),
                "p99": float(features[feature].quantile(0.99)),
                "missing_rate": float(features[feature].isna().mean()),
            }
            for feature in ACTIVE_FEATURES
        ],
        "permutation_importance": importance,
        "baseline_roc_auc": baseline_auc,
    }


def _validate_training_frame(frame: pd.DataFrame) -> pd.DataFrame:
    required = [*MODEL_FEATURES, TARGET]
    missing = sorted(set(required) - set(frame.columns))
    if missing:
        raise ValueError(f"Primary training frame is missing: {', '.join(missing)}")
    clean = frame.loc[:, required].copy()
    if clean[TARGET].isna().any() or not set(clean[TARGET].unique()) <= {0, 1}:
        raise ValueError("Primary target must contain only 0 and 1 with no blanks")
    if clean[TARGET].nunique() != 2 or len(clean) < 100:
        raise ValueError("Primary training requires both target classes and at least 100 rows")
    for name in ACTIVE_FEATURES:
        clean[name] = pd.to_numeric(clean[name], errors="coerce")
        if clean[name].isna().any() or not np.isfinite(clean[name]).all():
            raise ValueError(f"Primary active feature must be finite numeric: {name}")
    return clean


def train_primary(
    frame: pd.DataFrame,
    provenance: dict[str, Any],
    *,
    model_dir: Path = MODEL_DIR,
    report_dir: Path = REPORT_DIR,
    bootstrap_repeats: int = 500,
    challenger_iterations: int = 160,
) -> dict[str, Any]:
    """Select, freeze, test and persist the source-coherent primary model."""
    if bootstrap_repeats < 20:
        raise ValueError("At least 20 bootstrap repeats are required")
    clean = _validate_training_frame(frame)
    features = clean[MODEL_FEATURES]
    target = clean[TARGET].astype(int)
    train_x, holdout_x, train_y, holdout_y = train_test_split(
        features, target, test_size=0.4, stratify=target, random_state=SEED
    )
    validation_x, test_x, validation_y, test_y = train_test_split(
        holdout_x, holdout_y, test_size=0.5, stratify=holdout_y, random_state=SEED
    )

    validation_models: dict[str, dict[str, Any]] = {}
    fitted: dict[str, Any] = {}
    for name, candidate in _candidate_models(challenger_iterations).items():
        candidate.fit(train_x, train_y)
        probability = candidate.predict_proba(validation_x)[:, 1]
        threshold = _threshold(validation_y, probability)
        validation_models[name] = _metrics(validation_y, probability, threshold)
        fitted[name] = candidate
    best_auc = max(result["roc_auc"] for result in validation_models.values())
    eligible = {
        name: result
        for name, result in validation_models.items()
        if result["roc_auc"] >= best_auc - 0.02
    }
    champion_name = min(eligible, key=lambda name: (eligible[name]["brier_score"], name))
    validation_probability = fitted[champion_name].predict_proba(validation_x)[:, 1]
    selected_threshold = _threshold(validation_y, validation_probability)

    champion = _candidate_models(challenger_iterations)[champion_name]
    development_x = pd.concat([train_x, validation_x])
    development_y = pd.concat([train_y, validation_y])
    champion.fit(development_x, development_y)
    test_probability = champion.predict_proba(test_x)[:, 1]
    test_metrics = _metrics(test_y, test_probability, selected_threshold)
    test_metrics["confidence_intervals"] = _bootstrap_intervals(
        test_y, test_probability, bootstrap_repeats
    )
    diagnostics = _test_diagnostics(test_x, test_y, test_probability)
    for item in diagnostics["permutation_importance"]:
        shuffled_probability = champion.predict_proba(item.pop("_frame"))[:, 1]
        item["roc_auc_drop"] = diagnostics["baseline_roc_auc"] - float(
            roc_auc_score(test_y, shuffled_probability)
        )
    diagnostics.pop("baseline_roc_auc")
    test_metrics.update(diagnostics)

    model_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    model_path = model_dir / PRIMARY_MODEL_PATH.name
    schema_path = model_dir / PRIMARY_SCHEMA_PATH.name
    report_path = report_dir / PRIMARY_REPORT_PATH.name
    joblib.dump(champion, model_path, compress=3)
    schema = {
        "input_columns": MODEL_FEATURES,
        "active_decision_features": ACTIVE_FEATURES,
        "constant_context": {"region": "asia"},
        "unavailable_source_features": UNAVAILABLE_FEATURES,
        "target": TARGET,
        "target_definition": provenance["target_definition"],
        "prediction_horizon": provenance["prediction_horizon"],
    }
    _write_json(schema_path, schema)
    training_config = {
        "random_seed": SEED,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "split": "stratified 60/20/20",
        "calibration": "sigmoid, three-fold development CV",
        "challenger_iterations": challenger_iterations,
        "selection_rule": (
            "Lowest validation Brier score among candidates within 0.02 ROC-AUC of the best"
        ),
        "threshold_rule": "Validation cost: false negatives weighted 5x false positives",
    }
    payload = {
        "classification": "Source-coherent application candidate; educational use only",
        "role": "Primary decision-model candidate",
        "global_model_role": "Separate multi-source transportability research benchmark",
        "intended_use": "Educational simulation of credit-line policy for Taiwan-like inputs",
        "prohibited_uses": [
            "Real lending decisions",
            "Regulatory or IFRS 9 probability of default",
            "Indian-market deployment without local outcome validation",
        ],
        "trained_at": datetime.now(UTC).isoformat(),
        "source": provenance,
        "rows": len(clean),
        "event_rate": float(target.mean()),
        "dataset_checksum": _frame_sha256(clean),
        "feature_schema_checksum": _canonical_sha256(schema),
        "training_config_checksum": _canonical_sha256(training_config),
        "training_config": training_config,
        "split": {
            "train": len(train_x),
            "validation": len(validation_x),
            "untouched_test": len(test_x),
        },
        "champion": champion_name,
        "selected_threshold": selected_threshold,
        "validation_models": validation_models,
        "untouched_test_metrics": test_metrics,
        "model_checksum": _sha256(model_path),
        "feature_schema": schema,
        "limitations": [
            "Random within-source splitting is not out-of-time validation.",
            "Only delinquency count and utilization are observed in the harmonized contract.",
            "The source is Taiwan-only and does not establish geographic transportability.",
            "Credit-line response and economics remain simulated, not causal observations.",
        ],
    }
    payload["model_version"] = f"limitiq-primary-3.0.0-{payload['model_checksum'][:12]}"
    payload["dataset_version"] = f"uci-350-next-month-{payload['dataset_checksum'][:12]}"
    _write_json(report_path, payload)
    metadata = {
        key: payload[key]
        for key in (
            "model_version",
            "dataset_version",
            "classification",
            "role",
            "trained_at",
            "champion",
            "selected_threshold",
            "source",
            "split",
            "model_checksum",
            "dataset_checksum",
            "feature_schema_checksum",
            "training_config_checksum",
            "feature_schema",
            "limitations",
        )
    }
    metadata["artifact_checksums"] = {
        model_path.name: _sha256(model_path),
        schema_path.name: _sha256(schema_path),
        report_path.name: _sha256(report_path),
    }
    _write_json(model_dir / PRIMARY_METADATA_PATH.name, metadata)
    return payload


def write_primary_demo(
    model: Any,
    metadata: dict[str, Any],
    *,
    processed_dir: Path = PROCESSED_DIR,
    report_dir: Path = REPORT_DIR,
) -> dict[str, Any]:
    """Score and optimize a deterministic synthetic portfolio with the primary model."""
    from limitiq.optimizer import portfolio_sensitivity, recommend_portfolio, summarize_portfolio

    profiles = synthetic_primary_profiles()
    probabilities = model.predict_proba(profiles[MODEL_FEATURES])[:, 1]
    account_ids = profiles["account_id"].tolist()
    assumptions = PolicyAssumptions()
    decisions = recommend_portfolio(profiles, probabilities, account_ids, assumptions)
    output = profiles.copy()
    decision_rows = [decision.to_dict() for decision in decisions]
    for column in (
        "action",
        "increase_pct",
        "proposed_limit",
        "pd",
        "risk_band",
        "current_ead",
        "proposed_ead",
        "current_expected_loss",
        "proposed_expected_loss",
        "incremental_contribution",
        "risk_adjusted_return",
    ):
        output[column] = [row[column] for row in decision_rows]
    output["reason_codes"] = [" | ".join(decision.reason_codes) for decision in decisions]
    output["policy_checks"] = [json.dumps(decision.policy_checks) for decision in decisions]
    output["missing_model_fields"] = " | ".join(UNAVAILABLE_FEATURES)

    processed_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    portfolio_path = processed_dir / PRIMARY_DEMO_PATH.name
    temporary_path = portfolio_path.with_suffix(".csv.tmp")
    output.to_csv(temporary_path, index=False, lineterminator="\n")
    temporary_path.replace(portfolio_path)
    payload = {
        "classification": "Deterministic synthetic scenario; not observed or causal impact",
        "model_version": metadata["model_version"],
        "dataset_version": metadata["dataset_version"],
        "model_checksum": metadata["model_checksum"],
        "dataset_checksum": metadata["dataset_checksum"],
        "random_seed": SEED,
        "generated_at": datetime.now(UTC).isoformat(),
        "demo_rows": int(len(output)),
        "demo_portfolio_sha256": _text_sha256(portfolio_path),
        "assumptions": assumptions.to_dict(),
        "summary": summarize_portfolio(decisions),
        "sensitivity": portfolio_sensitivity(profiles, probabilities, account_ids, assumptions),
        "limitations": [
            "Profiles match the Taiwan field-availability contract but use fixed synthetic distributions; they are not source records or an empirical population replica.",
            "Limit response, LGD, CCF, revenue and cost inputs are assumptions, not observed causal effects.",
            "Expected-loss values are simulated management proxies, not IFRS 9 provisions.",
            "The primary model is not validated for India or any production lending use.",
        ],
    }
    _write_json(report_dir / PRIMARY_SIMULATION_PATH.name, payload)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the coherent LimitIQ primary PD model")
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Fit a deterministic 1,200-row check without writing release artifacts",
    )
    parser.add_argument(
        "--demo-only",
        action="store_true",
        help="Regenerate the synthetic decision portfolio from trusted primary artifacts",
    )
    args = parser.parse_args()
    if args.smoke and args.demo_only:
        parser.error("--smoke and --demo-only cannot be combined")
    if args.demo_only:
        metadata = json.loads(PRIMARY_METADATA_PATH.read_text(encoding="utf-8"))
        if _sha256(PRIMARY_MODEL_PATH) != metadata["model_checksum"]:
            raise RuntimeError("Primary model checksum does not match trusted metadata")
        write_primary_demo(joblib.load(PRIMARY_MODEL_PATH), metadata)  # noqa: S301
        payload = json.loads(PRIMARY_REPORT_PATH.read_text(encoding="utf-8"))
    elif args.smoke:
        frame, provenance = _smoke_training_frame()
        import tempfile

        with tempfile.TemporaryDirectory(prefix="limitiq-primary-smoke-") as directory:
            root = Path(directory)
            payload = train_primary(
                frame,
                provenance,
                model_dir=root / "models",
                report_dir=root / "reports",
                bootstrap_repeats=20,
                challenger_iterations=30,
            )
    else:
        frame, provenance = load_primary_source()
        payload = train_primary(frame, provenance)
        write_primary_demo(joblib.load(PRIMARY_MODEL_PATH), payload)  # noqa: S301
    print(
        json.dumps(
            {
                "model_version": payload["model_version"],
                "dataset_version": payload["dataset_version"],
                "champion": payload["champion"],
                "untouched_test_metrics": {
                    name: payload["untouched_test_metrics"][name]
                    for name in ("roc_auc", "pr_auc", "brier_score", "log_loss")
                },
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
