"""ONNX export and parity-check utilities."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
import onnxmltools  # type: ignore[import-untyped]
import onnxruntime as ort  # type: ignore[import-untyped]
import pandas as pd  # type: ignore[import-untyped]
from lightgbm import LGBMClassifier
from onnxmltools.convert.common.data_types import FloatTensorType  # type: ignore[import-untyped]
from skl2onnx.common.data_types import FloatTensorType as SklearnFloatTensorType  # type: ignore[import-untyped]
from sklearn.impute import SimpleImputer  # type: ignore[import-untyped]
from sklearn.linear_model import LogisticRegression  # type: ignore[import-untyped]
from sklearn.pipeline import make_pipeline  # type: ignore[import-untyped]
from sklearn.preprocessing import StandardScaler  # type: ignore[import-untyped]


def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def export_mouse_onnx(
    rows: pd.DataFrame,
    output_dir: Path,
    *,
    feature_columns: list[str],
    version: str = "v1",
    data_manifest_hash: str = "unknown",
    seed: int = 42,
    hyperparameters: dict[str, Any] | None = None,
    metrics: dict[str, Any] | None = None,
    calibration: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Fit the mouse LightGBM model and export it with metadata."""
    if not feature_columns:
        raise ValueError("feature_columns must not be empty")
    labels = rows["label"].to_numpy(dtype=int)
    if len(np.unique(labels)) < 2:
        raise ValueError("training data must contain both labels")
    imputer = SimpleImputer(strategy="median", keep_empty_features=True)
    values = imputer.fit_transform(rows[feature_columns]).astype(np.float32)
    params: dict[str, Any] = (
        dict(hyperparameters)
        if hyperparameters is not None
        else {
            "n_estimators": 100,
            "learning_rate": 0.05,
            "num_leaves": 31,
        }
    )
    model = LGBMClassifier(
        **params,
        random_state=seed,
        n_jobs=1,
        verbosity=-1,
    )
    model.fit(values, labels)
    output_dir.mkdir(parents=True, exist_ok=True)
    onnx_path = output_dir / "model.onnx"
    onnx_model = onnxmltools.convert_lightgbm(
        model,
        initial_types=[("features", FloatTensorType([None, len(feature_columns)]))],
    )
    onnxmltools.save_model(onnx_model, str(onnx_path))
    medians = {
        col: (float(val) if np.isfinite(val) else 0.0)
        for col, val in zip(feature_columns, imputer.statistics_, strict=False)
    }
    metadata: dict[str, Any] = {
        "version": version,
        "feature_order": feature_columns,
        "data_manifest_hash": data_manifest_hash,
        "git_commit": _git_commit(),
        "model": "lightgbm",
        "imputation": "median",
        "imputer_medians": medians,
        "hyperparameters": params,
        "seed": seed,
    }
    if metrics is not None:
        metadata["metrics"] = metrics
    if calibration is not None:
        metadata["calibration"] = calibration
    (output_dir / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    return metadata


def predict_onnx(model_path: Path, values: np.ndarray) -> np.ndarray:
    """Return positive-class probabilities from an exported ONNX model."""
    session = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
    output = session.run(None, {session.get_inputs()[0].name: values.astype(np.float32)})
    probabilities = output[-1]
    if isinstance(probabilities, list):
        return np.asarray([item[1] for item in probabilities], dtype=np.float32)
    return np.asarray(probabilities)[:, 1]


def export_keyboard_onnx(
    rows: pd.DataFrame,
    output_dir: Path,
    *,
    feature_columns: list[str],
    version: str = "v1",
    data_manifest_hash: str = "unknown",
    seed: int = 42,
) -> dict[str, Any]:
    """Fit the fixed keyboard Logistic Regression model and export it."""
    training = rows[rows["bot_type"] != "K3"]
    labels = training["label"].to_numpy(dtype=int)
    if not feature_columns:
        raise ValueError("feature_columns must not be empty")
    if len(np.unique(labels)) < 2:
        raise ValueError("training data must contain both labels")
    model = make_pipeline(
        SimpleImputer(strategy="median", keep_empty_features=True),
        StandardScaler(),
        LogisticRegression(max_iter=1000, random_state=seed),
    )
    model.fit(training[feature_columns], labels)
    output_dir.mkdir(parents=True, exist_ok=True)
    onnx_path = output_dir / "model.onnx"
    onnx_model = onnxmltools.convert_sklearn(
        model,
        initial_types=[("features", SklearnFloatTensorType([None, len(feature_columns)]))],
    )
    onnxmltools.save_model(onnx_model, str(onnx_path))
    metadata = {
        "version": version,
        "feature_order": feature_columns,
        "data_manifest_hash": data_manifest_hash,
        "git_commit": _git_commit(),
        "model": "logistic_regression",
        "preprocessing": ["median_imputation", "standard_scaling"],
        "k3_policy": "excluded_from_training",
        "seed": seed,
    }
    (output_dir / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    return metadata
