from __future__ import annotations

import pandas as pd
import pytest

from limitiq.features import BILL_COLUMNS, MODEL_INPUT_COLUMNS, PAY_COLUMNS, PAYMENT_COLUMNS


@pytest.fixture
def healthy_row() -> pd.Series:
    values = {column: 0.0 for column in MODEL_INPUT_COLUMNS}
    values.update(
        {
            "LIMIT_BAL": 100_000.0,
            **dict.fromkeys(PAY_COLUMNS, -1.0),
            **{column: 80_000.0 - index * 2_000 for index, column in enumerate(BILL_COLUMNS)},
            **dict.fromkeys(PAYMENT_COLUMNS, 20_000.0),
        }
    )
    return pd.Series(values)
