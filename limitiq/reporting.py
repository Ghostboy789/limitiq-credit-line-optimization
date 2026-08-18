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

from limitiq.config import DISCLAIMER, DISPLAY_CURRENCY, MODEL_DIR, REPORT_DIR


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _money(value: float) -> str:
    return f"{DISPLAY_CURRENCY} {value:,.0f}"


def _pct(value: float) -> str:
    return f"{value:.2%}"


def _html_page(title: str, label: str, sections: list[tuple[str, str]]) -> str:
    body = "".join(
        f"<section><h2>{html.escape(name)}</h2>{content}</section>" for name, content in sections
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>{html.escape(title)} — LimitIQ</title><link rel="stylesheet" href="/static/report.css">
</head><body><div class="label">{html.escape(label)}</div><h1>{html.escape(title)}</h1>{body}
<p class="notice"><strong>Educational-use notice.</strong> {html.escape(DISCLAIMER)}</p></body></html>"""


def _table(headers: list[str], rows: list[list[str]]) -> str:
    head = "".join(f"<th>{html.escape(value)}</th>" for value in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{html.escape(value)}</td>" for value in row) + "</tr>"
        for row in rows
    )
    return f'<div class="table-wrap"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def _write_html(
    directory: Path, name: str, title: str, label: str, sections: list[tuple[str, str]]
) -> None:
    (directory / name).write_text(_html_page(title, label, sections), encoding="utf-8")


def _executive_pdf(summary: dict[str, Any], model: dict[str, Any], directory: Path) -> None:
    path = directory / "executive_report.pdf"
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
                    "Current / proposed EAD",
                    f"{_money(simulation['current_ead'])} / {_money(simulation['proposed_ead'])}",
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
            "All line response, drawdown and financial effects are deterministic simulations. PD is not causal. Source TWD monetary values are converted to INR at the documented fixed rate for presentation; this is not Indian borrower evidence. A production build needs current local-law review, verified ability-to-pay inputs, outcome monitoring, model validation, controlled overrides, change approval and rollback. The displayed management ECL is not an IFRS 9 allowance or regulatory-capital calculation.",
            styles["BodyText"],
        ),
        Spacer(1, 8 * mm),
        Paragraph(DISCLAIMER, styles["BodyText"]),
    ]

    def metadata(canvas: Any, _document: Any) -> None:
        canvas.setTitle("LimitIQ v1 executive decision brief")
        canvas.setAuthor("LimitIQ")
        canvas.setSubject("Educational credit-line optimization evidence and governance")

    doc.build(story, onFirstPage=metadata, onLaterPages=metadata)


def _global_executive_pdf(
    simulation: dict[str, Any], model: dict[str, Any], directory: Path
) -> None:
    path = directory / "global_executive_report.pdf"
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="GlobalTitle",
            parent=styles["Title"],
            alignment=TA_CENTER,
            textColor=colors.HexColor("#17324d"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="GlobalTeal", parent=styles["Heading2"], textColor=colors.HexColor("#087f80")
        )
    )
    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )
    summary = simulation["summary"]
    macro = model["macro_test_metrics"]
    pooled = model["test_metrics"]
    action_rows = [[name, f"{count:,}"] for name, count in summary["action_counts"].items()]
    source_rows = [
        [
            model["datasets"][key]["name"],
            f"{value['accounts']:,}",
            f"{value['roc_auc']:.3f}",
            f"{value['brier_score']:.3f}",
        ]
        for key, value in model["per_market_test_metrics"].items()
    ]
    table_style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17324d")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dce5eb")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]
    story = [
        Paragraph("LimitIQ v2", styles["GlobalTitle"]),
        Paragraph("Multi-source credit-line governance benchmark", styles["Heading2"]),
        Spacer(1, 4 * mm),
        Paragraph("Executive evidence", styles["GlobalTeal"]),
        Paragraph(
            "One pooled model evaluates harmonized adverse-credit outcomes across six independent source cohorts. Source labels have different events and horizons, so the score is not a common-horizon regulatory probability of default.",
            styles["BodyText"],
        ),
        Spacer(1, 3 * mm),
        Table(
            [
                ["Evidence class", "Verified result"],
                ["Training union", f"{model['rows']:,} rows; six independent cohorts"],
                ["Champion", model["champion"]],
                [
                    "Macro untouched test",
                    f"ROC-AUC {macro['roc_auc']:.4f}; Brier {macro['brier_score']:.4f}",
                ],
                [
                    "Pooled untouched test",
                    f"ROC-AUC {pooled['roc_auc']:.4f}; Brier {pooled['brier_score']:.4f}",
                ],
                [
                    "Synthetic scenario",
                    f"{summary['eligible_increases']:,} increases; {_money(summary['incremental_contribution'])} contribution",
                ],
            ],
            colWidths=[46 * mm, 130 * mm],
            style=table_style,
        ),
        Spacer(1, 4 * mm),
        Paragraph("Synthetic portfolio decisioning", styles["GlobalTeal"]),
        Table(
            [["Action", "Accounts"], *action_rows], colWidths=[110 * mm, 45 * mm], style=table_style
        ),
        Spacer(1, 3 * mm),
        Paragraph(
            f"Current versus proposed exposure: {_money(summary['current_limit'])} to {_money(summary['proposed_limit'])}. Simulated expected-loss proxy: {_money(summary['current_expected_loss'])} to {_money(summary['proposed_expected_loss'])}. Simulated risk-adjusted return: {_pct(summary['risk_adjusted_return'])}. These are deterministic assumption-driven outputs, not causal or realized impact.",
            styles["BodyText"],
        ),
        PageBreak(),
        Paragraph("Untouched test by source cohort", styles["GlobalTeal"]),
        Table(
            [["Source cohort", "N", "ROC", "Brier"], *source_rows],
            colWidths=[102 * mm, 24 * mm, 24 * mm, 24 * mm],
            style=table_style,
        ),
        Spacer(1, 4 * mm),
        Paragraph("Governance boundaries", styles["GlobalTeal"]),
        Paragraph(
            "The seeded random split measures within-source interpolation only. Lending Club dominates pooled rows, while macro metrics weight cohorts equally. Region is one-hot encoded; missingness can identify a source. The model does not establish unseen-country, out-of-time, Indian, IFRS 9, fair-lending, or production generalization.",
            styles["BodyText"],
        ),
        Spacer(1, 3 * mm),
        Paragraph(
            "Publication gate: cleared by repository-owner attestation on 14 August 2026. NOTICE.md retains the review history for Give Me Some Credit, FICO HELOC, Lending Club, and Home Credit. This attestation is not an independent legal opinion; institutional use requires its own source-terms review.",
            styles["BodyText"],
        ),
        Spacer(1, 5 * mm),
        Paragraph(DISCLAIMER, styles["BodyText"]),
    ]

    def footer(canvas: Any, document: Any) -> None:
        canvas.saveState()
        canvas.setTitle("LimitIQ v2 multi-source executive evidence")
        canvas.setAuthor("LimitIQ")
        canvas.setSubject("Educational multi-source credit-risk benchmark and governance")
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#557083"))
        canvas.drawString(16 * mm, 8 * mm, model["model_version"])
        canvas.drawRightString(A4[0] - 16 * mm, 8 * mm, f"Page {document.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)


def build_global_reports(report_dir: Path | None = None, model_dir: Path | None = None) -> None:
    report_dir = report_dir or REPORT_DIR
    model_dir = model_dir or MODEL_DIR
    report_dir.mkdir(parents=True, exist_ok=True)
    model = _load(model_dir / "global_metadata.json")
    simulation = _load(report_dir / "global_policy_simulation.json")
    summary = simulation["summary"]
    macro = model["macro_test_metrics"]
    pooled = model["test_metrics"]
    quality_rows = []
    for source in model["datasets"].values():
        missing = source["feature_missing_rate"]
        quality_rows.append(
            [
                source["name"],
                source["role"].replace("_", " ").title(),
                f"{source['rows_in_union']:,}",
                f"{source['risk_rate']:.2%}",
                ", ".join(
                    f"{feature.replace('_', ' ')} {rate:.0%}" for feature, rate in missing.items()
                ),
                source["file_sha256"][:12] + "…",
            ]
        )
    _write_html(
        report_dir,
        "global_data_quality_report.html",
        "LimitIQ v2 Global Data-Quality Report",
        "Observed source provenance and harmonization quality",
        [
            (
                "Validated union",
                f"<p><strong>{model['rows']:,}</strong> harmonized rows from six independent training cohorts; one duplicate-population German file is retained as reference only. The fixed seed is {model['random_seed']} and the dataset version is <code>{html.escape(model['dataset_version'])}</code>.</p>",
            ),
            (
                "Source checks",
                _table(
                    [
                        "Source",
                        "Role",
                        "Union rows",
                        "Outcome rate",
                        "Feature missingness",
                        "SHA-256",
                    ],
                    quality_rows,
                ),
            ),
            (
                "Quality boundary",
                "<p>Harmonizers validate required columns, numeric coercion, binary targets and source-specific ranges before concatenation. Missingness is preserved because source coverage differs; it is not silently imputed in the stored evidence. File hashes bind every source. The public repository excludes raw data.</p>",
            ),
        ],
    )
    composition_rows = [
        [
            source["name"],
            source["region"].replace("_", " ").title(),
            source["period"],
            f"{source['rows_in_union']:,}",
            f"{source['risk_rate']:.2%}",
        ]
        for source in model["datasets"].values()
        if source["role"] == "training"
    ]
    risk_band_rows = [
        [name, f"{count:,}"]
        for name, count in model["test_metrics"]["probability_summary"]["risk_bands"].items()
    ]
    _write_html(
        report_dir,
        "global_eda_report.html",
        "LimitIQ v2 Global Exploratory Analysis",
        "Observed source composition and model-score context",
        [
            (
                "Training-cohort composition",
                _table(
                    ["Source", "Region category", "Period", "Rows", "Outcome rate"],
                    composition_rows,
                ),
            ),
            (
                "Untouched-test score bands",
                _table(["Descriptive score band", "Accounts"], risk_band_rows),
            ),
            (
                "Interpretation",
                f"<p>The pooled observed outcome rate is <strong>{model['risk_rate']:.2%}</strong>, but source labels use different events and horizons. Cohort outcome rates and model-score bands are descriptive; they are not comparable jurisdiction-level default rates. {html.escape(model['evaluation_scope'])}</p>",
            ),
        ],
    )
    metric_html = "".join(
        f'<div class="metric"><small>{html.escape(label)}</small><br><strong>{value}</strong></div>'
        for label, value in (
            ("Macro ROC-AUC", f"{macro['roc_auc']:.4f}"),
            ("Macro Brier", f"{macro['brier_score']:.4f}"),
            ("Pooled ROC-AUC", f"{pooled['roc_auc']:.4f}"),
            ("Synthetic current exposure", _money(summary["current_limit"])),
            ("Synthetic proposed exposure", _money(summary["proposed_limit"])),
            ("Synthetic contribution", _money(summary["incremental_contribution"])),
        )
    )
    source_rows = [
        [
            model["datasets"][key]["name"],
            f"{value['accounts']:,}",
            f"{value['roc_auc']:.4f}",
            f"{value['brier_score']:.4f}",
            f"{value['mean_absolute_calibration_gap']:.4f}",
        ]
        for key, value in model["per_market_test_metrics"].items()
    ]
    _write_html(
        report_dir,
        "global_executive_report.html",
        "LimitIQ v2 Executive Report",
        "Observed source evidence, model estimates and synthetic economics",
        [
            ("Evidence snapshot", metric_html),
            (
                "Decision system",
                "<p>The platform evaluates current, +10%, +20% and +30% line candidates and applies exposure, expected-loss-proxy, profitability, payment-history and overextension controls before selecting an action.</p>",
            ),
            (
                "Untouched test by source cohort",
                _table(["Source cohort", "N", "ROC-AUC", "Brier", "Calibration gap"], source_rows),
            ),
            (
                "Synthetic action distribution",
                _table(
                    ["Action", "Accounts"],
                    [[key, f"{value:,}"] for key, value in summary["action_counts"].items()],
                ),
            ),
            (
                "Governance boundary",
                f"<p>{html.escape(model['target_note'])} {html.escape(model['evaluation_scope'])}</p><p><strong>Publication gate: {html.escape(model['publication_gate']['status'])}.</strong> {html.escape(model['publication_gate']['reason'])}</p>",
            ),
        ],
    )
    sensitivity_rows = [
        [
            item["assumption"].replace("_", " ").title(),
            item["scenario"],
            f"{item['value']:.4f}",
            f"{item['eligible_increases']:,}",
            _money(item["proposed_expected_loss"]),
            _money(item["incremental_contribution"]),
        ]
        for item in simulation.get("sensitivity", [])
    ]
    _write_html(
        report_dir,
        "global_policy_simulation_report.html",
        "LimitIQ v2 Policy Simulation Report",
        "Deterministic synthetic scenario - fully re-optimized",
        [
            (
                "Assumptions",
                _table(
                    ["Assumption", "Value"],
                    [
                        [name.replace("_", " ").title(), str(value)]
                        for name, value in simulation["assumptions"].items()
                    ],
                ),
            ),
            (
                "One-at-a-time sensitivity",
                _table(
                    [
                        "Assumption",
                        "Scenario",
                        "Value",
                        "Increases",
                        "Loss proxy",
                        "Contribution",
                    ],
                    sensitivity_rows,
                )
                + "<p>Every non-base row re-optimizes all 1,200 synthetic profiles while other assumptions stay fixed.</p>",
            ),
            (
                "Limitations",
                "<ul>"
                + "".join(f"<li>{html.escape(item)}</li>" for item in simulation["limitations"])
                + "</ul>",
            ),
        ],
    )
    _write_html(
        report_dir,
        "global_financial_impact_analysis.html",
        "LimitIQ v2 Financial Impact Analysis",
        "Synthetic economics - not observed impact",
        [
            (
                "Equation",
                "<p>Incremental interchange + incremental interest - incremental expected-loss proxy - funding cost - capital cost - servicing cost.</p>",
            ),
            (
                "Base scenario",
                f"<p>Current to proposed simulated limits: <strong>{_money(summary['current_limit'])} to {_money(summary['proposed_limit'])}</strong>. Simulated incremental contribution: <strong>{_money(summary['incremental_contribution'])}</strong>. Risk-adjusted return proxy: <strong>{_pct(summary['risk_adjusted_return'])}</strong>.</p>",
            ),
            (
                "Interpretation boundary",
                "<p>These values are deterministic outputs of visible INR assumptions. They are not causal estimates, forecasts, realized profit, regulatory capital, or IFRS 9 allowances.</p>",
            ),
        ],
    )
    _global_executive_pdf(simulation, model, report_dir)


def build_reports(report_dir: Path | None = None, model_dir: Path | None = None) -> None:
    report_dir = report_dir or REPORT_DIR
    model_dir = model_dir or MODEL_DIR
    report_dir.mkdir(parents=True, exist_ok=True)
    quality = _load(report_dir / "data_quality.json")
    eda = _load(report_dir / "eda.json")
    model = _load(model_dir / "metadata.json")
    simulation = _load(report_dir / "policy_simulation.json")
    summary = simulation["summary"]
    test = model["test_metrics"]
    metrics = "".join(
        f'<div class="metric"><small>{html.escape(label)}</small><br><strong>{value}</strong></div>'
        for label, value in (
            ("Untouched-test ROC-AUC", f"{test['roc_auc']:.3f}"),
            ("Untouched-test PR-AUC", f"{test['pr_auc']:.3f}"),
            ("Brier score", f"{test['brier_score']:.3f}"),
            ("Current credit limits", _money(summary["current_limit"])),
            ("Proposed credit limits — simulated", _money(summary["proposed_limit"])),
            ("Current EAD — simulated", _money(summary["current_ead"])),
            ("Proposed EAD — simulated", _money(summary["proposed_ead"])),
            ("Current expected loss — simulated", _money(summary["current_expected_loss"])),
            ("Proposed expected loss — simulated", _money(summary["proposed_expected_loss"])),
            ("Incremental contribution — simulated", _money(summary["incremental_contribution"])),
            ("Risk-adjusted return — simulated", _pct(summary["risk_adjusted_return"])),
        )
    )
    _write_html(
        report_dir,
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
                "Currency localization",
                f"<p>Observed TWD monetary fields are converted to INR at {quality['twd_to_inr']:.2f} INR per TWD using the documented July 2026 cross-rate. This presentation transform is not evidence about Indian borrowers.</p>",
            ),
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
            (
                "Limitations and roadmap",
                "<p>The old single-market source has no affordability, external-obligation, line-treatment, EAD/LGD or causal response outcomes. Next steps are current multi-market data, verified affordability inputs, randomized line experiments, independent validation, shadow mode, a monitored pilot and controlled rollback.</p>",
            ),
        ],
    )
    _write_html(
        report_dir,
        "data_quality_report.html",
        "Data Quality Report",
        "Observed source-data evidence",
        [
            (
                "Lineage",
                f"<p>UCI Default of Credit Card Clients; dataset version <code>{quality['dataset_version']}</code>; CC BY 4.0. Source {quality['source_currency']} monetary fields are converted to {quality['model_currency']} at {quality['twd_to_inr']:.2f} per TWD before modelling.</p>",
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
        report_dir,
        "eda_report.html",
        "Exploratory Data Analysis",
        "Observed behavior; currency-converted presentation",
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
    importance_rows = [
        [item["feature"], f"{item['importance']:.2%}", f"{item['brier_degradation']:.6f}"]
        for item in test["feature_importance"][:12]
    ]
    drift_rows = [
        [item["feature"], f"{item['psi']:.4f}", item["status"]]
        for item in test["drift_indicators"][:12]
    ]
    segment_rows = [
        [
            item["dimension"],
            item["segment"],
            str(item["accounts"]),
            _pct(item["observed_default_rate"]),
            _pct(item["mean_pd"]),
            "n/a" if item["roc_auc"] is None else f"{item['roc_auc']:.3f}",
        ]
        for item in test["segments"]
    ]
    _write_html(
        report_dir,
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
            (
                "Permutation importance",
                _table(
                    ["Raw behavioral field", "Normalized share", "Brier degradation"],
                    importance_rows,
                )
                + f"<p>{html.escape(model['feature_importance_method'])}</p>",
            ),
            (
                "Development-split drift indicators",
                _table(["Engineered feature", "PSI", "Status"], drift_rows)
                + f"<p>{html.escape(model['drift_method'])}</p>",
            ),
            (
                "Fairness diagnostics",
                _table(
                    ["Dimension", "Segment", "N", "Observed", "Mean PD", "ROC-AUC"],
                    segment_rows,
                )
                + "<p>Sex and age are audit-only. These historical diagnostics identify review questions and do not prove fair-lending compliance.</p>",
            ),
            (
                "Monitoring, override and rollback",
                "<p>Monitor schema/ranges, feature and PD drift, calibration, risk-band loss, action/override rates and segment gaps. Record every human override with actor, rationale and approval. On material deterioration, disable automatic increases and restore the prior checksum-verified artifact.</p>",
            ),
        ],
    )
    assumptions = simulation["assumptions"]
    sensitivity_rows = [
        [
            item["assumption"].replace("_", " ").title(),
            item["scenario"],
            f"{item['value']:.4f}",
            f"{item['eligible_increases']:,}",
            _money(item["proposed_expected_loss"]),
            _money(item["incremental_contribution"]),
        ]
        for item in simulation.get("sensitivity", [])
    ]
    _write_html(
        report_dir,
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
            (
                "One-at-a-time sensitivity",
                _table(
                    [
                        "Assumption",
                        "Scenario",
                        "Value",
                        "Increases",
                        "Expected loss",
                        "Contribution",
                    ],
                    sensitivity_rows,
                )
                + "<p>Each low/base/high row re-optimizes the full demonstration portfolio while holding other assumptions fixed.</p>",
            ),
        ],
    )
    _write_html(
        report_dir,
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
            (
                "Sensitivity and limitations",
                "<p>The policy report re-optimizes low/base/high scenarios for LGD, CCF, interchange, APR, funding, capital, response elasticity, maximum increase, expected-loss ceiling and profitability hurdle. Results remain assumption-driven and exclude taxes, rewards, fraud, collections, macro stress and verified affordability.</p>",
            ),
            (
                "Roadmap",
                "<p>Estimate economics from governed experiments, validate affordability and loss assumptions, add macro scenarios and concentration limits, run shadow mode, then pilot with monitoring and rollback thresholds.</p>",
            ),
        ],
    )
    _executive_pdf(simulation, model, report_dir)
    if (model_dir / "global_metadata.json").exists() and (
        report_dir / "global_policy_simulation.json"
    ).exists():
        build_global_reports(report_dir, model_dir)


if __name__ == "__main__":
    build_reports()
