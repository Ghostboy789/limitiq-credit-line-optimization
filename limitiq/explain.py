"""Model-linked behavioral sensitivities kept separate from policy reason codes."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from limitiq.features import BILL_COLUMNS, PAY_COLUMNS, PAYMENT_COLUMNS, validate_taiwan_input


def explain_account(model: Any, raw_account: pd.DataFrame) -> dict[str, Any]:
    """Measure score changes under documented one-group-at-a-time neutralizations."""
    account = validate_taiwan_input(raw_account)
    if len(account) != 1:
        raise ValueError("Local explanation requires exactly one account")
    baseline = float(model.predict_proba(account)[:, 1][0])
    scenarios: dict[str, pd.DataFrame] = {}

    no_delinquency = account.copy()
    no_delinquency[PAY_COLUMNS] = np.minimum(no_delinquency[PAY_COLUMNS], 0)
    scenarios["repayment_status_history"] = no_delinquency

    moderate_utilization = account.copy()
    moderate_utilization[BILL_COLUMNS] = np.minimum(
        moderate_utilization[BILL_COLUMNS],
        moderate_utilization["LIMIT_BAL"].to_numpy()[:, None] * 0.30,
    )
    scenarios["bill_and_utilization_history"] = moderate_utilization

    consistent_payment = account.copy()
    target_payment = account[BILL_COLUMNS].to_numpy() * 0.10
    consistent_payment[PAYMENT_COLUMNS] = np.maximum(
        consistent_payment[PAYMENT_COLUMNS].to_numpy(), target_payment
    )
    scenarios["payment_amount_history"] = consistent_payment

    stable_balance = account.copy()
    stable_balance[BILL_COLUMNS] = np.repeat(
        account[BILL_COLUMNS].mean(axis=1).to_numpy()[:, None], len(BILL_COLUMNS), axis=1
    )
    scenarios["balance_trend_and_volatility"] = stable_balance

    sensitivities = []
    for group, scenario in scenarios.items():
        counterfactual = float(model.predict_proba(scenario)[:, 1][0])
        score_change = counterfactual - baseline
        sensitivities.append(
            {
                "feature_group": group,
                "observed_score": baseline,
                "neutralized_score": counterfactual,
                "score_change_when_neutralized": score_change,
                "direction": (
                    "no material effect"
                    if abs(score_change) < 0.005
                    else "risk-increasing evidence"
                    if score_change < 0
                    else "risk-reducing evidence"
                ),
            }
        )
    sensitivities.sort(key=lambda row: abs(row["score_change_when_neutralized"]), reverse=True)
    return {
        "classification": "Local model sensitivity; not a causal effect or policy reason",
        "baseline_score": baseline,
        "sensitivities": sensitivities,
        "boundary": (
            "Each row changes a correlated behavioral group to a documented neutral scenario; "
            "results describe model response, not customer outcomes"
        ),
    }
