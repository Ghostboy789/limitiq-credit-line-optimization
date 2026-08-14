from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Any

import numpy as np
import pandas as pd

from limitiq.config import PolicyAssumptions

ACTION_LABELS = {
    0.0: "No change",
    0.1: "Increase 10%",
    0.2: "Increase 20%",
    0.3: "Increase 30%",
}


@dataclass(frozen=True)
class Decision:
    account_id: str
    action: str
    increase_pct: float
    current_limit: float
    proposed_limit: float
    pd: float
    risk_band: str
    current_ead: float
    proposed_ead: float
    current_expected_loss: float
    proposed_expected_loss: float
    incremental_contribution: float
    risk_adjusted_return: float
    reason_codes: tuple[str, ...]
    policy_checks: dict[str, bool]
    candidate_results: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["reason_codes"] = list(self.reason_codes)
        result["candidate_results"] = list(self.candidate_results)
        return result


def risk_band(pd_value: float) -> str:
    if pd_value < 0.05:
        return "Low"
    if pd_value < 0.15:
        return "Moderate"
    if pd_value < 0.30:
        return "High"
    return "Very high"


def exposure(limit: float, balance: float, ccf: float) -> float:
    drawn = min(max(balance, 0.0), limit)
    return drawn + ccf * max(limit - drawn, 0.0)


def expected_loss(pd_value: float, lgd: float, ead: float) -> float:
    if not 0 <= pd_value <= 1 or not 0 <= lgd <= 1 or ead < 0:
        raise ValueError("PD and LGD must be in [0, 1], and EAD cannot be negative")
    return pd_value * lgd * ead


def _behavior(row: pd.Series) -> dict[str, Any]:
    limit = float(row["current_limit_inr"])
    balance = max(float(row["current_balance_inr"]), 0.0)
    reported_utilization = pd.to_numeric(row.get("utilization"), errors="coerce")
    utilization = (
        float(reported_utilization) if pd.notna(reported_utilization) else balance / max(limit, 1.0)
    )
    delinquency = pd.to_numeric(row.get("delinquency_count"), errors="coerce")
    debt_to_income = pd.to_numeric(row.get("debt_to_income"), errors="coerce")
    history_fields = (
        "delinquency_count",
        "utilization",
        "debt_to_income",
        "credit_lines",
        "credit_age_months",
    )
    return {
        "limit": limit,
        "balance": balance,
        "delinquency_count": float(delinquency) if pd.notna(delinquency) else None,
        "debt_to_income": float(debt_to_income) if pd.notna(debt_to_income) else None,
        "utilization": min(max(utilization, 0.0), 5.0),
        "history_fields": sum(pd.notna(row.get(column)) for column in history_fields),
    }


def _warning_state(behavior: dict[str, Any]) -> tuple[str | None, list[str]]:
    delinquency = behavior["delinquency_count"]
    debt_to_income = behavior["debt_to_income"]
    reasons: list[str] = []
    if behavior["history_fields"] < 2 or delinquency is None:
        return "Manual review", ["Insufficient behavioral history", "Manual review required"]
    if delinquency >= 2:
        reasons.append("Repeated delinquency")
        return "Freeze automatic increases", reasons
    if delinquency == 1:
        return "Manual review", ["Reported delinquency", "Manual review required"]
    if debt_to_income is not None and debt_to_income > 0.60:
        return "Manual review", ["Customer-overextension safeguard", "Manual review required"]
    if behavior["utilization"] > 1.10:
        return "Manual review", ["Customer-overextension safeguard", "Manual review required"]
    return None, reasons


def _candidate(
    behavior: dict[str, Any],
    pd_value: float,
    increase_pct: float,
    assumptions: PolicyAssumptions,
    automatic_increases_enabled: bool,
) -> dict[str, Any]:
    limit = behavior["limit"]
    balance = behavior["balance"]
    proposed_limit = limit * (1 + increase_pct)
    current_ead = exposure(limit, balance, assumptions.ccf)
    proposed_ead = exposure(proposed_limit, balance, assumptions.ccf)
    current_ecl = expected_loss(pd_value, assumptions.lgd, current_ead)
    proposed_ecl = expected_loss(pd_value, assumptions.lgd, proposed_ead)
    delta_ead = proposed_ead - current_ead
    utilization = behavior["utilization"]
    # Elasticity is the simulated monthly spend response to incremental line; annual economics
    # therefore use 12 periods. This is an assumption, never an observed causal estimate.
    incremental_spend = (
        (proposed_limit - limit) * assumptions.response_elasticity * utilization * 12
    )
    interchange = incremental_spend * assumptions.interchange_rate
    interest = incremental_spend * assumptions.revolving_rate * assumptions.apr
    incremental_ecl = proposed_ecl - current_ecl
    funding = delta_ead * assumptions.funding_cost
    capital = delta_ead * assumptions.capital_cost
    servicing = assumptions.servicing_cost if increase_pct else 0.0
    contribution = interchange + interest - incremental_ecl - funding - capital - servicing
    checks = {
        "automatic_increases_enabled": automatic_increases_enabled,
        "within_maximum_increase": bool(increase_pct <= assumptions.max_increase + 1e-12),
        "within_account_exposure": bool(proposed_limit <= assumptions.max_account_exposure),
        "within_expected_loss_ceiling": bool(
            pd_value * assumptions.lgd <= assumptions.expected_loss_ceiling
        ),
        "meets_profitability_hurdle": bool(contribution >= assumptions.profitability_hurdle),
        "payment_history_eligible": bool(behavior["delinquency_count"] == 0),
        "not_overextended": bool(
            utilization <= 1.10
            and (behavior["debt_to_income"] is None or behavior["debt_to_income"] <= 0.60)
        ),
    }
    eligible = increase_pct == 0 or all(checks.values())
    return {
        "increase_pct": increase_pct,
        "label": ACTION_LABELS.get(increase_pct, f"Increase {increase_pct:.0%}"),
        "proposed_limit": proposed_limit,
        "proposed_ead": proposed_ead,
        "proposed_expected_loss": proposed_ecl,
        "incremental_contribution": contribution,
        "risk_adjusted_return": contribution / delta_ead if delta_ead > 0 else 0.0,
        "eligible": eligible,
        "checks": checks,
    }


