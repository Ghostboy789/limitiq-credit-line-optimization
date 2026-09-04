from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
import secrets
import threading
import time
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from markdown_it import MarkdownIt
from starlette.concurrency import run_in_threadpool
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from limitiq import __version__
from limitiq.config import (
    AUTO_INCREASES_ENABLED,
    DEFAULT_DISPLAY_CURRENCY,
    DISCLAIMER,
    DISPLAY_CURRENCY,
    DISPLAY_RATES,
    DOCS_DIR,
    MODEL_DIR,
    PROCESSED_DIR,
    REPORT_DIR,
    ROOT,
    SEED,
    PolicyAssumptions,
)
from limitiq.features import (
    BATCH_COLUMNS,
    BILL_COLUMNS,
    EXPOSURE_COLUMNS,
    MODEL_INPUT_COLUMNS,
    PAY_COLUMNS,
    TAIWAN_MODEL_INPUT_COLUMNS,
    SchemaError,
    validate_behavioral_input,
)
from limitiq.india import validate_india_contract
from limitiq.optimizer import Decision, recommend_account, recommend_portfolio, summarize_portfolio
from limitiq.review import DECISIONS, REASONS, ReviewLedger
from limitiq.robustness import behavioral_support_flags

MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(5 * 1024 * 1024)))
MAX_UPLOAD_REQUEST_BYTES = MAX_UPLOAD_BYTES + 64 * 1024
MAX_UPLOAD_ROWS = 5_000
RATE_LIMIT_BURST = 60
RATE_LIMIT_REFILL_PER_SECOND = 1.0
RATE_LIMIT_MAX_CLIENTS = 10_000
RATE_LIMIT_PATHS = frozenset({"/batch", "/simulator", "/api/predict", "/v4-lab/reviews"})
REVIEW_LEDGER_MAX_EVENTS = 500
REVIEW_RENDER_LIMIT = 100
REVIEW_CSRF_COOKIE = "limitiq_review_csrf"
ACCOUNT_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{2,39}$")
MONETARY_KEYS = (
    "servicing_cost",
    "max_account_exposure",
    "portfolio_capital_budget",
    "profitability_hurdle",
)
PRIMARY_REPORT_FILES = {
    "behavioral-primary-evidence": "behavioral_model.json",
    "behavioral-policy-simulation": "behavioral_policy_simulation.json",
    "behavioral-executive-html": "executive_report.html",
    "behavioral-executive-pdf": "executive_report.pdf",
}
V4_SUPPORTING_REPORT_FILES = {
    "temporal-validation-evidence": "temporal_validation.json",
    "monitoring-replay-evidence": "monitoring_replay.json",
    "experiment-replay-evidence": "experiment_replay.json",
    "model-robustness-evidence": "model_robustness.json",
    "india-validation-readiness": "india_validation_readiness.json",
}
V3_ARCHIVE_REPORT_FILES = {
    "v3-primary-model-evidence": "primary_model.json",
    "v3-primary-policy-simulation": "primary_policy_simulation.json",
}
RESEARCH_REPORT_FILES = {
    "global-data-quality": "global_data_quality_report.html",
    "global-eda": "global_eda_report.html",
    "global-executive-html": "global_executive_report.html",
    "global-executive-pdf": "global_executive_report.pdf",
    "global-policy-simulation": "global_policy_simulation_report.html",
    "global-financial-impact": "global_financial_impact_analysis.html",
    "global-model": "global_model_report.html",
    "global-out-of-time": "global_oot_report.html",
    "global-leakage-ablation": "global_leakage_report.html",
    "global-feature-evidence": "global_feature_report.html",
    "global-monitoring-baseline": "global_monitoring_report.html",
}
LEGACY_REPORT_FILES = {
    "data-quality": "data_quality_report.html",
    "eda": "eda_report.html",
    "model-performance": "model_performance_report.html",
    "policy-simulation": "policy_simulation_report.html",
    "financial-impact": "financial_impact_analysis.html",
    "external-validation": "external_validation_report.html",
}
REPORT_FILES = {
    **PRIMARY_REPORT_FILES,
    **V4_SUPPORTING_REPORT_FILES,
    **V3_ARCHIVE_REPORT_FILES,
    **RESEARCH_REPORT_FILES,
    **LEGACY_REPORT_FILES,
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
    "independent-validation": "INDEPENDENT_VALIDATION.md",
    "validation-issues": "VALIDATION_ISSUES.md",
    "model-inventory": "MODEL_INVENTORY.md",
    "experiment-design": "EXPERIMENT_DESIGN.md",
    "india-readiness": "INDIA_READINESS.md",
    "v4-workbench": "V4_WORKBENCH.md",
    "recruiter-brief": "RECRUITER_BRIEF.md",
    "model-improvement-evidence": "MODEL_IMPROVEMENT_EVIDENCE.md",
}
MARKDOWN = MarkdownIt("commonmark", {"html": False, "linkify": False}).enable("table")
RELEASE_MANIFEST_PATH = ROOT / "release" / "checksums-v4.1.0.sha256"


