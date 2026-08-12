from __future__ import annotations

import csv
import hashlib
import html
import io
import json
import os
import re
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from limitiq import __version__
from limitiq.config import (
    DEFAULT_DISPLAY_CURRENCY,
    DISCLAIMER,
    DISPLAY_CURRENCY,
    DISPLAY_RATES,
    DOCS_DIR,
    MODEL_DIR,
    PROCESSED_DIR,
    REPORT_DIR,
    ROOT,
    PolicyAssumptions,
)
from limitiq.features import (
    BATCH_COLUMNS,
    EXPOSURE_COLUMNS,
    MODEL_INPUT_COLUMNS,
    SchemaError,
    validate_input,
)
from limitiq.optimizer import Decision, recommend_portfolio, summarize_portfolio

MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(5 * 1024 * 1024)))
MAX_UPLOAD_ROWS = 5_000
ACCOUNT_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{2,39}$")
MONETARY_KEYS = ("servicing_cost", "max_account_exposure", "profitability_hurdle")
REPORT_FILES = {
    "global-executive-html": "global_executive_report.html",
    "global-executive-pdf": "global_executive_report.pdf",
    "global-policy-simulation": "global_policy_simulation_report.html",
    "global-financial-impact": "global_financial_impact_analysis.html",
    "executive-report-html": "executive_report.html",
    "executive-report-pdf": "executive_report.pdf",
    "data-quality": "data_quality_report.html",
    "eda": "eda_report.html",
    "model-performance": "model_performance_report.html",
    "policy-simulation": "policy_simulation_report.html",
    "financial-impact": "financial_impact_analysis.html",
    "external-validation": "external_validation_report.html",
    "global-model": "global_model_report.html",
}
DOCUMENT_FILES = {
    "methodology": "METHODOLOGY.md",
    "data-card": "DATA_CARD.md",
    "model-card": "MODEL_CARD.md",
    "prd": "PRD.md",
    "assumptions": "ASSUMPTIONS.md",
    "case-study": "CASE_STUDY.md",
    "data-dictionary": "DATA_DICTIONARY.md",
    "architecture": "ARCHITECTURE.md",
    "interview-walkthrough": "INTERVIEW_WALKTHROUGH.md",
    "career-targeting": "CAREER_TARGETING.md",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_artifacts() -> tuple[Any, dict[str, Any], pd.DataFrame, dict[str, Any]]:
    model_path = MODEL_DIR / "global_champion.joblib"
    metadata_path = MODEL_DIR / "global_metadata.json"
    portfolio_path = PROCESSED_DIR / "global_demo_portfolio.csv"
    simulation_path = REPORT_DIR / "global_policy_simulation.json"
    for path in (model_path, metadata_path, portfolio_path, simulation_path):
        if not path.exists():
            raise RuntimeError(
                f"Required artifact missing: {path.name}; run python -m limitiq.multisource"
            )
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if _sha256(model_path) != metadata["model_checksum"]:
        raise RuntimeError("Champion model checksum does not match trusted metadata")
    model = joblib.load(model_path)  # noqa: S301 — repository-built artifact, checksum verified above.
    portfolio = pd.read_csv(portfolio_path)
    names = {key: value["name"] for key, value in metadata["datasets"].items()}
    portfolio["source_name"] = portfolio["source_dataset"].map(names)
    portfolio["display_utilization"] = portfolio["utilization"].fillna(
        portfolio["current_balance_inr"] / portfolio["current_limit_inr"]
    )
    simulation = json.loads(simulation_path.read_text(encoding="utf-8"))
    return model, metadata, portfolio, simulation


def _svg_points(x_values: list[float], y_values: list[float]) -> str:
    """Map bounded probabilities into the chart's 640x360 SVG plot area."""
    return " ".join(
        f"{56 + min(max(float(x), 0), 1) * 560:.2f},{304 - min(max(float(y), 0), 1) * 280:.2f}"
        for x, y in zip(x_values, y_values, strict=True)
    )


def _governance_charts(metadata: dict[str, Any]) -> dict[str, Any]:
    pooled = metadata["test_metrics"]
    sources = metadata["per_market_test_metrics"]

    def series(key: str, value: dict[str, Any], x_key: str, y_key: str) -> dict[str, str]:
        if x_key == "fpr":
            points = value["roc_points"]
            x_values, y_values = points[x_key], points[y_key]
        else:
            points = value["calibration_points"]
            x_values = [point[x_key] for point in points]
            y_values = [point[y_key] for point in points]
        return {
            "label": metadata["datasets"].get(key, {}).get("name", "Pooled test"),
            "points": _svg_points(x_values, y_values),
        }

    return {
        "pooled_roc": [series("pooled", pooled, "fpr", "tpr")],
        "source_roc": [series(key, value, "fpr", "tpr") for key, value in sources.items()],
        "pooled_calibration": [series("pooled", pooled, "mean_predicted", "observed_rate")],
        "source_calibration": [
            series(key, value, "mean_predicted", "observed_rate") for key, value in sources.items()
        ],
    }


def _money(value: float, ccy: str = DISPLAY_CURRENCY) -> str:
    converted = value * DISPLAY_RATES.get(ccy, 1.0)
    magnitude = abs(converted)
    if magnitude >= 1_000_000_000:
        return f"{ccy} {converted / 1_000_000_000:,.2f}B"
    if magnitude >= 1_000_000:
        return f"{ccy} {converted / 1_000_000:,.2f}M"
    return f"{ccy} {converted:,.0f}"


def _resolve_ccy(value: str | None) -> str:
    if value and str(value).upper() in DISPLAY_RATES:
        return str(value).upper()
    return DEFAULT_DISPLAY_CURRENCY


def _percent(value: float, digits: int = 1) -> str:
    return f"{value:.{digits}%}"


def _number(value: float) -> str:
    return f"{value:,.0f}"


def _safe_csv(frame: pd.DataFrame) -> str:
    safe = frame.copy()
    for column in safe.select_dtypes(include="object").columns:
        safe[column] = safe[column].map(
            lambda value: f"'{value}" if str(value).startswith(("=", "+", "-", "@")) else value
        )
    return safe.to_csv(index=False, quoting=csv.QUOTE_MINIMAL)


def _decision_frame(decisions: list[Decision]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "ACCOUNT_ID": item.account_id,
                "PD": item.pd,
                "RISK_BAND": item.risk_band,
                "RECOMMENDATION": item.action,
                "CURRENT_LIMIT": item.current_limit,
                "PROPOSED_LIMIT": item.proposed_limit,
                "CURRENT_EAD": item.current_ead,
                "PROPOSED_EAD": item.proposed_ead,
                "CURRENT_EXPECTED_LOSS": item.current_expected_loss,
                "PROPOSED_EXPECTED_LOSS": item.proposed_expected_loss,
                "SIMULATED_INCREMENTAL_CONTRIBUTION": item.incremental_contribution,
                "REASON_CODES": " | ".join(item.reason_codes),
            }
            for item in decisions
        ]
    )


