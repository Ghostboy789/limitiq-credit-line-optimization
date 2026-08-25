from __future__ import annotations

import pandas as pd
import pytest

from limitiq.india_validation import (
    TARGET,
    forward_splits,
    train_forward_validation,
    validate_account_months,
)


def _account_months() -> pd.DataFrame:
    rows = []
    for month in range(1, 7):
        for index in range(12):
            snapshot = pd.Timestamp(2024, month, 1, tz="Asia/Kolkata")
            rows.append(
                {
                    "customer_reference": f"TOKEN-{month:02d}-{index:03d}",
                    "as_of_date": snapshot.isoformat(),
                    "consent_reference": f"CONSENT-{month:02d}-{index:03d}",
                    "consent_timestamp": (snapshot - pd.Timedelta(days=1)).isoformat(),
                    "bureau_report_date": (snapshot - pd.Timedelta(days=5)).isoformat(),
                    "bureau_dpd_30_12m": index % 2,
                    "bureau_dpd_90_24m": 0,
                    "open_trades": 2,
                    "total_monthly_obligation_inr": 20_000,
                    "verified_monthly_income_inr": 100_000,
                    "income_verified_at": (snapshot - pd.Timedelta(days=15)).isoformat(),
                    "current_limit_inr": 300_000,
                    "other_credit_limits_inr": 100_000,
                    "current_balance_inr": 100_000,
                    "statement_months": 12,
                    "data_lineage_id": f"LINEAGE-{month:02d}-{index:03d}",
                    "outcome_end_date": (snapshot + pd.Timedelta(days=365)).isoformat(),
                    TARGET: index % 2,
                }
            )
    return pd.DataFrame(rows)


def test_india_account_month_contract_and_forward_split() -> None:
    clean = validate_account_months(_account_months(), minimum_rows=50)
    splits = forward_splits(clean)
    assert splits["train"]["snapshot_month"].max() == "2024-03"
    assert splits["calibration"]["snapshot_month"].unique().tolist() == ["2024-04"]
    assert splits["selection"]["snapshot_month"].unique().tolist() == ["2024-05"]
    assert splits["test"]["snapshot_month"].unique().tolist() == ["2024-06"]
    assert not set(splits["train"]["customer_reference"]) & set(
        splits["test"]["customer_reference"]
    )
    evidence = train_forward_validation(clean)
    assert evidence["champion"] in evidence["selection_metrics"]
    assert evidence["untouched_final_month_metrics"]["roc_auc"] >= 0.5


def test_india_validation_rejects_incomplete_outcome_window() -> None:
    frame = _account_months()
    frame.loc[0, "outcome_end_date"] = frame.loc[0, "as_of_date"]
    with pytest.raises(ValueError, match="at least 365 days"):
        validate_account_months(frame, minimum_rows=50)
