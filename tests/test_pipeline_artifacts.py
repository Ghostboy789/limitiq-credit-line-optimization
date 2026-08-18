from __future__ import annotations

import hashlib
import json
import shutil

import joblib
import numpy as np
import pandas as pd

from limitiq.config import MODEL_DIR, PROCESSED_DIR, REPORT_DIR, ROOT, SEED
from limitiq.features import EXPOSURE_COLUMNS, MODEL_INPUT_COLUMNS, TAIWAN_MODEL_INPUT_COLUMNS
from limitiq.pipeline import _model_candidates, _save_model_ready_splits, synthetic_account_id
from limitiq.reporting import build_reports


def test_data_quality_evidence_matches_source() -> None:
    quality = json.loads((REPORT_DIR / "data_quality.json").read_text(encoding="utf-8"))
    assert quality["source_rows"] == 30_000
    assert quality["clean_rows"] == 30_000
    assert quality["missing_cells"] == 0
    assert quality["license"] == "CC BY 4.0"
    assert quality["source_currency"] == "TWD"
    assert quality["model_currency"] == "INR"
    assert quality["twd_to_inr"] == 2.97
    assert quality["dataset_version"].endswith("-inr297")


def test_model_checksum_and_versions_are_bound() -> None:
    metadata = json.loads((MODEL_DIR / "metadata.json").read_text(encoding="utf-8"))
    checksum = hashlib.sha256((MODEL_DIR / "champion.joblib").read_bytes()).hexdigest()
    assert checksum == metadata["model_checksum"]
    assert metadata["dataset_checksum"].startswith("30c6be3abd8d")
    assert metadata["split"] == {"train": 18_000, "validation": 6_000, "test": 6_000}


def test_legacy_inference_probability_bounds_and_schema() -> None:
    model = joblib.load(MODEL_DIR / "champion.joblib")
    demo = pd.read_csv(PROCESSED_DIR / "demo_portfolio.csv", nrows=25)
    probability = model.predict_proba(demo[TAIWAN_MODEL_INPUT_COLUMNS])[:, 1]
    assert probability.shape == (25,)
    assert np.all((probability >= 0) & (probability <= 1))


def test_global_inference_probability_bounds_and_schema() -> None:
    model = joblib.load(MODEL_DIR / "global_champion.joblib")
    demo = pd.read_csv(PROCESSED_DIR / "global_demo_portfolio.csv", nrows=25)
    probability = model.predict_proba(demo[MODEL_INPUT_COLUMNS])[:, 1]
    assert probability.shape == (25,)
    assert np.all((probability >= 0) & (probability <= 1))
    assert set(EXPOSURE_COLUMNS) <= set(demo)


def test_synthetic_ids_are_deterministic_and_not_source_ids() -> None:
    assert synthetic_account_id(123) == synthetic_account_id(123)
    assert synthetic_account_id(123) != synthetic_account_id(124)
    assert synthetic_account_id(123).startswith("LIQ-")
    assert "123" not in synthetic_account_id(123)


def test_committed_demo_has_no_demographics_or_source_ids() -> None:
    demo = pd.read_csv(PROCESSED_DIR / "demo_portfolio.csv", nrows=2)
    assert not {"ID", "SEX", "EDUCATION", "MARRIAGE", "AGE", "default_next_month"} & set(
        demo.columns
    )
    assert demo["account_id"].str.match(r"^LIQ-[A-F0-9]{10}$").all()

    global_demo = pd.read_csv(PROCESSED_DIR / "global_demo_portfolio.csv")
    assert not {
        "ID",
        "SEX",
        "EDUCATION",
        "MARRIAGE",
        "AGE",
        "default",
        "default_next_month",
    } & set(global_demo)
    assert global_demo["account_id"].is_unique
    assert global_demo["account_id"].str.match(r"^LIQ-[0-9]{6}$").all()


def test_real_candidate_pipelines_train_reproducibly() -> None:
    demo = pd.read_csv(PROCESSED_DIR / "demo_portfolio.csv", nrows=240)
    x = demo[TAIWAN_MODEL_INPUT_COLUMNS]
    y = pd.Series(np.tile([0, 0, 1], 80), index=x.index)
    for name in _model_candidates():
        first_model = _model_candidates()[name].fit(x, y)
        second_model = _model_candidates()[name].fit(x, y)
        first = first_model.predict_proba(x)[:, 1]
        second = second_model.predict_proba(x)[:, 1]
        assert np.array_equal(first, second), name


