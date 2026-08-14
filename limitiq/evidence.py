"""Additive diagnostic evidence for the deployed multi-source benchmark.

Two studies, both purely additive: they fit diagnostic models on the same
harmonized union and write new evidence files under ``reports/`` without
touching the deployed model or metadata artifacts.

1. Out-of-time vintage evidence (Lending Club only — the single cohort with
   disclosed issue dates). The same calibrated histogram-gradient-boosting
   recipe as the deployed champion is fitted on earlier vintages and scored on
   later vintages, with per-vintage-year results, to expose time decay that a
   random within-source split cannot show.
2. Source-leakage ablation. The champion recipe is fitted three ways — with
   the one-hot region context feature, without it, and on region alone — to
   quantify how much of the benchmark discrimination comes from region
   base-rate and structural-missingness learning rather than harmonized
   feature signal.

No claim of causality or production generalization is made; both studies share
the evidence boundary documented in README.md.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score, roc_curve
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from limitiq.config import MODEL_DIR, RAW_DIR, REPORT_DIR, SEED
from limitiq.external import _sha256, _write_json
from limitiq.multisource import (
    CONTEXT_FEATURES,
    HARMONIZED_FEATURES,
    MODEL_FEATURES,
    TARGET,
    _harmonize_lending_club,
    _union_frame,
)
from limitiq.pipeline import _metrics, _threshold
from limitiq.reporting import _table, _write_html

OUTPUT_DIR = REPORT_DIR
OOT_SOURCE = "lending_club_full"
LC_GOOD_STATUS = "Fully Paid"
LC_BAD_STATUSES = (
    "Charged Off",
    "Default",
    "Late (16-30 days)",
    "Late (31-120 days)",
)


def _variant(use_region: bool, use_features: bool) -> Pipeline:
    transformers: list[tuple[str, object, object]] = []
    if use_features:
        transformers.append(("numeric", "passthrough", HARMONIZED_FEATURES))
    if use_region:
        transformers.append(
            (
                "region",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                CONTEXT_FEATURES,
            )
        )
    return Pipeline(
        [
            ("preprocess", ColumnTransformer(transformers, verbose_feature_names_out=False)),
            (
                "model",
                HistGradientBoostingClassifier(
                    learning_rate=0.06,
                    max_iter=180,
                    max_leaf_nodes=15,
                    l2_regularization=1.0,
                    random_state=SEED,
                ),
            ),
        ]
    )


def _calibrated(use_region: bool = True, use_features: bool = True) -> CalibratedClassifierCV:
    """Calibrated wrapper around a recipe variant, as used in multisource.py."""
    return CalibratedClassifierCV(_variant(use_region, use_features), method="sigmoid", cv=3)


def _lc_issue_dates() -> pd.DataFrame:
    """Issue dates for the rows kept by the Lending Club harmonizer, index-aligned."""
    out = RAW_DIR / "lending_club_full.csv"
    frame = pd.read_csv(out, usecols=["issue_d", "loan_status"], low_memory=False)
    kept = frame["loan_status"].eq(LC_GOOD_STATUS) | frame["loan_status"].isin(LC_BAD_STATUSES)
    dates = pd.to_datetime(frame.loc[kept, "issue_d"], format="%b-%Y", errors="coerce")
    return pd.DataFrame({"issue_date": dates}, index=frame.loc[kept].index)


def _vintage_split(
    dates: np.ndarray, boundaries: tuple[float, float, float] = (0.60, 0.80, 1.0)
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Deterministic vintage-quantile split; rows are ordered by issue date."""
    train_cutoff = np.quantile(dates, boundaries[0])
    validation_cutoff = np.quantile(dates, boundaries[1])
    train = dates <= train_cutoff
    validation = (dates > train_cutoff) & (dates <= validation_cutoff)
    test = dates > validation_cutoff
    return train, validation, test


