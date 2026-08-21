from __future__ import annotations

import os
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
MODEL_DIR = ROOT / "models"
REPORT_DIR = ROOT / "reports"
DOCS_DIR = ROOT / "docs"

SEED = 42
DATASET_URL = (
    "https://archive.ics.uci.edu/static/public/350/default%2Bof%2Bcredit%2Bcard%2Bclients.zip"
)
DATASET_PAGE = "https://archive.ics.uci.edu/dataset/350/default+of+credit+card+clients"
DATASET_DOI = "https://doi.org/10.24432/C55S3H"
DATASET_LICENSE = "CC BY 4.0"

SOURCE_CURRENCY = "TWD"
DISPLAY_CURRENCY = "INR"
TWD_TO_INR = 2.97
USD_TO_INR = 83.0
DEM_TO_INR = 45.0
EUR_TO_INR = 90.0
CURRENCY_RATE_DATE = "2026-07-31"
CURRENCY_RATE_SOURCES = (
    "https://rate.bot.com.tw/cr?Lang=en-US",
    "https://m.rbi.org.in/Scripts/BS_ViewBulletin.aspx?Id=22920",
)
CURRENCY_RATES = {
    "TWD": TWD_TO_INR,
    "USD": USD_TO_INR,
    "DEM": DEM_TO_INR,
    "EUR": EUR_TO_INR,
    "INR": 1.0,
}

# Presentation-only display rates (INR per display unit). These are fixed
# reference rates for converting the canonical INR portfolio at render time and
# are intentionally separate from the modelling-time transform rates above,
# which stay locked to keep versioned model evidence reproducible.
DEFAULT_DISPLAY_CURRENCY = "INR"
DISPLAY_RATES = {
    "INR": 1.0,
    "USD": 1.0 / 95.4,
    "EUR": 1.0 / 110.0,
}
DISPLAY_RATE_DATE = "2026-07-31"
DISPLAY_RATE_SOURCES = CURRENCY_RATE_SOURCES

AUTO_INCREASES_ENABLED = os.getenv("AUTO_INCREASES_ENABLED", "true").strip().lower() in {
    "1",
    "true",
    "yes",
}

DISCLAIMER = (
    "LimitIQ is an educational portfolio demonstration using public and synthetic data. "
    "It is not a production credit-decision system and must not be used to make real "
    "lending decisions."
)


@dataclass(frozen=True)
class PolicyAssumptions:
    """Annualized simulated economics and policy controls; monetary values are INR."""

    lgd: float = 0.65
    ccf: float = 0.75
    interchange_rate: float = 0.018
    apr: float = 0.18
    revolving_rate: float = 0.45
    funding_cost: float = 0.045
    capital_cost: float = 0.025
    servicing_cost: float = 180.0
    response_elasticity: float = 0.35
    max_increase: float = 0.30
    max_account_exposure: float = 3_000_000.0
    portfolio_growth_cap: float = 0.10
    portfolio_loss_growth_cap: float = 0.08
    capital_allocation_rate: float = 0.08
    portfolio_capital_budget: float = 25_000_000.0
    max_higher_risk_increase_share: float = 0.25
    expected_loss_ceiling: float = 0.12
    profitability_hurdle: float = 300.0

    def validate(self) -> None:
        rates = (
            "lgd",
            "ccf",
            "interchange_rate",
            "apr",
            "revolving_rate",
            "funding_cost",
            "capital_cost",
            "response_elasticity",
            "max_increase",
            "portfolio_growth_cap",
            "portfolio_loss_growth_cap",
            "capital_allocation_rate",
            "max_higher_risk_increase_share",
            "expected_loss_ceiling",
        )
        for name in rates:
            value = getattr(self, name)
            if not 0 <= value <= 1:
                raise ValueError(f"{name} must be between 0 and 1")
        if self.max_account_exposure <= 0 or self.portfolio_capital_budget <= 0:
            raise ValueError("exposure and capital budgets must be positive")
        if self.servicing_cost < 0 or self.profitability_hurdle < 0:
            raise ValueError("cost and hurdle values cannot be negative")

    def to_dict(self) -> dict[str, float]:
        return asdict(self)

    @classmethod
    def from_mapping(cls, values: dict[str, Any]) -> PolicyAssumptions:
        allowed = {field.name for field in fields(cls)}
        parsed = {
            key: float(value)
            for key, value in values.items()
            if key in allowed and value not in (None, "")
        }
        result = cls(**parsed)
        result.validate()
        return result
