"""Tests for mouse ONNX export and native parity."""

from __future__ import annotations

import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.impute import SimpleImputer

from botguard_ml.export_onnx import export_mouse_onnx, predict_onnx


def test_exported_model_matches_native_lightgbm(tmp_path) -> None:
    rows = pd.DataFrame(
        {
            "label": [0, 1, 0, 1, 0, 1, 0, 1],
            "a": [0.0, 1.0, 0.2, 1.2, 0.1, 1.1, 0.3, 1.3],
            "b": [1.0, 1.0, 0.8, 0.9, 1.2, 0.7, 0.6, 0.5],
        }
    )
    export_mouse_onnx(rows, tmp_path, feature_columns=["a", "b"])
    imputer = SimpleImputer(strategy="median")
    values = imputer.fit_transform(rows[["a", "b"]]).astype(np.float32)
    native = LGBMClassifier(
        n_estimators=100,
        learning_rate=0.05,
        num_leaves=31,
        random_state=42,
        n_jobs=1,
        verbosity=-1,
    )
    native.fit(values, rows["label"])

    expected = native.predict_proba(values)[:, 1]
    actual = predict_onnx(tmp_path / "model.onnx", values)

    np.testing.assert_allclose(actual, expected, rtol=1e-4, atol=1e-4)
