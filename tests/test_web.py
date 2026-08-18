from __future__ import annotations

import io
import json

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from limitiq.config import PROCESSED_DIR
from limitiq.features import BATCH_COLUMNS
from limitiq.web import MAX_UPLOAD_BYTES, MAX_UPLOAD_ROWS, REPORT_FILES, app

client = TestClient(app)


@pytest.mark.parametrize(
    "path",
    ["/", "/portfolio", "/simulator", "/batch", "/governance", "/monitoring", "/reports"],
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
    assert response.json()["automatic_increases_enabled"] is True
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
    assert "unsafe-inline" not in response.headers["content-security-policy"]
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["strict-transport-security"].startswith("max-age=31536000")
    assert "deployment_commit" in response.json()


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


def test_portfolio_utilization_filters_and_sort_links() -> None:
    for value in ("low", "moderate", "high", "very_high"):
        response = client.get("/portfolio", params={"utilization_band": value})
        assert response.status_code == 200, value
        assert f'value="{value}" selected' in response.text
    filtered = client.get(
        "/portfolio.csv",
        params={"utilization_band": "high", "sort": "display_utilization", "direction": "asc"},
    )
    frame = pd.read_csv(io.BytesIO(filtered.content))
    assert frame["display_utilization"].between(0.6, 0.9, inclusive="left").all()
    assert frame["display_utilization"].is_monotonic_increasing
    risk_sorted = pd.read_csv(
        io.BytesIO(
            client.get("/portfolio.csv", params={"sort": "risk_band", "direction": "asc"}).content
        )
    )
    assert (
        risk_sorted["risk_band"]
        .map({"Low": 0, "Moderate": 1, "High": 2, "Very high": 3})
        .is_monotonic_increasing
    )
    html = client.get("/portfolio").text
    for sort in (
        "action",
        "risk_band",
        "display_utilization",
        "current_limit_inr",
        "proposed_expected_loss",
        "pd",
    ):
        assert f"sort={sort}" in html


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
    assert "Illustrative six-period behavior" in response.text
    assert "Synthetic history" in response.text
    assert "never used by the model or optimizer" in response.text
    assert response.text == client.get(f"/accounts/{account_id}").text
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


def test_batch_enforces_byte_and_row_boundaries() -> None:
    oversized = client.post(
        "/batch",
        files={"file": ("large.csv", b"x" * (MAX_UPLOAD_BYTES + 1), "text/csv")},
    )
    assert oversized.status_code == 413
    assert "MB limit" in oversized.text

    seed = _sample_frame(1)
    exact = pd.concat([seed] * MAX_UPLOAD_ROWS, ignore_index=True)
    exact["ACCOUNT_ID"] = [f"LIQ-QA-{index:06d}" for index in range(MAX_UPLOAD_ROWS)]
    assert _upload(exact).status_code == 200
    too_many = pd.concat([exact, seed], ignore_index=True)
    too_many.loc[MAX_UPLOAD_ROWS, "ACCOUNT_ID"] = "LIQ-QA-TOO-MANY"
    response = _upload(too_many)
    assert response.status_code == 413
    assert "row limit" in response.text


def test_palette_search_endpoint() -> None:
    pages = client.get("/api/search").json()["results"]
    assert any(item["label"] == "Portfolio explorer" for item in pages)
    assert any(item["label"] == "Monitoring readiness" for item in pages)
    account_id = pd.read_csv(PROCESSED_DIR / "global_demo_portfolio.csv", nrows=1).loc[
        0, "account_id"
    ]
    matches = client.get("/api/search", params={"q": account_id}).json()["results"]
    assert any(
        item["label"] == account_id and item["href"] == f"/accounts/{account_id}"
        for item in matches
    )
    assert client.get("/api/search", params={"q": "x" * 41}).status_code == 422


def test_governance_feature_and_monitoring_sections_render() -> None:
    governance = client.get("/governance")
    assert governance.status_code == 200
    assert "Permutation importance" in governance.text
    assert "Gini coefficient" in governance.text
    assert "Decile lift" in governance.text
    monitoring = client.get("/monitoring")
    assert monitoring.status_code == 200
    assert "Monitoring readiness" in monitoring.text
    assert "Baseline feature missingness" in monitoring.text
    assert "Proposed thresholds" in monitoring.text
    assert "illustrative governance proposals" in monitoring.text


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
        "/downloads/reports/global-data-quality",
        "/downloads/reports/global-eda",
        "/downloads/reports/global-executive-html",
        "/downloads/reports/global-executive-pdf",
        "/downloads/reports/global-policy-simulation",
        "/downloads/reports/global-financial-impact",
        "/downloads/reports/global-feature-evidence",
        "/downloads/reports/global-monitoring-baseline",
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


def test_html_reports_use_csp_safe_shared_stylesheet() -> None:
    for slug, filename in REPORT_FILES.items():
        if not filename.endswith(".html"):
            continue
        response = client.get(f"/downloads/reports/{slug}")
        assert response.status_code == 200, slug
        assert '<link rel="stylesheet" href="/static/report.css">' in response.text, slug
        assert "<style" not in response.text, slug
        assert "style=" not in response.text, slug


def test_report_and_document_allowlists_block_unknown_paths() -> None:
    assert client.get("/downloads/reports/../../README").status_code == 404
    assert client.get("/documents/not-real").status_code == 404


def test_document_pages_render_safe_markdown() -> None:
    response = client.get("/documents/model-card")
    assert response.status_code == 200
    assert "<strong>deployed v2 model</strong>" in response.text
    assert "<code>limitiq-global-2.0.0-37a14c45a811</code>" in response.text
    assert "<table>" in response.text
    assert "**deployed v2 model**" not in response.text
    assert "| Candidate |" not in response.text


def test_static_assets_and_navigation_are_real() -> None:
    css = client.get("/static/style.css")
    js = client.get("/static/app.js")
    assert css.status_code == js.status_code == 200
    overview = client.get("/").text
    assert "Current loss proxy" in overview
    assert '<option value="INR" selected>' in overview
    assert "heterogeneous outcomes" in overview
    for path in ("/portfolio", "/simulator", "/batch", "/governance", "/monitoring", "/reports"):
        assert f'href="{path}"' in overview

    governance = client.get("/governance").text
    assert "Global benchmark governance" in governance
    assert "Pooled ROC curve" in governance
    assert "ROC by source cohort" in governance
    assert "Calibration by source cohort" in governance
    assert "Source-cohort comparison" in governance
    assert "<svg" in governance


def test_display_currency_toggle_converts_and_validates() -> None:
    with TestClient(app) as isolated:
        default = isolated.get("/")
        assert '<option value="INR" selected>' in default.text
        eur = isolated.get("/", params={"ccy": "EUR"})
        assert '<option value="EUR" selected>' in eur.text
        assert "limitiq_ccy=EUR" in eur.headers["set-cookie"]
        persisted = isolated.get("/portfolio")
        assert '<option value="EUR" selected>' in persisted.text
        fallback = isolated.get("/", params={"ccy": "GBP"})
        assert "GBP" not in fallback.text
        assert '<option value="INR" selected>' in fallback.text
        assert ">Currency</label>" in default.text


def test_accessible_search_and_single_portfolio_row_tab_stop() -> None:
    overview = client.get("/").text
    assert "data-palette-close" in overview
    assert 'aria-controls="palette-results"' in overview
    portfolio = client.get("/portfolio").text
    assert "tr data-href=" in portfolio
    assert 'tr data-href="/accounts/' in portfolio
    assert 'tabindex="0" aria-label="View' not in portfolio


def test_reports_separate_current_and_superseded_evidence() -> None:
    response = client.get("/reports")
    assert response.status_code == 200
    assert "V2 multi-source evidence" in response.text
    assert "V1 Taiwan archive" in response.text
