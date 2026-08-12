from __future__ import annotations

import io
import json

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from limitiq.config import PROCESSED_DIR
from limitiq.features import BATCH_COLUMNS
from limitiq.web import app

client = TestClient(app)


@pytest.mark.parametrize(
    "path",
    ["/", "/portfolio", "/simulator", "/batch", "/governance", "/reports"],
)
def test_major_pages_render(path: str) -> None:
    response = client.get(path)
    assert response.status_code == 200
    assert "LimitIQ" in response.text
    assert "educational" in response.text.lower()


def test_health_contract_and_security_headers() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["model_version"].startswith("limitiq-global-2.0.0-")
    assert response.json()["dataset_version"].startswith("global-7-")
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"


def test_portfolio_filter_search_sort_and_pagination() -> None:
    demo = pd.read_csv(PROCESSED_DIR / "global_demo_portfolio.csv", nrows=1)
    account_id = demo.loc[0, "account_id"]
    response = client.get(
        "/portfolio",
        params={
            "search": account_id,
            "risk": demo.loc[0, "risk_band"],
            "sort": "pd",
            "direction": "asc",
        },
    )
    assert response.status_code == 200
    assert account_id in response.text
    assert ">1</strong> matching accounts" in response.text


def test_empty_portfolio_state() -> None:
    response = client.get("/portfolio", params={"search": "DOES-NOT-EXIST"})
    assert response.status_code == 200
    assert "No accounts match" in response.text


def test_portfolio_global_delinquency_filters() -> None:
    for value in ("yes", "no", "unknown"):
        response = client.get("/portfolio", params={"delinquency": value})
        assert response.status_code == 200, value


def test_account_decision_and_missing_account() -> None:
    account_id = pd.read_csv(PROCESSED_DIR / "global_demo_portfolio.csv", nrows=1).loc[
        0, "account_id"
    ]
    response = client.get(f"/accounts/{account_id}")
    assert response.status_code == 200
    assert account_id in response.text
    assert "Reason codes" in response.text
    assert "Harmonized source profile" in response.text
    assert "Source cohort" in response.text
    missing = client.get("/accounts/LIQ-0000000000")
    assert missing.status_code == 404
    assert "Account not found" in missing.text


def test_policy_simulator_recalculates_and_validates_extremes() -> None:
    baseline = client.get("/simulator")
    assert baseline.text.count('step="0.001"') >= 10
    for label in (
        "Current / proposed exposure proxy",
        "Current / proposed loss proxy",
        "Risk-adjusted return",
        "Computed directional sensitivity",
    ):
        assert label in baseline.text
    stressed = client.post(
        "/simulator",
        data={
            "lgd": "1",
            "ccf": "1",
            "interchange_rate": "0",
            "apr": "0",
            "revolving_rate": "0.45",
            "funding_cost": "0.1",
            "capital_cost": "0.1",
            "servicing_cost": "180",
            "response_elasticity": "0",
            "max_increase": "0.3",
            "max_account_exposure": "3000000",
            "portfolio_growth_cap": "0.1",
            "expected_loss_ceiling": "0.01",
            "profitability_hurdle": "300",
        },
    )
    assert baseline.status_code == stressed.status_code == 200
    assert baseline.text != stressed.text
    invalid = client.post("/simulator", data={"lgd": "1.5"})
    assert invalid.status_code == 200
    assert "Assumptions not applied" in invalid.text


def _sample_frame(rows: int = 2) -> pd.DataFrame:
    demo = pd.read_csv(PROCESSED_DIR / "global_demo_portfolio.csv", nrows=rows)
    return demo.rename(columns={"account_id": "ACCOUNT_ID"})[BATCH_COLUMNS]


def _upload(frame: pd.DataFrame):
    return client.post(
        "/batch",
        files={"file": ("accounts.csv", frame.to_csv(index=False).encode(), "text/csv")},
    )


def test_batch_valid_upload_returns_decisions_without_retention() -> None:
    response = _upload(_sample_frame())
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert response.headers["cache-control"] == "no-store"
    result = pd.read_csv(io.BytesIO(response.content))
    assert len(result) == 2
    assert {"PD", "RECOMMENDATION", "PROPOSED_EXPECTED_LOSS", "REASON_CODES"} <= set(result.columns)

    nullable = _sample_frame(1)
    nullable.loc[0, ["utilization", "income_inr", "credit_age_months"]] = np.nan
    assert _upload(nullable).status_code == 200


def test_single_prediction_api_validates_and_returns_no_store_decision() -> None:
    payload = json.loads(_sample_frame(1).to_json(orient="records"))[0]
    response = client.post("/api/predict", json=payload)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    result = response.json()
    assert result["classification"] == "Educational synthetic-economics decision"
    assert 0 <= result["decision"]["pd"] <= 1
    assert result["decision"]["account_id"] == payload["ACCOUNT_ID"]

    assert client.post("/api/predict", json={**payload, "UNEXPECTED": 1}).status_code == 422
    missing = dict(payload)
    missing.pop("region")
    assert client.post("/api/predict", json=missing).status_code == 422


