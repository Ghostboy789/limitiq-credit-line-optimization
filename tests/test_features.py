from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from limitiq.features import (
    DEMOGRAPHIC_COLUMNS,
    FEATURE_NAMES,
    MODEL_INPUT_COLUMNS,
    TARGET,
    FeatureBuilder,
    SchemaError,
    clean_source,
    engineer_features,
    validate_input,
)


def test_feature_engineering_schema_and_finite_values(healthy_row: pd.Series) -> None:
    engineered = engineer_features(pd.DataFrame([healthy_row]))
    assert list(engineered.columns) == FEATURE_NAMES
    assert engineered.shape == (1, 17)
    assert np.isfinite(engineered.to_numpy()).all()
    assert engineered.loc[0, "current_utilization"] == pytest.approx(0.8)
    assert engineered.loc[0, "payment_consistency"] == 1


def test_unified_transformer_is_deterministic(healthy_row: pd.Series) -> None:
    frame = pd.DataFrame([healthy_row, healthy_row])
    builder = FeatureBuilder().fit(frame)
    assert np.array_equal(builder.transform(frame), builder.transform(frame))
    assert list(builder.get_feature_names_out()) == FEATURE_NAMES


def test_missing_batch_column_is_specific(healthy_row: pd.Series) -> None:
    frame = pd.DataFrame([healthy_row]).drop(columns=["PAY_6"])
    with pytest.raises(SchemaError, match="PAY_6"):
        validate_input(frame)


@pytest.mark.parametrize(
    ("column", "value", "message"),
    [
        ("LIMIT_BAL", 0, "greater than zero"),
        ("PAY_0", 10, "between -2 and 9"),
        ("PAY_AMT1", -1, "cannot be negative"),
    ],
)
def test_input_range_validation(
    healthy_row: pd.Series, column: str, value: float, message: str
) -> None:
    frame = pd.DataFrame([healthy_row])
    frame.loc[0, column] = value
    with pytest.raises(SchemaError, match=message):
        validate_input(frame)


def test_account_id_duplicate_rejected(healthy_row: pd.Series) -> None:
    frame = pd.DataFrame([healthy_row, healthy_row])
    frame.insert(0, "ACCOUNT_ID", ["TEST-001", "TEST-001"])
    with pytest.raises(SchemaError, match="Duplicate"):
        validate_input(frame, require_account_id=True)


def test_source_cleaning_rejects_duplicate_and_invalid_rows(healthy_row: pd.Series) -> None:
    frame = pd.DataFrame([healthy_row, healthy_row, healthy_row])
    frame.insert(0, "ID", [1, 1, 3])
    for column in DEMOGRAPHIC_COLUMNS:
        frame[column] = 1
    frame[TARGET] = [0, 0, 2]
    clean, report = clean_source(frame)
    assert len(clean) == 1
    assert report["duplicate_ids"] == 1
    assert report["invalid_target_rows"] == 1


def test_target_and_demographics_cannot_enter_model_input() -> None:
    assert TARGET not in MODEL_INPUT_COLUMNS
    assert not set(DEMOGRAPHIC_COLUMNS) & set(MODEL_INPUT_COLUMNS)
    assert "ID" not in MODEL_INPUT_COLUMNS


def test_zero_bill_has_safe_payment_ratio(healthy_row: pd.Series) -> None:
    row = healthy_row.copy()
    for column in [f"BILL_AMT{i}" for i in range(1, 7)]:
        row[column] = 0
    result = engineer_features(pd.DataFrame([row]))
    assert np.isfinite(result.to_numpy()).all()
