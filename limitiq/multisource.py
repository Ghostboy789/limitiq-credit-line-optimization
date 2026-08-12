"""Multi-source adverse-credit-outcome benchmark on public credit datasets.

The source labels have different events and horizons, so the pooled score is not
a common-horizon probability of default. Six independent source cohorts are
harmonized onto a deliberately small feature set and evaluated both separately
and as a row-weighted pool. A seventh, legacy German representation is retained
for provenance but excluded because it duplicates the South German population.

Harmonized feature set (per account):

* ``delinquency_count`` — recent late-payment / derogatory events.
* ``utilization`` — balance-to-limit ratio (0-1+).
* ``debt_to_income`` — instalment / debt load relative to income (0-1).
* ``credit_lines`` — number of open credit lines or existing credits.
* ``income_inr`` — reported annual income converted to INR.
* ``credit_age_months`` — age of the oldest credit line in months.

``region`` is one-hot encoded as a coarse context feature. Missingness can also
identify a source cohort, so results demonstrate only within-source
interpolation—not unseen-country or out-of-time generalization.

The modelling recipe (seeded stratified 60/20/20 split, regularized logistic
baseline and calibrated histogram gradient boosting, sigmoid calibration and the
loss-weighted threshold rule) follows the existing project pipeline. Every
source cohort is evaluated with the same pooled model on untouched test rows.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_curve
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from limitiq.config import (
    CURRENCY_RATES,
    MODEL_DIR,
    PROCESSED_DIR,
    RAW_DIR,
    REPORT_DIR,
    SEED,
    USD_TO_INR,
    PolicyAssumptions,
)
from limitiq.external import _fetch_uci_zip, _sha256, _write_json
from limitiq.pipeline import _metrics, _threshold
from limitiq.reporting import _table, _write_html

OUTPUT_DIR = REPORT_DIR

HARMONIZED_FEATURES = [
    "delinquency_count",
    "utilization",
    "debt_to_income",
    "credit_lines",
    "income_inr",
    "credit_age_months",
]
CONTEXT_FEATURES = ["region"]
MODEL_FEATURES = [*HARMONIZED_FEATURES, *CONTEXT_FEATURES]
TARGET = "default"

REGIONS = ("asia", "europe", "north_america", "undisclosed")
_INSTALLMENT_RATE = {1: 0.35, 2: 0.30, 3: 0.225, 4: 0.125}
_MAX_HF_BYTES = 2 * 1024 * 1024 * 1024


def _read_arff(path: Path) -> pd.DataFrame:
    """Minimal ARFF reader; returns string-valued cells, '?' becomes NaN."""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    names: list[str] = []
    rows: list[list[str]] = []
    in_data = False
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("%"):
            continue
        lower = stripped.lower()
        if lower.startswith("@attribute"):
            names.append(stripped.split()[1])
        elif lower.startswith("@data"):
            in_data = True
        elif in_data:
            rows.append([part.strip() for part in stripped.split(",")])
    frame = pd.DataFrame(rows, columns=names)
    frame = frame.replace("?", np.nan)
    return frame


def _numeric(frame: pd.DataFrame, columns: list[str]) -> None:
    for column in columns:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")


def _fetch_openml(file_id: int, out: Path) -> str:
    """Download an OpenML dataset file, or reuse a cached copy."""
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        return _sha256(out)
    url = f"https://api.openml.org/data/download/{file_id}/dataset"
    source = urlparse(url)
    if source.scheme != "https" or source.hostname != "api.openml.org":
        raise ValueError(f"OpenML source must be the approved HTTPS host: {url}")
    request = urllib.request.Request(  # noqa: S310 — constant approved source.
        url, headers={"User-Agent": "Mozilla/5.0 LimitIQ/1.0"}
    )
    with urllib.request.urlopen(request, timeout=120) as response:  # nosec B310  # noqa: S310
        payload = response.read(40 * 1024 * 1024 + 1)
    if len(payload) > 40 * 1024 * 1024:
        raise ValueError("OpenML dataset exceeds the 40 MB safety limit")
    out.write_bytes(payload)
    return _sha256(out)


def _fetch_hf(url: str, out: Path) -> str:
    """Stream a Hugging Face dataset file to disk, or reuse a cached copy."""
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        return _sha256(out)
    source = urlparse(url)
    if source.scheme != "https" or source.hostname != "huggingface.co":
        raise ValueError(f"Hugging Face source must be the approved HTTPS host: {url}")
    request = urllib.request.Request(  # noqa: S310 — constant approved source.
        url, headers={"User-Agent": "Mozilla/5.0 LimitIQ/1.0"}
    )
    written = 0
    with urllib.request.urlopen(request, timeout=600) as response:  # nosec B310  # noqa: S310
        with out.open("wb") as handle:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                written += len(chunk)
                if written > _MAX_HF_BYTES:
                    raise ValueError("Hugging Face file exceeds the 2 GB safety limit")
                handle.write(chunk)
    return _sha256(out)


def _harmonize_taiwan() -> tuple[pd.DataFrame, str]:
    from limitiq.pipeline import load_source

    frame, _ = load_source()
    work = pd.DataFrame(index=frame.index)
    work["delinquency_count"] = (frame[[f"PAY_{i}" for i in (0, 2, 3, 4, 5, 6)]] > 0).sum(axis=1)
    work["utilization"] = (
        frame["BILL_AMT1"].clip(lower=0) / frame["LIMIT_BAL"].clip(lower=1)
    ).clip(upper=5)
    work["debt_to_income"] = np.nan
    work["credit_lines"] = np.nan
    work["income_inr"] = np.nan
    work["credit_age_months"] = np.nan
    work["region"] = "asia"
    work[TARGET] = frame["default_next_month"].astype(int)
    return work, "taiwan_credit"


def _harmonize_german() -> tuple[pd.DataFrame, str]:
    spec = {
        "url": "https://archive.ics.uci.edu/static/public/144/statlog+german+credit+data.zip",
        "member": "german.data",
    }
    out = RAW_DIR / "german.data"
    _fetch_uci_zip(spec["url"], spec["member"], out)
    lines = [
        line.split() for line in out.read_text(encoding="latin-1").splitlines() if line.strip()
    ]
    raw = pd.DataFrame(lines)
    work = pd.DataFrame(index=raw.index)
    history = raw.iloc[:, 2]
    work["delinquency_count"] = history.isin(["A33", "A34"]).astype(int)
    work["utilization"] = np.nan
    work["debt_to_income"] = raw.iloc[:, 7].astype(int).map(_INSTALLMENT_RATE).astype(float)
    work["credit_lines"] = raw.iloc[:, 15].astype(int)
    work["income_inr"] = np.nan
    work["credit_age_months"] = np.nan
    work["region"] = "europe"
    work[TARGET] = (raw.iloc[:, -1].astype(int).map({1: 0, 2: 1})).astype(int)
    return work, "german_credit"


def _harmonize_south_german() -> tuple[pd.DataFrame, str]:
    spec = {
        "url": "https://archive.ics.uci.edu/static/public/573/south+german+credit+update.zip",
        "member": "SouthGermanCredit.asc",
    }
    out = RAW_DIR / "SouthGermanCredit.asc"
    _fetch_uci_zip(spec["url"], spec["member"], out)
    lines = [
        line.split() for line in out.read_text(encoding="latin-1").splitlines() if line.strip()
    ]
    raw = pd.DataFrame(lines[1:], columns=lines[0])
    work = pd.DataFrame(index=raw.index)
    work["delinquency_count"] = raw["moral"].astype(int).isin([0, 1]).astype(int)
    work["utilization"] = np.nan
    work["debt_to_income"] = raw["rate"].astype(int).map(_INSTALLMENT_RATE).astype(float)
    work["credit_lines"] = raw["bishkred"].astype(int).map({1: 1, 2: 2.5, 3: 4.5, 4: 6})
    work["income_inr"] = np.nan
    work["credit_age_months"] = np.nan
    work["region"] = "europe"
    work[TARGET] = (raw["kredit"].astype(int) == 0).astype(int)
    return work, "south_german_credit"


def _harmonize_gms() -> tuple[pd.DataFrame, str]:
    out = RAW_DIR / "give_me_some_credit.arff"
    _fetch_openml(22116561, out)
    raw = _read_arff(out)
    _numeric(raw, list(raw.columns))
    work = pd.DataFrame(index=raw.index)
    delinquency_columns = [
        "NumberOfTime30-59DaysPastDueNotWorse",
        "NumberOfTime60-89DaysPastDueNotWorse",
        "NumberOfTimes90DaysLate",
    ]
    delinquency = raw[delinquency_columns].mask(raw[delinquency_columns] >= 90)
    work["delinquency_count"] = delinquency.sum(axis=1, min_count=1)
    work["utilization"] = raw["RevolvingUtilizationOfUnsecuredLines"].clip(lower=0, upper=5)
    work["debt_to_income"] = raw["DebtRatio"].clip(lower=0, upper=1)
    work["credit_lines"] = raw["NumberOfOpenCreditLinesAndLoans"]
    work["income_inr"] = np.nan
    work["credit_age_months"] = np.nan
    work["region"] = "undisclosed"
    work[TARGET] = raw["SeriousDlqin2yrs"].astype(int)
    return work, "give_me_some_credit"


def _harmonize_heloc() -> tuple[pd.DataFrame, str]:
    out = RAW_DIR / "heloc.arff"
    _fetch_openml(22116522, out)
    raw = _read_arff(out)
    numeric_columns = [column for column in raw.columns if column != "RiskPerformance"]
    _numeric(raw, numeric_columns)
    raw[numeric_columns] = raw[numeric_columns].mask(raw[numeric_columns] < 0)
    raw["RiskPerformance"] = raw["RiskPerformance"].map({"Bad": 1, "Good": 0})
    work = pd.DataFrame(index=raw.index)
    work["delinquency_count"] = (
        raw["NumTrades60Ever2DerogPubRec"] + raw["NumTrades90Ever2DerogPubRec"]
    )
    work["utilization"] = raw["NetFractionRevolvingBurden"].div(100)
    work["debt_to_income"] = np.nan
    work["credit_lines"] = raw["NumTotalTrades"]
    work["income_inr"] = np.nan
    work["credit_age_months"] = raw["MSinceOldestTradeOpen"]
    work["region"] = "undisclosed"
    work[TARGET] = raw["RiskPerformance"].astype(int)
    return work, "fico_heloc"


def _harmonize_lending_club() -> tuple[pd.DataFrame, str]:
    out = RAW_DIR / "lending_club_full.csv"
    _fetch_hf(
        "https://huggingface.co/datasets/codesignal/lending-club-loan-accepted/resolve/main/"
        "accepted_2007_to_2018Q4.csv",
        out,
    )
    frame = pd.read_csv(
        out,
        usecols=[
            "loan_status",
            "delinq_2yrs",
            "revol_util",
            "dti",
            "open_acc",
            "annual_inc",
            "earliest_cr_line",
            "issue_d",
        ],
        low_memory=False,
    )
    good = frame["loan_status"].eq("Fully Paid")
    bad = frame["loan_status"].isin(
        ["Charged Off", "Default", "Late (16-30 days)", "Late (31-120 days)"]
    )
    frame = frame.loc[good | bad].copy()
    work = pd.DataFrame(index=frame.index)
    work["delinquency_count"] = frame["delinq_2yrs"]
    work["utilization"] = frame["revol_util"].div(100).clip(lower=0, upper=5)
    work["debt_to_income"] = frame["dti"].div(100).clip(lower=0, upper=1)
    work["credit_lines"] = frame["open_acc"]
    work["income_inr"] = frame["annual_inc"] * USD_TO_INR
    issued = pd.to_datetime(frame["issue_d"], format="%b-%Y", errors="coerce")
    opened = pd.to_datetime(frame["earliest_cr_line"], format="%b-%Y", errors="coerce")
    work["credit_age_months"] = (issued - opened).dt.days.div(30.44).clip(lower=0)
    work["region"] = "north_america"
    work[TARGET] = bad.astype(int)
    return work, "lending_club_full"


def _harmonize_home_credit() -> tuple[pd.DataFrame, str]:
    out = RAW_DIR / "home_credit_train.csv"
    _fetch_hf(
        "https://huggingface.co/cantalapiedra/poc_scoring_fair/resolve/main/"
        "application_train.csv?download=true",
        out,
    )
    frame = pd.read_csv(
        out,
        usecols=["TARGET", "AMT_INCOME_TOTAL", "AMT_ANNUITY"],
        low_memory=False,
    )
    work = pd.DataFrame(index=frame.index)
    work["delinquency_count"] = np.nan
    work["utilization"] = np.nan
    work["debt_to_income"] = (
        frame["AMT_ANNUITY"].div(frame["AMT_INCOME_TOTAL"].clip(lower=1)).clip(lower=0, upper=1)
    )
    work["credit_lines"] = np.nan
    work["income_inr"] = np.nan
    work["credit_age_months"] = np.nan
    work["region"] = "undisclosed"
    work[TARGET] = frame["TARGET"].astype(int)
    return work, "home_credit"


def _harmonizers() -> dict[str, Any]:
    return {
        "taiwan_credit": _harmonize_taiwan,
        "german_credit": _harmonize_german,
        "south_german_credit": _harmonize_south_german,
        "give_me_some_credit": _harmonize_gms,
        "fico_heloc": _harmonize_heloc,
        "lending_club_full": _harmonize_lending_club,
        "home_credit": _harmonize_home_credit,
    }


DATASET_META = {
    "taiwan_credit": {
        "name": "Default of Credit Card Clients (Taiwan)",
        "publisher": "I-Cheng Yeh / UCI Machine Learning Repository",
        "source_url": "https://archive.ics.uci.edu/dataset/350/default+of+credit+card+clients",
        "doi": "10.24432/C55S3H",
        "license": "CC BY 4.0",
        "currency": "TWD",
        "currency_status": "disclosed",
        "region": "asia",
        "geography_status": "Taiwan disclosed",
        "period": "April-September 2005 behavior; subsequent-month target",
        "source_rows": 30_000,
        "target_definition": "Subsequent-month default indicator",
        "target_horizon": "one month",
        "license_status": "open",
        "population_id": "taiwan-card-clients-2005",
        "exclusions": "None after schema validation",
    },
    "german_credit": {
        "name": "Statlog (German Credit Data)",
        "publisher": "UCI Machine Learning Repository",
        "source_url": "https://archive.ics.uci.edu/dataset/144/statlog+german+credit+data",
        "doi": "10.24432/C5NC77",
        "license": "CC BY 4.0",
        "currency": "DEM",
        "currency_status": "disclosed",
        "region": "europe",
        "geography_status": "South Germany disclosed",
        "period": "1973-1975",
        "source_rows": 1_000,
        "target_definition": "UCI bad-credit class (2=bad)",
        "target_horizon": "not disclosed",
        "license_status": "open",
        "population_id": "south-germany-credit-1973-1975",
        "exclusions": "All rows excluded from union training to prevent population duplication",
        "relationship_note": (
            "Legacy representation of the same 1,000-credit population as South German; "
            "retained for provenance only and excluded from union training."
        ),
    },
    "south_german_credit": {
        "name": "South German Credit Data",
        "publisher": "UCI Machine Learning Repository",
        "source_url": "https://archive.ics.uci.edu/dataset/573/south+german+credit+update",
        "doi": "10.24432/C5QG88",
        "license": "CC BY 4.0",
        "currency": "DEM",
        "currency_status": "disclosed",
        "region": "europe",
        "geography_status": "South Germany disclosed",
        "period": "1973-1975",
        "source_rows": 1_000,
        "target_definition": "UCI bad-credit class (kredit=0)",
        "target_horizon": "not disclosed",
        "license_status": "open",
        "population_id": "south-germany-credit-1973-1975",
        "exclusions": "None; corrected representation replaces legacy Statlog in training",
        "relationship_note": "Corrected representation used for union training.",
    },
    "give_me_some_credit": {
        "name": "Give Me Some Credit (geography undisclosed)",
        "publisher": "Kaggle competition contributors / OpenML mirror",
        "source_url": "https://www.openml.org/search?type=data&id=45577",
        "mirror_url": "https://api.openml.org/data/download/22116561/dataset",
        "doi": None,
        "license": "OpenML-listed public dataset; original competition terms apply",
        "currency": "Undisclosed",
        "currency_status": "not disclosed",
        "region": "undisclosed",
        "geography_status": "not disclosed",
        "period": "not disclosed",
        "source_rows": 150_000,
        "target_definition": "Serious delinquency within two years",
        "target_horizon": "two years",
        "license_status": "unresolved; OpenML metadata says Public",
        "population_id": "give-me-some-credit-training-150k",
        "exclusions": "96/98 delinquency placeholders converted to missing",
    },
    "fico_heloc": {
        "name": "FICO Explainable ML / HELOC (geography undisclosed)",
        "publisher": "FICO / OpenML mirror",
        "source_url": "https://investors.fico.com/news-releases/news-release-details/fico-announces-xml-challenge/",
        "mirror_url": "https://api.openml.org/data/download/22116522/dataset",
        "doi": None,
        "license": "OpenML Unknown / FICO custom challenge terms",
        "currency": "Not applicable",
        "currency_status": "no monetary feature used",
        "region": "undisclosed",
        "geography_status": "not disclosed",
        "period": "not disclosed",
        "source_rows": 10_459,
        "target_definition": "FICO RiskPerformance=Bad",
        "target_horizon": "not disclosed",
        "license_status": "unresolved; OpenML Unknown / FICO custom",
        "population_id": "fico-heloc-challenge",
        "exclusions": "OpenML cleaned mirror removes 588 all-special-value rows; 9,871 remain",
    },
    "lending_club_full": {
        "name": "Lending Club Loans 2007-2018 (US)",
        "publisher": "Lending Club / CodeSignal Hugging Face mirror",
        "source_url": "https://huggingface.co/datasets/codesignal/lending-club-loan-accepted",
        "mirror_url": "https://huggingface.co/datasets/codesignal/lending-club-loan-accepted/resolve/main/accepted_2007_to_2018Q4.csv",
        "doi": None,
        "license": "Mirror declares CC0; upstream Lending Club rights not independently verified",
        "currency": "USD",
        "currency_status": "disclosed",
        "region": "north_america",
        "geography_status": "United States disclosed",
        "period": "2007-2018 Q4",
        "source_rows": 2_260_701,
        "target_definition": "Status at extract: charged off/default/late versus fully paid",
        "target_horizon": "variable status-at-extract horizon",
        "license_status": "unresolved upstream; mirror declares CC0",
        "population_id": "lending-club-accepted-2007-2018q4",
        "exclusions": "Current, in-grace and other statuses excluded",
    },
    "home_credit": {
        "name": "Home Credit Default Risk (geography undisclosed)",
        "publisher": "Home Credit / poc_scoring_fair Hugging Face mirror",
        "source_url": "https://huggingface.co/cantalapiedra/poc_scoring_fair/blob/main/application_train.csv",
        "doi": None,
        "license": "Competition and mirror terms unresolved; human review required",
        "currency": "Undisclosed",
        "currency_status": "not disclosed",
        "region": "undisclosed",
        "geography_status": "not disclosed",
        "period": "not disclosed",
        "source_rows": 307_511,
        "target_definition": "Home Credit TARGET payment-difficulty indicator; horizon undisclosed",
        "target_horizon": "X-day delinquency within Y days; X and Y undisclosed",
        "license_status": "unresolved; mirror has no licence declaration",
        "population_id": "home-credit-application-train",
        "exclusions": "None; monetary inputs excluded because currency is undisclosed",
        "relationship_note": (
            "Competition data do not identify sample country or currency; monetary fields are not "
            "converted or used as INR values."
        ),
    },
}

REFERENCE_ONLY = {"german_credit"}

RAW_FILES = {
    "taiwan_credit": "default_of_credit_card_clients.xls",
    "german_credit": "german.data",
    "south_german_credit": "SouthGermanCredit.asc",
    "give_me_some_credit": "give_me_some_credit.arff",
    "fico_heloc": "heloc.arff",
    "lending_club_full": "lending_club_full.csv",
    "home_credit": "home_credit_train.csv",
}


def _union_frame() -> tuple[pd.DataFrame, dict[str, dict[str, Any]]]:
    harmonizers = _harmonizers()
    if set(harmonizers) != set(DATASET_META) or set(harmonizers) != set(RAW_FILES):
        raise RuntimeError("Every harmonizer requires matching metadata and a raw-file mapping")
    frames: dict[str, pd.DataFrame] = {}
    provenance: dict[str, dict[str, Any]] = {}
    for key, loader in harmonizers.items():
        frame, _ = loader()
        required = {TARGET, *MODEL_FEATURES}
        if set(frame.columns) != required:
            raise ValueError(f"{key} harmonizer emitted unexpected columns: {list(frame.columns)}")
        frame = frame.copy()
        frame[HARMONIZED_FEATURES] = frame[HARMONIZED_FEATURES].apply(
            pd.to_numeric, errors="coerce"
        )
        frame[HARMONIZED_FEATURES] = frame[HARMONIZED_FEATURES].replace([np.inf, -np.inf], np.nan)
        frame["region"] = frame["region"].astype(str)
        if frame.empty or frame[TARGET].isna().any() or not frame[TARGET].isin([0, 1]).all():
            raise ValueError(f"{key} harmonizer emitted an invalid binary target")
        if not frame["region"].isin(REGIONS).all():
            raise ValueError(f"{key} harmonizer emitted an invalid region")
        frame[TARGET] = frame[TARGET].astype(int)
        if key not in REFERENCE_ONLY:
            frames[key] = frame
        source_path = RAW_DIR / RAW_FILES[key]
        provenance[key] = {
            **DATASET_META[key],
            "role": "reference_only" if key in REFERENCE_ONLY else "training",
            "rows": int(len(frame)),
            "rows_in_union": 0 if key in REFERENCE_ONLY else int(len(frame)),
            "risk_rate": float(frame[TARGET].mean()),
            "file_sha256": _sha256(source_path),
            "feature_missing_rate": {
                column: float(frame[column].isna().mean()) for column in HARMONIZED_FEATURES
            },
        }
    union = pd.concat(
        [frame.assign(market=key) for key, frame in frames.items()], ignore_index=True
    )
    union = union[["market", TARGET, *MODEL_FEATURES]].copy()
    return union, provenance


def _model_pairs() -> dict[str, object]:
    def preprocess(impute: bool) -> ColumnTransformer:
        numeric: str | Pipeline = "passthrough"
        if impute:
            numeric = Pipeline(
                [("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())]
            )
        return ColumnTransformer(
            [
                ("numeric", numeric, HARMONIZED_FEATURES),
                (
                    "region",
                    OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                    CONTEXT_FEATURES,
                ),
            ],
            verbose_feature_names_out=False,
        )

    def logistic() -> Pipeline:
        return Pipeline(
            [
                ("preprocess", preprocess(impute=True)),
                ("model", LogisticRegression(C=0.5, max_iter=2_000, random_state=SEED)),
            ]
        )

    return {
        "Regularized logistic regression": CalibratedClassifierCV(
            logistic(), method="sigmoid", cv=3
        ),
        "Histogram gradient boosting": CalibratedClassifierCV(
            Pipeline(
                [
                    ("preprocess", preprocess(impute=False)),
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
            ),
            method="sigmoid",
            cv=3,
        ),
    }


def _roc_points(
    y_true: pd.Series, probability: np.ndarray, max_points: int = 250
) -> dict[str, list[float]]:
    fpr, tpr, _ = roc_curve(y_true, probability)
    if len(fpr) > max_points:
        selected = np.linspace(0, len(fpr) - 1, max_points, dtype=int)
        fpr, tpr = fpr[selected], tpr[selected]
    return {"fpr": [float(x) for x in fpr], "tpr": [float(x) for x in tpr]}


def _calibration_points(y_true: pd.Series, probability: np.ndarray) -> list[dict[str, float]]:
    fraction_positive, mean_predicted = calibration_curve(
        y_true, probability, n_bins=10, strategy="quantile"
    )
    return [
        {"mean_predicted": float(x), "observed_rate": float(y)}
        for x, y in zip(mean_predicted, fraction_positive, strict=True)
    ]


def _probability_summary(probability: np.ndarray) -> dict[str, Any]:
    edges = np.linspace(0, 1, 21)
    counts, _ = np.histogram(probability, bins=edges)
    labels = ("Low", "Moderate", "High", "Very high")
    bands = pd.cut(
        probability,
        bins=[-np.inf, 0.05, 0.15, 0.30, np.inf],
        labels=labels,
        right=False,
    )
    return {
        "histogram": [
            {"lower": float(edges[index]), "upper": float(edges[index + 1]), "count": int(count)}
            for index, count in enumerate(counts)
        ],
        "risk_bands": {label: int((bands == label).sum()) for label in labels},
    }


def _calibration_gap(points: list[dict[str, float]]) -> float:
    return float(np.mean([abs(item["mean_predicted"] - item["observed_rate"]) for item in points]))


def build_global() -> dict[str, Any]:
    union, provenance = _union_frame()
    X = union[MODEL_FEATURES]  # noqa: N806
    y = union[TARGET].astype(int)
    strata = union["market"].astype(str) + "|" + y.astype(str)
    train_index, holdout_index = train_test_split(
        union.index, test_size=0.4, stratify=strata, random_state=SEED
    )
    validation_index, test_index = train_test_split(
        holdout_index,
        test_size=0.5,
        stratify=strata.loc[holdout_index],
        random_state=SEED,
    )
    train_x, train_y = X.loc[train_index], y.loc[train_index]
    validation_x, validation_y = X.loc[validation_index], y.loc[validation_index]
    test_x, test_y = X.loc[test_index], y.loc[test_index]
    validation_sources = union.loc[validation_index, "market"].to_numpy()
    validation_results: dict[str, Any] = {}
    fitted: dict[str, Any] = {}
    for name, model in _model_pairs().items():
        model.fit(train_x, train_y)
        probability = model.predict_proba(validation_x)[:, 1]
        threshold = _threshold(validation_y, probability)
        validation_results[name] = _metrics(validation_y, probability, threshold)
        source_metrics = [
            _metrics(
                validation_y.iloc[np.flatnonzero(validation_sources == key)],
                probability[validation_sources == key],
                threshold,
            )
            for key in sorted(union["market"].unique())
        ]
        validation_results[name]["macro_roc_auc"] = float(
            np.mean([item["roc_auc"] for item in source_metrics])
        )
        validation_results[name]["macro_brier_score"] = float(
            np.mean([item["brier_score"] for item in source_metrics])
        )
        fitted[name] = model
    best_auc = max(value["macro_roc_auc"] for value in validation_results.values())
    eligible = {
        name: value
        for name, value in validation_results.items()
        if value["macro_roc_auc"] >= best_auc - 0.02
    }
    champion_name = min(eligible, key=lambda name: eligible[name]["macro_brier_score"])
    champion = fitted[champion_name]
    selected_threshold = _threshold(validation_y, champion.predict_proba(validation_x)[:, 1])
    champion = _model_pairs()[champion_name]
    combined_x = pd.concat([train_x, validation_x])
    combined_y = pd.concat([train_y, validation_y])
    champion.fit(combined_x, combined_y)
    test_probability = champion.predict_proba(test_x)[:, 1]
    test_metrics = _metrics(test_y, test_probability, selected_threshold)
    test_metrics["roc_points"] = _roc_points(test_y, test_probability)
    test_metrics["calibration_points"] = _calibration_points(test_y, test_probability)
    test_metrics["mean_absolute_calibration_gap"] = _calibration_gap(
        test_metrics["calibration_points"]
    )
    test_metrics["probability_summary"] = _probability_summary(test_probability)

    market_rows = union.loc[test_x.index, "market"].to_numpy()
    per_market: dict[str, Any] = {}
    for key in sorted(union["market"].unique()):
        mask = market_rows == key
        market_y = test_y.iloc[np.flatnonzero(mask)]
        market_p = test_probability[mask]
        market_metrics = _metrics(market_y, market_p, selected_threshold)
        market_metrics["roc_points"] = _roc_points(market_y, market_p)
        market_metrics["calibration_points"] = _calibration_points(market_y, market_p)
        market_metrics["mean_absolute_calibration_gap"] = _calibration_gap(
            market_metrics["calibration_points"]
        )
        market_metrics["probability_summary"] = _probability_summary(market_p)
        market_metrics["accounts"] = int(len(market_y))
        market_metrics["risk_rate"] = float(market_y.mean())
        per_market[key] = market_metrics

    macro_fields = (
        "roc_auc",
        "pr_auc",
        "brier_score",
        "log_loss",
        "mean_absolute_calibration_gap",
    )
    macro_test_metrics = {
        field: float(np.mean([item[field] for item in per_market.values()]))
        for field in macro_fields
    }

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    model_path = MODEL_DIR / "global_champion.joblib"
    joblib.dump(champion, model_path, compress=3)
    model_checksum = _sha256(model_path)
    dataset_checksum = hashlib.sha256(
        json.dumps(provenance, sort_keys=True).encode("utf-8")
    ).hexdigest()
    datasets_above_200k = [
        key for key, item in provenance.items() if item["rows_in_union"] >= 200_000
    ]
    payload = {
        "classification": "Multi-source adverse-credit-outcome benchmark",
        "model_version": f"limitiq-global-2.0.0-{model_checksum[:12]}",
        "dataset_version": f"global-7-{dataset_checksum[:12]}",
        "generated_at": datetime.now(UTC).isoformat(),
        "random_seed": SEED,
        "harmonized_features": HARMONIZED_FEATURES,
        "context_features": CONTEXT_FEATURES,
        "region_categories": list(REGIONS),
        "source_files": len(provenance),
        "training_sources": sorted(set(provenance) - REFERENCE_ONLY),
        "reference_sources": sorted(REFERENCE_ONLY),
        "rows": int(len(union)),
        "risk_rate": float(y.mean()),
        "target_note": (
            "Source labels have different horizons and event definitions. The calibrated output is "
            "an educational adverse-credit-outcome probability, not a common-horizon regulatory PD."
        ),
        "evaluation_scope": (
            "Seeded random within-source interpolation. No leave-one-source-out, unseen-country or "
            "out-of-time generalization claim is made."
        ),
        "row_budget": {
            "minimum": 1_500_000,
            "expected_approx": 1_869_500,
            "actual": int(len(union)),
            "datasets_above_200k": datasets_above_200k,
            "minimum_satisfied": bool(len(union) >= 1_500_000 and len(datasets_above_200k) >= 2),
        },
        "currency_note": (
            "Only currencies disclosed by their source are converted to INR at fixed rates "
            f"(TWD {CURRENCY_RATES['TWD']:g}, USD {CURRENCY_RATES['USD']:g}). Home Credit's "
            "currency and geography are undisclosed, so its monetary fields are not converted or "
            "used as INR values. FX conversion is presentation localization, not Indian evidence."
        ),
        "datasets": provenance,
        "split": {
            "train": int(len(train_x)),
            "validation": int(len(validation_x)),
            "test": int(len(test_x)),
        },
        "validation_models": validation_results,
        "champion": champion_name,
        "selection_rule": (
            "Lowest macro source-cohort validation Brier score among models within 0.02 "
            "macro ROC-AUC of the best"
        ),
        "threshold_rule": "Minimize validation cost with false negatives weighted 5x false positives",
        "selected_threshold": selected_threshold,
        "test_metrics": test_metrics,
        "macro_test_metrics": macro_test_metrics,
        "per_market_test_metrics": per_market,
        "publication_gate": {
            "status": "blocked",
            "reason": (
                "Upstream or competition redistribution and derived-artifact terms require "
                "manual review before publishing the v2 model or source-derived demo rows."
            ),
            "sources": [
                "give_me_some_credit",
                "fico_heloc",
                "lending_club_full",
                "home_credit",
            ],
        },
        "dataset_checksum": dataset_checksum,
        "model_checksum": model_checksum,
    }
    _write_json(MODEL_DIR / "global_metadata.json", payload)
    _write_json(OUTPUT_DIR / "global_model.json", payload)
    _write_demo(champion, payload)
    _write_report(payload)
    return payload


def _synthetic_profiles(rows_per_cohort: int = 200) -> pd.DataFrame:
    """Create deterministic source-shaped profiles without copying source records."""
    rng = np.random.default_rng(SEED)
    frames: list[pd.DataFrame] = []
    for source in sorted(set(DATASET_META) - REFERENCE_ONLY):
        size = rows_per_cohort
        frame = pd.DataFrame(index=range(size), columns=MODEL_FEATURES, dtype=float)
        frame["region"] = DATASET_META[source]["region"]
        if source in {"taiwan_credit", "give_me_some_credit", "fico_heloc", "lending_club_full"}:
            frame["delinquency_count"] = rng.poisson(0.35, size).clip(0, 6)
        if source in {"taiwan_credit", "give_me_some_credit", "fico_heloc", "lending_club_full"}:
            frame["utilization"] = (rng.beta(2.2, 2.8, size) * 1.35).clip(0, 1.4)
        if source in {
            "south_german_credit",
            "give_me_some_credit",
            "lending_club_full",
            "home_credit",
        }:
            frame["debt_to_income"] = rng.beta(2.0, 5.0, size).clip(0, 0.95)
        if source in {
            "south_german_credit",
            "give_me_some_credit",
            "fico_heloc",
            "lending_club_full",
        }:
            frame["credit_lines"] = (rng.poisson(7, size) + 1).clip(1, 45)
        if source == "lending_club_full":
            frame["income_inr"] = rng.lognormal(np.log(900_000), 0.6, size).clip(
                180_000, 15_000_000
            )
        if source in {"fico_heloc", "lending_club_full"}:
            frame["credit_age_months"] = rng.gamma(5, 28, size).clip(6, 600)
        frame["source_dataset"] = source
        frames.append(frame)
    profiles = pd.concat(frames, ignore_index=True)
    profiles = profiles.iloc[rng.permutation(len(profiles))].reset_index(drop=True)
    fallback_limit = rng.lognormal(np.log(350_000), 0.65, len(profiles))
    income_limit = profiles["income_inr"].mul(0.25)
    profiles["current_limit_inr"] = (
        income_limit.fillna(pd.Series(fallback_limit)).clip(50_000, 2_500_000).round(-3)
    )
    utilization = profiles["utilization"].fillna(pd.Series(rng.beta(2, 4, len(profiles))))
    profiles["current_balance_inr"] = (
        profiles["current_limit_inr"] * utilization.clip(0, 1.5)
    ).round(-2)
    profiles["account_id"] = [f"LIQ-{index + 1:06d}" for index in range(len(profiles))]
    return profiles


def _write_demo(model: object, metadata: dict[str, Any]) -> None:
    from limitiq.optimizer import portfolio_sensitivity, recommend_portfolio, summarize_portfolio

    profiles = _synthetic_profiles()
    probabilities = model.predict_proba(profiles[MODEL_FEATURES])[:, 1]
    eligible = profiles.index[
        (probabilities < 0.15)
        & profiles["delinquency_count"].eq(0)
        & profiles["utilization"].between(0.35, 0.90)
        & (profiles["debt_to_income"].isna() | profiles["debt_to_income"].le(0.55))
    ]
    for indices, limit in ((eligible[:18], 2_600_000), (eligible[18:36], 2_500_000)):
        profiles.loc[indices, "current_limit_inr"] = limit
        profiles.loc[indices, "current_balance_inr"] = (
            profiles.loc[indices, "utilization"] * limit
        ).round(-2)
    assumptions = PolicyAssumptions()
    decisions = recommend_portfolio(
        profiles,
        probabilities,
        profiles["account_id"].tolist(),
        assumptions,
    )
    output = profiles.copy()
    decision_rows = [item.to_dict() for item in decisions]
    for column in (
        "action",
        "increase_pct",
        "proposed_limit",
        "pd",
        "risk_band",
        "current_ead",
        "proposed_ead",
        "current_expected_loss",
        "proposed_expected_loss",
        "incremental_contribution",
        "risk_adjusted_return",
    ):
        output[column] = [item[column] for item in decision_rows]
    output["reason_codes"] = [" | ".join(item.reason_codes) for item in decisions]
    output["policy_checks"] = [json.dumps(item.policy_checks) for item in decisions]
    output["missing_model_fields"] = output[HARMONIZED_FEATURES].apply(
        lambda row: " | ".join(row.index[row.isna()]), axis=1
    )
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    output.to_csv(PROCESSED_DIR / "global_demo_portfolio.csv", index=False)
    _write_json(
        REPORT_DIR / "global_policy_simulation.json",
        {
            "classification": "Deterministic synthetic scenario; not observed or causal impact",
            "model_version": metadata["model_version"],
            "assumptions": assumptions.to_dict(),
            "summary": summarize_portfolio(decisions),
            "sensitivity": portfolio_sensitivity(
                profiles,
                probabilities,
                profiles["account_id"].tolist(),
                assumptions,
            ),
            "limitations": [
                "Candidate probabilities inherit source-specific outcome definitions and horizons.",
                "Limit response, LGD, CCF, revenue and cost inputs are assumptions, not observed causal effects.",
                "Expected-loss values are simulated management proxies, not IFRS 9 provisions.",
            ],
        },
    )


def _write_report(payload: dict[str, Any]) -> None:
    headers = [
        "Dataset",
        "Role",
        "Region",
        "Source rows",
        "Harmonized rows",
        "Rows in union",
        "Risk rate",
        "Currency",
        "Licence / terms",
        "SHA-256",
    ]
    rows = [
        [
            DATASET_META[key]["name"],
            item["role"].replace("_", " ").title(),
            item["region"],
            f"{item['source_rows']:,}",
            f"{item['rows']:,}",
            f"{item['rows_in_union']:,}",
            f"{item['risk_rate']:.1%}",
            item["currency"],
            item["license"],
            item["file_sha256"][:12] + "…",
        ]
        for key, item in payload["datasets"].items()
    ]
    pooled = payload["test_metrics"]
    macro = payload["macro_test_metrics"]
    detail_rows = [
        [
            DATASET_META[key]["name"],
            f"{item['accounts']:,}",
            f"{item['roc_auc']:.4f}",
            f"{item['pr_auc']:.4f}",
            f"{item['brier_score']:.4f}",
            f"{item['log_loss']:.4f}",
            f"{item['mean_absolute_calibration_gap']:.4f}",
        ]
        for key, item in payload["per_market_test_metrics"].items()
    ]
    validation_rows = [
        [
            name,
            f"{item['macro_roc_auc']:.4f}",
            f"{item['macro_brier_score']:.4f}",
            f"{item['roc_auc']:.4f}",
            f"{item['brier_score']:.4f}",
        ]
        for name, item in payload["validation_models"].items()
    ]
    calibration_tables = [
        "<h3>Pooled untouched test</h3>"
        + _table(
            ["Mean predicted adverse-outcome probability", "Observed event rate"],
            [
                [f"{point['mean_predicted']:.4f}", f"{point['observed_rate']:.4f}"]
                for point in pooled["calibration_points"]
            ],
        )
    ]
    calibration_tables.extend(
        "<h3>"
        + DATASET_META[key]["name"]
        + "</h3>"
        + _table(
            ["Mean predicted adverse-outcome probability", "Observed event rate"],
            [
                [f"{point['mean_predicted']:.4f}", f"{point['observed_rate']:.4f}"]
                for point in item["calibration_points"]
            ],
        )
        for key, item in payload["per_market_test_metrics"].items()
    )
    sections = [
        (
            "Multi-source benchmark summary",
            f'<div class="notice"><strong>Method.</strong> {payload["classification"]}. '
            f"{payload['rows']:,} accounts from {len(payload['training_sources'])} independent "
            f"training cohorts plus {len(payload['reference_sources'])} reference-only source; "
            f"seeded 60/20/20 within-source interpolation.</div>"
            f"<p><strong>Macro source-cohort evidence:</strong> ROC-AUC {macro['roc_auc']:.4f} "
            f"&bull; PR-AUC {macro['pr_auc']:.4f} &bull; Brier {macro['brier_score']:.4f} "
            f"&bull; calibration gap {macro['mean_absolute_calibration_gap']:.4f}.</p>"
            f"<p><strong>Row-weighted pooled evidence:</strong> ROC-AUC {pooled['roc_auc']:.4f} "
            f"&bull; PR-AUC {pooled['pr_auc']:.4f} &bull; Brier {pooled['brier_score']:.4f} "
            f"&bull; calibration gap {pooled['mean_absolute_calibration_gap']:.4f} &bull; "
            f"threshold {payload['selected_threshold']:.4f}.</p>"
            f"<p>{payload['target_note']} {payload['evaluation_scope']}</p>",
        ),
        (
            "Dataset provenance",
            _table(headers, rows) + f"<p>{payload['currency_note']}</p>"
            f"<p>Harmonized features: {', '.join(payload['harmonized_features'])}; context: "
            f"{', '.join(payload['context_features'])}.</p>",
        ),
        (
            "Held-out test detail",
            _table(
                [
                    "Source cohort",
                    "N",
                    "ROC-AUC",
                    "PR-AUC",
                    "Brier",
                    "Log-loss",
                    "Calibration gap",
                ],
                detail_rows,
            )
            + "<p>Each source cohort's untouched test rows are scored with the same pooled champion. "
            "Macro metrics weight each cohort equally; pooled metrics are dominated by Lending Club.</p>",
        ),
        ("Calibration evidence", "".join(calibration_tables)),
        (
            "Validation model comparison",
            _table(
                ["Model", "Macro ROC-AUC", "Macro Brier", "Pooled ROC-AUC", "Pooled Brier"],
                validation_rows,
            )
            + f"<p>{payload['selection_rule']}. {payload['threshold_rule']}.</p>",
        ),
        (
            "Publication gate",
            f'<div class="notice"><strong>Status: {payload["publication_gate"]["status"]}.</strong> '
            f"{payload['publication_gate']['reason']}</div><p>Affected sources: "
            f"{', '.join(payload['publication_gate']['sources'])}. Local modelling may continue, "
            "but v2 model and source-derived artifacts must not be publicly redistributed until "
            "the terms review is resolved.</p>",
        ),
        (
            "Interpretation",
            "<p>The pooled champion learns source-mixed patterns conditioned on a one-hot coarse "
            "region category. Missingness can indirectly identify a source cohort. Different target "
            "definitions and horizons prevent jurisdiction-equivalent PD comparison. Feature sets are "
            "intentionally narrow because sources report different fields; missing fields remain NaN "
            "for gradient boosting and are median-imputed for logistic regression. This benchmark "
            "does not establish unseen-country, out-of-time or production generalization.</p>"
            f"<p>Generated {payload['generated_at'][:10]} &bull; random seed {payload['random_seed']}.</p>",
        ),
    ]
    _write_html(
        OUTPUT_DIR,
        "global_model_report.html",
        "Multi-source adverse-credit-outcome benchmark",
        "Multi-source evidence &bull; LimitIQ",
        sections,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="LimitIQ multi-source adverse-credit-outcome benchmark"
    )
    parser.add_argument(
        "--demo-only",
        action="store_true",
        help="Regenerate only the deterministic synthetic demo from verified global artifacts",
    )
    args = parser.parse_args()
    if args.demo_only:
        model_path = MODEL_DIR / "global_champion.joblib"
        metadata_path = MODEL_DIR / "global_metadata.json"
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
        if _sha256(model_path) != payload["model_checksum"]:
            raise RuntimeError("Global model checksum does not match metadata")
        model = joblib.load(model_path)  # noqa: S301 -- checksum-verified local artifact.
        _write_demo(model, payload)
        print(json.dumps({"demo_rows": 1_200, "model_version": payload["model_version"]}))
        return
    payload = build_global()
    summary = {
        "model_version": payload["model_version"],
        "dataset_version": payload["dataset_version"],
        "rows": payload["rows"],
        "champion": payload["champion"],
        "selected_threshold": payload["selected_threshold"],
        "macro_test_metrics": payload["macro_test_metrics"],
        "pooled_test_metrics": {
            key: payload["test_metrics"][key]
            for key in ("roc_auc", "pr_auc", "brier_score", "log_loss")
        },
        "publication_gate": payload["publication_gate"],
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
