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
    _paired_bootstrap,
)
from limitiq.config import ROOT
from limitiq.features import TAIWAN_MODEL_INPUT_COLUMNS


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


def test_behavioral_primary_artifacts_are_checksum_bound_and_sane() -> None:
    metadata = json.loads(CANDIDATE_METADATA_PATH.read_text(encoding="utf-8"))
    report = json.loads(CANDIDATE_REPORT_PATH.read_text(encoding="utf-8"))
    simulation = json.loads(BEHAVIORAL_SIMULATION_PATH.read_text(encoding="utf-8"))
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
    score = joblib.load(CANDIDATE_MODEL_PATH).predict_proba(
        demo[TAIWAN_MODEL_INPUT_COLUMNS].head(5)
    )[:, 1]
    assert np.all((0 <= score) & (score <= 1))


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
