from __future__ import annotations

import json

from limitiq.robustness import REPORT_PATH


def test_model_robustness_report_is_sane_and_does_not_claim_promotion() -> None:
    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    assert report["development_rows"] == 24_000
    assert report["development_preference"] in report["candidates"]
    assert "frozen v4 test was not reread" in report["classification"]
    assert report["promotion_status"].startswith("No promotion")
    assert len(report["support_bounds"]) == 17
    for candidate in report["candidates"].values():
        assert 0.5 < candidate["roc_auc"] <= 1
        assert 0 < candidate["brier_score"] < 0.25
