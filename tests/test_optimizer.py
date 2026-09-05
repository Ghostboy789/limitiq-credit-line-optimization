from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from limitiq.config import PolicyAssumptions
from limitiq.features import EXPOSURE_COLUMNS, MODEL_INPUT_COLUMNS
from limitiq.optimizer import (
    expected_loss,
    exposure,
    portfolio_sensitivity,
    recommend_account,
    recommend_portfolio,
    summarize_portfolio,
)

DECISION_COLUMNS = [*MODEL_INPUT_COLUMNS, *EXPOSURE_COLUMNS]


def test_expected_loss_and_exposure_math() -> None:
    assert expected_loss(0.1, 0.6, 100_000) == pytest.approx(6_000)
    assert exposure(100_000, 40_000, 0.75) == pytest.approx(85_000)
    assert exposure(100_000, 120_000, 0.75) == pytest.approx(100_000)
    with pytest.raises(ValueError):
        expected_loss(1.1, 0.6, 100)
    with pytest.raises(ValueError):
        expected_loss(0.1, 0.6, -1)


def test_profitable_low_risk_account_gets_governed_increase(healthy_row: pd.Series) -> None:
    decision = recommend_account(healthy_row, 0.06, "TEST-001")
    assert decision.action in {"Increase 10%", "Increase 20%", "Increase 30%"}
    assert decision.proposed_limit > decision.current_limit
    assert decision.incremental_contribution > 0
    assert "No reported delinquency in the harmonized source fields" in decision.reason_codes
    assert "High utilization with low estimated risk" in decision.reason_codes


def test_repeated_delinquency_freezes_without_decrease(healthy_row: pd.Series) -> None:
    row = healthy_row.copy()
    row["delinquency_count"] = 2
    decision = recommend_account(row, 0.30, "TEST-002")
    assert decision.action == "Freeze automatic increases"
    assert decision.proposed_limit == decision.current_limit
    assert decision.reason_codes == ("Repeated delinquency",)


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"delinquency_count": 1}, "Reported delinquency"),
        ({"delinquency_count": np.nan}, "Insufficient behavioral history"),
        ({"debt_to_income": 0.75}, "Customer-overextension safeguard"),
        ({"utilization": 1.2}, "Customer-overextension safeguard"),
    ],
)
def test_manual_review_conditions(
    healthy_row: pd.Series, changes: dict[str, float], reason: str
) -> None:
    row = healthy_row.copy()
    for column, value in changes.items():
        row[column] = value
    decision = recommend_account(row, 0.15, "TEST-003")
    assert decision.action == "Manual review"
    assert decision.proposed_limit == decision.current_limit
    assert reason in decision.reason_codes
    assert "Manual review required" in decision.reason_codes


def test_low_need_loss_and_exposure_policies_return_no_change(healthy_row: pd.Series) -> None:
    low_need = healthy_row.copy()
    low_need["utilization"] = 0.01
    low_need["current_balance_inr"] = 1_000
    decision = recommend_account(low_need, 0.05, "TEST-004")
    assert decision.action == "No change"
    assert "Low utilization provides no evidence of additional need" in decision.reason_codes
    assert "Incremental return below profitability hurdle" in decision.reason_codes

    loss = recommend_account(
        healthy_row,
        0.10,
        "TEST-005",
        PolicyAssumptions(expected_loss_ceiling=0.01),
    )
    assert loss.action == "No change"
    assert "Expected-loss rate exceeds policy ceiling" in loss.reason_codes

    capped = recommend_account(
        healthy_row,
        0.04,
        "TEST-006",
        PolicyAssumptions(max_account_exposure=100_001),
    )
    assert capped.action == "No change"
    assert "Exposure limit reached" in capped.reason_codes


def test_maximum_increase_and_portfolio_growth_cap_are_deterministic(
    healthy_row: pd.Series,
) -> None:
    limited = recommend_account(
        healthy_row,
        0.04,
        "TEST-007",
        PolicyAssumptions(max_increase=0.10),
    )
    assert limited.increase_pct <= 0.10
    assert len(limited.candidate_results) == 2

    frame = pd.DataFrame([healthy_row, healthy_row], columns=DECISION_COLUMNS)
    assumptions = PolicyAssumptions(portfolio_growth_cap=0.05)
    first = recommend_portfolio(frame, np.array([0.04, 0.04]), ["A-001", "A-002"], assumptions)
    second = recommend_portfolio(frame, np.array([0.04, 0.04]), ["A-001", "A-002"], assumptions)
    assert [item.to_dict() for item in first] == [item.to_dict() for item in second]
    assert sum(item.proposed_limit for item in first) <= 210_000
    held = next(item for item in first if item.increase_pct == 0)
    assert "Portfolio limit growth cap retained current limit" in held.reason_codes
    assert not {
        "Exposure limit reached",
        "Best eligible risk-adjusted contribution",
        "Explicit customer acceptance required before activation",
    } & set(held.reason_codes)


