"""Executable randomized-pilot design and deterministic analysis demonstration."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import UTC, datetime
from pathlib import Path
from statistics import NormalDist
from typing import Any

import numpy as np
import pandas as pd

from limitiq.config import REPORT_DIR, SEED

ARMS = ("control", "increase_10", "increase_20", "increase_30")


def required_sample_per_arm(
    baseline_rate: float,
    minimum_detectable_effect: float,
    *,
    power: float = 0.80,
    alpha: float = 0.05,
) -> int:
    """Normal-approximation sample size for an absolute two-proportion effect."""
    treatment_rate = baseline_rate + minimum_detectable_effect
    if not 0 < baseline_rate < 1 or not 0 < treatment_rate < 1:
        raise ValueError("Baseline plus minimum detectable effect must remain inside (0,1)")
    if not 0 < power < 1 or not 0 < alpha < 1:
        raise ValueError("Power and alpha must be inside (0,1)")
    normal = NormalDist()
    z_alpha = normal.inv_cdf(1 - alpha / 2)
    z_power = normal.inv_cdf(power)
    pooled = (baseline_rate + treatment_rate) / 2
    numerator = (
        z_alpha * math.sqrt(2 * pooled * (1 - pooled))
        + z_power
        * math.sqrt(baseline_rate * (1 - baseline_rate) + treatment_rate * (1 - treatment_rate))
    ) ** 2
    return math.ceil(numerator / minimum_detectable_effect**2)


def assign_arm(account_id: str, seed: int = SEED) -> str:
    digest = hashlib.sha256(f"{seed}:{account_id}".encode()).digest()
    return ARMS[int.from_bytes(digest[:8], "big") % len(ARMS)]


def synthetic_pilot(rows: int = 20_000) -> pd.DataFrame:
    """Generate a deterministic fake trial used only to verify analysis code."""
    rng = np.random.default_rng(SEED + 10_000)
    account_id = [f"TRIAL-{index + 1:07d}" for index in range(rows)]
    arm = np.asarray([assign_arm(value) for value in account_id])
    increase = (
        pd.Series(arm)
        .map({"control": 0.0, "increase_10": 0.10, "increase_20": 0.20, "increase_30": 0.30})
        .to_numpy()
    )
    baseline_spend = rng.lognormal(math.log(25_000), 0.55, rows)
    risk = rng.beta(2.0, 8.0, rows)
    contribution = 0.10 * baseline_spend + increase * baseline_spend * 0.18 - risk * 2_500
    contribution += rng.normal(0, 1_400, rows)
    delinquency = rng.binomial(1, np.clip(risk + increase * 0.025, 0, 1))
    accepted = rng.binomial(1, np.clip(0.15 + increase * 0.8, 0, 1))
    return pd.DataFrame(
        {
            "account_id": account_id,
            "arm": arm,
            "baseline_spend": baseline_spend,
            "contribution": contribution,
            "delinquency": delinquency,
            "accepted": accepted,
        }
    )


def _difference_interval(
    treatment: pd.Series, control: pd.Series
) -> tuple[float, float, float, float]:
    delta = float(treatment.mean() - control.mean())
    standard_error = math.sqrt(
        float(treatment.var(ddof=1)) / len(treatment) + float(control.var(ddof=1)) / len(control)
    )
    return delta, standard_error, delta - 1.96 * standard_error, delta + 1.96 * standard_error


def analyze_pilot(
    frame: pd.DataFrame,
    *,
    classification: str = "Deterministic synthetic experiment-analysis demonstration",
    delinquency_harm_bound: float = 0.01,
) -> dict[str, Any]:
    """Return ITT and CUPED results; treatment assignment is never conditioned on acceptance."""
    required = {"account_id", "arm", "baseline_spend", "contribution", "delinquency", "accepted"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"Pilot data missing columns: {', '.join(missing)}")
    if set(frame["arm"]) - set(ARMS):
        raise ValueError("Pilot arm is outside the frozen four-arm design")
    if frame["account_id"].duplicated().any():
        raise ValueError("Pilot account IDs must be unique")
    if set(ARMS) - set(frame["arm"]):
        raise ValueError("Pilot data must contain every frozen arm, including control")
    if (frame["arm"].value_counts() < 2).any():
        raise ValueError("Pilot data must contain at least two observations per arm")
    numeric_columns = ["baseline_spend", "contribution", "delinquency", "accepted"]
    numeric = frame[numeric_columns].apply(pd.to_numeric, errors="coerce")
    if not np.isfinite(numeric.to_numpy()).all():
        raise ValueError("Pilot numeric outcomes must be finite")
    if (numeric["baseline_spend"] < 0).any():
        raise ValueError("Pilot baseline spend cannot be negative")
    if not set(numeric["delinquency"].unique()).issubset({0, 1}) or not set(
        numeric["accepted"].unique()
    ).issubset({0, 1}):
        raise ValueError("Pilot delinquency and acceptance must contain only 0 and 1")
    if not 0 <= delinquency_harm_bound < 1:
        raise ValueError("Delinquency harm bound must be inside [0,1)")
    frame = frame.copy()
    frame[numeric_columns] = numeric
    variance = float(frame["baseline_spend"].var(ddof=0))
    theta = (
        float(frame[["contribution", "baseline_spend"]].cov(ddof=0).iloc[0, 1]) / variance
        if variance
        else 0.0
    )
    adjusted = frame["contribution"] - theta * (
        frame["baseline_spend"] - frame["baseline_spend"].mean()
    )
    analysis = frame.assign(cuped_contribution=adjusted)
    grouped = analysis.groupby("arm", observed=True)
    summaries = {
        arm: {
            "rows": int(len(group)),
            "mean_contribution": float(group["contribution"].mean()),
            "cuped_mean_contribution": float(group["cuped_contribution"].mean()),
            "delinquency_rate": float(group["delinquency"].mean()),
            "acceptance_rate": float(group["accepted"].mean()),
        }
        for arm, group in grouped
    }
    comparisons = {}
    control_rows = analysis[analysis["arm"] == "control"]
    for arm in ARMS[1:]:
        treatment_rows = analysis[analysis["arm"] == arm]
        itt = _difference_interval(treatment_rows["contribution"], control_rows["contribution"])
        cuped = _difference_interval(
            treatment_rows["cuped_contribution"], control_rows["cuped_contribution"]
        )
        delinquency = _difference_interval(
            treatment_rows["delinquency"], control_rows["delinquency"]
        )
        comparisons[arm] = {
            "itt_contribution_delta": itt[0],
            "itt_standard_error": itt[1],
            "itt_95_interval": [itt[2], itt[3]],
            "cuped_contribution_delta": cuped[0],
            "cuped_standard_error": cuped[1],
            "cuped_95_interval": [cuped[2], cuped[3]],
            "delinquency_delta": delinquency[0],
            "delinquency_standard_error": delinquency[1],
            "delinquency_95_interval": [delinquency[2], delinquency[3]],
            "guardrail_status": (
                "review_stop" if delinquency[3] > delinquency_harm_bound else "within_bound"
            ),
        }
    return {
        "classification": classification,
        "analysis_protocol_version": "1.1",
        "generated_at": datetime.now(UTC).isoformat(),
        "estimand": "Intent-to-treat effect by assigned credit-line arm",
        "arms": summaries,
        "comparisons_to_control": comparisons,
        "cuped_theta": theta,
        "guardrail": {
            "metric": "Upper 95% interval for delinquency risk difference",
            "harm_bound": delinquency_harm_bound,
            "rule": "Route the arm to stop review when the upper interval exceeds the bound",
        },
        "limitations": [
            "Synthetic outcomes prove analysis plumbing only and are not causal business evidence.",
            "A real pilot requires consent, eligibility, harm monitoring and independent approval.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the LimitIQ randomized-pilot analysis")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--input", type=Path, help="Observed randomized-pilot CSV")
    source.add_argument("--rows", type=int, help="Rows in the synthetic plumbing replay")
    parser.add_argument("--output", type=Path, default=REPORT_DIR / "experiment_replay.json")
    parser.add_argument("--delinquency-harm-bound", type=float, default=0.01)
    args = parser.parse_args()
    if args.input:
        frame = pd.read_csv(args.input)
        classification = "Observed randomized-pilot analysis supplied by operator"
    else:
        frame = synthetic_pilot(args.rows or 20_000)
        classification = "Deterministic synthetic experiment-analysis demonstration"
    payload = analyze_pilot(
        frame,
        classification=classification,
        delinquency_harm_bound=args.delinquency_harm_bound,
    )
    if args.input:
        payload["input_sha256"] = hashlib.sha256(args.input.read_bytes()).hexdigest()
    payload["power_example"] = {
        "baseline_rate": 0.10,
        "absolute_mde": 0.01,
        "power": 0.80,
        "alpha": 0.05,
        "required_rows_per_arm": required_sample_per_arm(0.10, 0.01),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
