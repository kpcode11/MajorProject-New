"""Tests for keyboard ONNX export and native parity."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from botguard_ml.baselines import _feature_columns
from botguard_ml.export_onnx import export_keyboard_onnx, predict_onnx


def test_keyboard_export_matches_native_pipeline(tmp_path) -> None:
    rows = pd.DataFrame(
        {
            "label": [0, 1, 0, 1, 0, 1, 0, 1],
            "bot_type": ["human", "K1", "human", "K2", "human", "K3", "human", "K4"],
            "a": [0.0, 1.0, 0.2, 1.2, 0.1, 1.1, 0.3, 1.3],
            "b": [1.0, 1.0, 0.8, 0.9, 1.2, 0.7, 0.6, 0.5],
        }
    )
    export_keyboard_onnx(rows, tmp_path, feature_columns=["a", "b"])
    training = rows[rows["bot_type"] != "K3"]
    native = make_pipeline(
        SimpleImputer(strategy="median"),
        StandardScaler(),
        LogisticRegression(max_iter=1000, random_state=42),
    )
    native.fit(training[["a", "b"]], training["label"])
    values = rows[["a", "b"]].to_numpy(dtype=np.float32)
    expected = native.predict_proba(values)[:, 1]
    actual = predict_onnx(tmp_path / "model.onnx", values)
    np.testing.assert_allclose(actual, expected, rtol=1e-4, atol=1e-4)


def test_keyboard_export_writes_feature_metadata(tmp_path) -> None:
    rows = pd.DataFrame(
        {
            "label": [0, 1, 0, 1],
            "bot_type": ["human", "K1", "human", "K2"],
            "a": [0.0, 1.0, 0.2, 1.2],
            "b": [1.0, 1.0, 0.8, 0.9],
        }
    )
    metadata = export_keyboard_onnx(
        rows,
        tmp_path,
        feature_columns=_feature_columns(rows),
    )
    assert metadata["k3_policy"] == "excluded_from_training"
    assert metadata["feature_order"] == ["a", "b"]
