from __future__ import annotations

import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from limitiq.behavioral import (
    BEHAVIORAL_DEMO_PATH,
    BEHAVIORAL_SIMULATION_PATH,
    CANDIDATE_METADATA_PATH,
    CANDIDATE_MODEL_PATH,
    CANDIDATE_REPORT_PATH,
    CANDIDATE_SCHEMA_PATH,
    OPTIMIZER_STRESS_PATH,
    _canonical_sha256,
    _paired_bootstrap,
    _text_sha256,
    synthetic_behavioral_profiles,
    train_behavioral_candidate,
)
from limitiq.config import ROOT
from limitiq.features import TAIWAN_MODEL_INPUT_COLUMNS
from limitiq.multisource import TARGET


def test_paired_bootstrap_is_deterministic_and_directional() -> None:
    truth = pd.Series(([0] * 80) + ([1] * 20))
    benchmark = np.full(100, 0.2)
    candidate = benchmark.copy()
    candidate[:80] = np.linspace(0.02, 0.18, 80)
    candidate[80:] = np.linspace(0.65, 0.95, 20)
    first = _paired_bootstrap(truth, candidate, benchmark, 20)
    second = _paired_bootstrap(truth, candidate, benchmark, 20)
    assert first == second
    assert first["roc_auc"]["candidate_minus_v3"] > 0
    assert first["brier_score"]["candidate_minus_v3"] < 0


def test_tiny_end_to_end_training_enforces_selection_and_checksum_contracts(
    tmp_path: Path,
) -> None:
    profiles = synthetic_behavioral_profiles(300)
    features = profiles[TAIWAN_MODEL_INPUT_COLUMNS]
    target = (
        (features["PAY_0"] > 0) | (features["BILL_AMT1"] / features["LIMIT_BAL"] > 0.55)
    ).astype(int)
    provenance = {
        "dataset": "Deterministic synthetic unit-test fixture",
        "source_file": "generated-in-memory",
        "source_sha256": "synthetic",
        "rows": len(features),
        "event_rate": float(target.mean()),
        "geography": "Synthetic",
        "target_definition": "Synthetic repayment-or-utilization outcome",
        "prediction_horizon": "Synthetic next period",
        "protected_attributes_excluded": ["SEX", "EDUCATION", "MARRIAGE", "AGE"],
    }
    model_dir = tmp_path / "models"
    report_dir = tmp_path / "reports"

    payload = train_behavioral_candidate(
        features,
        target,
        provenance,
        model_dir=model_dir,
        report_dir=report_dir,
        iterations=5,
        bootstrap_repeats=5,
    )

    assert payload["split"] == {"train": 180, "validation": 60, "test": 60}
    candidates = payload["validation_models"]
    best_auc = max(metrics["roc_auc"] for metrics in candidates.values())
    eligible = {
        name: metrics
        for name, metrics in candidates.items()
        if metrics["roc_auc"] >= best_auc - 0.02
    }
    expected_champion = min(eligible, key=lambda name: (eligible[name]["brier_score"], name))
    assert payload["champion"] == expected_champion

    model_path = model_dir / CANDIDATE_MODEL_PATH.name
    metadata_path = model_dir / CANDIDATE_METADATA_PATH.name
    schema_path = model_dir / CANDIDATE_SCHEMA_PATH.name
    report_path = report_dir / CANDIDATE_REPORT_PATH.name
    report = json.loads(report_path.read_text(encoding="utf-8"))
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    model_checksum = hashlib.sha256(model_path.read_bytes()).hexdigest()
    dataset_checksum = hashlib.sha256(
        pd.concat([features, target.rename(TARGET)], axis=1)
        .to_csv(index=False, lineterminator="\n")
        .encode()
    ).hexdigest()

    assert report == payload
    assert schema == payload["schema"]
    assert payload["model_checksum"] == metadata["model_checksum"] == model_checksum
    assert payload["dataset_checksum"] == metadata["dataset_checksum"] == dataset_checksum
    assert payload["schema_checksum"] == metadata["schema_checksum"] == _canonical_sha256(schema)
    assert payload["model_version"].endswith(model_checksum[:12])
    assert payload["dataset_version"].endswith(dataset_checksum[:12])
    assert metadata["artifact_checksums"] == {
        model_path.name: model_checksum,
        schema_path.name: _text_sha256(schema_path),
        report_path.name: _text_sha256(report_path),
    }