def recommend_account(
    row: pd.Series,
    pd_value: float,
    account_id: str,
    assumptions: PolicyAssumptions | None = None,
    automatic_increases_enabled: bool = True,
) -> Decision:
    assumptions = assumptions or PolicyAssumptions()
    assumptions.validate()
    if not 0 <= pd_value <= 1:
        raise ValueError("PD must be between 0 and 1")
    behavior = _behavior(row)
    warning_action, warning_reasons = _warning_state(behavior)
    allowed = [pct for pct in (0.0, 0.1, 0.2, 0.3) if pct <= assumptions.max_increase + 1e-12]
    candidates = tuple(
        _candidate(behavior, pd_value, pct, assumptions, automatic_increases_enabled)
        for pct in allowed
    )
    baseline = candidates[0]
    if warning_action:
        selected = baseline
        reasons = warning_reasons + (
            ["Manual review required"] if warning_action == "Manual review" else []
        )
        action = warning_action
    elif not automatic_increases_enabled:
        selected = baseline
        action = "Manual review"
        reasons = ["Automatic increases disabled by governance control", "Manual review required"]
    else:
        eligible = [item for item in candidates if item["eligible"]]
        selected = max(
            eligible, key=lambda item: (item["incremental_contribution"], -item["increase_pct"])
        )
        action = selected["label"]
        utilization = behavior["utilization"]
        reasons = []
        if behavior["delinquency_count"] == 0:
            reasons.append("No reported delinquency in the harmonized source fields")
        if utilization >= 0.65 and pd_value < 0.15:
            reasons.append("High utilization with low estimated risk")
        if utilization < 0.20:
            reasons.append("Low utilization provides no evidence of additional need")
        if selected["increase_pct"] == 0:
            failed = [name for name, ok in candidates[-1]["checks"].items() if not ok]
            mapping = {
                "automatic_increases_enabled": "Automatic increases disabled by governance control",
                "within_account_exposure": "Exposure limit reached",
                "within_expected_loss_ceiling": "Expected loss exceeds policy ceiling",
                "meets_profitability_hurdle": "Incremental return below profitability hurdle",
                "payment_history_eligible": "Payment-history eligibility rule not met",
                "not_overextended": "Customer-overextension safeguard",
            }
            reasons.extend(mapping[name] for name in failed if name in mapping)
        if not reasons:
            reasons.append("Best eligible risk-adjusted contribution")
    limit = behavior["limit"]
    balance = behavior["balance"]
    current_ead = exposure(limit, balance, assumptions.ccf)
    current_ecl = expected_loss(pd_value, assumptions.lgd, current_ead)
    return Decision(
        account_id=account_id,
        action=action,
        increase_pct=float(selected["increase_pct"]),
        current_limit=limit,
        proposed_limit=float(selected["proposed_limit"]),
        pd=float(pd_value),
        risk_band=risk_band(pd_value),
        current_ead=current_ead,
        proposed_ead=float(selected["proposed_ead"]),
        current_expected_loss=current_ecl,
        proposed_expected_loss=float(selected["proposed_expected_loss"]),
        incremental_contribution=float(selected["incremental_contribution"]),
        risk_adjusted_return=float(selected["risk_adjusted_return"]),
        reason_codes=tuple(dict.fromkeys(reasons)),
        policy_checks=selected["checks"],
        candidate_results=candidates,
    )


