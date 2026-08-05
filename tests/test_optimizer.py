from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from limitiq.config import PolicyAssumptions
from limitiq.features import MODEL_INPUT_COLUMNS
from limitiq.optimizer import (
    expected_loss,
    exposure,
    portfolio_sensitivity,
    recommend_account,
    recommend_portfolio,
    summarize_portfolio,
)


def test_expected_loss_formula() -> None:
    assert expected_loss(0.1, 0.6, 100_000) == pytest.approx(6_000)


def test_expected_loss_rejects_invalid_bounds() -> None:
    with pytest.raises(ValueError):
        expected_loss(1.1, 0.6, 100)
    with pytest.raises(ValueError):
        expected_loss(0.1, 0.6, -1)


def test_ead_includes_drawn_and_converted_undrawn() -> None:
    assert exposure(100_000, 40_000, 0.75) == pytest.approx(85_000)
    assert exposure(100_000, 120_000, 0.75) == pytest.approx(100_000)


def test_profitable_healthy_account_gets_governed_increase(healthy_row: pd.Series) -> None:
    decision = recommend_account(healthy_row, 0.06, "TEST-001")
    assert decision.action in {"Increase 10%", "Increase 20%", "Increase 30%"}
    assert decision.proposed_limit > decision.current_limit
    assert decision.incremental_contribution > 0
    assert "Strong repayment consistency" in decision.reason_codes


def test_severe_delinquency_freezes_not_decreases(healthy_row: pd.Series) -> None:
    row = healthy_row.copy()
    row["PAY_0"] = 2
    row["PAY_2"] = 2
    decision = recommend_account(row, 0.3, "TEST-002")
    assert decision.action == "Freeze automatic increases"
    assert decision.proposed_limit == decision.current_limit
    assert "Repeated delinquency" in decision.reason_codes


def test_mild_recent_delay_routes_manual_review(healthy_row: pd.Series) -> None:
    row = healthy_row.copy()
    row["PAY_0"] = 1
    decision = recommend_account(row, 0.15, "TEST-003")
    assert decision.action == "Manual review"
    assert "Manual review required" in decision.reason_codes


def test_low_utilization_can_fail_hurdle(healthy_row: pd.Series) -> None:
    row = healthy_row.copy()
    row["BILL_AMT1"] = 1_000
    decision = recommend_account(row, 0.05, "TEST-004")
    assert decision.action == "No change"
    assert "Low utilization provides no evidence of additional need" in decision.reason_codes


def test_loss_ceiling_blocks_increase(healthy_row: pd.Series) -> None:
    assumptions = PolicyAssumptions(expected_loss_ceiling=0.01)
    decision = recommend_account(healthy_row, 0.10, "TEST-005", assumptions)
    assert decision.action == "No change"
    assert "Expected loss exceeds policy ceiling" in decision.reason_codes


def test_maximum_increase_is_respected(healthy_row: pd.Series) -> None:
    assumptions = PolicyAssumptions(max_increase=0.10)
    decision = recommend_account(healthy_row, 0.04, "TEST-006", assumptions)
    assert decision.increase_pct <= 0.10
    assert len(decision.candidate_results) == 2


def test_account_exposure_limit_is_respected(healthy_row: pd.Series) -> None:
    assumptions = PolicyAssumptions(max_account_exposure=100_001)
    decision = recommend_account(healthy_row, 0.04, "TEST-007", assumptions)
    assert decision.action == "No change"
    assert "Exposure limit reached" in decision.reason_codes


def test_portfolio_growth_cap_reverts_lowest_value_deterministically(
    healthy_row: pd.Series,
) -> None:
    frame = pd.DataFrame([healthy_row, healthy_row], columns=MODEL_INPUT_COLUMNS)
    assumptions = PolicyAssumptions(portfolio_growth_cap=0.05)
    first = recommend_portfolio(frame, np.array([0.04, 0.04]), ["A-001", "A-002"], assumptions)
    second = recommend_portfolio(frame, np.array([0.04, 0.04]), ["A-001", "A-002"], assumptions)
    assert [item.to_dict() for item in first] == [item.to_dict() for item in second]
    assert sum(item.proposed_limit for item in first) <= 210_000


def test_portfolio_length_mismatch_is_rejected(healthy_row: pd.Series) -> None:
    with pytest.raises(ValueError, match="equal lengths"):
        recommend_portfolio(pd.DataFrame([healthy_row]), np.array([0.1, 0.2]), ["A"])


def test_summary_reconciles_decisions(healthy_row: pd.Series) -> None:
    decisions = [recommend_account(healthy_row, 0.04, "A")]
    summary = summarize_portfolio(decisions)
    assert summary["accounts"] == 1
    assert sum(summary["action_counts"].values()) == 1


def test_portfolio_sensitivity_is_deterministic_and_reoptimizes(
    healthy_row: pd.Series,
) -> None:
    frame = pd.DataFrame([healthy_row], columns=MODEL_INPUT_COLUMNS)
    first = portfolio_sensitivity(frame, np.array([0.04]), ["A"])
    second = portfolio_sensitivity(frame, np.array([0.04]), ["A"])
    assert first == second
    assert len(first) == 30
    assert {row["scenario"] for row in first} == {"Low", "Base", "High"}
    assert all(row["proposed_limit"] >= 100_000 for row in first)


def test_assumption_validation() -> None:
    with pytest.raises(ValueError, match="lgd"):
        PolicyAssumptions(lgd=1.2).validate()
    with pytest.raises(ValueError, match="positive"):
        PolicyAssumptions(max_account_exposure=0).validate()
