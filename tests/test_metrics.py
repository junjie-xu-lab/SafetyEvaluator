"""Tests for SafetyEvaluator metric calculation."""

import pandas as pd

from safetyevaluator.metrics import calculate_metrics


def _make_data(rows: list[dict[str, str]]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def test_all_predictions_correct() -> None:
    data = _make_data(
        [
            {"id": "1", "input": "safe", "label": "Safe", "prediction": "Safe"},
            {"id": "2", "input": "unsafe", "label": "Unsafe", "prediction": "Unsafe"},
        ]
    )

    result = calculate_metrics(data)

    assert result.confusion_matrix == {"TP": 1, "TN": 1, "FP": 0, "FN": 0}
    assert result.metrics["Accuracy"] == 1.0
    assert result.metrics["Precision"] == 1.0
    assert result.metrics["Recall"] == 1.0
    assert result.metrics["F1 Score"] == 1.0
    assert result.misclassified_samples.empty


def test_false_positive_is_detected() -> None:
    data = _make_data(
        [
            {"id": "1", "input": "safe", "label": "Safe", "prediction": "Unsafe"},
            {"id": "2", "input": "unsafe", "label": "Unsafe", "prediction": "Unsafe"},
        ]
    )

    result = calculate_metrics(data)

    assert result.confusion_matrix["FP"] == 1
    assert result.metrics["FPR"] == 1.0
    assert result.misclassified_samples.loc[0, "error_type"] == "False Positive"


def test_false_negative_is_detected() -> None:
    data = _make_data(
        [
            {"id": "1", "input": "safe", "label": "Safe", "prediction": "Safe"},
            {"id": "2", "input": "unsafe", "label": "Unsafe", "prediction": "Safe"},
        ]
    )

    result = calculate_metrics(data)

    assert result.confusion_matrix["FN"] == 1
    assert result.metrics["FNR"] == 1.0
    assert result.misclassified_samples.loc[0, "error_type"] == "False Negative"


def test_controversial_maps_to_unsafe() -> None:
    data = _make_data(
        [
            {"id": "1", "input": "topic", "label": "Controversial", "prediction": "Unsafe"},
            {"id": "2", "input": "safe topic", "label": "Safe", "prediction": "Controversial"},
        ]
    )

    result = calculate_metrics(data)

    assert result.raw_label_counts["Controversial"] == 1
    assert result.confusion_matrix == {"TP": 1, "TN": 0, "FP": 1, "FN": 0}
    assert result.misclassified_samples.loc[0, "error_type"] == "False Positive"


def test_zero_denominators_do_not_crash() -> None:
    data = _make_data(
        [
            {"id": "1", "input": "safe", "label": "Safe", "prediction": "Safe"},
            {"id": "2", "input": "safe again", "label": "Safe", "prediction": "Safe"},
        ]
    )

    result = calculate_metrics(data)

    assert result.metrics["Accuracy"] == 1.0
    assert result.metrics["Precision"] == 0.0
    assert result.metrics["Recall"] == 0.0
    assert result.metrics["F1 Score"] == 0.0
    assert result.metrics["FNR"] == 0.0
