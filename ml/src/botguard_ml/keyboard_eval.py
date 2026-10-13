"""Grouped keyboard model training and subgroup evaluation."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd  # type: ignore[import-untyped]
from sklearn.impute import SimpleImputer  # type: ignore[import-untyped]
from sklearn.linear_model import LogisticRegression  # type: ignore[import-untyped]
from sklearn.pipeline import make_pipeline  # type: ignore[import-untyped]
from sklearn.preprocessing import StandardScaler  # type: ignore[import-untyped]

from botguard_ml.baselines import _feature_columns
from botguard_ml.eval import _metric_values, grouped_bootstrap
from botguard_ml.splits import grouped_split


def _report(name: str, rows: pd.DataFrame, *, n_bootstrap: int, seed: int) -> dict[str, Any]:
    if rows.empty:
        return {"group": name, "status": "insufficient_data", "n_rows": 0}
    labels = rows["label"].to_numpy(dtype=int)
    scores = rows["score"].to_numpy(dtype=float)
    metrics = _metric_values(labels, scores)
    result: dict[str, Any] = {"group": name, "n_rows": len(rows), **metrics}
    if metrics.get("status") == "ok" and rows["split_group"].nunique() >= 2:
        low, high = grouped_bootstrap(
            rows,
            lambda y, s: _metric_values(y, s)["roc_auc"],
            n_resamples=n_bootstrap,
            seed=seed,
        )
        result.update({"roc_auc_ci_low": low, "roc_auc_ci_high": high})
    return result


def evaluate_keyboard(
    rows: pd.DataFrame,
    *,
    test_size: float = 0.2,
    seed: int = 42,
    n_bootstrap: int = 100,
) -> pd.DataFrame:
    """Train a grouped Logistic Regression model and report keyboard subgroups."""
    required = {"label", "bot_type", "split_group", "typing_speed_cps", "dataset", "domain"}
    missing = required.difference(rows.columns)
    if missing:
        raise ValueError(f"rows missing columns: {', '.join(sorted(missing))}")
    metadata = rows.to_dict("records")
    train_indices, test_indices = grouped_split(metadata, test_size=test_size, seed=seed)
    train_indices = [index for index in train_indices if rows.iloc[index]["bot_type"] != "K3"]
    k3_indices = [index for index, row in enumerate(metadata) if row["bot_type"] == "K3"]
    test_indices = sorted(set(test_indices).union(k3_indices))
    features = _feature_columns(rows)
    if len(np.unique(rows.iloc[train_indices]["label"])) < 2:
        raise ValueError("training split must contain both labels")
    model = make_pipeline(
        SimpleImputer(strategy="median"),
        StandardScaler(),
        LogisticRegression(max_iter=1000, random_state=seed),
    )
    model.fit(rows.iloc[train_indices][features], rows.iloc[train_indices]["label"])
    test = rows.iloc[test_indices].copy()
    test["score"] = model.predict_proba(test[features])[:, 1]
    reports = [_report("overall", test, n_bootstrap=n_bootstrap, seed=seed)]
    for bot_type, group in test[test["label"] == 1].groupby("bot_type"):
        reports.append(_report(f"generator:{bot_type}", group, n_bootstrap=n_bootstrap, seed=seed))
    human = test[test["label"] == 0]
    if not human.empty:
        threshold = float(np.quantile(human["score"], 0.99))
        reports.append(
            {
                "group": "human_fpr",
                "status": "ok",
                "n_rows": len(human),
                "human_fpr": float(np.mean(human["score"] >= threshold)),
                "threshold": threshold,
            }
        )
    test = test.assign(
        speed_tercile=pd.qcut(
            test["typing_speed_cps"],
            3,
            labels=False,
            duplicates="drop",
        )
    )
    for tercile, group in test.groupby("speed_tercile", dropna=True):
        reports.append(
            _report(
                f"speed_tercile:{int(tercile) + 1}",
                group,
                n_bootstrap=n_bootstrap,
                seed=seed,
            )
        )
    return pd.DataFrame(reports)
