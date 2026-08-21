from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from limitiq.features import (
    BATCH_COLUMNS,
    DEMOGRAPHIC_COLUMNS,
    EXPOSURE_COLUMNS,
    FEATURE_NAMES,
    MODEL_INPUT_COLUMNS,
    REGION_CATEGORIES,
    TAIWAN_MODEL_INPUT_COLUMNS,
    TARGET,
    FeatureBuilder,
    SchemaError,
    clean_source,
    engineer_features,
    validate_input,
    validate_taiwan_input,
)


def test_global_schema_contract_and_nullable_harmonized_fields(healthy_row: pd.Series) -> None:
    frame = pd.DataFrame([healthy_row])
    frame.loc[0, ["utilization", "income_inr", "credit_age_months"]] = np.nan
    clean = validate_input(frame)
    assert list(clean.columns) == [*MODEL_INPUT_COLUMNS, *EXPOSURE_COLUMNS]
    assert clean.loc[0, "region"] == "asia"
    assert clean.loc[0, ["utilization", "income_inr", "credit_age_months"]].isna().all()


def test_global_batch_identifier_and_schema_are_strict(healthy_row: pd.Series) -> None:
    frame = pd.DataFrame([healthy_row, healthy_row])
    frame.insert(0, "ACCOUNT_ID", ["TEST-001", "TEST-001"])
    with pytest.raises(SchemaError, match="Duplicate"):
        validate_input(frame, require_account_id=True)
    with pytest.raises(SchemaError, match="credit_age_months"):
        validate_input(frame.drop(columns="credit_age_months"), require_account_id=True)
    assert BATCH_COLUMNS == ["ACCOUNT_ID", *MODEL_INPUT_COLUMNS, *EXPOSURE_COLUMNS]


@pytest.mark.parametrize(
    ("column", "value", "message"),
    [
        ("delinquency_count", -1, "delinquency_count"),
        ("utilization", 5.1, "utilization"),
        ("debt_to_income", 1.1, "debt_to_income"),
        ("credit_lines", 501, "credit_lines"),
        ("income_inr", -1, "income_inr"),
        ("credit_age_months", 2_001, "credit_age_months"),
        ("current_limit_inr", 0, "current_limit_inr"),
        ("current_balance_inr", 200_001, "current_balance_inr"),
    ],
)
def test_global_input_range_validation(
    healthy_row: pd.Series, column: str, value: float, message: str
) -> None:
    frame = pd.DataFrame([healthy_row])
    frame.loc[0, column] = value
    with pytest.raises(SchemaError, match=message):
        validate_input(frame)


def test_global_region_numeric_and_exposure_validation(healthy_row: pd.Series) -> None:
    frame = pd.DataFrame([healthy_row])
    frame.loc[0, "region"] = "not-a-region"
    with pytest.raises(SchemaError, match="Unsupported region"):
        validate_input(frame)

    frame = pd.DataFrame([healthy_row])
    frame.loc[0, "current_balance_inr"] = np.nan
    with pytest.raises(SchemaError, match="cannot be blank"):
        validate_input(frame)

    frame = pd.DataFrame([healthy_row])
    frame["utilization"] = frame["utilization"].astype(object)
    frame.loc[0, "utilization"] = "not-a-number"
    with pytest.raises(SchemaError, match="Numeric values required"):
        validate_input(frame)

    frame = pd.DataFrame([healthy_row])
    frame.loc[0, "income_inr"] = np.inf
    with pytest.raises(SchemaError, match="finite"):
        validate_input(frame)

    assert REGION_CATEGORIES == {
        "asia",
        "europe",
        "north_america",
        "taiwan",
        "undisclosed",
    }


def test_legacy_feature_engineering_schema_and_determinism(
    healthy_taiwan_row: pd.Series,
) -> None:
    frame = pd.DataFrame([healthy_taiwan_row, healthy_taiwan_row])
    engineered = engineer_features(frame)
    builder = FeatureBuilder().fit(frame)
    assert list(engineered.columns) == FEATURE_NAMES
    assert engineered.shape == (2, 17)
    assert np.isfinite(engineered.to_numpy()).all()
    assert engineered.loc[0, "current_utilization"] == pytest.approx(0.8)
    assert np.array_equal(builder.transform(frame), builder.transform(frame))
    assert list(builder.get_feature_names_out()) == FEATURE_NAMES


def test_legacy_taiwan_validation_and_zero_bill_are_safe(healthy_taiwan_row: pd.Series) -> None:
    frame = pd.DataFrame([healthy_taiwan_row])
    assert list(validate_taiwan_input(frame).columns) == TAIWAN_MODEL_INPUT_COLUMNS
    with pytest.raises(SchemaError, match="PAY_6"):
        validate_taiwan_input(frame.drop(columns="PAY_6"))
    frame.loc[0, "PAY_0"] = 10
    with pytest.raises(SchemaError, match="between -2 and 9"):
        validate_taiwan_input(frame)

    zero_bill = healthy_taiwan_row.copy()
    for column in [f"BILL_AMT{i}" for i in range(1, 7)]:
        zero_bill[column] = 0
    assert np.isfinite(engineer_features(pd.DataFrame([zero_bill])).to_numpy()).all()


def test_legacy_source_cleaning_rejects_duplicate_and_invalid_rows(
    healthy_taiwan_row: pd.Series,
) -> None:
    frame = pd.DataFrame([healthy_taiwan_row, healthy_taiwan_row, healthy_taiwan_row])
    frame.insert(0, "ID", [1, 1, 3])
    for column in DEMOGRAPHIC_COLUMNS:
        frame[column] = 1
    frame[TARGET] = [0, 0, 2]
    clean, report = clean_source(frame)
    assert len(clean) == 1
    assert report["duplicate_ids"] == 1
    assert report["invalid_target_rows"] == 1


def test_targets_identifiers_and_demographics_cannot_enter_global_model() -> None:
    assert not {TARGET, "default", "ID", "ACCOUNT_ID"} & set(MODEL_INPUT_COLUMNS)
    assert not set(DEMOGRAPHIC_COLUMNS) & set(MODEL_INPUT_COLUMNS)
