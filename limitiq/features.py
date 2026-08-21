from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin

TARGET = "default_next_month"
ID_COLUMN = "ID"
PAY_COLUMNS = ["PAY_0", "PAY_2", "PAY_3", "PAY_4", "PAY_5", "PAY_6"]
BILL_COLUMNS = [f"BILL_AMT{i}" for i in range(1, 7)]
PAYMENT_COLUMNS = [f"PAY_AMT{i}" for i in range(1, 7)]
DEMOGRAPHIC_COLUMNS = ["SEX", "EDUCATION", "MARRIAGE", "AGE"]
TAIWAN_MODEL_INPUT_COLUMNS = ["LIMIT_BAL", *PAY_COLUMNS, *BILL_COLUMNS, *PAYMENT_COLUMNS]
TAIWAN_BATCH_COLUMNS = ["ACCOUNT_ID", *TAIWAN_MODEL_INPUT_COLUMNS]
MODEL_INPUT_COLUMNS = [
    "delinquency_count",
    "utilization",
    "debt_to_income",
    "credit_lines",
    "income_inr",
    "credit_age_months",
    "region",
]
EXPOSURE_COLUMNS = ["current_limit_inr", "current_balance_inr"]
BATCH_COLUMNS = ["ACCOUNT_ID", *MODEL_INPUT_COLUMNS, *EXPOSURE_COLUMNS]
REGION_CATEGORIES = {"asia", "europe", "north_america", "taiwan", "undisclosed"}
FEATURE_NAMES = [
    "limit_bal",
    "current_utilization",
    "average_utilization",
    "maximum_utilization",
    "utilization_trend",
    "recent_payment_ratio",
    "average_payment_ratio",
    "payment_consistency",
    "delinquent_month_count",
    "maximum_delinquency_severity",
    "recent_payment_deterioration",
    "revolving_balance_proxy",
    "limit_headroom",
    "balance_volatility",
    "payment_volatility",
    "recent_balance_growth",
    "inactive_month_count",
]


class SchemaError(ValueError):
    pass


def _missing(columns: Iterable[str], frame: pd.DataFrame) -> list[str]:
    return sorted(set(columns) - set(frame.columns))


def validate_input(frame: pd.DataFrame, *, require_account_id: bool = False) -> pd.DataFrame:
    """Validate the harmonized model and simulated-exposure application contract."""
    required = BATCH_COLUMNS if require_account_id else [*MODEL_INPUT_COLUMNS, *EXPOSURE_COLUMNS]
    missing = _missing(required, frame)
    if missing:
        raise SchemaError(f"Missing required columns: {', '.join(missing)}")
    clean = frame.loc[:, required].copy()
    if require_account_id:
        clean["ACCOUNT_ID"] = clean["ACCOUNT_ID"].astype(str).str.strip()
        if clean["ACCOUNT_ID"].eq("").any():
            raise SchemaError("ACCOUNT_ID cannot be blank")
        if clean["ACCOUNT_ID"].duplicated().any():
            duplicates = clean.loc[clean["ACCOUNT_ID"].duplicated(), "ACCOUNT_ID"].head(3)
            raise SchemaError(f"Duplicate ACCOUNT_ID values: {', '.join(duplicates)}")
    numeric = [*MODEL_INPUT_COLUMNS[:-1], *EXPOSURE_COLUMNS]
    converted = clean[numeric].apply(pd.to_numeric, errors="coerce")
    invalid = converted.isna() & clean[numeric].notna()
    if invalid.any().any():
        raise SchemaError(
            f"Numeric values required when supplied in: {', '.join(invalid.columns[invalid.any()])}"
        )
    clean[numeric] = converted
    finite = np.isfinite(clean[numeric].fillna(0).to_numpy())
    if not finite.all():
        raise SchemaError("Numeric values must be finite")
    clean["region"] = clean["region"].astype(str).str.strip().str.lower()
    invalid_regions = sorted(set(clean["region"]) - REGION_CATEGORIES)
    if invalid_regions:
        raise SchemaError(f"Unsupported region: {', '.join(invalid_regions)}")
    required_numeric = clean[EXPOSURE_COLUMNS]
    if required_numeric.isna().any().any():
        raise SchemaError("current_limit_inr and current_balance_inr cannot be blank")
    if (clean["current_limit_inr"] <= 0).any() or (clean["current_limit_inr"] > 10_000_000).any():
        raise SchemaError("current_limit_inr must be greater than zero and at most 10,000,000")
    if (clean["current_balance_inr"] < 0).any() or (
        clean["current_balance_inr"] > clean["current_limit_inr"] * 2
    ).any():
        raise SchemaError("current_balance_inr must be between zero and twice the current limit")
    bounds = {
        "delinquency_count": (0, 100),
        "utilization": (0, 5),
        "debt_to_income": (0, 1),
        "credit_lines": (0, 500),
        "income_inr": (0, 1_000_000_000),
        "credit_age_months": (0, 2_000),
    }
    for column, (lower, upper) in bounds.items():
        present = clean[column].dropna()
        if ((present < lower) | (present > upper)).any():
            raise SchemaError(f"{column} must be between {lower} and {upper} when supplied")
    return clean