def test_model_ready_splits_are_saved_with_metadata(tmp_path) -> None:
    demo = pd.read_csv(PROCESSED_DIR / "demo_portfolio.csv", nrows=9)
    target = pd.Series(np.tile([0, 1, 0], 3))
    metadata = _save_model_ready_splits(
        {
            "train": (demo[TAIWAN_MODEL_INPUT_COLUMNS].iloc[:5], target.iloc[:5]),
            "validation": (demo[TAIWAN_MODEL_INPUT_COLUMNS].iloc[5:7], target.iloc[5:7]),
            "test": (demo[TAIWAN_MODEL_INPUT_COLUMNS].iloc[7:], target.iloc[7:]),
        },
        "test-dataset",
        tmp_path,
    )
    assert metadata["random_seed"] == SEED
    assert metadata["files"]["train"]["rows"] == 5
    assert list(pd.read_csv(tmp_path / "train.csv").columns) == [
        *TAIWAN_MODEL_INPUT_COLUMNS,
        "default_next_month",
    ]


def test_reports_are_actually_generated_and_nonempty(tmp_path) -> None:
    report_dir = tmp_path / "reports"
    model_dir = tmp_path / "models"
    report_dir.mkdir()
    model_dir.mkdir()
    for name in ("data_quality.json", "eda.json", "policy_simulation.json"):
        shutil.copyfile(REPORT_DIR / name, report_dir / name)
    shutil.copyfile(MODEL_DIR / "metadata.json", model_dir / "metadata.json")
    build_reports(report_dir, model_dir)
    expected = [
        "executive_report.html",
        "executive_report.pdf",
        "data_quality_report.html",
        "eda_report.html",
        "model_performance_report.html",
        "policy_simulation_report.html",
        "financial_impact_analysis.html",
    ]
    for name in expected:
        assert (report_dir / name).stat().st_size > 1_000
    assert (report_dir / "executive_report.pdf").read_bytes().startswith(b"%PDF")
    assert "One-at-a-time sensitivity" in (report_dir / "policy_simulation_report.html").read_text(
        encoding="utf-8"
    )


def test_external_validation_evidence_is_present_and_sane() -> None:
    evidence = json.loads((REPORT_DIR / "external_validation.json").read_text(encoding="utf-8"))
    keys = {item["dataset"] for item in evidence["comparison"]}
    assert "Statlog (German Credit Data)" in keys
    assert "Australian Credit Approval" in keys
    assert evidence["random_seed"] == SEED
    for item in evidence["comparison"]:
        assert 0.0 < item["roc_auc"] <= 1.0
        assert 0.0 <= item["brier_score"] < 0.5
        assert item["rows"] > 0
    assert (REPORT_DIR / "external_validation_report.html").stat().st_size > 1_000


