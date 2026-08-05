from __future__ import annotations

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

DISCLAIMER = (
    "LimitIQ is an educational portfolio demonstration using public and synthetic data. "
    "It is not a production credit-decision system and must not be used to make real "
    "lending decisions."
)


@dataclass(frozen=True)
class PolicyAssumptions:
    """Annualized simulated economics and policy controls; monetary values are TWD."""

    lgd: float = 0.65
    ccf: float = 0.75
    interchange_rate: float = 0.018
    apr: float = 0.18
    revolving_rate: float = 0.45
    funding_cost: float = 0.045
    capital_cost: float = 0.025
    servicing_cost: float = 60.0
    response_elasticity: float = 0.35
    max_increase: float = 0.30
    max_account_exposure: float = 1_000_000.0
    portfolio_growth_cap: float = 0.10
    expected_loss_ceiling: float = 0.12
    profitability_hurdle: float = 100.0

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
            "expected_loss_ceiling",
        )
        for name in rates:
            value = getattr(self, name)
            if not 0 <= value <= 1:
                raise ValueError(f"{name} must be between 0 and 1")
        if self.max_account_exposure <= 0:
            raise ValueError("max_account_exposure must be positive")
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
