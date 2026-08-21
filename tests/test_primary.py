from __future__ import annotations

import hashlib
import json

import joblib
import numpy as np
import pandas as pd
import pytest

from limitiq.config import RAW_DIR, ROOT
from limitiq.multisource import MODEL_FEATURES, TARGET
from limitiq.primary import (
    ACTIVE_FEATURES,
    PRIMARY_DEMO_PATH,
    PRIMARY_METADATA_PATH,
    PRIMARY_MODEL_PATH,
    PRIMARY_REPORT_PATH,
    PRIMARY_SCHEMA_PATH,
    PRIMARY_SIMULATION_PATH,
    load_primary_source,
    synthetic_primary_profiles,
    train_primary,
    write_primary_demo,
)


def _fixture(rows: int = 600) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    delinquency = rng.integers(0, 5, rows)
    utilization = rng.uniform(0, 1.5, rows)
    event_probability = 1 / (1 + np.exp(-(-2.5 + 0.65 * delinquency + utilization)))
    frame = pd.DataFrame(
        {
            "delinquency_count": delinquency,
            "utilization": utilization,
            "debt_to_income": np.nan,
            "credit_lines": np.nan,
            "income_inr": np.nan,
            "credit_age_months": np.nan,
            "region": "asia",
            TARGET: rng.binomial(1, event_probability),
        }
    )
    return frame[[*MODEL_FEATURES, TARGET]]


def _provenance() -> dict[str, object]:
    return {
        "dataset": "Deterministic test fixture",
        "target_definition": "Default payment in the following month",
        "prediction_horizon": "One month",
    }