def test_batch_missing_extra_duplicate_invalid_types_and_ranges() -> None:
    sample = _sample_frame()
    cases = []
    cases.append((sample.drop(columns=["credit_age_months"]), "Missing required columns"))
    extra = sample.copy()
    extra["UNEXPECTED"] = 1
    cases.append((extra, "Unexpected columns"))
    duplicate = sample.copy()
    duplicate.loc[1, "ACCOUNT_ID"] = duplicate.loc[0, "ACCOUNT_ID"]
    cases.append((duplicate, "Duplicate ACCOUNT_ID"))
    invalid_type = sample.copy()
    invalid_type["utilization"] = invalid_type["utilization"].astype(object)
    invalid_type.loc[0, "utilization"] = "not-a-number"
    cases.append((invalid_type, "Numeric values required"))
    invalid_range = sample.copy()
    invalid_range.loc[0, "debt_to_income"] = 1.1
    cases.append((invalid_range, "debt_to_income"))
    invalid_region = sample.copy()
    invalid_region.loc[0, "region"] = "antarctica"
    cases.append((invalid_region, "Unsupported region"))
    missing_exposure = sample.copy()
    missing_exposure.loc[0, "current_limit_inr"] = np.nan
    cases.append((missing_exposure, "cannot be blank"))
    excessive_balance = sample.copy()
    excessive_balance.loc[0, "current_balance_inr"] = (
        excessive_balance.loc[0, "current_limit_inr"] * 2.01
    )
    cases.append((excessive_balance, "current_balance_inr"))
    non_finite = sample.copy()
    non_finite.loc[0, "income_inr"] = np.inf
    cases.append((non_finite, "finite"))
    for frame, message in cases:
        response = _upload(frame)
        assert response.status_code == 422
        assert message in response.text


def test_batch_rejects_empty_wrong_media_and_invalid_identifier() -> None:
    empty = pd.DataFrame(columns=BATCH_COLUMNS)
    assert _upload(empty).status_code == 422
    wrong = client.post("/batch", files={"file": ("x.json", b"{}", "application/json")})
    assert wrong.status_code == 415
    invalid = _sample_frame(1)
    invalid.loc[0, "ACCOUNT_ID"] = "=FORMULA"
    response = _upload(invalid)
    assert response.status_code == 422
    assert "ACCOUNT_ID" in response.text


def test_sample_and_filtered_csv_downloads_are_valid() -> None:
    sample = client.get("/sample-input.csv")
    filtered = client.get("/portfolio.csv", params={"risk": "Moderate"})
    assert sample.status_code == filtered.status_code == 200
    assert list(pd.read_csv(io.BytesIO(sample.content)).columns) == BATCH_COLUMNS
    assert "REASON" not in pd.read_csv(io.BytesIO(sample.content)).columns
    assert "reason_codes" in pd.read_csv(io.BytesIO(filtered.content)).columns


@pytest.mark.parametrize(
    "path",
    [
        "/downloads/reports/executive-report-pdf",
        "/downloads/reports/executive-report-html",
        "/downloads/reports/data-quality",
        "/downloads/reports/global-model",
        "/downloads/reports/global-executive-html",
        "/downloads/reports/global-executive-pdf",
        "/downloads/reports/global-policy-simulation",
        "/downloads/reports/global-financial-impact",
        "/documents/methodology",
        "/documents/model-card",
        "/documents/data-card",
        "/documents/prd",
        "/documents/case-study",
        "/documents/career-targeting",
    ],
)
def test_report_and_document_downloads(path: str) -> None:
    response = client.get(path)
    assert response.status_code == 200
    assert len(response.content) > 1_000


def test_report_and_document_allowlists_block_unknown_paths() -> None:
    assert client.get("/downloads/reports/../../README").status_code == 404
    assert client.get("/documents/not-real").status_code == 404


def test_static_assets_and_navigation_are_real() -> None:
    css = client.get("/static/style.css")
    js = client.get("/static/app.js")
    assert css.status_code == js.status_code == 200
    overview = client.get("/").text
    assert "Current loss proxy" in overview
    assert "INR" in overview
    assert "heterogeneous outcomes" in overview
    for path in ("/portfolio", "/simulator", "/batch", "/governance", "/reports"):
        assert f'href="{path}"' in overview

    governance = client.get("/governance").text
    assert "Global benchmark governance" in governance
    assert "Pooled ROC curve" in governance
    assert "ROC by source cohort" in governance
    assert "Calibration by source cohort" in governance
    assert "Source-cohort comparison" in governance
    assert "<svg" in governance