class RequestBodyLimitMiddleware:
    """Bound every POST before Starlette parses or buffers its body."""

    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("method") != "POST":
            await self.app(scope, receive, send)
            return

        messages: list[Message] = []
        total = 0
        while True:
            message = await receive()
            messages.append(message)
            if message["type"] == "http.request":
                total += len(message.get("body", b""))
                if total > self.max_bytes:
                    response = Response(
                        f"Request exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit",
                        status_code=413,
                        media_type="text/plain",
                        headers={"Cache-Control": "no-store"},
                    )
                    await response(scope, receive, send)
                    return
                if not message.get("more_body", False):
                    break
            elif message["type"] == "http.disconnect":
                break

        index = 0

        async def replay() -> Message:
            nonlocal index
            if index < len(messages):
                message = messages[index]
                index += 1
                return message
            return {"type": "http.disconnect"}

        await self.app(scope, replay, send)


class TokenBucketRateLimitMiddleware:
    """Apply a bounded in-process token bucket to resource-intensive POST routes."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        paths: frozenset[str],
        burst: int,
        refill_per_second: float,
        max_clients: int,
    ) -> None:
        self.app = app
        self.paths = paths
        self.burst = float(burst)
        self.refill_per_second = refill_per_second
        self.max_clients = max_clients
        self._buckets: dict[str, tuple[float, float]] = {}
        self._lock = threading.Lock()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if (
            scope["type"] != "http"
            or scope.get("method") != "POST"
            or scope.get("path") not in self.paths
        ):
            await self.app(scope, receive, send)
            return

        client = scope.get("client")
        client_ip = str(client[0]) if client else "unknown"
        now = time.monotonic()
        with self._lock:
            if client_ip not in self._buckets and len(self._buckets) >= self.max_clients:
                self._buckets.pop(next(iter(self._buckets)))
            tokens, updated_at = self._buckets.get(client_ip, (self.burst, now))
            tokens = min(self.burst, tokens + (now - updated_at) * self.refill_per_second)
            allowed = tokens >= 1
            self._buckets[client_ip] = (tokens - 1 if allowed else tokens, now)
        if not allowed:
            response = Response(
                "Rate limit exceeded; retry later.",
                status_code=429,
                media_type="text/plain",
                headers={"Cache-Control": "no-store", "Retry-After": "1"},
            )
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _verify_release_manifest(required_paths: list[Path]) -> None:
    if not RELEASE_MANIFEST_PATH.is_file():
        raise RuntimeError("V4 release checksum manifest is missing")
    entries: dict[str, str] = {}
    for line in RELEASE_MANIFEST_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        checksum, relative = line.split(maxsplit=1)
        normalized = Path(relative).as_posix()
        if normalized in entries or len(checksum) != 64:
            raise RuntimeError("V4 release checksum manifest is invalid")
        entries[normalized] = checksum
    for path in required_paths:
        relative = path.relative_to(ROOT).as_posix()
        actual = _sha256(path) if path.suffix == ".joblib" else _text_sha256(path)
        if entries.get(relative) != actual:
            raise RuntimeError(f"Release checksum mismatch: {relative}")


def _text_sha256(path: Path) -> str:
    """Hash UTF-8 text with platform newlines normalized to LF."""
    return hashlib.sha256(path.read_text(encoding="utf-8").encode()).hexdigest()


def _load_artifacts() -> tuple[
    Any,
    dict[str, Any],
    dict[str, Any],
    pd.DataFrame,
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
]:
    model_path = MODEL_DIR / "behavioral_candidate.joblib"
    metadata_path = MODEL_DIR / "behavioral_metadata.json"
    report_path = REPORT_DIR / "behavioral_model.json"
    portfolio_path = PROCESSED_DIR / "behavioral_demo_portfolio.csv"
    simulation_path = REPORT_DIR / "behavioral_policy_simulation.json"
    research_path = MODEL_DIR / "global_metadata.json"
    schema_path = MODEL_DIR / "behavioral_feature_schema.json"
    research_feature_path = REPORT_DIR / "global_feature_evidence.json"
    robustness_path = REPORT_DIR / "model_robustness.json"
    for path in (
        model_path,
        metadata_path,
        schema_path,
        report_path,
        portfolio_path,
        simulation_path,
        research_path,
        research_feature_path,
        robustness_path,
    ):
        if not path.exists():
            raise RuntimeError(
                f"Required artifact missing: {path.name}; run python -m limitiq.behavioral"
            )
    _verify_release_manifest(
        [
            model_path,
            metadata_path,
            schema_path,
            report_path,
            portfolio_path,
            simulation_path,
            research_path,
            research_feature_path,
            robustness_path,
        ]
    )
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if _sha256(model_path) != metadata["model_checksum"]:
        raise RuntimeError("Behavioral model checksum does not match trusted metadata")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if _text_sha256(report_path) != metadata["artifact_checksums"][report_path.name]:
        raise RuntimeError("Behavioral model report checksum does not match trusted metadata")
    model = joblib.load(model_path)  # noqa: S301 — repository-built artifact, checksum verified above.
    simulation = json.loads(simulation_path.read_text(encoding="utf-8"))
    expected_provenance = {
        "model_version": metadata["model_version"],
        "dataset_version": metadata["dataset_version"],
        "model_checksum": metadata["model_checksum"],
        "dataset_checksum": metadata["dataset_checksum"],
        "random_seed": SEED,
        "demo_portfolio_sha256": _text_sha256(portfolio_path),
    }
    if any(simulation.get(key) != value for key, value in expected_provenance.items()):
        raise RuntimeError("Synthetic demo artifacts do not match trusted primary metadata")
    portfolio = pd.read_csv(portfolio_path)
    if len(portfolio) != simulation.get("demo_rows"):
        raise RuntimeError("Synthetic demo row count does not match trusted simulation metadata")
    portfolio["missing_model_fields"] = portfolio["missing_model_fields"].fillna("")
    portfolio["source_name"] = report["source"]["dataset"]
    portfolio["display_utilization"] = portfolio["utilization"].fillna(
        portfolio["current_balance_inr"] / portfolio["current_limit_inr"]
    )
    increased = portfolio["increase_pct"].gt(0)
    acceptance_reason = "Explicit customer acceptance required before activation"
    portfolio.loc[
        increased & ~portfolio["reason_codes"].str.contains(acceptance_reason), "reason_codes"
    ] = (
        portfolio.loc[
            increased & ~portfolio["reason_codes"].str.contains(acceptance_reason), "reason_codes"
        ]
        + " | "
        + acceptance_reason
    )
    if not AUTO_INCREASES_ENABLED:
        increase = portfolio["increase_pct"].gt(0)
        portfolio.loc[increase, "action"] = "Manual review"
        portfolio.loc[increase, "increase_pct"] = 0.0
        portfolio.loc[increase, "proposed_limit"] = portfolio.loc[increase, "current_limit_inr"]
        portfolio.loc[increase, "proposed_ead"] = portfolio.loc[increase, "current_ead"]
        portfolio.loc[increase, "proposed_expected_loss"] = portfolio.loc[
            increase, "current_expected_loss"
        ]
        portfolio.loc[increase, ["incremental_contribution", "risk_adjusted_return"]] = 0.0
        portfolio.loc[increase, "reason_codes"] = (
            portfolio.loc[increase, "reason_codes"].fillna("")
            + " | Automatic increases disabled by governance control"
        ).str.strip(" |")
        current_limit = float(portfolio["current_limit_inr"].sum())
        proposed_limit = float(portfolio["proposed_limit"].sum())
        current_ead = float(portfolio["current_ead"].sum())
        proposed_ead = float(portfolio["proposed_ead"].sum())
        contribution = float(portfolio["incremental_contribution"].sum())
        simulation["summary"] = {
            **simulation["summary"],
            "current_limit": current_limit,
            "proposed_limit": proposed_limit,
            "current_ead": current_ead,
            "proposed_ead": proposed_ead,
            "current_expected_loss": float(portfolio["current_expected_loss"].sum()),
            "proposed_expected_loss": float(portfolio["proposed_expected_loss"].sum()),
            "incremental_contribution": contribution,
            "incremental_exposure": proposed_ead - current_ead,
            "risk_adjusted_return": contribution / (proposed_ead - current_ead)
            if proposed_ead > current_ead
            else 0.0,
            "eligible_increases": int(portfolio["increase_pct"].gt(0).sum()),
            "early_warning": int(
                portfolio["action"].isin({"Freeze automatic increases", "Manual review"}).sum()
            ),
            "action_counts": portfolio["action"].value_counts().to_dict(),
            "risk_counts": portfolio["risk_band"].value_counts().to_dict(),
        }
    research_metadata = json.loads(research_path.read_text(encoding="utf-8"))
    robustness = json.loads(robustness_path.read_text(encoding="utf-8"))
    return model, metadata, report, portfolio, simulation, research_metadata, robustness


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


def _primary_governance_charts(report: dict[str, Any]) -> dict[str, Any]:
    metrics = report["untouched_test_metrics"]
    roc = metrics["roc_points"]
    calibration = metrics["calibration"]
    return {
        "roc": [
            {
                "label": "Primary untouched test",
                "points": _svg_points(roc["fpr"], roc["tpr"]),
            }
        ],
        "calibration": [
            {
                "label": "Primary untouched test",
                "points": _svg_points(
                    [point["mean_predicted"] for point in calibration],
                    [point["observed_rate"] for point in calibration],
                ),
            }
        ],
    }


def _pdp_cards(pdps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Map partial-dependence curves to self-scaled mini-chart point strings."""
    cards: list[dict[str, Any]] = []
    for pdp in pdps:
        if not pdp["points"]:
            continue
        y_values = [point["y"] for point in pdp["points"]]
        y_min, y_max = min(y_values), max(y_values)
        y_range = y_max - y_min or 1.0
        cards.append(
            {
                "title": pdp["feature"].replace("_", " ").title(),
                "points": " ".join(
                    f"{18 + point['x'] * 196:.2f},{82 - ((point['y'] - y_min) / y_range) * 60:.2f}"
                    for point in pdp["points"]
                ),
                "y_min": f"{y_min:.1%}",
                "y_max": f"{y_max:.1%}",
                "caption": (
                    f"Equal-source mean score ranges {y_min:.1%} to {y_max:.1%} across "
                    f"the 1st to 99th percentile in {len(pdp.get('sources', [])) or 'available'} "
                    "reporting cohorts."
                ),
            }
        )
    return cards


