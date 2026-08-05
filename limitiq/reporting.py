from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table

from limitiq.config import DISCLAIMER, MODEL_DIR, REPORT_DIR


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _money(value: float) -> str:
    return f"TWD {value:,.0f}"


def _pct(value: float) -> str:
    return f"{value:.2%}"


def _html_page(title: str, label: str, sections: list[tuple[str, str]]) -> str:
    body = "".join(
        f"<section><h2>{html.escape(name)}</h2>{content}</section>" for name, content in sections
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>{html.escape(title)} — LimitIQ</title><style>
body{{font:16px/1.55 Inter,Arial,sans-serif;color:#17324d;max-width:980px;margin:40px auto;padding:0 24px}}
h1{{font-size:38px;margin-bottom:4px}}h2{{border-bottom:2px solid #0f8b8d;padding-bottom:8px;margin-top:34px}}
.label{{color:#087f80;font-weight:700;text-transform:uppercase;letter-spacing:.08em}}.notice{{background:#eef7f7;padding:16px;border-left:4px solid #0f8b8d}}
table{{border-collapse:collapse;width:100%}}th,td{{border-bottom:1px solid #dce5eb;text-align:left;padding:10px}}th{{background:#f4f7f9}}
.metric{{display:inline-block;width:29%;padding:14px;margin:4px;background:#f4f7f9;vertical-align:top}}small{{color:#557083}}
@media(max-width:700px){{.metric{{width:auto;display:block}}}}
</style></head><body><div class="label">{html.escape(label)}</div><h1>{html.escape(title)}</h1>{body}
<p class="notice"><strong>Educational-use notice.</strong> {html.escape(DISCLAIMER)}</p></body></html>"""


def _table(headers: list[str], rows: list[list[str]]) -> str:
    head = "".join(f"<th>{html.escape(value)}</th>" for value in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{html.escape(value)}</td>" for value in row) + "</tr>"
        for row in rows
    )
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def _write_html(name: str, title: str, label: str, sections: list[tuple[str, str]]) -> None:
    (REPORT_DIR / name).write_text(_html_page(title, label, sections), encoding="utf-8")


def _executive_pdf(summary: dict[str, Any], model: dict[str, Any]) -> None:
    path = REPORT_DIR / "executive_report.pdf"
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="CenterTitle",
            parent=styles["Title"],
            alignment=TA_CENTER,
            textColor=colors.HexColor("#17324d"),
        )
    )
    styles.add(
        ParagraphStyle(name="Teal", parent=styles["Heading2"], textColor=colors.HexColor("#087f80"))
    )
    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
    )
    test = model["test_metrics"]
    simulation = summary["summary"]
    story = [
        Paragraph("LimitIQ", styles["CenterTitle"]),
        Paragraph("Dynamic Credit Line Management & Exposure Optimization", styles["Heading2"]),
        Spacer(1, 6 * mm),
        Paragraph("Executive decision brief", styles["Teal"]),
        Paragraph(
            "LimitIQ evaluates current limit, +10%, +20% and +30% candidates, then selects the highest eligible simulated risk-adjusted contribution under loss, exposure, payment-history, overextension and profitability controls. Deteriorating accounts are frozen or referred rather than automatically decreased.",
            styles["BodyText"],
        ),
        Spacer(1, 4 * mm),
        Table(
            [
                ["Evidence class", "Result"],
                [
                    "Observed source",
                    "30,000 Taiwan credit-card accounts; April–September 2005 behavior",
                ],
                [
                    "Model estimate",
                    f"Untouched-test ROC-AUC {test['roc_auc']:.3f}; Brier {test['brier_score']:.3f}",
                ],
                [
                    "Simulation",
                    f"{simulation['eligible_increases']:,} increases; {_money(simulation['incremental_contribution'])} contribution",
                ],
            ],
            colWidths=[42 * mm, 128 * mm],
            style=[
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17324d")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dce5eb")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("PADDING", (0, 0), (-1, -1), 7),
            ],
        ),
        Spacer(1, 5 * mm),
        Paragraph("Portfolio simulation", styles["Teal"]),
        Table(
            [
                ["Accounts", f"{simulation['accounts']:,}"],
                [
                    "Current / proposed limits",
                    f"{_money(simulation['current_limit'])} / {_money(simulation['proposed_limit'])}",
                ],
                [
                    "Current / proposed expected loss",
                    f"{_money(simulation['current_expected_loss'])} / {_money(simulation['proposed_expected_loss'])}",
                ],
                [
                    "Simulated incremental contribution",
                    _money(simulation["incremental_contribution"]),
                ],
                ["Simulated risk-adjusted return", _pct(simulation["risk_adjusted_return"])],
                ["Early-warning / manual review", f"{simulation['early_warning']:,}"],
            ],
            colWidths=[72 * mm, 98 * mm],
            style=[
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dce5eb")),
                ("PADDING", (0, 0), (-1, -1), 7),
            ],
        ),
        PageBreak(),
        Paragraph("Model governance", styles["Teal"]),
        Paragraph(
            f"Champion: {model['champion']}. The model type and threshold ({model['selected_threshold']:.3f}) were selected using validation data before one untouched-test evaluation. Sex, education, marital status, age, customer ID and target are excluded from decisioning.",
            styles["BodyText"],
        ),
        Spacer(1, 3 * mm),
        Paragraph("Boundaries and committee actions", styles["Teal"]),
        Paragraph(
            "All line response, drawdown and financial effects are deterministic simulations. PD is not causal. A production build needs current local-law review, verified ability-to-pay inputs, outcome monitoring, model validation, controlled overrides, change approval and rollback. The displayed management ECL is not an IFRS 9 allowance or regulatory-capital calculation.",
            styles["BodyText"],
        ),
        Spacer(1, 8 * mm),
        Paragraph(DISCLAIMER, styles["BodyText"]),
    ]
    doc.build(story)


def build_reports() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    quality = _load(REPORT_DIR / "data_quality.json")
    eda = _load(REPORT_DIR / "eda.json")
    model = _load(MODEL_DIR / "metadata.json")
    simulation = _load(REPORT_DIR / "policy_simulation.json")
    summary = simulation["summary"]
    test = model["test_metrics"]
    metrics = "".join(
        f'<div class="metric"><small>{html.escape(label)}</small><br><strong>{value}</strong></div>'
        for label, value in (
            ("Untouched-test ROC-AUC", f"{test['roc_auc']:.3f}"),
            ("Untouched-test PR-AUC", f"{test['pr_auc']:.3f}"),
            ("Brier score", f"{test['brier_score']:.3f}"),
            ("Current exposure", _money(summary["current_limit"])),
            ("Proposed exposure — simulated", _money(summary["proposed_limit"])),
            ("Incremental contribution — simulated", _money(summary["incremental_contribution"])),
        )
    )
    _write_html(
        "executive_report.html",
        "Executive Report",
        "Observed, modelled and simulated evidence",
        [
            (
                "Decision",
                "<p>Evaluate a governed candidate set and choose the highest eligible simulated risk-adjusted contribution; freeze or refer early-warning accounts.</p>",
            ),
            ("Evidence snapshot", metrics),
            (
                "Action distribution — simulated",
                _table(
                    ["Action", "Accounts"],
                    [[key, f"{value:,}"] for key, value in summary["action_counts"].items()],
                ),
            ),
            (
                "Recommendation",
                "<p>Use the platform as a portfolio-design and governance demonstration. Production use requires current ability-to-pay data, jurisdiction-specific legal review, independent validation, monitoring and controlled overrides.</p>",
            ),
        ],
    )
    _write_html(
        "data_quality_report.html",
        "Data Quality Report",
        "Observed source-data evidence",
        [
            (
                "Lineage",
                f"<p>UCI Default of Credit Card Clients; dataset version <code>{quality['dataset_version']}</code>; CC BY 4.0.</p>",
            ),
            (
                "Validation results",
                _table(
                    ["Check", "Result"],
                    [
                        [key.replace("_", " ").title(), str(value)]
                        for key, value in quality.items()
                        if isinstance(value, int | float)
                    ],
                ),
            ),
            (
                "Decision",
                "<p>Invalid rows are rejected; ID is removed from modelling; demographics remain audit-only.</p>",
            ),
        ],
    )
    _write_html(
        "eda_report.html",
        "Exploratory Data Analysis",
        "Observed source-data statistics",
        [
            (
                "Portfolio",
                metrics[:0]
                + f"<p>{eda['accounts']:,} accounts; observed subsequent default rate {_pct(eda['default_rate'])}; median limit {_money(eda['limit']['median'])}.</p>",
            ),
            (
                "Behavior",
                f"<p>Median current utilization {_pct(eda['current_utilization']['median'])}; {eda['delinquent_accounts']:,} accounts have at least one positive repayment-delay status.</p>",
            ),
            (
                "Known gaps",
                "<ul>"
                + "".join(f"<li>{html.escape(note)}</li>" for note in eda["notes"])
                + "</ul>",
            ),
        ],
    )
    comparison_rows = []
    for name, values in model["validation_models"].items():
        comparison_rows.append(
            [
                name,
                f"{values['roc_auc']:.3f}",
                f"{values['pr_auc']:.3f}",
                f"{values['brier_score']:.3f}",
                f"{values['log_loss']:.3f}",
            ]
        )
    _write_html(
        "model_performance_report.html",
        "Model Performance Report",
        "Model estimates on held-out data",
        [
            (
                "Validation comparison",
                _table(["Model", "ROC-AUC", "PR-AUC", "Brier", "Log loss"], comparison_rows),
            ),
            (
                "Untouched test",
                _table(
                    ["Metric", "Value"],
                    [
                        [key.replace("_", " ").title(), f"{value:.4f}"]
                        for key, value in test.items()
                        if isinstance(value, float)
                    ],
                ),
            ),
            (
                "Selection",
                f"<p>{html.escape(model['selection_rule'])}. Threshold: {model['selected_threshold']:.3f}; {html.escape(model['threshold_rule'])}.</p>",
            ),
        ],
    )
    assumptions = simulation["assumptions"]
    _write_html(
        "policy_simulation_report.html",
        "Policy Simulation Report",
        "Deterministic simulation — not observed impact",
        [
            ("Outcome", metrics),
            (
                "Assumptions",
                _table(
                    ["Assumption", "Value"],
                    [
                        [key.replace("_", " ").title(), str(value)]
                        for key, value in assumptions.items()
                    ],
                ),
            ),
            (
                "Limitations",
                "<ul>"
                + "".join(f"<li>{html.escape(note)}</li>" for note in simulation["limitations"])
                + "</ul>",
            ),
        ],
    )
    _write_html(
        "financial_impact_analysis.html",
        "Financial Impact Analysis",
        "Simulated economics",
        [
            (
                "Equation",
                "<p>Incremental interchange + incremental interest − incremental ECL − funding cost − capital cost − servicing cost.</p>",
            ),
            (
                "Result",
                f"<p>Simulated incremental contribution: <strong>{_money(summary['incremental_contribution'])}</strong>; risk-adjusted return: <strong>{_pct(summary['risk_adjusted_return'])}</strong>.</p>",
            ),
            (
                "Interpretation",
                "<p>These values are scenario outputs driven by visible assumptions. They are neither causal estimates nor realized business results.</p>",
            ),
        ],
    )
    _executive_pdf(simulation, model)
