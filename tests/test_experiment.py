from __future__ import annotations

from limitiq.experiment import analyze_pilot, assign_arm, required_sample_per_arm, synthetic_pilot


def test_assignment_power_and_analysis_are_reproducible() -> None:
    assert assign_arm("A-1") == assign_arm("A-1")
    assert required_sample_per_arm(0.10, 0.01) > required_sample_per_arm(0.10, 0.02)
    first = analyze_pilot(synthetic_pilot(2_000))
    second = analyze_pilot(synthetic_pilot(2_000))
    first.pop("generated_at")
    second.pop("generated_at")
    assert first == second
    assert set(first["comparisons_to_control"]) == {"increase_10", "increase_20", "increase_30"}
