"""Train and package the rich UCI Taiwan behavioral model used by LimitIQ v4."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    log_loss,
    roc_auc_score,
    roc_curve,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from limitiq.config import MODEL_DIR, PROCESSED_DIR, RAW_DIR, REPORT_DIR, SEED, PolicyAssumptions
from limitiq.features import (
    BILL_COLUMNS,
    FEATURE_NAMES,
    PAY_COLUMNS,
    PAYMENT_COLUMNS,
    TAIWAN_MODEL_INPUT_COLUMNS,
    FeatureBuilder,
    engineer_features,
)
from limitiq.multisource import MODEL_FEATURES, TARGET
from limitiq.pipeline import _metrics, _sha256, _threshold, _write_json, load_source
from limitiq.primary import PRIMARY_METADATA_PATH, PRIMARY_MODEL_PATH, _bootstrap_intervals
from limitiq.splits import frozen_split

CANDIDATE_MODEL_PATH = MODEL_DIR / "behavioral_candidate.joblib"
CANDIDATE_METADATA_PATH = MODEL_DIR / "behavioral_metadata.json"
CANDIDATE_SCHEMA_PATH = MODEL_DIR / "behavioral_feature_schema.json"
CANDIDATE_REPORT_PATH = REPORT_DIR / "behavioral_model.json"
BEHAVIORAL_DEMO_PATH = PROCESSED_DIR / "behavioral_demo_portfolio.csv"
BEHAVIORAL_SIMULATION_PATH = REPORT_DIR / "behavioral_policy_simulation.json"
OPTIMIZER_STRESS_PATH = REPORT_DIR / "behavioral_optimizer_stress.json"
BOOTSTRAP_SEED = SEED + 4_100
BEHAVIORAL_HGB_ITERATIONS = 180


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def _text_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_text(encoding="utf-8").encode()).hexdigest()


def synthetic_behavioral_account(account_id: str) -> pd.DataFrame:
    """Build one deterministic synthetic six-month history for explanation demos."""
    seed = int.from_bytes(hashlib.sha256(account_id.encode()).digest()[:8], "big")
    rng = np.random.default_rng(seed)
    limit = float(rng.lognormal(np.log(350_000), 0.55))
    utilization = float(rng.beta(2.2, 2.8))
    bills = np.clip(
        limit * (utilization + np.linspace(-0.08, 0.08, 6) + rng.normal(0, 0.04, 6)),
        0,
        limit * 1.4,
    )
    statuses = rng.choice([-1, 0, 1, 2], 6, p=[0.10, 0.73, 0.13, 0.04])
    payments = np.maximum(bills * rng.uniform(0.03, 0.22, 6), 0)
    values = {
        "LIMIT_BAL": limit,
        **dict(zip(PAY_COLUMNS, statuses, strict=True)),
        **dict(zip(BILL_COLUMNS, bills, strict=True)),
        **dict(zip(PAYMENT_COLUMNS, payments, strict=True)),
    }
    return pd.DataFrame([values], columns=TAIWAN_MODEL_INPUT_COLUMNS)


def synthetic_behavioral_profiles(rows: int = 1_200) -> pd.DataFrame:
    """Build deterministic synthetic histories; no public source row is exposed."""
    if not 1 <= rows <= 10_000:
        raise ValueError("Synthetic profile rows must be between 1 and 10,000")
    raw = pd.concat(
        [synthetic_behavioral_account(f"LIQ-{index + 1:06d}") for index in range(rows)],
        ignore_index=True,
    )
    raw["account_id"] = [f"LIQ-{index + 1:06d}" for index in range(rows)]
    raw["current_limit_inr"] = raw["LIMIT_BAL"]
    raw["current_balance_inr"] = raw["BILL_AMT1"].clip(lower=0, upper=raw["LIMIT_BAL"] * 2)
    sequence = np.arange(rows)
    verified_monthly_income = np.clip(
        raw["LIMIT_BAL"] / 5 + raw[PAYMENT_COLUMNS].mean(axis=1) * 2,
        25_000,
        500_000,
    )
    synthetic_foir = 0.18 + (sequence % 37) * 0.01
    synthetic_foir[sequence % 97 == 0] = 0.68
    raw["income_inr"] = verified_monthly_income * 12
    raw["total_monthly_obligation_inr"] = verified_monthly_income * synthetic_foir
    raw["debt_to_income"] = raw["total_monthly_obligation_inr"] / verified_monthly_income
    raw["delinquency_count"] = (raw[PAY_COLUMNS] > 0).sum(axis=1).astype(float)
    raw["utilization"] = (raw["BILL_AMT1"].clip(lower=0) / raw["LIMIT_BAL"].clip(lower=1)).clip(
        upper=5
    )
    raw["credit_lines"] = 1 + sequence % 8
    raw["credit_age_months"] = 12 + sequence * 17 % 240
    for name in MODEL_FEATURES:
        if name not in raw:
            raw[name] = "taiwan" if name == "region" else np.nan
    return raw


def load_behavioral_source() -> tuple[pd.DataFrame, pd.Series, dict[str, Any]]:
    """Load the cached UCI source without demographics or customer ID."""
    path = RAW_DIR / "default_of_credit_card_clients.xls"
    if not path.exists():
        raise FileNotFoundError(f"Cached source required at {path}")
    source, quality = load_source(path)
    features = source[TAIWAN_MODEL_INPUT_COLUMNS].copy()
    target = source["default_next_month"].astype(int)
    provenance = {
        "dataset": "Default of Credit Card Clients",
        "source_file": path.name,
        "source_sha256": quality["dataset_sha256"],
        "rows": int(len(source)),
        "event_rate": float(target.mean()),
        "geography": "Taiwan",
        "target_definition": "Default payment in the following month",
        "prediction_horizon": "One month",
        "protected_attributes_excluded": ["SEX", "EDUCATION", "MARRIAGE", "AGE"],
    }
    return features, target, provenance


def _candidate_models(iterations: int) -> dict[str, CalibratedClassifierCV]:
    logistic = Pipeline(
        [
            ("behavior", FeatureBuilder()),
            ("scale", StandardScaler()),
            ("model", LogisticRegression(C=0.5, max_iter=2_000, random_state=SEED)),
        ]
    )
    challenger = Pipeline(
        [
            ("behavior", FeatureBuilder()),
            (
                "model",
                HistGradientBoostingClassifier(
                    learning_rate=0.06,
                    max_iter=iterations,
                    max_leaf_nodes=15,
                    l2_regularization=1.0,
                    random_state=SEED,
                ),
            ),
        ]
    )
    return {
        "Regularized logistic regression": CalibratedClassifierCV(logistic, method="sigmoid", cv=3),
        "Histogram gradient boosting": CalibratedClassifierCV(challenger, method="sigmoid", cv=3),
    }


def _v3_probability(test_x: pd.DataFrame) -> tuple[np.ndarray, dict[str, Any]]:
    """Score the same untouched rows with the checksum-verified two-feature v3 model."""
    metadata = json.loads(PRIMARY_METADATA_PATH.read_text(encoding="utf-8"))
    if _sha256(PRIMARY_MODEL_PATH) != metadata["model_checksum"]:
        raise RuntimeError("Verified v3 primary model checksum mismatch")
    frame = pd.DataFrame(index=test_x.index, columns=MODEL_FEATURES, dtype=float)
    frame["delinquency_count"] = (test_x[PAY_COLUMNS] > 0).sum(axis=1).astype(float)
    frame["utilization"] = (
        test_x["BILL_AMT1"].clip(lower=0) / test_x["LIMIT_BAL"].clip(lower=1)
    ).clip(upper=5)
    frame["region"] = "asia"
    model = joblib.load(PRIMARY_MODEL_PATH)  # noqa: S301 - checksum verified above
    return model.predict_proba(frame[MODEL_FEATURES])[:, 1], metadata


def _paired_bootstrap(
    truth: pd.Series, candidate: np.ndarray, benchmark: np.ndarray, repeats: int
) -> dict[str, dict[str, float | int | str]]:
    """Paired percentile intervals for candidate-minus-v3 metric differences."""
    y = truth.to_numpy(dtype=int)
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    metrics = {
        "roc_auc": roc_auc_score,
        "pr_auc": average_precision_score,
        "brier_score": brier_score_loss,
        "log_loss": lambda actual, score: log_loss(actual, score, labels=[0, 1]),
    }
    samples: dict[str, list[float]] = {name: [] for name in metrics}
    while len(samples["roc_auc"]) < repeats:
        indexes = rng.integers(0, len(y), len(y))
        actual = y[indexes]
        if np.unique(actual).size != 2:
            continue
        for name, metric in metrics.items():
            samples[name].append(
                float(metric(actual, candidate[indexes]) - metric(actual, benchmark[indexes]))
            )
    return {
        name: {
            "candidate_minus_v3": float(metric(y, candidate) - metric(y, benchmark)),
            "lower_95": float(np.quantile(samples[name], 0.025)),
            "upper_95": float(np.quantile(samples[name], 0.975)),
            "repeats": repeats,
            "method": "seeded paired nonparametric percentile bootstrap",
            "higher_is_better": name not in {"brier_score", "log_loss"},
        }
        for name, metric in metrics.items()
    }


def _test_diagnostics(
    model: Any, features: pd.DataFrame, target: pd.Series, probability: np.ndarray
) -> dict[str, Any]:
    truth = target.to_numpy(dtype=int)
    fpr, tpr, _ = roc_curve(truth, probability)
    if len(fpr) > 201:
        indexes = np.unique(np.linspace(0, len(fpr) - 1, 201).astype(int))
        fpr, tpr = fpr[indexes], tpr[indexes]
    edges = np.linspace(0, 1, 21)
    counts, _ = np.histogram(probability, bins=edges)
    engineered = engineer_features(features)
    segment_masks = {
        "Utilization <30%": engineered["current_utilization"] < 0.30,
        "Utilization 30–70%": engineered["current_utilization"].between(
            0.30, 0.70, inclusive="left"
        ),
        "Utilization ≥70%": engineered["current_utilization"] >= 0.70,
        "No reported delinquency": engineered["delinquent_month_count"] == 0,
        "One delinquent month": engineered["delinquent_month_count"] == 1,
        "Two or more delinquent months": engineered["delinquent_month_count"] >= 2,
    }
    segments = []
    for name, mask in segment_masks.items():
        actual = truth[mask.to_numpy()]
        score = probability[mask.to_numpy()]
        segments.append(
            {
                "segment": name,
                "accounts": int(mask.sum()),
                "event_rate": float(actual.mean()),
                "mean_probability": float(score.mean()),
                "roc_auc": float(roc_auc_score(actual, score))
                if np.unique(actual).size == 2
                else None,
            }
        )
    rng = np.random.default_rng(SEED + 4_200)
    groups = {
        "repayment_status_history": PAY_COLUMNS,
        "bill_and_utilization_history": BILL_COLUMNS,
        "payment_amount_history": PAYMENT_COLUMNS,
        "current_limit": ["LIMIT_BAL"],
    }
    importance = []
    baseline_auc = float(roc_auc_score(target, probability))
    for name, columns in groups.items():
        shuffled = features.copy()
        permutation = rng.permutation(len(shuffled))
        shuffled[columns] = shuffled[columns].to_numpy()[permutation]
        shuffled_score = model.predict_proba(shuffled)[:, 1]
        importance.append(
            {
                "feature": name,
                "roc_auc_drop": baseline_auc - float(roc_auc_score(target, shuffled_score)),
            }
        )
    return {
        "roc_points": {"fpr": fpr.tolist(), "tpr": tpr.tolist()},
        "probability_summary": {
            "histogram": [
                {"lower": float(edges[i]), "upper": float(edges[i + 1]), "count": int(count)}
                for i, count in enumerate(counts)
            ],
            "risk_bands": {
                "Low": int((probability < 0.05).sum()),
                "Moderate": int(((probability >= 0.05) & (probability < 0.15)).sum()),
                "High": int(((probability >= 0.15) & (probability < 0.30)).sum()),
                "Very high": int((probability >= 0.30).sum()),
            },
        },
        "segments": segments,
        "feature_summary": [
            {
                "feature": name,
                "p01": float(engineered[name].quantile(0.01)),
                "median": float(engineered[name].median()),
                "p99": float(engineered[name].quantile(0.99)),
                "missing_rate": 0.0,
            }
            for name in FEATURE_NAMES
        ],
        "permutation_importance": importance,
    }


def train_behavioral_candidate(
    features: pd.DataFrame,
    target: pd.Series,
    provenance: dict[str, Any],
    *,
    model_dir: Path = MODEL_DIR,
    report_dir: Path = REPORT_DIR,
    bootstrap_repeats: int = 500,
    iterations: int = BEHAVIORAL_HGB_ITERATIONS,
) -> dict[str, Any]:
    """Train and compare the rich behavioral model without promoting it."""
    if list(features.columns) != TAIWAN_MODEL_INPUT_COLUMNS:
        raise ValueError("Behavioral source columns do not match the frozen Taiwan contract")
    if len(features) < 100 or target.nunique() != 2:
        raise ValueError("Behavioral training requires at least 100 rows and both target classes")
    (train_x, train_y), (validation_x, validation_y), (test_x, test_y) = frozen_split(
        features, target
    )

    validation_models: dict[str, dict[str, Any]] = {}
    fitted: dict[str, Any] = {}
    for name, model in _candidate_models(iterations).items():
        model.fit(train_x, train_y)
        score = model.predict_proba(validation_x)[:, 1]
        validation_models[name] = _metrics(validation_y, score, _threshold(validation_y, score))
        fitted[name] = model
    best_auc = max(metrics["roc_auc"] for metrics in validation_models.values())
    eligible = {
        name: metrics
        for name, metrics in validation_models.items()
        if metrics["roc_auc"] >= best_auc - 0.02
    }
    champion_name = min(eligible, key=lambda name: (eligible[name]["brier_score"], name))
    validation_score = fitted[champion_name].predict_proba(validation_x)[:, 1]
    threshold = _threshold(validation_y, validation_score)

    champion = _candidate_models(iterations)[champion_name]
    champion.fit(pd.concat([train_x, validation_x]), pd.concat([train_y, validation_y]))
    test_score = champion.predict_proba(test_x)[:, 1]
    test_metrics = _metrics(test_y, test_score, threshold)
    test_metrics["confidence_intervals"] = _bootstrap_intervals(
        test_y, test_score, bootstrap_repeats
    )
    test_metrics.update(_test_diagnostics(champion, test_x, test_y, test_score))
    v3_score, v3_metadata = _v3_probability(test_x)
    v3_metrics = _metrics(test_y, v3_score, float(v3_metadata["selected_threshold"]))
    comparison = _paired_bootstrap(test_y, test_score, v3_score, bootstrap_repeats)

    model_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    model_path = model_dir / CANDIDATE_MODEL_PATH.name
    schema_path = model_dir / CANDIDATE_SCHEMA_PATH.name
    report_path = report_dir / CANDIDATE_REPORT_PATH.name
    joblib.dump(champion, model_path, compress=3)
    schema = {
        "raw_input_columns": TAIWAN_MODEL_INPUT_COLUMNS,
        "engineered_features": FEATURE_NAMES,
        "protected_attributes_excluded": provenance["protected_attributes_excluded"],
        "target": TARGET,
        "target_definition": provenance["target_definition"],
        "prediction_horizon": provenance["prediction_horizon"],
    }
    _write_json(schema_path, schema)
    payload = {
        "classification": "Source-coherent v4 behavioral primary; educational use only",
        "trained_at": datetime.now(UTC).isoformat(),
        "source": provenance,
        "split": {"train": len(train_x), "validation": len(validation_x), "test": len(test_x)},
        "champion": champion_name,
        "selected_threshold": threshold,
        "validation_models": validation_models,
        "untouched_test_metrics": test_metrics,
        "v3_two_feature_benchmark": {
            "model_version": v3_metadata["model_version"],
            "metrics_on_same_test_rows": v3_metrics,
        },
        "paired_comparison": comparison,
        "model_checksum": _sha256(model_path),
        "dataset_checksum": hashlib.sha256(
            pd.concat([features, target.rename(TARGET)], axis=1)
            .to_csv(index=False, lineterminator="\n")
            .encode()
        ).hexdigest(),
        "schema": schema,
        "schema_checksum": _canonical_sha256(schema),
        "promotion_gate": {
            "status": "application_primary",
            "rule": (
                "Promoted from v3 after paired improvement, inference-contract migration, "
                "governance review and full local release gates; production lending remains prohibited"
            ),
        },
        "limitations": [
            "Random within-source splitting is not future-vintage validation.",
            "The 2005 Taiwan source does not establish India or current-population portability.",
            "Limit response and economics remain simulated rather than causal observations.",
        ],
    }
    payload["model_version"] = f"limitiq-behavioral-4.0.0-{payload['model_checksum'][:12]}"
    payload["dataset_version"] = f"uci-350-behavioral-{payload['dataset_checksum'][:12]}"
    _write_json(report_path, payload)
    metadata = {
        key: payload[key]
        for key in (
            "model_version",
            "dataset_version",
            "classification",
            "trained_at",
            "champion",
            "selected_threshold",
            "model_checksum",
            "dataset_checksum",
            "schema_checksum",
            "schema",
            "promotion_gate",
            "limitations",
        )
    }
    metadata["artifact_checksums"] = {
        model_path.name: _sha256(model_path),
        schema_path.name: _text_sha256(schema_path),
        report_path.name: _text_sha256(report_path),
    }
    _write_json(model_dir / CANDIDATE_METADATA_PATH.name, metadata)
    return payload


def _optimizer_stress_evidence(
    profiles: pd.DataFrame,
    probabilities: np.ndarray,
    metadata: dict[str, Any],
    assumptions: PolicyAssumptions,
) -> dict[str, Any]:
    """Build deterministic finite-difference evidence for one binding portfolio constraint."""
    from limitiq.optimizer import recommend_portfolio, summarize_portfolio

    frame = profiles[MODEL_FEATURES + ["current_limit_inr", "current_balance_inr"]]
    account_ids = profiles["account_id"].tolist()
    stressed = replace(assumptions, max_higher_risk_increase_share=0.05)
    stressed_decisions = recommend_portfolio(frame, probabilities, account_ids, stressed)
    stressed_summary = summarize_portfolio(stressed_decisions)
    cap_accounts = int(len(stressed_decisions) * stressed.max_higher_risk_increase_share)
    activity_accounts = sum(
        decision.increase_pct > 0 and decision.risk_band in {"Moderate", "High", "Very high"}
        for decision in stressed_decisions
    )
    relaxed = replace(
        stressed,
        max_higher_risk_increase_share=(cap_accounts + 1) / len(stressed_decisions),
    )
    relaxed_summary = summarize_portfolio(
        recommend_portfolio(frame, probabilities, account_ids, relaxed)
    )
    shadow_price = (
        relaxed_summary["incremental_contribution"] - stressed_summary["incremental_contribution"]
    )
    evidence = {
        "classification": (
            "Deterministic synthetic optimizer stress; finite-difference shadow price, "
            "not an LP dual or observed impact"
        ),
        "model_version": metadata["model_version"],
        "dataset_version": metadata["dataset_version"],
        "model_checksum": metadata["model_checksum"],
        "dataset_checksum": metadata["dataset_checksum"],
        "random_seed": SEED,
        "assumptions": stressed.to_dict(),
        "summary": stressed_summary,
        "binding_constraint": {
            "name": "Portfolio higher-risk concentration cap",
            "activity_accounts": activity_accounts,
            "cap_accounts": cap_accounts,
            "slack_accounts": cap_accounts - activity_accounts,
            "binding": activity_accounts == cap_accounts,
            "shadow_price_inr_per_additional_account": shadow_price,
            "method": (
                "Re-optimize after relaxing the integer cap by exactly one account; "
                "contribution difference is the finite-difference shadow price."
            ),
        },
        "limitations": [
            "All accounts, affordability fields, actions and economics are synthetic.",
            "The shadow price is a discrete finite difference, not a continuous solver dual.",
            "No causal customer response or realized financial outcome is claimed.",
        ],
    }
    if not evidence["binding_constraint"]["binding"] or shadow_price <= 0:
        raise RuntimeError(
            "Configured optimizer stress must produce a binding, valuable constraint"
        )
    return evidence


def write_behavioral_demo(model: Any, metadata: dict[str, Any]) -> dict[str, Any]:
    """Score and optimize the deterministic rich-history demonstration portfolio."""
    from limitiq.optimizer import portfolio_sensitivity, recommend_portfolio, summarize_portfolio

    profiles = synthetic_behavioral_profiles()
    probabilities = model.predict_proba(profiles[TAIWAN_MODEL_INPUT_COLUMNS])[:, 1]
    assumptions = PolicyAssumptions()
    decisions = recommend_portfolio(
        profiles[MODEL_FEATURES + ["current_limit_inr", "current_balance_inr"]],
        probabilities,
        profiles["account_id"].tolist(),
        assumptions,
    )
    output = profiles.copy()
    output["source_dataset"] = "taiwan_credit"
    output["source_name"] = "UCI Default of Credit Card Clients"
    output["missing_model_fields"] = ""
    rows = [decision.to_dict() for decision in decisions]
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
        output[column] = [row[column] for row in rows]
    output["reason_codes"] = [" | ".join(item.reason_codes) for item in decisions]
    output["policy_checks"] = [json.dumps(item.policy_checks) for item in decisions]
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    temporary = BEHAVIORAL_DEMO_PATH.with_suffix(".csv.tmp")
    output.to_csv(temporary, index=False, lineterminator="\n")
    temporary.replace(BEHAVIORAL_DEMO_PATH)
    optimizer_stress = _optimizer_stress_evidence(profiles, probabilities, metadata, assumptions)
    _write_json(OPTIMIZER_STRESS_PATH, optimizer_stress)
    payload = {
        "classification": "Deterministic synthetic rich-history scenario; not observed impact",
        "model_version": metadata["model_version"],
        "dataset_version": metadata["dataset_version"],
        "model_checksum": metadata["model_checksum"],
        "dataset_checksum": metadata["dataset_checksum"],
        "random_seed": SEED,
        "generated_at": datetime.now(UTC).isoformat(),
        "demo_rows": len(output),
        "demo_portfolio_sha256": _text_sha256(BEHAVIORAL_DEMO_PATH),
        "optimizer_stress_sha256": _text_sha256(OPTIMIZER_STRESS_PATH),
        "assumptions": assumptions.to_dict(),
        "summary": summarize_portfolio(decisions),
        "sensitivity": portfolio_sensitivity(
            profiles[MODEL_FEATURES + ["current_limit_inr", "current_balance_inr"]],
            probabilities,
            profiles["account_id"].tolist(),
            assumptions,
        ),
        "limitations": [
            "All histories and account identifiers are deterministic synthetic data.",
            "Income, obligations, FOIR, line response, LGD, CCF, revenue and costs are synthetic assumptions.",
            "The expected-loss ceiling is a PD × LGD rate ceiling, not a currency loss cap.",
            "The Taiwan model is not validated for India or production lending.",
        ],
    }
    _write_json(BEHAVIORAL_SIMULATION_PATH, payload)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the LimitIQ v4 behavioral primary")
    parser.add_argument("--bootstrap-repeats", type=int, default=500)
    parser.add_argument("--demo-only", action="store_true")
    args = parser.parse_args()
    metadata = json.loads(CANDIDATE_METADATA_PATH.read_text(encoding="utf-8"))
    if args.demo_only:
        if _sha256(CANDIDATE_MODEL_PATH) != metadata["model_checksum"]:
            raise RuntimeError("Behavioral model checksum mismatch")
        payload = json.loads(CANDIDATE_REPORT_PATH.read_text(encoding="utf-8"))
    else:
        features, target, provenance = load_behavioral_source()
        payload = train_behavioral_candidate(
            features, target, provenance, bootstrap_repeats=args.bootstrap_repeats
        )
        metadata = json.loads(CANDIDATE_METADATA_PATH.read_text(encoding="utf-8"))
    write_behavioral_demo(joblib.load(CANDIDATE_MODEL_PATH), metadata)  # noqa: S301
    print(
        json.dumps(
            {
                "model_version": payload["model_version"],
                "champion": payload["champion"],
                "metrics": {
                    name: payload["untouched_test_metrics"][name]
                    for name in ("roc_auc", "pr_auc", "brier_score", "log_loss")
                },
                "paired_comparison": payload["paired_comparison"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