def _directional_sensitivity(
    summary: dict[str, Any],
    assumptions: PolicyAssumptions,
    pd_values: np.ndarray,
    current_ead: np.ndarray,
    proposed_ead: np.ndarray,
    current_limit: np.ndarray,
    proposed_limit: np.ndarray,
    utilization: np.ndarray,
) -> dict[str, list[dict[str, Any]]]:
    """Fast fixed-action sensitivity; the offline report performs full re-optimization."""
    contribution = float(summary["incremental_contribution"])
    loss_driver = float(np.sum(pd_values * (proposed_ead - current_ead)))
    spend_driver = float(np.sum((proposed_limit - current_limit) * utilization * 12))
    revenue_rate = assumptions.interchange_rate + assumptions.revolving_rate * assumptions.apr
    charts: dict[str, list[dict[str, Any]]] = {}
    for name, base, driver in (
        ("lgd", assumptions.lgd, -loss_driver),
        ("response_elasticity", assumptions.response_elasticity, spend_driver * revenue_rate),
    ):
        points = []
        for label, factor in (("Low", 0.8), ("Base", 1.0), ("High", 1.2)):
            value = min(base * factor, 1.0)
            result = contribution + (value - base) * driver
            points.append({"label": label, "value": value, "contribution": result})
        maximum = max(abs(point["contribution"]) for point in points) or 1.0
        for point in points:
            point["width"] = max(2.0, abs(point["contribution"]) / maximum * 100)
            point["negative"] = point["contribution"] < 0
        charts[name] = points
    return charts