def _lorenz_series(power: dict[str, Any]) -> dict[str, str]:
    points = power["lorenz"]
    return {"label": "Lorenz curve · pooled test", "points": _svg_points(points["x"], points["y"])}


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
            lambda value: f"'{value}"
            if str(value).startswith(("\t", "\r", "=", "+", "-", "@"))
            else value
        )
    return safe.to_csv(index=False, quoting=csv.QUOTE_MINIMAL)


def _primary_model_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Return the exact six-month behavioral fields used during training."""
    return frame[TAIWAN_MODEL_INPUT_COLUMNS]


def _optimizer_frame(
    frame: pd.DataFrame, support: dict[str, dict[str, float]] | None = None
) -> pd.DataFrame:
    """Derive the small policy contract from validated behavioral inputs."""
    result = pd.DataFrame(index=frame.index, columns=MODEL_INPUT_COLUMNS)
    result["delinquency_count"] = (frame[PAY_COLUMNS] > 0).sum(axis=1).astype(float)
    result["utilization"] = (
        frame[BILL_COLUMNS[0]].clip(lower=0) / frame["LIMIT_BAL"].clip(lower=1)
    ).clip(upper=5)
    result["region"] = "taiwan"
    result[EXPOSURE_COLUMNS] = frame[EXPOSURE_COLUMNS]
    if support:
        result = result.join(
            behavioral_support_flags(frame[TAIWAN_MODEL_INPUT_COLUMNS], support)[
                ["outside_model_support", "support_breach_count"]
            ]
        )
    return result


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


def _run_simulator(
    source: pd.DataFrame, assumptions: PolicyAssumptions
) -> tuple[dict[str, Any], np.ndarray, np.ndarray, np.ndarray]:
    decisions = recommend_portfolio(
        source[[*MODEL_INPUT_COLUMNS, *EXPOSURE_COLUMNS, "outside_model_support"]],
        source["pd"].to_numpy(),
        source["ACCOUNT_ID"].tolist(),
        assumptions,
        AUTO_INCREASES_ENABLED,
    )
    return (
        summarize_portfolio(decisions),
        np.asarray([item.current_ead for item in decisions]),
        np.asarray([item.proposed_ead for item in decisions]),
        np.asarray([item.proposed_limit for item in decisions]),
    )


def _process_batch(
    model: Any, clean: pd.DataFrame, support_bounds: dict[str, dict[str, float]]
) -> str:
    probability = model.predict_proba(_primary_model_frame(clean))[:, 1]
    decisions = recommend_portfolio(
        _optimizer_frame(clean, support_bounds),
        probability,
        clean["ACCOUNT_ID"].tolist(),
        automatic_increases_enabled=AUTO_INCREASES_ENABLED,
    )
    return _safe_csv(_decision_frame(decisions))


def _load_v4_lab_state() -> tuple[dict[str, Any], dict[str, Any] | None]:
    from limitiq.behavioral import (
        CANDIDATE_METADATA_PATH,
        CANDIDATE_MODEL_PATH,
        synthetic_behavioral_account,
    )
    from limitiq.explain import explain_account

    evidence = {}
    for name, filename in V4_SUPPORTING_REPORT_FILES.items():
        path = REPORT_DIR / filename
        if path.exists():
            evidence[name] = json.loads(path.read_text(encoding="utf-8"))
    explanation = None
    if CANDIDATE_MODEL_PATH.exists() and CANDIDATE_METADATA_PATH.exists():
        candidate_metadata = json.loads(CANDIDATE_METADATA_PATH.read_text(encoding="utf-8"))
        if _sha256(CANDIDATE_MODEL_PATH) == candidate_metadata["model_checksum"]:
            candidate_model = joblib.load(CANDIDATE_MODEL_PATH)  # noqa: S301
            explanation = explain_account(
                candidate_model, synthetic_behavioral_account("LIQ-000001")
            )
    return evidence, explanation


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
    """Render repository-authored Markdown with raw HTML disabled."""
    rendered = MARKDOWN.render(text)
    return rendered.replace("<table>", '<div class="table-wrap"><table>').replace(
        "</table>", "</table></div>"
    )


def _synthetic_history(row: dict[str, Any]) -> list[dict[str, Any]]:
    """Expose the deterministic synthetic months supplied to behavioral inference."""
    limit = float(row["current_limit_inr"])
    rows = []
    for display_index, source_index in enumerate(reversed(range(6))):
        bill = float(row[BILL_COLUMNS[source_index]])
        rows.append(
            {
                "period": f"M-{5 - display_index}" if display_index < 5 else "Current",
                "bill": bill,
                "payment": float(row[f"PAY_AMT{source_index + 1}"]),
                "utilization": bill / limit if limit else 0.0,
                "delinquency": int(row[PAY_COLUMNS[source_index]] > 0),
            }
        )
    return rows


PALETTE_RESULTS = 8
PALETTE_PAGES = [
    {
        "type": "Page",
        "label": "Executive overview",
        "sublabel": "Portfolio summary and posture",
        "href": "/",
    },
    {
        "type": "Page",
        "label": "Portfolio explorer",
        "sublabel": "Search accounts and download decisions",
        "href": "/portfolio",
    },
    {
        "type": "Tool",
        "label": "Policy simulator",
        "sublabel": "Stress transparent economics assumptions",
        "href": "/simulator",
    },
    {
        "type": "Tool",
        "label": "Batch decisioning",
        "sublabel": "Score a transient CSV upload",
        "href": "/batch",
    },
    {
        "type": "Evidence",
        "label": "Model governance",
        "sublabel": "Champion, calibration and source-cohort evidence",
        "href": "/governance",
    },
    {
        "type": "Evidence",
        "label": "Monitoring readiness",
        "sublabel": "Baseline signals, proposed thresholds and response controls",
        "href": "/monitoring",
    },
    {
        "type": "Evidence",
        "label": "Reports & methodology",
        "sublabel": "Downloads and governance record",
        "href": "/reports",
    },
]


def create_app() -> FastAPI:
    (
        model,
        metadata,
        primary_report,
        portfolio,
        simulation,
        research_metadata,
        robustness,
    ) = _load_artifacts()
    portfolio = portfolio.copy()
    support_flags = behavioral_support_flags(
        portfolio[TAIWAN_MODEL_INPUT_COLUMNS], robustness["support_bounds"]
    )
    portfolio[support_flags.columns] = support_flags
    v4_evidence, v4_explanation = _load_v4_lab_state()
    review_ledger = ReviewLedger(max_events=REVIEW_LEDGER_MAX_EVENTS)
    app = FastAPI(
        title="LimitIQ",
        version=__version__,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.add_middleware(
        RequestBodyLimitMiddleware,
        max_bytes=MAX_UPLOAD_REQUEST_BYTES,
    )
    app.add_middleware(
        TokenBucketRateLimitMiddleware,
        paths=RATE_LIMIT_PATHS,
        burst=RATE_LIMIT_BURST,
        refill_per_second=RATE_LIMIT_REFILL_PER_SECOND,
        max_clients=RATE_LIMIT_MAX_CLIENTS,
    )
    templates = Jinja2Templates(directory=ROOT / "limitiq" / "templates")
    templates.env.filters.update(money=_money, percent=_percent, number=_number)
    app.mount("/static", StaticFiles(directory=ROOT / "limitiq" / "static"), name="static")
    app.state.model = model
    app.state.metadata = metadata
    app.state.primary_report = primary_report
    app.state.research_metadata = research_metadata
    app.state.portfolio = portfolio
    app.state.simulation = simulation
    app.state.robustness = robustness
    app.state.v4_evidence = v4_evidence
    app.state.v4_explanation = v4_explanation
    app.state.review_ledger = review_ledger
    app.state.started_at = time.monotonic()
    app.state.operations = {
        "requests": 0,
        "client_errors": 0,
        "server_errors": 0,
        "latency_seconds": 0.0,
        "max_latency_seconds": 0.0,
    }

    def context(request: Request, **values: Any) -> dict[str, Any]:
        return {
            "request": request,
            "disclaimer": DISCLAIMER,
            "model_version": metadata["model_version"],
            "dataset_version": metadata["dataset_version"],
            "benchmark_classification": metadata["classification"],
            "target_note": (
                f"{primary_report['source']['target_definition']} · "
                f"{primary_report['source']['prediction_horizon']} horizon"
            ),
            "ccy": _resolve_ccy(
                request.query_params.get("ccy") or request.cookies.get("limitiq_ccy")
            ),
            "automatic_increases_enabled": AUTO_INCREASES_ENABLED,
            **values,
        }

    @app.middleware("http")
    async def security_headers(request: Request, call_next: Any) -> Response:
        request_id = secrets.token_hex(16)
        request.state.request_id = request_id
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            elapsed = time.perf_counter() - started
            operations = app.state.operations
            operations["requests"] += 1
            operations["server_errors"] += 1
            operations["latency_seconds"] += elapsed
            operations["max_latency_seconds"] = max(operations["max_latency_seconds"], elapsed)
            raise
        elapsed = time.perf_counter() - started
        operations = app.state.operations
        operations["requests"] += 1
        operations["client_errors"] += 400 <= response.status_code < 500
        operations["server_errors"] += response.status_code >= 500
        operations["latency_seconds"] += elapsed
        operations["max_latency_seconds"] = max(operations["max_latency_seconds"], elapsed)
        response.headers["X-Request-ID"] = request_id
        response.headers["Server-Timing"] = f"app;dur={elapsed * 1_000:.2f}"
        response.headers.update(
            {
                "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'",
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "Referrer-Policy": "strict-origin-when-cross-origin",
                "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
                "Cross-Origin-Opener-Policy": "same-origin",
                "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            }
        )
        requested_currency = request.query_params.get("ccy")
        if requested_currency and _resolve_ccy(requested_currency) == requested_currency.upper():
            response.set_cookie(
                "limitiq_ccy",
                requested_currency.upper(),
                max_age=31_536_000,
                samesite="lax",
                secure=request.url.scheme == "https",
                httponly=True,
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
    def health() -> dict[str, str | bool]:
        return {
            "status": "ok",
            "version": __version__,
            "model_version": metadata["model_version"],
            "dataset_version": metadata["dataset_version"],
            "model_role": "source-coherent-behavioral-primary",
            "research_benchmark_version": research_metadata["model_version"],
            "automatic_increases_enabled": AUTO_INCREASES_ENABLED,
            "deployment_commit": os.getenv("RENDER_GIT_COMMIT", "not-provided"),
        }

    @app.get("/live")
    def live() -> dict[str, str]:
        """Process liveness probe; it intentionally does not claim dependency readiness."""
        return {"status": "alive"}

    @app.get("/ready")
    def ready() -> JSONResponse:
        artifacts_loaded = all(
            getattr(app.state, name, None) is not None
            for name in (
                "model",
                "metadata",
                "primary_report",
                "research_metadata",
                "portfolio",
                "simulation",
            )
        )
        return JSONResponse(
            {
                "status": "ready" if artifacts_loaded else "not-ready",
                "artifacts_loaded": artifacts_loaded,
                "model_version": metadata["model_version"],
                "dataset_version": metadata["dataset_version"],
            },
            status_code=200 if artifacts_loaded else 503,
            headers={"Cache-Control": "no-store"},
        )

    @app.get("/ops")
    def operations() -> JSONResponse:
        """Bounded, process-local aggregates only; no request paths, inputs or identities."""
        values = app.state.operations
        request_count = values["requests"]
        return JSONResponse(
            {
                "scope": "single-process in-memory aggregates",
                "uptime_seconds": round(time.monotonic() - app.state.started_at, 1),
                "requests": request_count,
                "client_errors": values["client_errors"],
                "server_errors": values["server_errors"],
                "mean_latency_ms": round(
                    values["latency_seconds"] * 1_000 / request_count if request_count else 0.0,
                    2,
                ),
                "max_latency_ms": round(values["max_latency_seconds"] * 1_000, 2),
                "contains_customer_data": False,
            },
            headers={"Cache-Control": "no-store"},
        )

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
                primary=primary_report,
                research=research_metadata,
            ),
        )

    @app.get("/committee-memo", response_class=HTMLResponse)
    def committee_memo(request: Request, download: bool = False) -> HTMLResponse:
        summary = simulation["summary"]
        response = templates.TemplateResponse(
            request,
            "committee_memo.html",
            context(
                request,
                title="Credit committee memo",
                summary=summary,
                assumptions=simulation["assumptions"],
                test=primary_report["untouched_test_metrics"],
                primary=primary_report,
                research=research_metadata,
            ),
        )
        if download:
            response.headers["Content-Disposition"] = (
                'attachment; filename="limitiq-credit-committee-memo.html"'
            )
        return response

    def filtered_portfolio(
        search: str,
        risk: str,
        action: str,
        delinquency: str,
        utilization_band: str,
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
        utilization_ranges = {
            "low": (0.0, 0.3),
            "moderate": (0.3, 0.6),
            "high": (0.6, 0.9),
            "very_high": (0.9, np.inf),
        }
        if utilization_band in utilization_ranges:
            lower, upper = utilization_ranges[utilization_band]
            result = result[
                result["display_utilization"].ge(lower) & result["display_utilization"].lt(upper)
            ]
        allowed_sort = {
            "account_id",
            "current_limit_inr",
            "proposed_limit",
            "pd",
            "current_expected_loss",
            "proposed_expected_loss",
            "incremental_contribution",
            "risk_band",
            "action",
            "display_utilization",
        }
        key = sort if sort in allowed_sort else "pd"
        return result.sort_values(
            key,
            ascending=direction != "desc",
            kind="stable",
            key=(
                lambda values: values.map({"Low": 0, "Moderate": 1, "High": 2, "Very high": 3})
                if key == "risk_band"
                else values
            ),
        )

    @app.get("/portfolio", response_class=HTMLResponse)
    def explorer(
        request: Request,
        search: str = Query("", max_length=40),
        risk: str = Query("", max_length=20),
        action: str = Query("", max_length=40),
        delinquency: str = Query("", max_length=7),
        utilization_band: str = Query("", max_length=20),
        sort: str = Query("pd", max_length=40),
        direction: str = Query("desc", pattern="^(asc|desc)$"),
        page: int = Query(1, ge=1),
    ) -> HTMLResponse:
        result = filtered_portfolio(
            search, risk, action, delinquency, utilization_band, sort, direction
        )
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
                utilization_band=utilization_band,
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
        utilization_band: str = Query("", max_length=20),
        sort: str = Query("pd", max_length=40),
        direction: str = Query("desc", pattern="^(asc|desc)$"),
    ) -> Response:
        result = filtered_portfolio(
            search, risk, action, delinquency, utilization_band, sort, direction
        )
        columns = [
            "account_id",
            "source_name",
            "region",
            "action",
            "risk_band",
            "display_utilization",
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
        missing_profile_fields = [label for label, value, _ in profile_rows if pd.isna(value)]
        return templates.TemplateResponse(
            request,
            "account.html",
            context(
                request,
                title=f"Account {account_id}",
                account=row,
                profile_rows=profile_rows,
                missing_profile_fields=missing_profile_fields,
                synthetic_history=_synthetic_history(row),
            ),
        )

    @app.api_route("/simulator", methods=["GET", "POST"], response_class=HTMLResponse)
    async def simulator(request: Request) -> HTMLResponse:
        assumptions = PolicyAssumptions()
        error = None
        baseline = simulation["summary"]
        source = portfolio.rename(columns={"account_id": "ACCOUNT_ID"})
        ccy = _resolve_ccy(request.query_params.get("ccy") or request.cookies.get("limitiq_ccy"))
        if request.method == "POST":
            form = await request.form()
            ccy = _resolve_ccy(form.get("ccy"))
            values = dict(form)
            try:
                for key in MONETARY_KEYS:
                    if values.get(key) not in (None, ""):
                        values[key] = float(values[key]) / DISPLAY_RATES[ccy]
                assumptions = PolicyAssumptions.from_mapping(values)
            except (TypeError, ValueError) as exc:
                error = str(exc)
        if request.method == "GET" or error:
            summary = baseline
            current_ead = source["current_ead"].to_numpy()
            proposed_ead = source["proposed_ead"].to_numpy()
            proposed_limit = source["proposed_limit"].to_numpy()
        else:
            summary, current_ead, proposed_ead, proposed_limit = await run_in_threadpool(
                _run_simulator, source, assumptions
            )
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
        scenario_applied = request.method == "POST" and error is None
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
                scenario_applied=scenario_applied,
            ),
            status_code=422 if error else 200,
        )

    @app.get("/api/search")
    def search_palette(q: str = Query("", max_length=40)) -> JSONResponse:
        needle = q.strip().lower()
        results = [item for item in PALETTE_PAGES if not needle or needle in item["label"].lower()]
        if needle:
            matches = portfolio[
                portfolio["account_id"].str.contains(re.escape(needle), case=False, na=False)
            ].head(PALETTE_RESULTS)
            for _, row in matches.iterrows():
                results.append(
                    {
                        "type": row["source_name"],
                        "label": row["account_id"],
                        "sublabel": f"{row['action']} · {row['risk_band']} · {row['pd']:.1%}",
                        "href": f"/accounts/{row['account_id']}",
                    }
                )
        return JSONResponse(
            {"results": results[: PALETTE_RESULTS + 6]},
            headers={"Cache-Control": "no-store"},
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
            clean = validate_behavioral_input(pd.DataFrame([payload]), require_account_id=True)
        except SchemaError as exc:
            raise HTTPException(422, str(exc)) from exc
        account_id = clean.loc[0, "ACCOUNT_ID"]
        if not ACCOUNT_ID_PATTERN.fullmatch(account_id):
            raise HTTPException(
                422, "ACCOUNT_ID must be 3–40 letters, numbers, underscores or hyphens"
            )
        probability = model.predict_proba(_primary_model_frame(clean))[:, 1]
        decision = recommend_account(
            _optimizer_frame(clean, robustness["support_bounds"]).iloc[0],
            float(probability[0]),
            account_id,
            automatic_increases_enabled=AUTO_INCREASES_ENABLED,
        )
        return JSONResponse(
            {
                "classification": "Educational synthetic-economics decision",
                "model_output": "Taiwan-source following-month default probability",
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
            clean = validate_behavioral_input(frame, require_account_id=True)
        except SchemaError as exc:
            raise HTTPException(422, str(exc)) from exc
        invalid_ids = [
            value for value in clean["ACCOUNT_ID"] if not ACCOUNT_ID_PATTERN.fullmatch(value)
        ]
        if invalid_ids:
            raise HTTPException(
                422, "ACCOUNT_ID must be 3–40 letters, numbers, underscores or hyphens"
            )
        content = await run_in_threadpool(
            _process_batch, model, clean, robustness["support_bounds"]
        )
        return Response(
            content,
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
                "source_name": research_metadata["datasets"][key]["name"],
                "region": research_metadata["datasets"][key]["region"],
                **value,
            }
            for key, value in research_metadata["per_market_test_metrics"].items()
        ]
        charts = _governance_charts(research_metadata)
        feature_path = REPORT_DIR / "global_feature_evidence.json"
        feature_evidence = json.loads(feature_path.read_text(encoding="utf-8"))
        importance_rows: list[tuple[str, float]] = []
        pdp_cards: list[dict[str, Any]] = []
        discriminatory: dict[str, Any] = {}
        if feature_evidence:
            charts["lorenz"] = [_lorenz_series(feature_evidence["discriminatory_power"])]
            importance_rows = [
                (item["feature"].replace("_", " ").title(), item["mean_roc_auc_drop"])
                for item in feature_evidence["permutation_importance"]
            ]
            pdp_cards = _pdp_cards(feature_evidence["partial_dependence"])
            discriminatory = feature_evidence["discriminatory_power"]
        return templates.TemplateResponse(
            request,
            "governance.html",
            context(
                request,
                title="Model governance",
                metadata=research_metadata,
                primary=primary_report,
                primary_charts=_primary_governance_charts(primary_report),
                primary_importance=[
                    (item["feature"].replace("_", " ").title(), item["roc_auc_drop"])
                    for item in primary_report["untouched_test_metrics"]["permutation_importance"]
                ],
                test=research_metadata["test_metrics"],
                candidates=research_metadata["validation_models"],
                macro=research_metadata["macro_test_metrics"],
                cohorts=cohorts,
                charts=charts,
                feature_evidence=feature_evidence,
                importance_rows=importance_rows,
                pdp_cards=pdp_cards,
                discriminatory=discriminatory,
                lift_rows=discriminatory.get("lift", []),
                per_source=feature_evidence.get("per_source", []),
            ),
        )

    @app.get("/monitoring", response_class=HTMLResponse)
    def monitoring(request: Request) -> HTMLResponse:
        metrics = primary_report["untouched_test_metrics"]
        threshold_rows = [
            ["Population stability index warning", "0.10"],
            ["Population stability index escalation", "0.25"],
            ["ROC-AUC deterioration warning", "0.03"],
            ["Brier-score increase warning", "0.02"],
            ["Calibration-gap warning", "0.03"],
        ]
        return templates.TemplateResponse(
            request,
            "monitoring.html",
            context(
                request,
                title="Monitoring readiness",
                primary=primary_report,
                monitoring=metrics,
                threshold_rows=threshold_rows,
                protocol=[
                    "Disable automatic increases and preserve manual-review routing.",
                    "Confirm data lineage, schema, missingness and score-distribution changes.",
                    "Recalculate performance and calibration on newly matured Taiwan outcomes.",
                    "Require documented model-risk approval before restoring automation.",
                ],
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
                primary_reports=PRIMARY_REPORT_FILES,
                supporting_reports=V4_SUPPORTING_REPORT_FILES,
                v3_reports=V3_ARCHIVE_REPORT_FILES,
                research_reports=RESEARCH_REPORT_FILES,
                legacy_reports=LEGACY_REPORT_FILES,
                documents=DOCUMENT_FILES,
            ),
        )

    @app.get("/v4-lab", response_class=HTMLResponse)
    def v4_lab(request: Request, message: str = Query("", max_length=120)) -> HTMLResponse:
        """Expose the executable decision-science and governance workbench."""
        evidence = app.state.v4_evidence
        review_csrf_token = request.cookies.get(REVIEW_CSRF_COOKIE) or secrets.token_urlsafe(32)
        response = templates.TemplateResponse(
            request,
            "v4_lab.html",
            context(
                request,
                title="V4.1 decision-science lab",
                behavioral=primary_report,
                temporal=evidence.get("temporal-validation-evidence"),
                monitoring_replay=evidence.get("monitoring-replay-evidence"),
                experiment_replay=evidence.get("experiment-replay-evidence"),
                robustness=evidence.get("model-robustness-evidence"),
                india_readiness=evidence.get("india-validation-readiness"),
                explanation=app.state.v4_explanation,
                review_events=review_ledger.events(limit=REVIEW_RENDER_LIMIT),
                review_decisions=sorted(DECISIONS),
                review_reasons=sorted(REASONS),
                review_csrf_token=review_csrf_token,
                message=message,
            ),
        )
        response.set_cookie(
            REVIEW_CSRF_COOKIE,
            review_csrf_token,
            max_age=3_600,
            path="/v4-lab",
            samesite="strict",
            secure=request.url.scheme == "https",
            httponly=True,
        )
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.post("/v4-lab/reviews")
    async def v4_review(request: Request) -> RedirectResponse:
        form = await request.form()
        cookie_token = request.cookies.get(REVIEW_CSRF_COOKIE, "")
        form_token = str(form.get("csrf_token", ""))
        if not (cookie_token and form_token and secrets.compare_digest(cookie_token, form_token)):
            raise HTTPException(403, "Invalid review CSRF token")
        try:
            if form.get("operation") == "approve":
                review_ledger.approve(str(form.get("review_id", "")), str(form.get("actor", "")))
                message = "Checker approval recorded"
            else:
                review_ledger.submit(
                    str(form.get("account_id", "")),
                    str(form.get("actor", "")),
                    str(form.get("decision", "")),
                    str(form.get("reason", "")),
                )
                message = "Maker submission recorded"
        except ValueError as exc:
            message = f"Review rejected: {exc}"
        return RedirectResponse(f"/v4-lab?message={quote_plus(message)}", status_code=303)

    @app.post("/api/india-readiness")
    def india_readiness(payload: dict[str, Any]) -> JSONResponse:
        try:
            result = validate_india_contract(payload)
        except (TypeError, ValueError) as exc:
            raise HTTPException(422, str(exc)) from exc
        return JSONResponse(result, headers={"Cache-Control": "no-store"})

    @app.get("/downloads/india-data-contract.json")
    def india_contract_download() -> Response:
        path = DOCS_DIR / "INDIA_DATA_CONTRACT.json"
        return Response(
            path.read_text(encoding="utf-8"),
            media_type="application/schema+json",
            headers={
                "Content-Disposition": 'attachment; filename="limitiq-india-data-contract.json"'
            },
        )

    @app.get("/downloads/reports/{slug}")
    def report_download(slug: str) -> Response:
        filename = REPORT_FILES.get(slug)
        if not filename:
            raise HTTPException(404, "Report not found")
        path = REPORT_DIR / filename
        if not path.exists():
            raise HTTPException(404, "Report has not been generated")
        media = {
            ".pdf": "application/pdf",
            ".json": "application/json; charset=utf-8",
        }.get(path.suffix, "text/html; charset=utf-8")
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
