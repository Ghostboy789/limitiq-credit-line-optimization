from __future__ import annotations

import hashlib
import json

import joblib
import numpy as np
import pandas as pd

from limitiq.config import MODEL_DIR, PROCESSED_DIR, REPORT_DIR, ROOT, SEED
from limitiq.features import MODEL_INPUT_COLUMNS
from limitiq.pipeline import synthetic_account_id


def test_data_quality_evidence_matches_source() -> None:
    quality = json.loads((REPORT_DIR / "data_quality.json").read_text(encoding="utf-8"))
    assert quality["source_rows"] == 30_000
    assert quality["clean_rows"] == 30_000
    assert quality["missing_cells"] == 0
    assert quality["license"] == "CC BY 4.0"


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


def test_training_configuration_and_predictions_are_reproducible() -> None:
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    demo = pd.read_csv(PROCESSED_DIR / "demo_portfolio.csv", nrows=400)
    x = demo[MODEL_INPUT_COLUMNS]
    y = (demo["pd"] >= demo["pd"].median()).astype(int)
    first_model = make_pipeline(StandardScaler(), LogisticRegression(random_state=SEED))
    second_model = make_pipeline(StandardScaler(), LogisticRegression(random_state=SEED))
    first = first_model.fit(x, y).predict_proba(x)[:, 1]
    second = second_model.fit(x, y).predict_proba(x)[:, 1]
    assert np.array_equal(first, second)


def test_reports_are_generated_and_nonempty() -> None:
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
        assert (REPORT_DIR / name).stat().st_size > 1_000
    assert (REPORT_DIR / "executive_report.pdf").read_bytes().startswith(b"%PDF")


def test_no_unresolved_placeholder_tokens_in_user_artifacts() -> None:
    paths = [ROOT / "README.md", *list((ROOT / "docs").glob("*.md"))]
    forbidden = ("TODO", "TBD", "CHANGEME", "example.com/live")
    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert not any(token in text for token in forbidden), path