def recommend_portfolio(
    frame: pd.DataFrame,
    probabilities: np.ndarray,
    account_ids: list[str],
    assumptions: PolicyAssumptions | None = None,
    automatic_increases_enabled: bool = True,
) -> list[Decision]:
    assumptions = assumptions or PolicyAssumptions()
    if len(frame) != len(probabilities) or len(frame) != len(account_ids):
        raise ValueError("Frame, probabilities, and account IDs must have equal lengths")
    decisions = [
        recommend_account(
            row,
            float(probability),
            account_id,
            assumptions,
            automatic_increases_enabled,
        )
        for (_, row), probability, account_id in zip(
            frame.iterrows(), probabilities, account_ids, strict=True
        )
    ]
    current_total = sum(item.current_limit for item in decisions)
    cap = current_total * (1 + assumptions.portfolio_growth_cap)
    proposed_total = sum(item.proposed_limit for item in decisions)
    if proposed_total <= cap:
        return decisions
    ranked = sorted(
        (item for item in decisions if item.increase_pct > 0),
        key=lambda item: (item.incremental_contribution, item.account_id),
    )
    by_id = {item.account_id: item for item in decisions}
    for item in ranked:
        if proposed_total <= cap:
            break
        proposed_total -= item.proposed_limit - item.current_limit
        base = item.candidate_results[0]
        by_id[item.account_id] = replace(
            item,
            action="No change",
            increase_pct=0.0,
            proposed_limit=item.current_limit,
            proposed_ead=item.current_ead,
            proposed_expected_loss=item.current_expected_loss,
            incremental_contribution=0.0,
            risk_adjusted_return=0.0,
            reason_codes=tuple(dict.fromkeys((*item.reason_codes, "Exposure limit reached"))),
            policy_checks=base["checks"],
        )
    return [by_id[account_id] for account_id in account_ids]


SENSITIVITY_ASSUMPTIONS = (
    "lgd",
    "ccf",
    "interchange_rate",
    "apr",
    "funding_cost",
    "capital_cost",
    "response_elasticity",
    "max_increase",
    "expected_loss_ceiling",
    "profitability_hurdle",
)


def portfolio_sensitivity(
    frame: pd.DataFrame,
    probabilities: np.ndarray,
    account_ids: list[str],
    assumptions: PolicyAssumptions | None = None,
) -> list[dict[str, Any]]:
    """Re-optimize low/base/high one-at-a-time scenarios for key assumptions."""
    assumptions = assumptions or PolicyAssumptions()
    base_values = assumptions.to_dict()
    base_summary = summarize_portfolio(
        recommend_portfolio(frame, probabilities, account_ids, assumptions)
    )
    rows: list[dict[str, Any]] = []
    for name in SENSITIVITY_ASSUMPTIONS:
        base = base_values[name]
        for label, factor in (("Low", 0.8), ("Base", 1.0), ("High", 1.2)):
            values = dict(base_values)
            values[name] = min(base * factor, 1.0) if base <= 1 else base * factor
            if factor == 1.0:
                summary = base_summary
            else:
                scenario = PolicyAssumptions(**values)
                summary = summarize_portfolio(
                    recommend_portfolio(frame, probabilities, account_ids, scenario)
                )
            rows.append(
                {
                    "assumption": name,
                    "scenario": label,
                    "value": values[name],
                    "eligible_increases": summary["eligible_increases"],
                    "proposed_limit": summary["proposed_limit"],
                    "proposed_expected_loss": summary["proposed_expected_loss"],
                    "incremental_contribution": summary["incremental_contribution"],
                    "risk_adjusted_return": summary["risk_adjusted_return"],
                }
            )
    return rows


def summarize_portfolio(decisions: list[Decision]) -> dict[str, Any]:
    current_limit = sum(item.current_limit for item in decisions)
    proposed_limit = sum(item.proposed_limit for item in decisions)
    current_ecl = sum(item.current_expected_loss for item in decisions)
    proposed_ecl = sum(item.proposed_expected_loss for item in decisions)
    current_ead = sum(item.current_ead for item in decisions)
    proposed_ead = sum(item.proposed_ead for item in decisions)
    contribution = sum(item.incremental_contribution for item in decisions)
    incremental_exposure = sum(item.proposed_ead - item.current_ead for item in decisions)
    action_counts: dict[str, int] = {}
    risk_counts: dict[str, int] = {}
    for item in decisions:
        action_counts[item.action] = action_counts.get(item.action, 0) + 1
        risk_counts[item.risk_band] = risk_counts.get(item.risk_band, 0) + 1
    return {
        "accounts": len(decisions),
        "current_limit": current_limit,
        "proposed_limit": proposed_limit,
        "current_ead": current_ead,
        "proposed_ead": proposed_ead,
        "current_expected_loss": current_ecl,
        "proposed_expected_loss": proposed_ecl,
        "incremental_contribution": contribution,
        "incremental_exposure": incremental_exposure,
        "risk_adjusted_return": contribution / incremental_exposure
        if incremental_exposure
        else 0.0,
        "eligible_increases": sum(item.increase_pct > 0 for item in decisions),
        "early_warning": sum(
            item.action in {"Freeze automatic increases", "Manual review"} for item in decisions
        ),
        "action_counts": action_counts,
        "risk_counts": risk_counts,
    }
