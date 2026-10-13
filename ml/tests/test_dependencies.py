"""Smoke tests for the ML package and its model-runtime dependencies."""

import lightgbm
import onnxmltools
import onnxruntime

import botguard_ml


def test_ml_dependencies_import() -> None:
    """ML dependencies required for feature work and ONNX export are importable."""
    assert botguard_ml.__doc__
    assert lightgbm.__version__
    assert onnxmltools.__version__
    assert onnxruntime.__version__
