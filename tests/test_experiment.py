from __future__ import annotations

import pytest

from limitiq.experiment import (
    _holm_adjust_p_values,
    analyze_pilot,
    assign_arm,
    required_sample_per_arm,
    synthetic_pilot,
)


def test_holm_step_down_ordering_is_correct() -> None:
    assert _holm_adjust_p_values({"a": 0.01, "b": 0.03, "c": 0.04}) == pytest.approx(
        {"a": 0.03, "b": 0.06, "c": 0.06}
    )
    with pytest.raises(ValueError, match="inside"):
        _holm_adjust_p_values({"invalid": 1.1})


def test_assignment_power_and_analysis_are_reproducible() -> None:
    assert assign_arm("A-1") == assign_arm("A-1")
    assert required_sample_per_arm(0.10, 0.01) > required_sample_per_arm(0.10, 0.02)
    first = analyze_pilot(synthetic_pilot(2_000))
    second = analyze_pilot(synthetic_pilot(2_000))
    first.pop("generated_at")
    second.pop("generated_at")
    assert first == second
    assert set(first["comparisons_to_control"]) == {"increase_10", "increase_20", "increase_30"}
    assert first["analysis_protocol_version"] == "1.2"
    assert set(first["multiplicity_families"]) == {
        "primary_contribution",
        "delinquency_guardrail",
    }
    comparison = first["comparisons_to_control"]["increase_10"]
    assert comparison["itt_family"] == "primary_contribution"
    assert comparison["delinquency_family"] == "delinquency_guardrail"
    assert comparison["itt_holm_adjusted_p_value"] >= comparison["itt_raw_p_value"]
    assert (
        comparison["delinquency_bonferroni_adjusted_p_value"]
        >= comparison["delinquency_raw_harm_p_value"]
    )
    assert len(comparison["itt_raw_95_interval"]) == 2
    assert len(comparison["itt_bonferroni_simultaneous_95_interval"]) == 2
    assert len(comparison["delinquency_raw_95_interval"]) == 2
    assert len(comparison["delinquency_bonferroni_simultaneous_95_interval"]) == 2
    expected_status = (
        "within_bound"
        if comparison["delinquency_familywise_upper_95"] <= first["guardrail"]["harm_bound"]
        else "review_stop"
    )
    assert comparison["guardrail_status"] == expected_status