def validate_taiwan_input(frame: pd.DataFrame, *, require_account_id: bool = False) -> pd.DataFrame:
    """Validate the legacy UCI 350 schema used only by the reproducible v1 pipeline."""
    required = TAIWAN_BATCH_COLUMNS if require_account_id else TAIWAN_MODEL_INPUT_COLUMNS
    missing = _missing(required, frame)
    if missing:
        raise SchemaError(f"Missing required columns: {', '.join(missing)}")
    clean = frame.loc[:, required].copy()
    if require_account_id:
        clean["ACCOUNT_ID"] = clean["ACCOUNT_ID"].astype(str).str.strip()
        if clean["ACCOUNT_ID"].eq("").any() or clean["ACCOUNT_ID"].duplicated().any():
            raise SchemaError("ACCOUNT_ID values must be non-blank and unique")
    converted = clean[TAIWAN_MODEL_INPUT_COLUMNS].apply(pd.to_numeric, errors="coerce")
    if converted.isna().any().any() or not np.isfinite(converted.to_numpy()).all():
        raise SchemaError("Legacy Taiwan model inputs must be finite numeric values with no blanks")
    clean[TAIWAN_MODEL_INPUT_COLUMNS] = converted.astype(float)
    if (clean["LIMIT_BAL"] <= 0).any():
        raise SchemaError("LIMIT_BAL must be greater than zero")
    if ((clean[PAY_COLUMNS] < -2) | (clean[PAY_COLUMNS] > 9)).any().any():
        raise SchemaError("Repayment status must be between -2 and 9")
    if (clean[PAYMENT_COLUMNS] < 0).any().any():
        raise SchemaError("Payment amounts cannot be negative")
    return clean