def test_global_model_evidence_is_present_checksum_bound_and_sane() -> None:
    metadata_path = MODEL_DIR / "global_metadata.json"
    report_path = REPORT_DIR / "global_model.json"
    model_path = MODEL_DIR / "global_champion.joblib"
    html_path = REPORT_DIR / "global_model_report.html"
    for path in (metadata_path, report_path, model_path, html_path):
        assert path.exists() and path.stat().st_size > 1_000

    evidence = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert evidence == json.loads(report_path.read_text(encoding="utf-8"))
    assert hashlib.sha256(model_path.read_bytes()).hexdigest() == evidence["model_checksum"]
    assert evidence["random_seed"] == SEED
    assert evidence["rows"] >= 1_500_000
    assert evidence["row_budget"]["minimum_satisfied"] is True
    assert len(evidence["row_budget"]["datasets_above_200k"]) >= 2
    assert len(evidence["datasets"]) == 7
    assert len(evidence["training_sources"]) == 6
    assert len(evidence["reference_sources"]) == 1
    assert set(evidence["training_sources"]) == set(evidence["per_market_test_metrics"])
    assert all(
        evidence["datasets"][key]["role"] == "training" for key in evidence["training_sources"]
    )
    assert all(
        evidence["datasets"][key]["role"] == "reference_only"
        for key in evidence["reference_sources"]
    )
    assert sum(evidence["split"].values()) == evidence["rows"]

    for metrics in [evidence["test_metrics"], *evidence["per_market_test_metrics"].values()]:
        assert 0 < metrics["roc_auc"] <= 1
        assert 0 < metrics["pr_auc"] <= 1
        assert 0 <= metrics["brier_score"] < 0.5
        roc = metrics["roc_points"]
        assert 2 <= len(roc["fpr"]) == len(roc["tpr"]) <= 250
        assert all(0 <= value <= 1 for value in [*roc["fpr"], *roc["tpr"]])
        calibration = metrics["calibration_points"]
        assert calibration and all(
            0 <= point["mean_predicted"] <= 1 and 0 <= point["observed_rate"] <= 1
            for point in calibration
        )

    macro = evidence["macro_test_metrics"]
    assert {"roc_auc", "pr_auc", "brier_score", "log_loss"} <= set(macro)
    assert (
        sum(item["accounts"] for item in evidence["per_market_test_metrics"].values())
        == evidence["split"]["test"]
    )

    owner_cleared = {
        key
        for key, item in evidence["datasets"].items()
        if str(item["license_status"]).startswith("owner-cleared")
    }
    gate = evidence["publication_gate"]
    assert gate["status"] == "cleared"
    assert set(gate.get("sources", [])) == owner_cleared
    assert gate.get("reason")
    assert gate.get("resolution_basis")

    simulation = json.loads((REPORT_DIR / "global_policy_simulation.json").read_text("utf-8"))
    demo_path = PROCESSED_DIR / "global_demo_portfolio.csv"
    assert simulation["model_version"] == evidence["model_version"]
    assert simulation["dataset_checksum"] == evidence["dataset_checksum"]
    assert simulation["dataset_version"] == evidence["dataset_version"]
    assert simulation["model_checksum"] == evidence["model_checksum"]
    assert simulation["random_seed"] == SEED
    assert simulation["demo_rows"] == len(pd.read_csv(demo_path))
    normalized = demo_path.read_text(encoding="utf-8").encode()
    assert hashlib.sha256(normalized).hexdigest() == simulation["demo_portfolio_sha256"]
    for name in ("global_data_quality_report.html", "global_eda_report.html"):
        assert (REPORT_DIR / name).exists() and (REPORT_DIR / name).stat().st_size > 1_000


def test_global_diagnostic_evidence_is_provenance_bound_and_sane() -> None:
    names = (
        "global_oot_evidence.json",
        "global_leakage_ablation.json",
        "global_feature_evidence.json",
        "global_monitoring_baseline.json",
    )
    payloads = {name: json.loads((REPORT_DIR / name).read_text(encoding="utf-8")) for name in names}
    metadata = json.loads((MODEL_DIR / "global_metadata.json").read_text(encoding="utf-8"))
    assert all((REPORT_DIR / name).stat().st_size > 1_000 for name in names)
    for payload in payloads.values():
        provenance = payload.get("provenance", payload)
        assert provenance["random_seed"] == SEED
        assert provenance["model_checksum"]
        assert provenance.get("model_version") == metadata["model_version"]
        assert provenance.get("dataset_version") == "global-7-94bb4c0ad0f1"
        assert provenance.get("dataset_checksum")
    assert "status-at-extract" in payloads[names[0]]["classification"]
    assert payloads[names[0]]["provenance"]["random_seed"] == SEED
    assert payloads[names[1]]["provenance"]["model_checksum"]
    feature = payloads[names[2]]
    assert feature["provenance"]["model_checksum"]
    assert all("pooled_mean_roc_auc_drop" in item for item in feature["permutation_importance"])
    assert all(item["sources"] and item["points"] for item in feature["partial_dependence"])
    monitoring = payloads[names[3]]
    assert monitoring["snapshot"]["sources"] == 6
    assert len(monitoring["missingness"]) == 6
    assert "german_credit" not in {item["source"] for item in monitoring["missingness"]}
    assert "illustrative" in monitoring["evidence_boundary"].lower()


def test_no_unresolved_placeholder_tokens_in_user_artifacts() -> None:
    paths = [ROOT / "README.md", *list((ROOT / "docs").glob("*.md"))]
    forbidden = ("TODO", "TBD", "CHANGEME", "example.com/live")
    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert not any(token in text for token in forbidden), path