def oot_evidence() -> dict[str, Any]:
    """Fit the champion recipe on early Lending Club vintages; score later ones.

    The model is fitted once; the vintage-quantile boundaries then select the
    in-time validation window and the strictly out-of-time test window. The
    loss-weighted threshold rule is applied on the in-time window exactly as in
    the published recipe, with the out-of-time window scored untouched.
    """
    harmonized, name = _harmonize_lending_club()
    if name != OOT_SOURCE:
        raise RuntimeError(f"Unexpected harmonizer identity: {name}")
    frame = harmonized.copy()
    issue = _lc_issue_dates()
    frame["issue_date"] = issue["issue_date"]
    undated = int(frame["issue_date"].isna().sum())
    frame = frame.dropna(subset=["issue_date"])
    dates = frame["issue_date"].to_numpy()
    train, validation, test = _vintage_split(dates)
    train_x, train_y = frame.loc[train, MODEL_FEATURES], frame.loc[train, TARGET]
    validation_x, validation_y = (
        frame.loc[validation, MODEL_FEATURES],
        frame.loc[validation, TARGET],
    )
    test_x, test_y = frame.loc[test, MODEL_FEATURES], frame.loc[test, TARGET]
    test_dates = frame.loc[test, "issue_date"]

    model = _calibrated()
    model.fit(train_x, train_y)
    in_time_probability = model.predict_proba(validation_x)[:, 1]
    in_time_threshold = _threshold(validation_y, in_time_probability)
    test_probability = model.predict_proba(test_x)[:, 1]
    in_time = _metrics(validation_y, in_time_probability, in_time_threshold)
    out_of_time = _metrics(test_y, test_probability, in_time_threshold)

    by_vintage: list[dict[str, Any]] = []
    for year, group in test_y.to_frame().groupby(test_dates.dt.year):
        mask = (test_dates.dt.year == year).to_numpy()
        metrics = _metrics(
            test_y.iloc[np.flatnonzero(mask)], test_probability[mask], in_time_threshold
        )
        by_vintage.append(
            {
                "vintage_year": int(year),
                "accounts": int(group[TARGET].count()),
                "risk_rate": float(group[TARGET].mean()),
                **metrics,
            }
        )

    reference = json.loads((MODEL_DIR / "global_metadata.json").read_text(encoding="utf-8"))
    random_split = reference["per_market_test_metrics"][OOT_SOURCE]
    payload = {
        "classification": "Vintage-split status-at-extract evidence for Lending Club only",
        "method": (
            "Calibrated histogram gradient boosting (champion recipe) fitted on the earliest "
            "60% of issues by date, threshold selected loss-weighted (5x FN) on the next "
            "20%, and scored on the most recent 20%. Loan status is observed at extract, "
            "so vintages have unequal seasoning and this is not a fixed-horizon PD backtest."
        ),
        "source": OOT_SOURCE,
        "undated_rows_dropped": undated,
        "cutoffs": {
            "in_time_validation_start": str(frame.loc[validation, "issue_date"].min().date()),
            "out_of_time_test_start": str(frame.loc[test, "issue_date"].min().date()),
        },
        "counts": {
            "train": int(train.sum()),
            "validation": int(validation.sum()),
            "test": int(test.sum()),
        },
        "in_time_holdout": in_time,
        "out_of_time": out_of_time,
        "by_vintage_year": by_vintage,
        "random_split_reference": {
            "roc_auc": random_split["roc_auc"],
            "pr_auc": random_split["pr_auc"],
            "brier_score": random_split["brier_score"],
            "log_loss": random_split["log_loss"],
        },
        "provenance": {
            "generated_at": datetime.now(UTC).isoformat(),
            "random_seed": SEED,
            "raw_file_sha256": _sha256(RAW_DIR / "lending_club_full.csv"),
            "diagnostic_recipe": "sigmoid-calibrated-histogram-gradient-boosting-cv3",
        },
        "evidence_boundary": (
            "Lending Club is the only training cohort with disclosed issue dates, so this "
            "evidence is single-source. Other cohorts have no published origination or behavior "
            "period and cannot support a temporal claim. Status-at-extract labels have unequal "
            "follow-up and censoring, so this is a vintage robustness diagnostic, not fixed-"
            "horizon out-of-time PD validation or unseen-country generalization."
        ),
    }
    return payload


