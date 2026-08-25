from __future__ import annotations

import json

from limitiq.monitoring_ops import REFERENCE_REPORT_PATH, evaluate_snapshot, synthetic_snapshot


def test_monitoring_replay_is_deterministic_and_detects_degradation() -> None:
    reference = json.loads(REFERENCE_REPORT_PATH.read_text(encoding="utf-8"))
    stable = evaluate_snapshot(reference, synthetic_snapshot())
    repeated = evaluate_snapshot(reference, synthetic_snapshot())
    degraded = evaluate_snapshot(reference, synthetic_snapshot(degraded=True))
    stable.pop("generated_at")
    repeated.pop("generated_at")
    stable.pop("report_sha256")
    repeated.pop("report_sha256")
    assert stable == repeated
    assert degraded["status"] == "red"
    assert "rollback" in degraded["required_response"].lower()
    assert stable["segment_metrics"]
