"""External cross-dataset validation of the LimitIQ PD methodology.

The production model is trained on a six-month repayment-status panel (UCI
Default of Credit Card Clients) whose 19 input fields do not generalise to
arbitrary credit datasets. This module re-runs the *same methodology* — seeded
stratified 60/20/20 split, regularized logistic-regression baseline and
calibrated histogram gradient boosting, sigmoid calibration, and the
loss-weighted threshold rule — on additional public credit datasets, and reports
out-of-domain discrimination and calibration. It is an external-validity check
of the modelling recipe, not evidence that the Taiwan-specific production
features port to other portfolios or to Indian borrowers.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
import zipfile
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from limitiq.config import SEED
from limitiq.pipeline import _metrics, _threshold
from limitiq.reporting import _table, _write_html

OUTPUT_DIR = Path("reports")

EXTERNAL_DATASETS = [
    {
        "key": "german_credit",
        "name": "Statlog (German Credit Data)",
        "url": "https://archive.ics.uci.edu/static/public/144/statlog+german+credit+data.zip",
        "member": "german.data",
        "doi": "10.24432/C5NC77",
        "license": "CC BY 4.0",
        "feature_continuous": {1, 4, 7, 10, 12, 15, 17},
        "target_map": {1: 0, 2: 1},
        "note": "19 symbolic and numeric attributes plus a binary credit-risk label (1 = bad).",
    },
    {
        "key": "australian_credit",
        "name": "Australian Credit Approval",
        "url": "https://archive.ics.uci.edu/static/public/143/statlog+australian+credit+approval.zip",
        "member": "australian.dat",
        "doi": "10.24432/C59012",
        "license": "CC BY 4.0",
        "feature_continuous": {1, 2, 6, 9, 12, 13},
        "target_map": {0: 1, 1: 0},
        "note": "Six continuous and eight categorical attributes; a few '?' values are "
        "median-imputed for modelling. Denied applications (encoded 0) are the risk event.",
    },
]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def _fetch_uci_zip(url: str, member: str, out: Path) -> str:
    """Download the named member of an approved UCI HTTPS ZIP, or reuse a cached copy."""
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        return _sha256(out)
    source = urlparse(url)
    if source.scheme != "https" or source.hostname != "archive.ics.uci.edu":
        raise ValueError(f"External source must be the approved UCI HTTPS host: {url}")
    request = urllib.request.Request(url, headers={"User-Agent": "LimitIQ/1.0"})  # noqa: S310
    with urllib.request.urlopen(request, timeout=60) as response:  # nosec B310  # noqa: S310
        payload = response.read(10 * 1024 * 1024 + 1)
    if len(payload) > 10 * 1024 * 1024:
        raise ValueError("External archive exceeds the 10 MB safety limit")
    with zipfile.ZipFile(BytesIO(payload)) as archive:
        members = [name for name in archive.namelist() if not name.endswith("/")]
        if member not in members:
            raise ValueError(f"Expected member {member!r} missing from {url}")
        data = archive.read(member)
    out.write_bytes(data)
    return _sha256(out)


def _encode_features(frame: pd.DataFrame, continuous: set[int]) -> pd.DataFrame:
    features = pd.DataFrame(index=frame.index)
    for i in range(frame.shape[1]):
        column = frame.iloc[:, i]
        if i in continuous:
            features[f"A{i + 1}"] = pd.to_numeric(column, errors="coerce")
        else:
            features = features.join(
                pd.get_dummies(column.astype(str), prefix=f"A{i + 1}", prefix_sep="_")
            )
    return features.astype(float)


def _remove_na(X: pd.DataFrame) -> pd.DataFrame:  # noqa: N803
    return pd.DataFrame(SimpleImputer(strategy="median").fit_transform(X), columns=X.columns)


def _evaluate_dataset(
    spec: dict[str, Any],
    X: pd.DataFrame,  # noqa: N803
    y: pd.Series,
    rows: int,
    source_sha256: str,
) -> dict[str, Any]:
    X = _remove_na(X)
    y = y.reset_index(drop=True)
    train_x, holdout_x, train_y, holdout_y = train_test_split(
        X, y, test_size=0.4, stratify=y, random_state=SEED
    )
    val_x, test_x, val_y, test_y = train_test_split(
        holdout_x, holdout_y, test_size=0.5, stratify=holdout_y, random_state=SEED
    )
    validation_results: dict[str, Any] = {}
    fitted: dict[str, Any] = {}
    for name, model in _model_pairs().items():
        model.fit(train_x, train_y)
        probability = model.predict_proba(val_x)[:, 1]
        threshold = _threshold(val_y, probability)
        validation_results[name] = _metrics(val_y, probability, threshold)
        fitted[name] = model
    best_auc = max(value["roc_auc"] for value in validation_results.values())
    eligible = {
        name: value
        for name, value in validation_results.items()
        if value["roc_auc"] >= best_auc - 0.02
    }
    champion_name = min(eligible, key=lambda name: eligible[name]["brier_score"])
    champion = fitted[champion_name]
    threshold = _threshold(val_y, champion.predict_proba(val_x)[:, 1])
    test_metrics = _metrics(test_y, champion.predict_proba(test_x)[:, 1], threshold)
    return {
        "key": spec["key"],
        "dataset": spec["name"],
        "publisher": "UCI Machine Learning Repository",
        "source_page": "https://archive.ics.uci.edu/",
        "download_url": spec["url"],
        "doi": spec["doi"],
        "license": spec["license"],
        "file_sha256": source_sha256,
        "notes": [spec["note"]],
        "rows": rows,
        "risk_rate": float(y.mean()),
        "n_features": int(X.shape[1]),
        "split": {"train": len(train_x), "validation": len(val_x), "test": len(test_x)},
        "validation_models": validation_results,
        "champion": champion_name,
        "selection_rule": "Lowest validation Brier score among models within 0.02 ROC-AUC of the best",
        "threshold_rule": "Minimize validation cost with false negatives weighted 5x false positives",
        "selected_threshold": threshold,
        "test_metrics": test_metrics,
        "trained_at": datetime.now(UTC).isoformat(),
    }


def _model_pairs() -> dict[str, object]:
    baseline = Pipeline(
        [
            ("scale", StandardScaler()),
            ("model", LogisticRegression(C=0.5, max_iter=2_000, random_state=SEED)),
        ]
    )
    challenger = HistGradientBoostingClassifier(
        learning_rate=0.06,
        max_iter=180,
        max_leaf_nodes=15,
        l2_regularization=1.0,
        random_state=SEED,
    )
    return {
        "Regularized logistic regression": CalibratedClassifierCV(baseline, method="sigmoid", cv=3),
        "Histogram gradient boosting": CalibratedClassifierCV(challenger, method="sigmoid", cv=3),
    }


def _production_reference() -> dict[str, Any] | None:
    model_path = Path("models") / "metadata.json"
    eda_path = OUTPUT_DIR / "eda.json"
    if not model_path.exists() or not eda_path.exists():
        return None
    model = json.loads(model_path.read_text(encoding="utf-8"))
    eda = json.loads(eda_path.read_text(encoding="utf-8"))
    test = model["test_metrics"]
    return {
        "dataset": "Default of Credit Card Clients (production)",
        "doi": "10.24432/C5HS4C",
        "rows": eda["accounts"],
        "risk_rate": eda["default_rate"],
        "champion": model["champion"],
        "roc_auc": test["roc_auc"],
        "pr_auc": test["pr_auc"],
        "brier_score": test["brier_score"],
        "selected_threshold": test["threshold"],
    }


def validate() -> dict[str, Any]:
    datasets: dict[str, Any] = {}
    comparison: list[dict[str, Any]] = []
    reference = _production_reference()
    if reference:
        comparison.append(reference)
    for spec in EXTERNAL_DATASETS:
        out = Path("data") / "raw" / (spec["member"])
        _fetch_uci_zip(spec["url"], spec["member"], out)
        lines = [
            line.split() for line in out.read_text(encoding="latin-1").splitlines() if line.strip()
        ]
        frame = pd.DataFrame(lines)
        target = frame.iloc[:, -1].astype(int).map(spec["target_map"]).astype(int)
        feats = _encode_features(frame.iloc[:, :-1], spec["feature_continuous"])
        result = _evaluate_dataset(spec, feats, target.astype(int), len(lines), _sha256(out))
        datasets[spec["key"]] = result
        test = result["test_metrics"]
        comparison.append(
            {
                "dataset": result["dataset"],
                "doi": result["doi"],
                "rows": result["rows"],
                "risk_rate": result["risk_rate"],
                "champion": result["champion"],
                "roc_auc": test["roc_auc"],
                "pr_auc": test["pr_auc"],
                "brier_score": test["brier_score"],
                "selected_threshold": test["threshold"],
            }
        )
    payload = {
        "classification": "External cross-dataset validation of the training recipe",
        "generated_at": datetime.now(UTC).isoformat(),
        "random_seed": SEED,
        "datasets": datasets,
        "comparison": comparison,
        "methodology": (
            "Per dataset: seeded stratified 60/20/20 split; regularized logistic-regression "
            "baseline and calibrated histogram gradient boosting; best of pair chosen by "
            "validation Brier within 0.02 ROC-AUC; cost-weighted threshold; all metrics on the "
            "untouched test split."
        ),
        "interpretation": (
            "External datasets have independent feature sets and target definitions, so they do "
            "not exercise the production LimitIQ input schema. Comparable discrimination and "
            "calibration across datasets is evidence the modelling methodology generalises; it is "
            "not evidence about portability of the Taiwan-specific features or about Indian "
            "borrowers."
        ),
    }
    _write_json(OUTPUT_DIR / "external_validation.json", payload)
    _write_report(payload)
    return payload


def _write_report(payload: dict[str, Any]) -> None:
    headers = [
        "Dataset",
        "N",
        "Risk rate",
        "Champion",
        "Test ROC-AUC",
        "Test PR-AUC",
        "Test Brier",
        "Threshold",
    ]
    rows = [
        [
            item["dataset"],
            f"{item['rows']:,}",
            f"{item['risk_rate']:.1%}",
            item["champion"],
            f"{item['roc_auc']:.4f}",
            f"{item['pr_auc']:.4f}",
            f"{item['brier_score']:.4f}",
            f"{item['selected_threshold']:.2f}",
        ]
        for item in payload["comparison"]
    ]
    details: list[tuple[str, str]] = []
    for result in payload["datasets"].values():
        model_rows = _table(
            ["Model", "ROC-AUC", "PR-AUC", "Brier", "Log-loss"],
            [
                [
                    name,
                    f"{item['roc_auc']:.4f}",
                    f"{item['pr_auc']:.4f}",
                    f"{item['brier_score']:.4f}",
                    f"{item['log_loss']:.4f}",
                ]
                for name, item in result["validation_models"].items()
            ],
        )
        test = result["test_metrics"]
        calib = "".join(
            f"<li>predicted {c['mean_predicted']:.2%} &rarr; observed {c['observed_rate']:.2%}</li>"
            for c in test["calibration"]
        )
        details.append(
            (
                result["dataset"],
                f"<p>{' '.join(result['notes'])}</p>"
                f"<p>{result['doi']} &bull; {result['license']}. {result['rows']:,} rows, "
                f"{result['risk_rate']:.1%} risk rate, {result['n_features']} features. Split: "
                f"train {result['split']['train']:,}, validation {result['split']['validation']:,}, "
                f"test {result['split']['test']:,}.</p>"
                f"<h3>Validation model comparison</h3>{model_rows}"
                f"<h3>Held-out test evidence</h3><p>ROC-AUC {test['roc_auc']:.4f} &bull; "
                f"PR-AUC {test['pr_auc']:.4f} &bull; Brier {test['brier_score']:.4f} &bull; "
                f"log-loss {test['log_loss']:.4f} &bull; threshold {test['threshold']:.2f}.</p>"
                f"<h3>Calibration on untouched test</h3><ul>{calib}</ul>",
            )
        )
    detail_html = "".join(
        f"<section><h2>{name}</h2>{content}</section>" for name, content in details
    )
    sections = [
        (
            "External validation summary",
            f'<div class="notice"><strong>Method.</strong> {payload["methodology"]}</div>'
            f"{_table(headers, rows)}",
        ),
        ("Per-dataset results", detail_html),
        (
            "Interpretation",
            f"<p>{payload['interpretation']}</p>"
            f"<p>Generated {payload['generated_at'][:10]} &bull; random seed "
            f"{payload['random_seed']}.</p>",
        ),
    ]
    _write_html(
        OUTPUT_DIR,
        "external_validation_report.html",
        "External model validation",
        "Evidence &bull; LimitIQ",
        sections,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="LimitIQ external cross-dataset validation")
    parser.parse_args()
    print(json.dumps(validate(), indent=2))


if __name__ == "__main__":
    main()