def _seeded_split(union: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """The published stratified 60/20/20 split with the same seed as build_global."""
    strata = union["market"].astype(str) + "|" + union[TARGET].astype(str)
    train_index, holdout_index = train_test_split(
        union.index, test_size=0.4, stratify=strata, random_state=SEED
    )
    validation_index, test_index = train_test_split(
        holdout_index,
        test_size=0.5,
        stratify=strata.loc[holdout_index],
        random_state=SEED,
    )
    return (
        union.loc[train_index],
        union.loc[validation_index],
        union.loc[test_index],
    )


def _macros(source_metrics: list[dict[str, Any]]) -> dict[str, float]:
    return {
        "macro_roc_auc": float(np.mean([item["roc_auc"] for item in source_metrics])),
        "macro_brier_score": float(np.mean([item["brier_score"] for item in source_metrics])),
    }


def leakage_ablation(union: pd.DataFrame | None = None) -> dict[str, Any]:
    """Discrimination from region context versus harmonized feature signal.

    The champion recipe is fitted on the published 60% training split with the
    region one-hot, without it, and on region alone; each variant is scored on
    the untouched 20% test split. The full-region variant doubles as a
    reproducibility check against the published validation-model evidence.
    """
    if union is None:
        union, _ = _union_frame()
    train_frame, validation_frame, test_frame = _seeded_split(union)
    train_x, train_y = train_frame[MODEL_FEATURES], train_frame[TARGET]
    validation_x, validation_y = validation_frame[MODEL_FEATURES], validation_frame[TARGET]
    test_x, test_y = test_frame[MODEL_FEATURES], test_frame[TARGET]
    markets = sorted(union["market"].unique())

    variants: dict[str, dict[str, Any]] = {}
    for label, use_region, use_features in (
        ("region_included", True, True),
        ("features_only", False, True),
        ("region_only", True, False),
    ):
        model = _calibrated(use_region, use_features)
        model.fit(train_x, train_y)
        validation_probability = model.predict_proba(validation_x)[:, 1]
        validation_threshold = _threshold(validation_y, validation_probability)
        test_probability = model.predict_proba(test_x)[:, 1]
        per_source_test: dict[str, Any] = {}
        for key in markets:
            mask = (test_frame["market"] == key).to_numpy()
            metrics = _metrics(
                test_y.iloc[np.flatnonzero(mask)], test_probability[mask], validation_threshold
            )
            metrics["accounts"] = int(mask.sum())
            metrics["risk_rate"] = float(test_y.iloc[np.flatnonzero(mask)].mean())
            per_source_test[key] = metrics
        source_validation = [
            _metrics(
                validation_y.iloc[np.flatnonzero(validation_frame["market"] == key)],
                validation_probability[(validation_frame["market"] == key).to_numpy()],
                validation_threshold,
            )
            for key in markets
        ]
        variants[label] = {
            "test_metrics": _metrics(test_y, test_probability, validation_threshold),
            "macro_test_metrics": _macros([per_source_test[key] for key in markets]),
            "per_source_test": per_source_test,
            "validation_macro_roc_auc": float(
                np.mean([item["roc_auc"] for item in source_validation])
            ),
            "validation_macro_brier": float(
                np.mean([item["brier_score"] for item in source_validation])
            ),
        }

    reference = json.loads((MODEL_DIR / "global_metadata.json").read_text(encoding="utf-8"))
    published = reference["validation_models"]["Histogram gradient boosting"]
    payload = {
        "classification": "Source-context ablation: explicit region contribution",
        "method": (
            "Same calibrated histogram-gradient-boosting recipe and published 60/20/20 split. "
            "'region_included' reproduces the champion pipeline; 'features_only' drops the "
            "one-hot region context; 'region_only' learns from region alone. Structural "
            "missingness remains available to both feature-bearing variants, so this analysis "
            "does not isolate or rule out source identification through missingness."
        ),
        "variants": variants,
        "published_validation_reference": {
            "macro_roc_auc": published["macro_roc_auc"],
            "macro_brier_score": published["macro_brier_score"],
        },
        "provenance": {
            "generated_at": datetime.now(UTC).isoformat(),
            "random_seed": SEED,
            "model_checksum": reference["model_checksum"],
            "dataset_version": reference["dataset_version"],
        },
        "interpretation": (
            "The gap between region_included and features_only measures only the incremental "
            "value of explicit region after the harmonized values and their missingness patterns "
            "are already present. The region_only row measures pooled separation from coarse "
            "regional base rates and has no within-source discrimination. Pooled figures are "
            "dominated by Lending Club; macro figures weight each cohort equally."
        ),
    }
    return payload


def _oot_report(payload: dict[str, Any]) -> None:
    in_time, out_of_time = payload["in_time_holdout"], payload["out_of_time"]
    vintage_rows = [
        [
            str(item["vintage_year"]),
            f"{item['accounts']:,}",
            f"{item['risk_rate']:.1%}",
            f"{item['roc_auc']:.4f}",
            f"{item['pr_auc']:.4f}",
            f"{item['brier_score']:.4f}",
            f"{item['log_loss']:.4f}",
        ]
        for item in payload["by_vintage_year"]
    ]
    reference = payload["random_split_reference"]
    sections = [
        (
            "Out-of-time vintage evidence",
            f'<div class="notice"><strong>Method.</strong> {payload["method"]} '
            f"Cutoff at {payload['cutoffs']['out_of_time_test_start']}; "
            f"{payload['counts']['train']:,} train / {payload['counts']['validation']:,} "
            f"in-time validation / {payload['counts']['test']:,} out-of-time test rows.</div>",
        ),
        (
            "In-time versus out-of-time",
            _table(
                [
                    "Window",
                    "ROC-AUC",
                    "PR-AUC",
                    "Brier",
                    "Log-loss",
                    "Threshold",
                ],
                [
                    [
                        "In-time holdout (vintages through "
                        + payload["cutoffs"]["out_of_time_test_start"]
                        + ")",
                        f"{in_time['roc_auc']:.4f}",
                        f"{in_time['pr_auc']:.4f}",
                        f"{in_time['brier_score']:.4f}",
                        f"{in_time['log_loss']:.4f}",
                        f"{in_time['threshold']:.4f}",
                    ],
                    [
                        "Out-of-time (newest 20% of vintages)",
                        f"{out_of_time['roc_auc']:.4f}",
                        f"{out_of_time['pr_auc']:.4f}",
                        f"{out_of_time['brier_score']:.4f}",
                        f"{out_of_time['log_loss']:.4f}",
                        f"{out_of_time['threshold']:.4f}",
                    ],
                ],
            )
            + "<p>The out-of-time window is scored with the in-time threshold only.</p>",
        ),
        (
            "Out-of-time test by vintage year",
            _table(
                ["Vintage year", "N", "Risk rate", "ROC-AUC", "PR-AUC", "Brier", "Log-loss"],
                vintage_rows,
            ),
        ),
        (
            "Random-split reference",
            _table(
                [
                    "Metric",
                    "Random within-source split (published per-source value)",
                    "Out-of-time",
                ],
                [
                    ["ROC-AUC", f"{reference['roc_auc']:.4f}", f"{out_of_time['roc_auc']:.4f}"],
                    ["PR-AUC", f"{reference['pr_auc']:.4f}", f"{out_of_time['pr_auc']:.4f}"],
                    [
                        "Brier",
                        f"{reference['brier_score']:.4f}",
                        f"{out_of_time['brier_score']:.4f}",
                    ],
                    ["Log-loss", f"{reference['log_loss']:.4f}", f"{out_of_time['log_loss']:.4f}"],
                ],
            )
            + "<p>Same cohort and recipe; the only difference is how test rows are chosen.</p>",
        ),
        (
            "Interpretation",
            f"<p>{payload['evidence_boundary']}</p>",
        ),
    ]
    _write_html(
        OUTPUT_DIR,
        "global_oot_report.html",
        "Vintage-split status-at-extract evidence · LimitIQ",
        "Vintage robustness evidence · LimitIQ",
        sections,
    )


def _leakage_report(payload: dict[str, Any]) -> None:
    variants = payload["variants"]
    variant_rows = [
        [
            label.replace("_", " ").title(),
            f"{variants[label]['macro_test_metrics']['macro_roc_auc']:.4f}",
            f"{variants[label]['macro_test_metrics']['macro_brier_score']:.4f}",
            f"{variants[label]['test_metrics']['roc_auc']:.4f}",
            f"{variants[label]['test_metrics']['brier_score']:.4f}",
        ]
        for label in ("region_included", "features_only", "region_only")
    ]
    markets = sorted(next(iter(variants.values()))["per_source_test"])
    names = {
        key: item["name"]
        for key, item in json.loads(
            (MODEL_DIR / "global_metadata.json").read_text(encoding="utf-8")
        )["datasets"].items()
    }
    per_source_rows = [
        [
            names.get(key, key),
            f"{variants['region_included']['per_source_test'][key]['roc_auc']:.4f}",
            f"{variants['features_only']['per_source_test'][key]['roc_auc']:.4f}",
            f"{variants['region_only']['per_source_test'][key]['roc_auc']:.4f}",
        ]
        for key in markets
    ]
    published = payload["published_validation_reference"]
    sections = [
        (
            "Source-context ablation",
            f'<div class="notice"><strong>Method.</strong> {payload["method"]} '
            f"Published validation reference: macro ROC-AUC {published['macro_roc_auc']:.4f}, "
            f"macro Brier {published['macro_brier_score']:.4f}.</div>",
        ),
        (
            "Untouched-test comparison",
            _table(
                [
                    "Variant",
                    "Macro ROC-AUC",
                    "Macro Brier",
                    "Pooled ROC-AUC",
                    "Pooled Brier",
                ],
                variant_rows,
            )
            + f"<p>{payload['interpretation']}</p>",
        ),
        (
            "Per-source ROC-AUC by variant",
            _table(
                ["Source", "Region included", "Features only", "Region only"],
                per_source_rows,
            ),
        ),
    ]
    _write_html(
        OUTPUT_DIR,
        "global_leakage_report.html",
        "Source-leakage ablation · LimitIQ",
        "Leakage ablation · LimitIQ",
        sections,
    )


def _champion() -> tuple[object, dict[str, Any]]:
    """Load the deployed champion after verifying its recorded checksum."""
    metadata = json.loads((MODEL_DIR / "global_metadata.json").read_text(encoding="utf-8"))
    model_path = MODEL_DIR / "global_champion.joblib"
    if _sha256(model_path) != metadata["model_checksum"]:
        raise RuntimeError("Global model checksum does not match metadata")
    return joblib.load(model_path), metadata  # noqa: S301 — checksum-verified artifact.


def _permutation_importance(
    model: object,
    x_frame: pd.DataFrame,
    y: pd.Series,
    base_auc: float,
    features: list[str],
    source: pd.Series,
    repeats: int = 5,
) -> list[dict[str, Any]]:
    """Source-preserving ROC-AUC drop when each field is shuffled."""
    rng = np.random.default_rng(SEED)
    source_keys = sorted(source.unique())
    base_probability = model.predict_proba(x_frame)[:, 1]
    base_source_auc = {
        key: roc_auc_score(y[source.eq(key)], base_probability[source.eq(key).to_numpy()])
        for key in source_keys
    }
    rows: list[dict[str, Any]] = []
    for feature in features:
        pooled_drops: list[float] = []
        macro_drops: list[float] = []
        for _ in range(repeats):
            permuted = x_frame.copy()
            for key in source_keys:
                mask = source.eq(key)
                permuted.loc[mask, feature] = rng.permutation(
                    permuted.loc[mask, feature].to_numpy()
                )
            probability = model.predict_proba(permuted)[:, 1]
            pooled_drops.append(base_auc - roc_auc_score(y, probability))
            macro_drops.append(
                float(
                    np.mean(
                        [
                            base_source_auc[key]
                            - roc_auc_score(
                                y[source.eq(key)], probability[source.eq(key).to_numpy()]
                            )
                            for key in source_keys
                        ]
                    )
                )
            )
        rows.append(
            {
                "feature": feature,
                "mean_roc_auc_drop": float(np.mean(macro_drops)),
                "std_roc_auc_drop": float(np.std(macro_drops)),
                "pooled_mean_roc_auc_drop": float(np.mean(pooled_drops)),
            }
        )
    return sorted(rows, key=lambda item: -item["mean_roc_auc_drop"])


def _partial_dependence(
    model: object,
    x_frame: pd.DataFrame,
    source: pd.Series,
    feature: str,
    points: int = 16,
    sample_per_source: int = 5_000,
) -> dict[str, Any]:
    """Equal-source effect curve using only cohorts where the field is observed."""
    quantiles = np.linspace(0.01, 0.99, points)
    cohorts: list[tuple[str, pd.DataFrame]] = []
    for key in sorted(source.unique()):
        observed = x_frame.loc[source.eq(key) & x_frame[feature].notna()]
        if len(observed) >= 100:
            cohorts.append(
                (key, observed.sample(min(len(observed), sample_per_source), random_state=SEED))
            )
    if not cohorts:
        return {
            "feature": feature,
            "points": [],
            "sources": [],
            "min_value": None,
            "max_value": None,
        }
    observed_values = pd.concat([frame[feature] for _, frame in cohorts])
    rows: list[dict[str, float]] = []
    for quantile in quantiles:
        scores: list[float] = []
        values: list[float] = []
        for _, cohort in cohorts:
            value = float(cohort[feature].quantile(quantile))
            shifted = cohort.copy()
            shifted[feature] = value
            scores.append(float(model.predict_proba(shifted)[:, 1].mean()))
            values.append(value)
        rows.append(
            {
                "x": float(quantile),
                "value": float(np.mean(values)),
                "y": float(np.mean(scores)),
            }
        )
    return {
        "feature": feature,
        "points": rows,
        "sources": [key for key, _ in cohorts],
        "min_value": float(observed_values.min()),
        "max_value": float(observed_values.max()),
    }


def _lift_table(y: pd.Series, probability: np.ndarray) -> list[dict[str, Any]]:
    """Score-decile table: risk rate, mean score, default share captured, lift."""
    order = np.argsort(-probability)
    ordered_y = y.to_numpy()[order]
    ordered_p = probability[order]
    total = max(int(y.sum()), 1)
    base_rate = total / len(y)
    rows: list[dict[str, Any]] = []
    for decile in range(10):
        lower, upper = decile * len(y) // 10, (decile + 1) * len(y) // 10
        events = int(ordered_y[lower:upper].sum())
        rows.append(
            {
                "decile": decile + 1,
                "accounts": int(upper - lower),
                "risk_rate": float(ordered_y[lower:upper].mean()),
                "mean_pd": float(ordered_p[lower:upper].mean()),
                "default_share": events / total,
                "lift": (events / max(upper - lower, 1)) / base_rate if base_rate else 0.0,
            }
        )
    return rows


def _discriminatory_power(y: pd.Series, probability: np.ndarray) -> dict[str, Any]:
    """Gini, Kolmogorov-Smirnov, Lorenz curve and decile lift on one population."""
    fpr, tpr, _ = roc_curve(y, probability)
    auc = float(roc_auc_score(y, probability))
    order = np.argsort(-probability)
    population = np.arange(1, len(order) + 1) / len(order)
    cumulative = np.cumsum(y.to_numpy()[order]) / max(int(y.sum()), 1)
    sampled = np.linspace(0, len(order) - 1, 250, dtype=int)
    return {
        "roc_auc": auc,
        "gini": 2 * auc - 1,
        "ks": float(np.max(tpr - fpr)),
        "lorenz": {
            "x": [float(value) for value in population[sampled]],
            "y": [float(value) for value in cumulative[sampled]],
        },
        "lift": _lift_table(y, probability),
    }


def feature_evidence(union: pd.DataFrame | None = None) -> dict[str, Any]:
    """Feature drivers and banking-standard discriminatory power on untouched test rows.

    The deployed champion is evaluated on the published test split;
    source-preserving permutation importance, sampled source-conditioned effect curves, Gini,
    Kolmogorov-Smirnov, a Lorenz curve and a decile lift table are measured on
    those rows. Diagnosis only - no model bytes are changed.
    """
    model, metadata = _champion()
    if union is None:
        union, _ = _union_frame()
    _, _, test_frame = _seeded_split(union)
    test_x, test_y = test_frame[MODEL_FEATURES], test_frame[TARGET]  # noqa: N806
    probability = model.predict_proba(test_x)[:, 1]
    importance_frame = pd.concat(
        [
            group.sample(min(len(group), 20_000), random_state=SEED)
            for _, group in test_frame.groupby("market", sort=True)
        ]
    )
    importance_x = importance_frame[MODEL_FEATURES]
    importance_y = importance_frame[TARGET]
    importance_probability = model.predict_proba(importance_x)[:, 1]
    per_source: list[dict[str, Any]] = []
    for key in sorted(union["market"].unique()):
        mask = (test_frame["market"] == key).to_numpy()
        source_y = test_y.iloc[np.flatnonzero(mask)]
        source_p = probability[mask]
        stats = _discriminatory_power(source_y, source_p)
        per_source.append(
            {
                "source": key,
                "accounts": int(mask.sum()),
                "risk_rate": float(source_y.mean()),
                "mean_score": float(source_p.mean()),
                "roc_auc": stats["roc_auc"],
                "gini": stats["gini"],
                "ks": stats["ks"],
                "calibration_gap": metadata["per_market_test_metrics"][key][
                    "mean_absolute_calibration_gap"
                ],
            }
        )
    return {
        "classification": "Feature-level and discriminatory-power diagnostics on the pooled test",
        "model_version": metadata["model_version"],
        "provenance": {
            "generated_at": datetime.now(UTC).isoformat(),
            "random_seed": SEED,
            "model_checksum": metadata["model_checksum"],
            "dataset_version": metadata["dataset_version"],
        },
        "test_rows": int(len(test_y)),
        "importance_rows": int(len(importance_frame)),
        "permutation_importance": _permutation_importance(
            model,
            importance_x,
            importance_y,
            float(roc_auc_score(importance_y, importance_probability)),
            MODEL_FEATURES,
            importance_frame["market"],
        ),
        "partial_dependence": [
            _partial_dependence(model, test_x, test_frame["market"], feature)
            for feature in HARMONIZED_FEATURES
        ],
        "discriminatory_power": _discriminatory_power(test_y, probability),
        "per_source": per_source,
        "missingness": [
            {
                "source": key,
                **{
                    column: float(
                        test_frame.loc[test_frame["market"].eq(key), column].isna().mean()
                    )
                    for column in HARMONIZED_FEATURES
                },
            }
            for key in sorted(test_frame["market"].unique())
        ],
    }


MONITORING_THRESHOLDS = {
    "score_psi_warning": 0.10,
    "score_psi_action": 0.25,
    "calibration_gap_warning": 0.05,
    "risk_rate_relative_shift_warning": 0.20,
    "missingness_relative_shift_warning": 0.20,
    "source_mix_share_shift_warning": 0.05,
}

MONITORING_PROTOCOL = [
    "Compare each scored population against this baseline score distribution monthly; a population-stability PSI at or above 0.10 warns and 0.25 requires model review.",
    "Track per-source mean score and risk rate; a relative shift beyond 20% against this snapshot triggers investigation before any automated use.",
    "Recompute calibration bins monthly; a mean absolute gap beyond 0.05 or monotone drift across three consecutive bins requires a recalibration assessment.",
    "Monitor per-source feature missingness; a relative change beyond 20% signals a schema or data-provider change and re-opens source equivalency.",
    "Track source-mix shares; a shift beyond 5 percentage points changes the pooled population and requires re-reading macro versus pooled evidence.",
    "On material deterioration, disable automatic increases and retain no-change, freeze and manual-review routing until the model is re-validated (rollback control).",
]


def _monitoring_baseline(feature_payload: dict[str, Any]) -> dict[str, Any]:
    """Assemble the monitoring-readiness baseline from metadata and test-scored rows."""
    metadata = json.loads((MODEL_DIR / "global_metadata.json").read_text(encoding="utf-8"))
    test_metrics = metadata["test_metrics"]
    return {
        "classification": (
            "Monitoring readiness baseline; LimitIQ is a research application and runs "
            "no live production scoring feed, shadow mode or monitoring job"
        ),
        "model_version": metadata["model_version"],
        "dataset_version": metadata["dataset_version"],
        "generated_at": datetime.now(UTC).isoformat(),
        "snapshot": {
            "test_rows": feature_payload["test_rows"],
            "sources": len(feature_payload["per_source"]),
            "pooled_roc_auc": test_metrics["roc_auc"],
            "macro_roc_auc": metadata["macro_test_metrics"]["roc_auc"],
            "pooled_calibration_gap": test_metrics["mean_absolute_calibration_gap"],
            "macro_calibration_gap": metadata["macro_test_metrics"][
                "mean_absolute_calibration_gap"
            ],
        },
        "source_mix": [
            {
                "source": item["source"],
                "accounts": item["accounts"],
                "risk_rate": item["risk_rate"],
                "mean_score": item["mean_score"],
            }
            for item in feature_payload["per_source"]
        ],
        "missingness": feature_payload["missingness"],
        "score_distribution": test_metrics["probability_summary"]["histogram"],
        "risk_bands": test_metrics["probability_summary"]["risk_bands"],
        "per_source_signals": feature_payload["per_source"],
        "thresholds": MONITORING_THRESHOLDS,
        "protocol": MONITORING_PROTOCOL,
        "evidence_boundary": (
            "Baseline snapshot from the seeded test split. Thresholds are illustrative "
            "governance proposals, not validated limits or live alerts; no production "
            "monitoring exists in this educational application. Relative-change checks "
            "must use an absolute-delta fallback when the baseline is zero."
        ),
    }


def _feature_report(payload: dict[str, Any]) -> None:
    power = payload["discriminatory_power"]
    importance_rows = [
        [
            item["feature"].replace("_", " ").title(),
            f"{item['mean_roc_auc_drop']:.4f}",
            f"± {item['std_roc_auc_drop']:.4f}",
        ]
        for item in payload["permutation_importance"]
    ]
    lift_rows = [
        [
            str(item["decile"]),
            f"{item['accounts']:,}",
            f"{item['risk_rate']:.2%}",
            f"{item['mean_pd']:.2%}",
            f"{item['default_share']:.2%}",
            f"{item['lift']:.2f}",
        ]
        for item in power["lift"]
    ]
    source_rows = [
        [
            item["source"],
            f"{item['accounts']:,}",
            f"{item['risk_rate']:.1%}",
            f"{item['mean_score']:.1%}",
            f"{item['roc_auc']:.4f}",
            f"{item['gini']:.4f}",
            f"{item['ks']:.4f}",
            f"{item['calibration_gap']:.4f}",
        ]
        for item in payload["per_source"]
    ]
    sections = [
        (
            "Feature and discriminatory-power evidence",
            f'<div class="notice"><strong>Method.</strong> {payload["classification"]}. '
            f"The deployed champion is evaluated on {payload['test_rows']:,} test rows; "
            "diagnostic perturbations do not change model bytes.</div>",
        ),
        (
            "Permutation importance",
            _table(
                ["Feature", "Mean ROC-AUC drop", "Standard deviation"],
                importance_rows,
            )
            + f"<p>Mean source-macro ROC-AUC drop on a deterministic, source-capped "
            f"{payload['importance_rows']:,}-row sample when the field is shuffled within each "
            "source cohort. This preserves cohort-specific missingness and avoids impossible "
            "cross-source permutations.</p>",
        ),
        (
            "Banking-standard discriminatory power",
            _table(
                ["Metric", "Value"],
                [
                    ["Gini coefficient (2 × ROC-AUC − 1)", f"{power['gini']:.4f}"],
                    ["Kolmogorov-Smirnov statistic", f"{power['ks']:.4f}"],
                    ["ROC-AUC", f"{power['roc_auc']:.4f}"],
                ],
            ),
        ),
        (
            "Decile lift table (highest-scored decile first)",
            _table(
                [
                    "Decile",
                    "Accounts",
                    "Risk rate",
                    "Mean score",
                    "Adverse-event share captured",
                    "Lift vs base rate",
                ],
                lift_rows,
            ),
        ),
        (
            "Per-source Gini and KS",
            _table(
                [
                    "Source",
                    "Test rows",
                    "Risk rate",
                    "Mean score",
                    "ROC-AUC",
                    "Gini",
                    "KS",
                    "Calibration gap",
                ],
                source_rows,
            ),
        ),
        (
            "Interpretation",
            "<p>Permutation importance ranks how much each harmonized field and the "
            "region context move within-source discrimination; sampled source-conditioned "
            "effect curves on the web governance page show fitted direction. Small-cohort metrics are "
            "descriptive and uncertain, not league tables.</p>",
        ),
    ]
    _write_html(
        OUTPUT_DIR,
        "global_feature_report.html",
        "Feature and discriminatory-power evidence · LimitIQ",
        "Feature evidence · LimitIQ",
        sections,
    )


def _monitoring_report(payload: dict[str, Any]) -> None:
    snapshot = payload["snapshot"]
    source_rows = [
        [
            item["source"],
            f"{item['accounts']:,}",
            f"{item['risk_rate']:.1%}",
            f"{item['mean_score']:.1%}",
            f"{item['calibration_gap']:.4f}",
            f"{item['gini']:.4f}",
        ]
        for item in payload["per_source_signals"]
    ]
    threshold_rows = [
        [name.replace("_", " ").title(), f"{value:g}"]
        for name, value in payload["thresholds"].items()
    ]
    protocol_rows = [[str(index), text] for index, text in enumerate(payload["protocol"], 1)]
    sections = [
        (
            "Monitoring readiness baseline",
            f'<div class="notice"><strong>Scope.</strong> {payload["classification"]}. '
            "The values below are a baseline snapshot from the test split.</div>"
            + _table(
                [
                    "Baseline signal",
                    "Value",
                ],
                [
                    ["Test rows", f"{snapshot['test_rows']:,}"],
                    ["Sources", str(snapshot["sources"])],
                    ["Pooled ROC-AUC", f"{snapshot['pooled_roc_auc']:.4f}"],
                    ["Macro ROC-AUC", f"{snapshot['macro_roc_auc']:.4f}"],
                    ["Pooled calibration gap", f"{snapshot['pooled_calibration_gap']:.4f}"],
                    ["Macro calibration gap", f"{snapshot['macro_calibration_gap']:.4f}"],
                ],
            ),
        ),
        (
            "Per-source signals",
            _table(
                [
                    "Source",
                    "Baseline rows",
                    "Risk rate",
                    "Mean score",
                    "Calibration gap",
                    "Gini",
                ],
                source_rows,
            ),
        ),
        (
            "Illustrative investigation thresholds",
            _table(["Signal", "Threshold"], threshold_rows),
        ),
        (
            "Response protocol",
            _table(["#", "Action"], protocol_rows),
        ),
        (
            "Boundary",
            f"<p>{payload['evidence_boundary']}</p>",
        ),
    ]
    _write_html(
        OUTPUT_DIR,
        "global_monitoring_report.html",
        "Monitoring readiness baseline · LimitIQ",
        "Monitoring baseline · LimitIQ",
        sections,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="LimitIQ additive out-of-time and source-leakage diagnostic evidence"
    )
    parser.add_argument("--oot-only", action="store_true", help="Run only the out-of-time study")
    parser.add_argument(
        "--leakage-only", action="store_true", help="Run only the source-leakage ablation study"
    )
    parser.add_argument(
        "--feature-only", action="store_true", help="Run only the feature and monitoring study"
    )
    args = parser.parse_args()
    run_oot = args.oot_only or not (args.leakage_only or args.feature_only)
    run_leakage = args.leakage_only or not (args.oot_only or args.feature_only)
    run_feature = args.feature_only or not (args.oot_only or args.leakage_only)
    union = None
    if run_leakage or run_feature:
        union, _ = _union_frame()
    if run_oot:
        payload = oot_evidence()
        _write_json(OUTPUT_DIR / "global_oot_evidence.json", payload)
        _oot_report(payload)
        print("out-of-time ROC-AUC:", payload["out_of_time"]["roc_auc"])
    if run_leakage:
        payload = leakage_ablation(union)
        _write_json(OUTPUT_DIR / "global_leakage_ablation.json", payload)
        _leakage_report(payload)
        for label in ("region_included", "features_only", "region_only"):
            print(
                label,
                payload["variants"][label]["macro_test_metrics"]["macro_roc_auc"],
            )
    if run_feature:
        payload = feature_evidence(union)
        _write_json(OUTPUT_DIR / "global_feature_evidence.json", payload)
        _feature_report(payload)
        print("Gini:", payload["discriminatory_power"]["gini"])
        print("KS:", payload["discriminatory_power"]["ks"])
        for item in payload["permutation_importance"]:
            print(item["feature"], round(item["mean_roc_auc_drop"], 4))
        monitoring = _monitoring_baseline(payload)
        _write_json(OUTPUT_DIR / "global_monitoring_baseline.json", monitoring)
        _monitoring_report(monitoring)
        print("monitoring baseline rows:", monitoring["snapshot"]["test_rows"])
    return None


if __name__ == "__main__":
    sys.exit(main())
