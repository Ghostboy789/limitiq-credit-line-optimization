from __future__ import annotations

import pytest

from limitiq.india import validate_india_contract


def _record() -> dict[str, object]:
    return {
        "customer_reference": "TOKEN-0001",
        "as_of_date": "2026-08-21T10:00:00+05:30",
        "consent_reference": "CONSENT-1",
        "consent_timestamp": "2026-08-20T10:00:00+05:30",
        "bureau_report_date": "2026-08-15T10:00:00+05:30",
        "bureau_dpd_30_12m": 0,
        "bureau_dpd_90_24m": 0,
        "open_trades": 4,
        "total_monthly_obligation_inr": 25_000,
        "verified_monthly_income_inr": 100_000,
        "income_verified_at": "2026-08-01T10:00:00+05:30",
        "current_limit_inr": 300_000,
        "current_balance_inr": 120_000,
        "statement_months": 12,
        "data_lineage_id": "LINEAGE-0001",
    }


def test_india_contract_validates_fresh_consent_lineage_and_affordability() -> None:
    result = validate_india_contract(_record())
    assert result["foir_proxy"] == pytest.approx(0.25)
    assert result["classification"].endswith("no PD or lending decision")
    with pytest.raises(ValueError, match="Direct identifiers"):
        validate_india_contract({**_record(), "pan": "NOT-ALLOWED"})
