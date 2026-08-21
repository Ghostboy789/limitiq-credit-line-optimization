"""Build and reconcile a small in-memory SQL decision mart."""

from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from limitiq.config import PROCESSED_DIR, REPORT_DIR, ROOT

PORTFOLIO_PATH = PROCESSED_DIR / "behavioral_demo_portfolio.csv"
SQL_PATH = ROOT / "analytics" / "portfolio_mart.sql"
SIMULATION_PATH = REPORT_DIR / "behavioral_policy_simulation.json"

REQUIRED_COLUMNS = {
    "account_id",
    "source_dataset",
    "action",
    "increase_pct",
    "risk_band",
    "pd",
    "utilization",
    "current_limit_inr",
    "proposed_limit",
    "current_ead",
    "proposed_ead",
    "current_expected_loss",
    "proposed_expected_loss",
    "incremental_contribution",
}


def _records(connection: sqlite3.Connection, view: str, order_by: str) -> list[dict[str, Any]]:
    queries = {
        ("portfolio_reconciliation", "accounts"): (
            "SELECT * FROM portfolio_reconciliation ORDER BY accounts"
        ),
        ("action_summary", "action"): "SELECT * FROM action_summary ORDER BY action",
        ("source_risk_summary", "source_dataset"): (
            "SELECT * FROM source_risk_summary ORDER BY source_dataset"
        ),
        ("risk_band_summary", "risk_band"): ("SELECT * FROM risk_band_summary ORDER BY risk_band"),
    }
    query = queries.get((view, order_by))
    if query is None:
        raise ValueError("Unknown analytics view or sort")
    cursor = connection.execute(query)
    columns = [item[0] for item in cursor.description]
    return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]


def build_snapshot(
    portfolio_path: Path = PORTFOLIO_PATH, sql_path: Path = SQL_PATH
) -> dict[str, Any]:
    frame = pd.read_csv(portfolio_path)
    missing = sorted(REQUIRED_COLUMNS - set(frame.columns))
    if missing:
        raise ValueError(f"Portfolio is missing columns: {', '.join(missing)}")
    if frame.empty or frame["account_id"].duplicated().any():
        raise ValueError("Portfolio must contain unique synthetic account IDs")
    connection = sqlite3.connect(":memory:")
    try:
        frame.to_sql("decisions", connection, index=False, if_exists="fail")
        connection.executescript(sql_path.read_text(encoding="utf-8"))
        reconciliation = _records(connection, "portfolio_reconciliation", "accounts")[0]
        return {
            "classification": "Deterministic synthetic portfolio SQL reconciliation",
            "model_track": "Source-coherent UCI Taiwan behavioral primary",
            "generated_at": datetime.now(UTC).isoformat(),
            "portfolio_file": portfolio_path.name,
            "sql_file": sql_path.name,
            "reconciliation": reconciliation,
            "actions": _records(connection, "action_summary", "action"),
            "sources": _records(connection, "source_risk_summary", "source_dataset"),
            "risk_bands": _records(connection, "risk_band_summary", "risk_band"),
            "limitations": [
                "All accounts, economics and decisions are deterministic simulations.",
                "This mart is a read-only analytics demonstration, not a retained decision store.",
            ],
        }
    finally:
        connection.close()


def check_reconciliation(snapshot: dict[str, Any], simulation_path: Path = SIMULATION_PATH) -> None:
    expected = json.loads(simulation_path.read_text(encoding="utf-8"))["summary"]
    actual = snapshot["reconciliation"]
    keys = (
        "accounts",
        "current_limit",
        "proposed_limit",
        "current_ead",
        "proposed_ead",
        "current_expected_loss",
        "proposed_expected_loss",
        "incremental_contribution",
        "eligible_increases",
    )
    for key in keys:
        tolerance = 0 if key in {"accounts", "eligible_increases"} else 0.02
        if abs(float(actual[key]) - float(expected[key])) > tolerance:
            raise ValueError(f"SQL reconciliation failed for {key}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    snapshot = build_snapshot()
    if args.check:
        check_reconciliation(snapshot)
    text = json.dumps(snapshot, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)


if __name__ == "__main__":
    main()