def clean_source(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, object]]:
    rename = {
        "default payment next month": TARGET,
        "default.payment.next.month": TARGET,
        "Y": TARGET,
    }
    clean = frame.rename(columns=rename).copy()
    required = [ID_COLUMN, *TAIWAN_MODEL_INPUT_COLUMNS, *DEMOGRAPHIC_COLUMNS, TARGET]
    missing = _missing(required, clean)
    if missing:
        raise SchemaError(f"Source dataset is missing: {', '.join(missing)}")
    before = len(clean)
    duplicate_ids = int(clean[ID_COLUMN].duplicated().sum())
    exact_duplicates = int(clean.duplicated().sum())
    clean = clean.drop_duplicates(subset=[ID_COLUMN], keep="first")
    numeric_columns = required
    clean[numeric_columns] = clean[numeric_columns].apply(pd.to_numeric, errors="coerce")
    missing_cells = int(clean[numeric_columns].isna().sum().sum())
    invalid_limit = int((clean["LIMIT_BAL"] <= 0).sum())
    invalid_target = int((~clean[TARGET].isin([0, 1])).sum())
    invalid_payment_status = int(
        ((clean[PAY_COLUMNS] < -2) | (clean[PAY_COLUMNS] > 9)).any(axis=1).sum()
    )
    invalid_payment_amount = int((clean[PAYMENT_COLUMNS] < 0).any(axis=1).sum())
    invalid_mask = (
        clean[numeric_columns].isna().any(axis=1)
        | (clean["LIMIT_BAL"] <= 0)
        | (~clean[TARGET].isin([0, 1]))
        | ((clean[PAY_COLUMNS] < -2) | (clean[PAY_COLUMNS] > 9)).any(axis=1)
        | (clean[PAYMENT_COLUMNS] < 0).any(axis=1)
    )
    clean = clean.loc[~invalid_mask].reset_index(drop=True)
    report = {
        "source_rows": before,
        "clean_rows": len(clean),
        "removed_rows": before - len(clean),
        "duplicate_ids": duplicate_ids,
        "exact_duplicates": exact_duplicates,
        "missing_cells": missing_cells,
        "invalid_limit_rows": invalid_limit,
        "invalid_target_rows": invalid_target,
        "invalid_payment_status_rows": invalid_payment_status,
        "invalid_payment_amount_rows": invalid_payment_amount,
        "target_rate": float(clean[TARGET].mean()),
        "observed_fields": required,
    }
    return clean, report


def engineer_features(frame: pd.DataFrame) -> pd.DataFrame:
    clean = validate_taiwan_input(frame)
    limit = clean["LIMIT_BAL"].clip(lower=1)
    bills = clean[BILL_COLUMNS].clip(lower=0)
    payments = clean[PAYMENT_COLUMNS].clip(lower=0)
    pay_status = clean[PAY_COLUMNS]
    utilization = bills.div(limit, axis=0)
    payment_ratios = payments.to_numpy() / np.maximum(bills.to_numpy(), 1)
    result = pd.DataFrame(index=clean.index)
    result["limit_bal"] = limit
    result["current_utilization"] = utilization["BILL_AMT1"]
    result["average_utilization"] = utilization.mean(axis=1)
    result["maximum_utilization"] = utilization.max(axis=1)
    result["utilization_trend"] = utilization["BILL_AMT1"] - utilization["BILL_AMT6"]
    result["recent_payment_ratio"] = payment_ratios[:, 0]
    result["average_payment_ratio"] = np.mean(payment_ratios, axis=1)
    result["payment_consistency"] = (payments > 0).mean(axis=1)
    result["delinquent_month_count"] = (pay_status > 0).sum(axis=1)
    result["maximum_delinquency_severity"] = pay_status.clip(lower=0).max(axis=1)
    result["recent_payment_deterioration"] = pay_status["PAY_0"] - pay_status.iloc[:, 1:].mean(
        axis=1
    )
    result["revolving_balance_proxy"] = (bills["BILL_AMT1"] - payments["PAY_AMT1"]).clip(
        lower=0
    ) / limit
    result["limit_headroom"] = (limit - bills["BILL_AMT1"]).clip(lower=0) / limit
    result["balance_volatility"] = bills.std(axis=1).fillna(0) / limit
    result["payment_volatility"] = payments.std(axis=1).fillna(0) / limit
    result["recent_balance_growth"] = (bills["BILL_AMT1"] - bills["BILL_AMT3"]) / limit
    result["inactive_month_count"] = (bills == 0).sum(axis=1)
    return result.replace([np.inf, -np.inf], 0).fillna(0).clip(-20, 20)


class FeatureBuilder(BaseEstimator, TransformerMixin):
    """Sklearn-compatible behavior transformer used identically in train and inference."""

    def fit(self, X: pd.DataFrame, y: object = None) -> FeatureBuilder:  # noqa: N803
        validate_taiwan_input(X)
        return self

    def transform(self, X: pd.DataFrame) -> np.ndarray:  # noqa: N803
        return engineer_features(X).to_numpy(dtype=float)

    def get_feature_names_out(self, input_features: object = None) -> np.ndarray:
        return np.asarray(FEATURE_NAMES, dtype=object)