def test_behavioral_primary_artifacts_are_checksum_bound_and_sane() -> None:
    metadata = json.loads(CANDIDATE_METADATA_PATH.read_text(encoding="utf-8"))
    report = json.loads(CANDIDATE_REPORT_PATH.read_text(encoding="utf-8"))
    simulation = json.loads(BEHAVIORAL_SIMULATION_PATH.read_text(encoding="utf-8"))
    optimizer_stress = json.loads(OPTIMIZER_STRESS_PATH.read_text(encoding="utf-8"))
    assert metadata["promotion_gate"]["status"] == "application_primary"
    assert report["model_version"] == metadata["model_version"]
    assert (
        hashlib.sha256(CANDIDATE_MODEL_PATH.read_bytes()).hexdigest() == metadata["model_checksum"]
    )
    assert report["split"] == {"train": 18_000, "validation": 6_000, "test": 6_000}
    assert 0.5 < report["untouched_test_metrics"]["roc_auc"] <= 1
    assert report["paired_comparison"]["roc_auc"]["lower_95"] > 0
    assert report["paired_comparison"]["brier_score"]["upper_95"] < 0
    assert CANDIDATE_SCHEMA_PATH.exists()
    demo = pd.read_csv(BEHAVIORAL_DEMO_PATH)
    assert len(demo) == simulation["demo_rows"] == 1_200
    assert demo["account_id"].is_unique
    assert not {"ID", "SEX", "EDUCATION", "MARRIAGE", "AGE"} & set(demo)
    assert {
        "income_inr",
        "total_monthly_obligation_inr",
        "debt_to_income",
        "credit_lines",
        "credit_age_months",
    } <= set(demo)
    assert (
        (demo["action"] == "Manual review")
        & demo["reason_codes"].str.contains("Customer-overextension safeguard")
    ).any()
    score = joblib.load(CANDIDATE_MODEL_PATH).predict_proba(
        demo[TAIWAN_MODEL_INPUT_COLUMNS].head(5)
    )[:, 1]
    assert np.all((0 <= score) & (score <= 1))

    assert simulation["summary"]["action_counts"]["Increase 10%"] > 0
    assert simulation["summary"]["action_counts"]["Increase 20%"] > 0
    assert optimizer_stress["binding_constraint"]["binding"] is True
    assert optimizer_stress["binding_constraint"]["shadow_price_inr_per_additional_account"] > 0


def test_v41_release_manifest_matches_current_artifacts() -> None:
    entries = {
        relative: checksum
        for checksum, relative in (
            line.split(maxsplit=1)
            for line in (ROOT / "release" / "checksums-v4.1.0.sha256")
            .read_text(encoding="utf-8")
            .splitlines()
            if line
        )
    }
    required = {
        "models/behavioral_candidate.joblib",
        "models/behavioral_metadata.json",
        "models/behavioral_feature_schema.json",
        "reports/behavioral_model.json",
        "reports/behavioral_policy_simulation.json",
        "data/processed/behavioral_demo_portfolio.csv",
        "models/temporal_champion.joblib",
        "reports/behavioral_optimizer_stress.json",
        "reports/temporal_validation.json",
        "reports/monitoring_replay.json",
        "reports/experiment_replay.json",
        "reports/model_robustness.json",
        "reports/india_validation_readiness.json",
        "docs/INDIA_DATA_CONTRACT.json",
        "reports/executive_report.html",
        "reports/executive_report.pdf",
        "sbom/limitiq.cdx.json",
    }
    assert required <= set(entries)
    for relative, expected in entries.items():
        path = Path(ROOT / relative)
        actual = (
            hashlib.sha256(path.read_bytes()).hexdigest()
            if path.suffix in {".joblib", ".pdf"}
            else hashlib.sha256(path.read_text(encoding="utf-8").encode()).hexdigest()
        )
        assert actual == expected, relative
