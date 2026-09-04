from __future__ import annotations

import joblib
import numpy as np
import pandas as pd
import pytest

from limitiq.behavioral import BEHAVIORAL_DEMO_PATH, CANDIDATE_MODEL_PATH
from limitiq.explain import explain_account
from limitiq.features import TAIWAN_MODEL_INPUT_COLUMNS
from limitiq.review import ReviewLedger


def test_behavioral_explanation_has_distinct_model_sensitivities() -> None:
    model = joblib.load(CANDIDATE_MODEL_PATH)
    source = pd.read_csv(BEHAVIORAL_DEMO_PATH, usecols=TAIWAN_MODEL_INPUT_COLUMNS, nrows=1)
    result = explain_account(model, source)
    assert result["classification"].startswith("Local model sensitivity")
    assert len(result["sensitivities"]) == 4
    assert all(0 <= row["neutralized_score"] <= 1 for row in result["sensitivities"])


def test_behavioral_explanation_labels_immaterial_changes_as_neutral() -> None:
    class NearNeutralModel:
        calls = 0

        def predict_proba(self, frame: pd.DataFrame) -> np.ndarray:
            self.calls += 1
            probability = 0.5 if self.calls == 1 else 0.504
            return np.array([[1 - probability, probability]])

    source = pd.read_csv(BEHAVIORAL_DEMO_PATH, usecols=TAIWAN_MODEL_INPUT_COLUMNS, nrows=1)
    result = explain_account(NearNeutralModel(), source)
    assert all(row["direction"] == "no material effect" for row in result["sensitivities"])


def test_review_ledger_enforces_maker_checker_and_hash_chain() -> None:
    ledger = ReviewLedger()
    submitted = ledger.submit(
        "LIQ-000001", "Analyst One", "Hold current limit", "Affordability concern"
    )
    with pytest.raises(ValueError, match="different"):
        ledger.approve(submitted.review_id, "analyst one")
    approved = ledger.approve(submitted.review_id, "Checker Two")
    assert approved.previous_hash == submitted.event_hash
    assert [row["event"] for row in ledger.events(submitted.review_id)] == [
        "submitted",
        "approved",
    ]