def _sha256(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_cached_primary_source_has_one_explicit_target_and_horizon() -> None:
    if not (RAW_DIR / "default_of_credit_card_clients.xls").exists():
        pytest.skip(
            "Open UCI source is fetched explicitly; release artifacts are tested separately"
        )
    frame, provenance = load_primary_source()

    assert len(frame) == 30_000
    assert list(frame.columns) == [*MODEL_FEATURES, TARGET]
    assert set(frame[TARGET].unique()) == {0, 1}
    assert frame["region"].eq("asia").all()
    assert frame[ACTIVE_FEATURES].notna().all().all()
    assert provenance["prediction_horizon"] == "One month"
    assert provenance["license"] == "CC BY 4.0"
    assert len(str(provenance["source_sha256"])) == 64


def test_release_primary_artifacts_are_checksum_bound_and_sane() -> None:
    metadata = json.loads(PRIMARY_METADATA_PATH.read_text())
    report = json.loads(PRIMARY_REPORT_PATH.read_text())
    simulation = json.loads(PRIMARY_SIMULATION_PATH.read_text())

    assert metadata["artifact_checksums"] == {
        PRIMARY_MODEL_PATH.name: _sha256(PRIMARY_MODEL_PATH),
        PRIMARY_SCHEMA_PATH.name: _sha256(PRIMARY_SCHEMA_PATH),
        PRIMARY_REPORT_PATH.name: _sha256(PRIMARY_REPORT_PATH),
    }
    assert report["model_checksum"] == _sha256(PRIMARY_MODEL_PATH)
    assert report["source"]["target_definition"] == "Default payment in the following month"
    assert report["source"]["prediction_horizon"] == "One month"
    assert report["split"]["untouched_test"] == 6_000
    assert 0 <= report["untouched_test_metrics"]["brier_score"] <= 1
    assert len(report["untouched_test_metrics"]["roc_points"]["fpr"]) >= 2
    assert len(report["untouched_test_metrics"]["permutation_importance"]) == 2
    assert len(report["untouched_test_metrics"]["segments"]) == 6
    assert len(report["untouched_test_metrics"]["feature_summary"]) == 2
    assert simulation["model_checksum"] == metadata["model_checksum"]
    assert simulation["dataset_checksum"] == metadata["dataset_checksum"]
    assert simulation["demo_rows"] == 1_200
    assert (
        simulation["demo_portfolio_sha256"]
        == hashlib.sha256(PRIMARY_DEMO_PATH.read_text(encoding="utf-8").encode()).hexdigest()
    )


def test_v3_release_checksum_manifest_matches_artifacts() -> None:
    manifest = ROOT / "release" / "checksums-v3.0.0.sha256"
    entries = [line.split(maxsplit=1) for line in manifest.read_text().splitlines() if line]

    assert {relative for _, relative in entries} == {
        "models/primary_champion.joblib",
        "models/primary_metadata.json",
        "models/primary_feature_schema.json",
        "reports/primary_model.json",
        "reports/primary_policy_simulation.json",
        "data/processed/primary_demo_portfolio.csv",
        "models/global_metadata.json",
        "reports/global_feature_evidence.json",
        "data/source_manifest.json",
        "sbom/limitiq.cdx.json",
    }
    for expected, relative_path in entries:
        assert _sha256(ROOT / relative_path) == expected


def test_primary_demo_is_deterministic_source_coherent_and_checksum_bound(tmp_path) -> None:
    profiles = synthetic_primary_profiles()
    assert len(profiles) == 1_200
    assert profiles["source_dataset"].eq("taiwan_credit").all()
    assert profiles["region"].eq("asia").all()
    assert (
        profiles[["debt_to_income", "credit_lines", "income_inr", "credit_age_months"]]
        .isna()
        .all()
        .all()
    )

    model = joblib.load(PRIMARY_MODEL_PATH)  # noqa: S301
    metadata = json.loads(PRIMARY_METADATA_PATH.read_text())
    payloads = []
    hashes = []
    for run in ("one", "two"):
        root = tmp_path / run
        payload = write_primary_demo(
            model,
            metadata,
            processed_dir=root / "data",
            report_dir=root / "reports",
        )
        portfolio = root / "data" / PRIMARY_DEMO_PATH.name
        assert (root / "reports" / PRIMARY_SIMULATION_PATH.name).exists()
        assert payload["model_version"] == metadata["model_version"]
        assert payload["dataset_checksum"] == metadata["dataset_checksum"]
        assert payload["demo_rows"] == 1_200
        assert (
            payload["demo_portfolio_sha256"]
            == hashlib.sha256(portfolio.read_text(encoding="utf-8").encode()).hexdigest()
        )
        payloads.append({key: value for key, value in payload.items() if key != "generated_at"})
        hashes.append(_sha256(portfolio))
    assert payloads[0] == payloads[1]
    assert hashes[0] == hashes[1]


def test_primary_training_is_reproducible_and_emits_auditable_artifacts(tmp_path) -> None:
    frame = _fixture()
    runs = []
    for run in ("one", "two"):
        root = tmp_path / run
        payload = train_primary(
            frame,
            _provenance(),
            model_dir=root / "models",
            report_dir=root / "reports",
            bootstrap_repeats=20,
            challenger_iterations=30,
        )
        metadata = json.loads((root / "models" / "primary_metadata.json").read_text())
        report = json.loads((root / "reports" / "primary_model.json").read_text())
        model = joblib.load(root / "models" / "primary_champion.joblib")  # noqa: S301
        probability = model.predict_proba(frame[MODEL_FEATURES])[:, 1]

        assert np.isfinite(probability).all()
        assert ((probability >= 0) & (probability <= 1)).all()
        assert report["role"] == "Primary decision-model candidate"
        assert report["global_model_role"].endswith("transportability research benchmark")
        assert report["split"] == {"train": 360, "validation": 120, "untouched_test": 120}
        assert report["feature_schema"]["active_decision_features"] == ACTIVE_FEATURES
        assert set(metadata["artifact_checksums"]) == {
            "primary_champion.joblib",
            "primary_feature_schema.json",
            "primary_model.json",
        }
        intervals = report["untouched_test_metrics"]["confidence_intervals"]
        assert set(intervals) == {"roc_auc", "pr_auc", "brier_score", "log_loss"}
        assert all(item["lower_95"] <= item["upper_95"] for item in intervals.values())
        runs.append(payload)

    stable_keys = (
        "model_checksum",
        "dataset_checksum",
        "feature_schema_checksum",
        "training_config_checksum",
        "champion",
        "selected_threshold",
        "validation_models",
        "untouched_test_metrics",
    )
    assert {key: runs[0][key] for key in stable_keys} == {key: runs[1][key] for key in stable_keys}


@pytest.mark.parametrize("bad_target", [2, np.nan])
def test_primary_training_rejects_invalid_targets(tmp_path, bad_target) -> None:
    frame = _fixture()
    frame.loc[0, TARGET] = bad_target

    with pytest.raises(ValueError, match="target"):
        train_primary(
            frame,
            _provenance(),
            model_dir=tmp_path / "models",
            report_dir=tmp_path / "reports",
            bootstrap_repeats=20,
            challenger_iterations=20,
        )