def test_portfolio_contract_summary_and_sensitivity(healthy_row: pd.Series) -> None:
    frame = pd.DataFrame([healthy_row], columns=DECISION_COLUMNS)
    with pytest.raises(ValueError, match="equal lengths"):
        recommend_portfolio(frame, np.array([0.1, 0.2]), ["A"])

    decisions = recommend_portfolio(frame, np.array([0.04]), ["A"])
    summary = summarize_portfolio(decisions)
    assert summary["accounts"] == 1
    assert sum(summary["action_counts"].values()) == 1

    first = portfolio_sensitivity(frame, np.array([0.04]), ["A"])
    second = portfolio_sensitivity(frame, np.array([0.04]), ["A"])
    assert first == second
    assert len(first) == 36
    assert {row["scenario"] for row in first} == {"Low", "Base", "High"}


def test_assumption_validation() -> None:
    with pytest.raises(ValueError, match="lgd"):
        PolicyAssumptions(lgd=1.2).validate()
    with pytest.raises(ValueError, match="positive"):
        PolicyAssumptions(max_account_exposure=0).validate()

    with pytest.raises(ValueError, match="response_decay_kappa"):
        PolicyAssumptions(response_decay_kappa=-0.1).validate()


def test_global_optimizer_respects_loss_cap_and_is_not_greedy(healthy_row: pd.Series) -> None:
    frame = pd.DataFrame([healthy_row, healthy_row], columns=DECISION_COLUMNS)
    assumptions = PolicyAssumptions(
        portfolio_growth_cap=0.20,
        portfolio_loss_growth_cap=0.02,
        portfolio_capital_budget=1_000_000,
        max_higher_risk_increase_share=0.50,
    )
    decisions = recommend_portfolio(frame, np.array([0.01, 0.08]), ["LOW", "HIGH"], assumptions)
    summary = summarize_portfolio(decisions)
    assert summary["proposed_expected_loss"] <= summary["current_expected_loss"] * 1.02 + 1e-6
    held = [decision for decision in decisions if decision.increase_pct == 0]
    assert held
    assert any(decision.increase_pct > 0 for decision in decisions)
    assert all(
        {reason for reason in decision.reason_codes if reason.startswith("Portfolio ")}
        == {"Portfolio loss growth cap retained current limit"}
        for decision in held
    )
    assert all(
        "Best eligible risk-adjusted contribution" not in decision.reason_codes for decision in held
    )
    for decision in decisions:
        consent = "Explicit customer acceptance required before activation"
        assert (consent in decision.reason_codes) is (decision.increase_pct > 0)


def test_diminishing_response_and_pd_linked_ccf_are_live(healthy_row: pd.Series) -> None:
    decision = recommend_account(healthy_row, 0.04, "DIMINISHING")
    assert decision.action in {"Increase 10%", "Increase 20%"}
    assert decision.action != "Increase 30%"

    low_risk = recommend_account(healthy_row, 0.02, "LOW-CCF")
    high_risk = recommend_account(
        healthy_row,
        0.20,
        "HIGH-CCF",
        PolicyAssumptions(expected_loss_ceiling=1),
    )
    assert high_risk.current_ead > low_risk.current_ead


def test_tightening_growth_cap_cannot_raise_aggregate_limit(healthy_row: pd.Series) -> None:
    frame = pd.DataFrame([healthy_row] * 12, columns=DECISION_COLUMNS)
    probabilities = np.full(len(frame), 0.04)
    account_ids = [f"CAP-{index}" for index in range(len(frame))]
    common = {
        "portfolio_loss_growth_cap": 1,
        "portfolio_capital_budget": 1_000_000_000,
        "max_higher_risk_increase_share": 1,
    }
    loose = recommend_portfolio(
        frame, probabilities, account_ids, PolicyAssumptions(portfolio_growth_cap=0.20, **common)
    )
    tight = recommend_portfolio(
        frame, probabilities, account_ids, PolicyAssumptions(portfolio_growth_cap=0.03, **common)
    )
    assert sum(item.proposed_limit for item in tight) <= sum(item.proposed_limit for item in loose)


def test_governance_switch_disables_automatic_increases(healthy_row: pd.Series) -> None:
    decision = recommend_account(
        healthy_row,
        0.03,
        "SWITCH-1",
        automatic_increases_enabled=False,
    )
    assert decision.action == "Manual review"
    assert decision.increase_pct == 0
    assert "Automatic increases disabled by governance control" in decision.reason_codes


def test_outside_model_support_routes_to_manual_review(healthy_row: pd.Series) -> None:
    row = healthy_row.copy()
    row["outside_model_support"] = True
    decision = recommend_account(row, 0.03, "OOD-1")
    assert decision.action == "Manual review"
    assert decision.policy_checks["within_model_support"] is False
    assert "Outside behavioral model support" in decision.reason_codes
