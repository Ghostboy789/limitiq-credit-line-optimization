"""Executable model-monitoring replay for scored populations with matured outcomes."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, roc_auc_score

from limitiq.config import REPORT_DIR, SEED


@dataclass(frozen=True)
class MonitoringThresholds:
    psi_amber: float = 0.10
    psi_red: float = 0.25
    brier_delta_amber: float = 0.01
    brier_delta_red: float = 0.02
    calibration_gap_amber: float = 0.03
    calibration_gap_red: float = 0.05
    missing_rate_red: float = 0.01


REQUIRED_COLUMNS = {
    "probability",
    "outcome",
    "delinquency_count",
    "utilization",
    "action",
    "override",
}
REFERENCE_REPORT_PATH = REPORT_DIR / "behavioral_model.json"


def _psi(reference: list[dict[str, Any]], probability: np.ndarray) -> float:
    expected = np.asarray([row["count"] for row in reference], dtype=float)
    expected /= expected.sum()
    edges = np.asarray([reference[0]["lower"], *[row["upper"] for row in reference]])
    actual, _ = np.histogram(probability, bins=edges)
    actual = actual / max(actual.sum(), 1)
    expected = np.clip(expected, 1e-6, None)
    actual = np.clip(actual, 1e-6, None)
    return float(np.sum((actual - expected) * np.log(actual / expected)))


def _calibration_gap(outcome: np.ndarray, probability: np.ndarray) -> float:
    bins = pd.qcut(probability, min(10, len(np.unique(probability))), duplicates="drop")
    grouped = pd.DataFrame({"outcome": outcome, "probability": probability, "bin": bins}).groupby(
        "bin", observed=True
    )
    return float((grouped["outcome"].mean() - grouped["probability"].mean()).abs().mean())


def _segment_metrics(clean: pd.DataFrame) -> list[dict[str, Any]]:
    segments = {
        "Utilization <30%": clean["utilization"] < 0.30,
        "Utilization 30–70%": clean["utilization"].between(0.30, 0.70, inclusive="left"),
        "Utilization ≥70%": clean["utilization"] >= 0.70,
        "No reported delinquency": clean["delinquency_count"] == 0,
        "Reported delinquency": clean["delinquency_count"] > 0,
    }
    rows = []
    for name, mask in segments.items():
        cohort = clean.loc[mask].dropna(subset=["probability", "outcome"])
        if len(cohort) < 2:
            continue
        metrics: dict[str, Any] = {
            "segment": name,
            "rows": len(cohort),
            "event_rate": float(cohort["outcome"].mean()),
            "mean_probability": float(cohort["probability"].mean()),
            "brier_score": float(brier_score_loss(cohort["outcome"], cohort["probability"])),
            "calibration_gap": _calibration_gap(
                cohort["outcome"].to_numpy(dtype=int),
                cohort["probability"].to_numpy(dtype=float),
            ),
        }
        metrics["roc_auc"] = (
            float(roc_auc_score(cohort["outcome"], cohort["probability"]))
            if cohort["outcome"].nunique() == 2
            else None
        )
        rows.append(metrics)
    return rows


def evaluate_snapshot(
    reference: dict[str, Any],
    frame: pd.DataFrame,
    thresholds: MonitoringThresholds | None = None,
) -> dict[str, Any]:
    """Evaluate a scored-and-matured population and return a governed status."""
    thresholds = thresholds or MonitoringThresholds()
    missing = sorted(REQUIRED_COLUMNS - set(frame.columns))
    if missing:
        raise ValueError(f"Monitoring snapshot missing columns: {', '.join(missing)}")
    clean = frame.loc[:, sorted(REQUIRED_COLUMNS)].copy()
    numeric = ["probability", "outcome", "delinquency_count", "utilization", "override"]
    clean[numeric] = clean[numeric].apply(pd.to_numeric, errors="coerce")
    missing_rate = float(clean[numeric].isna().mean().max())
    if clean[["probability", "outcome"]].isna().any().any():
        raise ValueError("Probability and matured outcome cannot be blank")
    if not clean["probability"].between(0, 1).all() or not set(clean["outcome"]) <= {0, 1}:
        raise ValueError("Probability must be in [0,1] and outcome must be binary")
    truth = clean["outcome"].to_numpy(dtype=int)
    probability = clean["probability"].to_numpy(dtype=float)
    if np.unique(truth).size != 2:
        raise ValueError("Both matured outcome classes are required")
    baseline = reference["untouched_test_metrics"]
    psi = _psi(baseline["probability_summary"]["histogram"], probability)
    brier = float(brier_score_loss(truth, probability))
    calibration_gap = _calibration_gap(truth, probability)
    signals = {
        "score_psi": psi,
        "roc_auc": float(roc_auc_score(truth, probability)),
        "brier_score": brier,
        "brier_delta": brier - float(baseline["brier_score"]),
        "calibration_gap": calibration_gap,
        "max_missing_rate": missing_rate,
        "override_rate": float(clean["override"].fillna(0).mean()),
    }
    red = (
        psi >= thresholds.psi_red
        or signals["brier_delta"] >= thresholds.brier_delta_red
        or calibration_gap >= thresholds.calibration_gap_red
        or missing_rate >= thresholds.missing_rate_red
    )
    amber = (
        psi >= thresholds.psi_amber
        or signals["brier_delta"] >= thresholds.brier_delta_amber
        or calibration_gap >= thresholds.calibration_gap_amber
    )
    status = "red" if red else "amber" if amber else "green"
    response = {
        "green": "Continue monitoring",
        "amber": "Investigate before expanding automatic decisions",
        "red": "Disable automatic increases and initiate rollback review",
    }[status]
    payload = {
        "classification": "Monitoring output; demonstration unless sourced from approved outcomes",
        "generated_at": datetime.now(UTC).isoformat(),
        "model_version": reference["model_version"],
        "dataset_version": reference["dataset_version"],
        "rows": int(len(clean)),
        "status": status,
        "required_response": response,
        "signals": signals,
        "action_mix": clean["action"].value_counts().sort_index().to_dict(),
        "segment_metrics": _segment_metrics(clean),
        "thresholds": asdict(thresholds),
    }
    payload["report_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return payload


def synthetic_snapshot(rows: int = 2_000, *, degraded: bool = False) -> pd.DataFrame:
    """Create deterministic monitoring replay data; never presented as production."""
    rng = np.random.default_rng(SEED + (9_000 if degraded else 8_000))
    reference = json.loads(REFERENCE_REPORT_PATH.read_text(encoding="utf-8"))
    histogram = reference["untouched_test_metrics"]["probability_summary"]["histogram"]
    weights = np.asarray([item["count"] for item in histogram], dtype=float)
    selected = rng.choice(len(histogram), rows, p=weights / weights.sum())
    probability = np.asarray(
        [rng.uniform(histogram[index]["lower"], histogram[index]["upper"]) for index in selected]
    )
    if degraded:
        probability = np.clip(probability * 1.7 + 0.08, 0, 1)
    outcome_probability = np.clip(probability + (0.09 if degraded else 0), 0, 1)
    return pd.DataFrame(
        {
            "probability": probability,
            "outcome": rng.binomial(1, outcome_probability),
            "delinquency_count": rng.poisson(0.35, rows),
            "utilization": rng.beta(2.2, 2.8, rows),
            "action": rng.choice(["No change", "Increase 10%", "Manual review"], rows),
            "override": rng.binomial(1, 0.03 if not degraded else 0.12, rows),
        }
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate LimitIQ monitoring snapshots")
    parser.add_argument("--input", type=Path)
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--output", type=Path, default=REPORT_DIR / "monitoring_replay.json")
    args = parser.parse_args()
    if bool(args.input) == bool(args.demo):
        parser.error("Choose exactly one of --input or --demo")
    reference = json.loads(REFERENCE_REPORT_PATH.read_text(encoding="utf-8"))
    if args.demo:
        payload: dict[str, Any] = {
            "classification": "Deterministic synthetic monitoring replay",
            "stable": evaluate_snapshot(reference, synthetic_snapshot()),
            "degraded": evaluate_snapshot(reference, synthetic_snapshot(degraded=True)),
        }
    else:
        payload = evaluate_snapshot(reference, pd.read_csv(args.input))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(payload, indent=2))
    if not args.demo and payload["status"] == "red":
        sys.exit(2)


if __name__ == "__main__":
    main()
