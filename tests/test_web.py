from __future__ import annotations

import io

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
    assert response.json()["model_version"].startswith("limitiq-1.0.0-")
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"


def test_portfolio_filter_search_sort_and_pagination() -> None:
    demo = pd.read_csv(PROCESSED_DIR / "demo_portfolio.csv", nrows=1)
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


def test_account_decision_and_missing_account() -> None:
    account_id = pd.read_csv(PROCESSED_DIR / "demo_portfolio.csv", nrows=1).loc[0, "account_id"]
    response = client.get(f"/accounts/{account_id}")
    assert response.status_code == 200
    assert account_id in response.text
    assert "Reason codes" in response.text
    assert "Six-month account history" in response.text
    missing = client.get("/accounts/LIQ-0000000000")
    assert missing.status_code == 404
    assert "Account not found" in missing.text


def test_policy_simulator_recalculates_and_validates_extremes() -> None:
    baseline = client.get("/simulator")
    assert baseline.text.count('step="0.001"') >= 10
    for label in (
        "Current / proposed EAD",
        "Current / proposed expected loss",
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
            "servicing_cost": "60",
            "response_elasticity": "0",
            "max_increase": "0.3",
            "max_account_exposure": "1000000",
            "portfolio_growth_cap": "0.1",
            "expected_loss_ceiling": "0.01",
            "profitability_hurdle": "100",
        },
    )
    assert baseline.status_code == stressed.status_code == 200
    assert baseline.text != stressed.text
    invalid = client.post("/simulator", data={"lgd": "1.5"})
    assert invalid.status_code == 200
    assert "Assumptions not applied" in invalid.text


def _sample_frame(rows: int = 2) -> pd.DataFrame:
    demo = pd.read_csv(PROCESSED_DIR / "demo_portfolio.csv", nrows=rows)
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


def test_batch_missing_extra_duplicate_invalid_types_and_ranges() -> None:
    sample = _sample_frame()
    cases = []
    cases.append((sample.drop(columns=["PAY_6"]), "Missing required columns"))
    extra = sample.copy()
    extra["UNEXPECTED"] = 1
    cases.append((extra, "Unexpected columns"))
    duplicate = sample.copy()
    duplicate.loc[1, "ACCOUNT_ID"] = duplicate.loc[0, "ACCOUNT_ID"]
    cases.append((duplicate, "Duplicate ACCOUNT_ID"))
    invalid_type = sample.copy()
    invalid_type["LIMIT_BAL"] = invalid_type["LIMIT_BAL"].astype(object)
    invalid_type.loc[0, "LIMIT_BAL"] = "not-a-number"
    cases.append((invalid_type, "Numeric values required"))
    invalid_range = sample.copy()
    invalid_range.loc[0, "PAY_0"] = 99
    cases.append((invalid_range, "between -2 and 9"))
    non_finite = sample.copy()
    non_finite.loc[0, "BILL_AMT1"] = np.inf
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
        "/documents/methodology",
        "/documents/model-card",
        "/documents/data-card",
        "/documents/prd",
        "/documents/case-study",
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
    assert "Current expected loss" in overview
    for path in ("/portfolio", "/simulator", "/batch", "/governance", "/reports"):
        assert f'href="{path}"' in overview

    governance = client.get("/governance").text
    assert "Permutation ranking" in governance
    assert "Drift indicators" in governance