def _markdownish(text: str) -> str:
    """Tiny safe Markdown subset for repository-authored docs; avoids a runtime dependency."""
    lines = text.splitlines()
    output: list[str] = []
    in_list = False
    for raw in lines:
        line = html.escape(raw)
        if line.startswith("### "):
            if in_list:
                output.append("</ul>")
                in_list = False
            output.append(f"<h3>{line[4:]}</h3>")
        elif line.startswith("## "):
            if in_list:
                output.append("</ul>")
                in_list = False
            output.append(f"<h2>{line[3:]}</h2>")
        elif line.startswith("# "):
            output.append(f"<h1>{line[2:]}</h1>")
        elif line.startswith("- "):
            if not in_list:
                output.append("<ul>")
                in_list = True
            output.append(f"<li>{line[2:]}</li>")
        elif not line.strip():
            if in_list:
                output.append("</ul>")
                in_list = False
        else:
            if in_list:
                output.append("</ul>")
                in_list = False
            output.append(f"<p>{line}</p>")
    if in_list:
        output.append("</ul>")
    return "".join(output)


def create_app() -> FastAPI:
    model, metadata, portfolio, simulation = _load_artifacts()
    app = FastAPI(
        title="LimitIQ",
        version=__version__,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    templates = Jinja2Templates(directory=ROOT / "limitiq" / "templates")
    templates.env.filters.update(money=_money, percent=_percent, number=_number)
    app.mount("/static", StaticFiles(directory=ROOT / "limitiq" / "static"), name="static")
    app.state.model = model
    app.state.metadata = metadata
    app.state.portfolio = portfolio
    app.state.simulation = simulation

    def context(request: Request, **values: Any) -> dict[str, Any]:
        return {
            "request": request,
            "disclaimer": DISCLAIMER,
            "model_version": metadata["model_version"],
            "dataset_version": metadata["dataset_version"],
            "benchmark_classification": metadata["classification"],
            "target_note": metadata["target_note"],
            "ccy": _resolve_ccy(request.query_params.get("ccy")),
            **values,
        }

    @app.middleware("http")
    async def security_headers(request: Request, call_next: Any) -> Response:
        response = await call_next(request)
        response.headers.update(
            {
                "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'",
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "Referrer-Policy": "strict-origin-when-cross-origin",
                "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
                "Cross-Origin-Opener-Policy": "same-origin",
            }
        )
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "error.html",
            context(
                request,
                status=422,
                title="Invalid request",
                message="Check the submitted values and try again.",
            ),
            status_code=422,
        )

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> HTMLResponse | JSONResponse:
        if request.url.path == "/health":
            return JSONResponse({"status": "error"}, status_code=exc.status_code)
        return templates.TemplateResponse(
            request,
            "error.html",
            context(
                request,
                status=exc.status_code,
                title="Request unavailable",
                message=str(exc.detail),
            ),
            status_code=exc.status_code,
        )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "version": __version__,
            "model_version": metadata["model_version"],
            "dataset_version": metadata["dataset_version"],
            "benchmark": "multi-source-adverse-credit-outcome",
        }

    @app.get("/", response_class=HTMLResponse)
    def overview(request: Request) -> HTMLResponse:
        summary = simulation["summary"]
        actions = sorted(summary["action_counts"].items(), key=lambda item: (-item[1], item[0]))
        risks = [
            (name, summary["risk_counts"].get(name, 0))
            for name in ("Low", "Moderate", "High", "Very high")
        ]
        return templates.TemplateResponse(
            request,
            "overview.html",
            context(
                request,
                title="Executive overview",
                summary=summary,
                actions=actions,
                risks=risks,
                assumptions=simulation["assumptions"],
            ),
        )

    def filtered_portfolio(
        search: str,
        risk: str,
        action: str,
        delinquency: str,
        sort: str,
        direction: str,
    ) -> pd.DataFrame:
        result = portfolio
        if search:
            result = result[
                result["account_id"].str.contains(re.escape(search), case=False, na=False)
            ]
        if risk:
            result = result[result["risk_band"] == risk]
        if action:
            result = result[result["action"] == action]
        if delinquency == "yes":
            result = result[result["delinquency_count"].gt(0)]
        elif delinquency == "no":
            result = result[result["delinquency_count"].eq(0)]
        elif delinquency == "unknown":
            result = result[result["delinquency_count"].isna()]
        allowed_sort = {
            "account_id",
            "current_limit_inr",
            "proposed_limit",
            "pd",
            "current_expected_loss",
            "incremental_contribution",
            "risk_band",
            "action",
        }
        key = sort if sort in allowed_sort else "pd"
        return result.sort_values(key, ascending=direction != "desc", kind="stable")

    @app.get("/portfolio", response_class=HTMLResponse)
    def explorer(
        request: Request,
        search: str = Query("", max_length=40),
        risk: str = Query("", max_length=20),
        action: str = Query("", max_length=40),
        delinquency: str = Query("", max_length=7),
        sort: str = Query("pd", max_length=40),
        direction: str = Query("desc", pattern="^(asc|desc)$"),
        page: int = Query(1, ge=1),
    ) -> HTMLResponse:
        result = filtered_portfolio(search, risk, action, delinquency, sort, direction)
        page_size = 25
        pages = max(1, int(np.ceil(len(result) / page_size)))
        page = min(page, pages)
        start = (page - 1) * page_size
        rows = result.iloc[start : start + page_size].to_dict("records")
        return templates.TemplateResponse(
            request,
            "portfolio.html",
            context(
                request,
                title="Portfolio explorer",
                rows=rows,
                total=len(result),
                page=page,
                pages=pages,
                search=search,
                risk=risk,
                action=action,
                delinquency=delinquency,
                sort=sort,
                direction=direction,
                risk_options=["Low", "Moderate", "High", "Very high"],
                action_options=sorted(portfolio["action"].unique()),
            ),
        )

    @app.get("/portfolio.csv")
    def explorer_download(
        search: str = Query("", max_length=40),
        risk: str = Query("", max_length=20),
        action: str = Query("", max_length=40),
        delinquency: str = Query("", max_length=7),
        sort: str = Query("pd", max_length=40),
        direction: str = Query("desc", pattern="^(asc|desc)$"),
    ) -> Response:
        result = filtered_portfolio(search, risk, action, delinquency, sort, direction)
        columns = [
            "account_id",
            "source_name",
            "action",
            "risk_band",
            "current_limit_inr",
            "proposed_limit",
            "pd",
            "current_expected_loss",
            "incremental_contribution",
            "reason_codes",
        ]
        return Response(
            _safe_csv(result[columns]),
            media_type="text/csv",
            headers={
                "Content-Disposition": 'attachment; filename="limitiq-filtered-decisions.csv"'
            },
        )

    @app.get("/accounts/{account_id}", response_class=HTMLResponse)
    def account(request: Request, account_id: str) -> HTMLResponse:
        match = portfolio[portfolio["account_id"] == account_id]
        if match.empty:
            raise HTTPException(404, "Account not found")
        row = match.iloc[0].to_dict()
        row["reason_list"] = str(row["reason_codes"]).split("|")
        row["checks"] = json.loads(row["policy_checks"])
        profile_rows = [
            ("Utilization", row.get("utilization"), "percent"),
            ("Debt to income", row.get("debt_to_income"), "percent"),
            ("Reported delinquency count", row.get("delinquency_count"), "number"),
            ("Credit lines", row.get("credit_lines"), "number"),
            ("Annual income", row.get("income_inr"), "money"),
            ("Credit age (months)", row.get("credit_age_months"), "number"),
        ]
        return templates.TemplateResponse(
            request,
            "account.html",
            context(
                request,
                title=f"Account {account_id}",
                account=row,
                profile_rows=profile_rows,
            ),
        )

    @app.api_route("/simulator", methods=["GET", "POST"], response_class=HTMLResponse)
    async def simulator(request: Request) -> HTMLResponse:
        assumptions = PolicyAssumptions()
        error = None
        baseline = simulation["summary"]
        source = portfolio.rename(columns={"account_id": "ACCOUNT_ID"})
        ccy = _resolve_ccy(request.query_params.get("ccy"))
        if request.method == "POST":
            form = await request.form()
            ccy = _resolve_ccy(form.get("ccy"))
            values = dict(form)
            for key in MONETARY_KEYS:
                if values.get(key) not in (None, ""):
                    values[key] = float(values[key]) / DISPLAY_RATES[ccy]
            try:
                assumptions = PolicyAssumptions.from_mapping(values)
            except (TypeError, ValueError) as exc:
                error = str(exc)
        if request.method == "GET" or error:
            summary = baseline
            current_ead = source["current_ead"].to_numpy()
            proposed_ead = source["proposed_ead"].to_numpy()
            proposed_limit = source["proposed_limit"].to_numpy()
        else:
            decisions = recommend_portfolio(
                source[[*MODEL_INPUT_COLUMNS, *EXPOSURE_COLUMNS]],
                source["pd"].to_numpy(),
                source["ACCOUNT_ID"].tolist(),
                assumptions,
            )
            summary = summarize_portfolio(decisions)
            current_ead = np.asarray([item.current_ead for item in decisions])
            proposed_ead = np.asarray([item.proposed_ead for item in decisions])
            proposed_limit = np.asarray([item.proposed_limit for item in decisions])
        utilization = (
            source["utilization"]
            .fillna(source["current_balance_inr"] / source["current_limit_inr"])
            .clip(0, 1.2)
            .to_numpy()
        )
        sensitivity = _directional_sensitivity(
            summary,
            assumptions,
            source["pd"].to_numpy(),
            current_ead,
            proposed_ead,
            source["current_limit_inr"].to_numpy(),
            proposed_limit,
            utilization,
        )
        changes = {
            key: summary[key] - baseline[key]
            for key in (
                "proposed_limit",
                "proposed_expected_loss",
                "eligible_increases",
                "incremental_contribution",
            )
        }
        actions = sorted(summary["action_counts"].items(), key=lambda item: (-item[1], item[0]))
        form_values = {
            key: value * DISPLAY_RATES[ccy] if key in MONETARY_KEYS else value
            for key, value in assumptions.to_dict().items()
        }
        return templates.TemplateResponse(
            request,
            "simulator.html",
            context(
                request,
                title="Policy simulator",
                assumptions=form_values,
                summary=summary,
                baseline=baseline,
                changes=changes,
                actions=actions,
                sensitivity=sensitivity,
                error=error,
            ),
        )

    @app.get("/batch", response_class=HTMLResponse)
    def batch_page(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "batch.html",
            context(
                request,
                title="Batch decisioning",
                columns=BATCH_COLUMNS,
                max_mb=MAX_UPLOAD_BYTES // (1024 * 1024),
                max_rows=MAX_UPLOAD_ROWS,
            ),
        )

    @app.post("/api/predict")
    def predict(payload: dict[str, Any]) -> JSONResponse:
        extra = sorted(set(payload) - set(BATCH_COLUMNS))
        if extra:
            raise HTTPException(422, f"Unexpected fields: {', '.join(extra)}")
        try:
            clean = validate_input(pd.DataFrame([payload]), require_account_id=True)
        except SchemaError as exc:
            raise HTTPException(422, str(exc)) from exc
        account_id = clean.loc[0, "ACCOUNT_ID"]
        if not ACCOUNT_ID_PATTERN.fullmatch(account_id):
            raise HTTPException(
                422, "ACCOUNT_ID must be 3–40 letters, numbers, underscores or hyphens"
            )
        probability = model.predict_proba(clean[MODEL_INPUT_COLUMNS])[:, 1]
        decision = recommend_portfolio(
            clean[[*MODEL_INPUT_COLUMNS, *EXPOSURE_COLUMNS]],
            probability,
            [account_id],
        )[0]
        return JSONResponse(
            {
                "classification": "Educational synthetic-economics decision",
                "model_output": "Source-horizon adverse-credit-outcome probability",
                "decision": decision.to_dict(),
            },
            headers={"Cache-Control": "no-store"},
        )

    @app.post("/batch")
    async def batch_process(file: UploadFile = File(...)) -> Response:
        if file.content_type not in {
            "text/csv",
            "application/csv",
            "application/vnd.ms-excel",
            "text/plain",
        }:
            raise HTTPException(415, "Upload a CSV file")
        data = await file.read(MAX_UPLOAD_BYTES + 1)
        await file.close()
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(
                413, f"CSV exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit"
            )
        try:
            text = data.decode("utf-8-sig")
            frame = pd.read_csv(io.StringIO(text))
        except (UnicodeDecodeError, pd.errors.ParserError) as exc:
            raise HTTPException(422, "CSV must be valid UTF-8 with one header row") from exc
        if len(frame) == 0:
            raise HTTPException(422, "CSV contains no account rows")
        if len(frame) > MAX_UPLOAD_ROWS:
            raise HTTPException(413, f"CSV exceeds the {MAX_UPLOAD_ROWS:,}-row limit")
        extra = sorted(set(frame.columns) - set(BATCH_COLUMNS))
        if extra:
            raise HTTPException(422, f"Unexpected columns: {', '.join(extra)}")
        try:
            clean = validate_input(frame, require_account_id=True)
        except SchemaError as exc:
            raise HTTPException(422, str(exc)) from exc
        invalid_ids = [
            value for value in clean["ACCOUNT_ID"] if not ACCOUNT_ID_PATTERN.fullmatch(value)
        ]
        if invalid_ids:
            raise HTTPException(
                422, "ACCOUNT_ID must be 3–40 letters, numbers, underscores or hyphens"
            )
        probability = model.predict_proba(clean[MODEL_INPUT_COLUMNS])[:, 1]
        decisions = recommend_portfolio(
            clean[[*MODEL_INPUT_COLUMNS, *EXPOSURE_COLUMNS]],
            probability,
            clean["ACCOUNT_ID"].tolist(),
        )
        result = _decision_frame(decisions)
        return Response(
            _safe_csv(result),
            media_type="text/csv",
            headers={
                "Content-Disposition": 'attachment; filename="limitiq-batch-decisions.csv"',
                "Cache-Control": "no-store",
            },
        )

    @app.get("/sample-input.csv")
    def sample_input() -> Response:
        sample = portfolio.head(5).rename(columns={"account_id": "ACCOUNT_ID"})[BATCH_COLUMNS]
        return Response(
            _safe_csv(sample),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="limitiq-sample-input.csv"'},
        )

    @app.get("/governance", response_class=HTMLResponse)
    def governance(request: Request) -> HTMLResponse:
        cohorts = [
            {
                "source_name": metadata["datasets"][key]["name"],
                "region": metadata["datasets"][key]["region"],
                **value,
            }
            for key, value in metadata["per_market_test_metrics"].items()
        ]
        return templates.TemplateResponse(
            request,
            "governance.html",
            context(
                request,
                title="Model governance",
                metadata=metadata,
                test=metadata["test_metrics"],
                candidates=metadata["validation_models"],
                macro=metadata["macro_test_metrics"],
                cohorts=cohorts,
                charts=_governance_charts(metadata),
            ),
        )

    @app.get("/reports", response_class=HTMLResponse)
    def reports(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "reports.html",
            context(
                request,
                title="Reports & methodology",
                reports=REPORT_FILES,
                documents=DOCUMENT_FILES,
            ),
        )

    @app.get("/downloads/reports/{slug}")
    def report_download(slug: str) -> Response:
        filename = REPORT_FILES.get(slug)
        if not filename:
            raise HTTPException(404, "Report not found")
        path = REPORT_DIR / filename
        if not path.exists():
            raise HTTPException(404, "Report has not been generated")
        media = "application/pdf" if path.suffix == ".pdf" else "text/html; charset=utf-8"
        disposition = "attachment" if path.suffix == ".pdf" else "inline"
        return Response(
            path.read_bytes(),
            media_type=media,
            headers={"Content-Disposition": f'{disposition}; filename="{path.name}"'},
        )

    @app.get("/documents/{slug}", response_class=HTMLResponse)
    def document(request: Request, slug: str) -> HTMLResponse:
        filename = DOCUMENT_FILES.get(slug)
        if not filename:
            raise HTTPException(404, "Document not found")
        path = DOCS_DIR / filename
        if not path.exists():
            raise HTTPException(404, "Document has not been generated")
        return templates.TemplateResponse(
            request,
            "document.html",
            context(
                request,
                title=slug.replace("-", " ").title(),
                content=_markdownish(path.read_text(encoding="utf-8")),
            ),
        )

    return app


app = create_app()
