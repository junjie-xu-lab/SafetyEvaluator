"""Tests for SafetyEvaluator report generation."""

from io import BytesIO

import pandas as pd
import pytest

from safetyevaluator.metrics import calculate_detector_comparison
from safetyevaluator.report import build_misclassified_samples_table, generate_multi_detector_excel_report


def test_excel_report_contains_expected_sheets() -> None:
    pytest.importorskip("openpyxl")

    data = pd.DataFrame(
        [
            {
                "id": "1",
                "input": "safe",
                "label": "Safe",
                "prediction_baseline": "Unsafe",
                "prediction_strict": "Safe",
                "source": "demo",
                "category": "normal",
            },
            {
                "id": "2",
                "input": "unsafe",
                "label": "Unsafe",
                "prediction_baseline": "Unsafe",
                "prediction_strict": "Unsafe",
                "source": "demo",
                "category": "cyber",
            },
        ]
    )
    comparison = calculate_detector_comparison(data, ["prediction_baseline", "prediction_strict"])

    report_bytes = generate_multi_detector_excel_report(comparison)
    workbook = pd.ExcelFile(BytesIO(report_bytes))

    assert workbook.sheet_names == [
        "Summary",
        "Detector Comparison",
        "Metrics",
        "Confusion Matrix",
        "Group Analysis",
        "Misclassified Samples",
    ]


def test_combined_misclassified_samples_include_detector_context() -> None:
    data = pd.DataFrame(
        [
            {"id": "1", "input": "safe", "label": "Safe", "prediction_a": "Unsafe", "prediction_b": "Safe"},
            {"id": "2", "input": "unsafe", "label": "Unsafe", "prediction_a": "Unsafe", "prediction_b": "Safe"},
        ]
    )
    comparison = calculate_detector_comparison(data, ["prediction_a", "prediction_b"])

    errors = build_misclassified_samples_table(comparison)

    assert list(errors["Prediction Column"]) == ["prediction_a", "prediction_b"]
    assert set(errors["error_type"]) == {"False Positive", "False Negative"}
