from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from limitiq.analytics import build_snapshot, check_reconciliation


def test_sql_snapshot_reconciles_with_versioned_simulation() -> None:
    snapshot = build_snapshot()
    check_reconciliation(snapshot)
    assert snapshot["reconciliation"]["accounts"] == 1200
    assert sum(row["accounts"] for row in snapshot["actions"]) == 1200
    assert snapshot["model_track"].startswith("Source-coherent")
    assert len(snapshot["sources"]) == 1
    assert snapshot["sources"][0]["source_dataset"] == "taiwan_credit"


def test_sql_snapshot_rejects_duplicate_and_missing_schema(tmp_path: Path) -> None:
    duplicate = pd.DataFrame(
        [
            {
                "account_id": "LIQ-1",
                "source_dataset": "source",
                "action": "No change",
                "increase_pct": 0,
                "risk_band": "Low",
                "pd": 0.1,
                "utilization": 0.2,
                "current_limit_inr": 100,
                "proposed_limit": 100,
                "current_ead": 20,
                "proposed_ead": 20,
                "current_expected_loss": 1,
                "proposed_expected_loss": 1,
                "incremental_contribution": 0,
            }
        ]
    )
    duplicate = pd.concat([duplicate, duplicate], ignore_index=True)
    path = tmp_path / "duplicate.csv"
    duplicate.to_csv(path, index=False)
    with pytest.raises(ValueError, match="unique"):
        build_snapshot(path)

    path.write_text("account_id\nLIQ-1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="missing columns"):
        build_snapshot(path)


def test_reconciliation_detects_drift(tmp_path: Path) -> None:
    snapshot = build_snapshot()
    simulation = tmp_path / "simulation.json"
    payload = {"summary": dict(snapshot["reconciliation"])}
    payload["summary"]["accounts"] += 1
    simulation.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="accounts"):
        check_reconciliation(snapshot, simulation)
