"""Tests for mouse SHAP explanation helpers."""

from __future__ import annotations

import numpy as np

from botguard_ml.explanations import shap_summary, top_contributing_features


def test_top_contributors_are_ranked_by_absolute_effect() -> None:
    values = np.array([[0.1, -0.8, 0.4, 0.2], [-0.9, 0.3, 0.2, -0.1]])

    result = top_contributing_features(values, ["a", "b", "c", "d"])

    assert [item["feature"] for item in result[0]["features"]] == ["b", "c", "d"]
    assert result[0]["features"][0]["contribution"] == -0.8
    assert result[1]["features"][0]["feature"] == "a"


def test_shap_summary_reports_sorted_signed_and_absolute_values() -> None:
    result = shap_summary(np.array([[1.0, -3.0], [2.0, 1.0]]), ["a", "b"])

    assert list(result["feature"]) == ["b", "a"]
    assert list(result["rank"]) == [1, 2]
    assert result.loc[0, "mean_abs_shap"] == 2.0
