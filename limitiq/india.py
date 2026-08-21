"""India deployment-readiness data contract; deliberately contains no scoring model."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import pandas as pd

INDIA_REQUIRED_FIELDS = (
    "customer_reference",
    "as_of_date",
    "consent_reference",
    "consent_timestamp",
    "bureau_report_date",
    "bureau_dpd_30_12m",
    "bureau_dpd_90_24m",
    "open_trades",
    "total_monthly_obligation_inr",
    "verified_monthly_income_inr",
    "income_verified_at",
    "current_limit_inr",
    "current_balance_inr",
    "statement_months",
    "data_lineage_id",
)
PROHIBITED_DIRECT_IDENTIFIERS = {
    "name",
    "pan",
    "aadhaar",
    "phone",
    "email",
    "address",
}


def validate_india_contract(record: dict[str, Any]) -> dict[str, Any]:
    """Validate readiness inputs and return derived controls without producing a score."""
    missing = [name for name in INDIA_REQUIRED_FIELDS if record.get(name) in (None, "")]
    if missing:
        raise ValueError(f"India readiness record missing: {', '.join(missing)}")
    prohibited = sorted(PROHIBITED_DIRECT_IDENTIFIERS & set(record))
    if prohibited:
        raise ValueError(f"Direct identifiers are prohibited: {', '.join(prohibited)}")
    as_of = pd.Timestamp(record["as_of_date"])
    consent = pd.Timestamp(record["consent_timestamp"])
    bureau = pd.Timestamp(record["bureau_report_date"])
    income_verified = pd.Timestamp(record["income_verified_at"])
    if any(value.tz is None for value in (as_of, consent, bureau, income_verified)):
        raise ValueError("India readiness timestamps must include an explicit timezone")
    if consent > as_of or bureau > as_of or income_verified > as_of:
        raise ValueError("Consent and source evidence cannot post-date the decision timestamp")
    if as_of - bureau > timedelta(days=30):
        raise ValueError("Bureau report is older than the 30-day readiness bound")
    if as_of - income_verified > timedelta(days=90):
        raise ValueError("Verified income is older than the 90-day readiness bound")
    numeric = {
        name: float(record[name])
        for name in (
            "bureau_dpd_30_12m",
            "bureau_dpd_90_24m",
            "open_trades",
            "total_monthly_obligation_inr",
            "verified_monthly_income_inr",
            "current_limit_inr",
            "current_balance_inr",
            "statement_months",
        )
    }
    if any(value < 0 for value in numeric.values()):
        raise ValueError("India readiness numeric fields cannot be negative")
    if numeric["verified_monthly_income_inr"] <= 0 or numeric["current_limit_inr"] <= 0:
        raise ValueError("Verified income and current limit must be positive")
    if numeric["current_balance_inr"] > numeric["current_limit_inr"] * 2:
        raise ValueError("Current balance exceeds the readiness contract bound")
    if numeric["statement_months"] < 6:
        raise ValueError("At least six statement months are required")
    return {
        "classification": "India data-readiness validation only; no PD or lending decision",
        "customer_reference": str(record["customer_reference"]),
        "data_lineage_id": str(record["data_lineage_id"]),
        "consent_reference": str(record["consent_reference"]),
        "foir_proxy": numeric["total_monthly_obligation_inr"]
        / numeric["verified_monthly_income_inr"],
        "utilization": numeric["current_balance_inr"] / numeric["current_limit_inr"],
        "bureau_age_days": (as_of - bureau).days,
        "income_age_days": (as_of - income_verified).days,
        "ready_for_local_model_validation": True,
        "next_gate": "Representative Indian outcomes, legal review and independent validation",
    }
