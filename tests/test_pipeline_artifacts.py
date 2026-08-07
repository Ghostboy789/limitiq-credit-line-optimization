from __future__ import annotations

import hashlib
import json
import shutil

import joblib
import numpy as np
import pandas as pd

from limitiq.config import MODEL_DIR, PROCESSED_DIR, REPORT_DIR, ROOT, SEED
from limitiq.features import MODEL_INPUT_COLUMNS
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


def test_inference_probability_bounds_and_schema() -> None:
    model = joblib.load(MODEL_DIR / "champion.joblib")
    demo = pd.read_csv(PROCESSED_DIR / "demo_portfolio.csv", nrows=25)
    probability = model.predict_proba(demo[MODEL_INPUT_COLUMNS])[:, 1]
    assert probability.shape == (25,)
    assert np.all((probability >= 0) & (probability <= 1))


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


def test_real_candidate_pipelines_train_reproducibly() -> None:
    demo = pd.read_csv(PROCESSED_DIR / "demo_portfolio.csv", nrows=240)
    x = demo[MODEL_INPUT_COLUMNS]
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
            "train": (demo[MODEL_INPUT_COLUMNS].iloc[:5], target.iloc[:5]),
            "validation": (demo[MODEL_INPUT_COLUMNS].iloc[5:7], target.iloc[5:7]),
            "test": (demo[MODEL_INPUT_COLUMNS].iloc[7:], target.iloc[7:]),
        },
        "test-dataset",
        tmp_path,
    )
    assert metadata["random_seed"] == SEED
    assert metadata["files"]["train"]["rows"] == 5
    assert list(pd.read_csv(tmp_path / "train.csv").columns) == [
        *MODEL_INPUT_COLUMNS,
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


def test_no_unresolved_placeholder_tokens_in_user_artifacts() -> None:
    paths = [ROOT / "README.md", *list((ROOT / "docs").glob("*.md"))]
    forbidden = ("TODO", "TBD", "CHANGEME", "example.com/live")
    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert not any(token in text for token in forbidden), path
