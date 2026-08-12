from __future__ import annotations

import pandas as pd
import pytest

from limitiq.features import (
    BILL_COLUMNS,
    EXPOSURE_COLUMNS,
    MODEL_INPUT_COLUMNS,
    PAY_COLUMNS,
    PAYMENT_COLUMNS,
    TAIWAN_MODEL_INPUT_COLUMNS,
)


@pytest.fixture
def healthy_row() -> pd.Series:
    return pd.Series(
        {
            "delinquency_count": 0.0,
            "utilization": 0.8,
            "debt_to_income": 0.25,
            "credit_lines": 6.0,
            "income_inr": 1_200_000.0,
            "credit_age_months": 120.0,
            "region": "asia",
            "current_limit_inr": 100_000.0,
            "current_balance_inr": 80_000.0,
        },
        index=[*MODEL_INPUT_COLUMNS, *EXPOSURE_COLUMNS],
    )


@pytest.fixture
def healthy_taiwan_row() -> pd.Series:
    values = {column: 0.0 for column in TAIWAN_MODEL_INPUT_COLUMNS}
    values.update(
        {
            "LIMIT_BAL": 100_000.0,
            **dict.fromkeys(PAY_COLUMNS, -1.0),
            **{column: 80_000.0 - index * 2_000 for index, column in enumerate(BILL_COLUMNS)},
            **dict.fromkeys(PAYMENT_COLUMNS, 20_000.0),
        }
    )
    return pd.Series(values)
