"""Markdown report generation for SafetyEvaluator."""

from __future__ import annotations

import pandas as pd

from safetyevaluator.metrics import DetectorComparisonResult, EvaluationResult


def generate_markdown_report(
    evaluation: EvaluationResult,
    missing_optional_columns: list[str] | None = None,
    max_samples: int = 100,
) -> str:
    """Generate a Markdown report for the evaluation result."""

    missing_optional_columns = missing_optional_columns or []
    lines = ["# Safety Evaluation Report", ""]
    _append_dataset_summary(lines, evaluation, missing_optional_columns)
    _append_evaluation_sections(lines, evaluation, max_samples=max_samples, heading_level=2)

    return "\n".join(lines)


def generate_multi_detector_markdown_report(
    comparison: DetectorComparisonResult,
    missing_optional_columns: list[str] | None = None,
    max_samples: int = 100,
) -> str:
    """Generate a Markdown report for one or more detector evaluations."""

    missing_optional_columns = missing_optional_columns or []
    first_evaluation = next(iter(comparison.evaluations.values()))
    lines = ["# Safety Evaluation Report", ""]
    _append_dataset_summary(lines, first_evaluation, missing_optional_columns)

    lines.extend(
        [
            "",
            "## Detector Comparison",
            "",
        ]
    )
    lines.extend(_dataframe_to_markdown(comparison.comparison_table))

    for evaluation in comparison.evaluations.values():
        lines.extend(
            [
                "",
                f"## Detector: {evaluation.detector_name}",
                "",
                f"- Prediction column: `{evaluation.prediction_column}`",
            ]
        )
        _append_evaluation_sections(lines, evaluation, max_samples=max_samples, heading_level=3)

    return "\n".join(lines)


def _append_dataset_summary(
    lines: list[str],
    evaluation: EvaluationResult,
    missing_optional_columns: list[str],
) -> None:
    """Append shared dataset summary sections."""

    counts = evaluation.raw_label_counts

    lines.extend(
        [
        "## 1. Dataset Summary",
        "",
        f"- Total samples: {evaluation.total_samples}",
        f"- Safe: {counts.get('Safe', 0)}",
        f"- Unsafe: {counts.get('Unsafe', 0)}",
        f"- Controversial: {counts.get('Controversial', 0)}",
        ]
    )

    if missing_optional_columns:
        lines.extend(
            [
                f"- Missing optional columns filled with empty strings: {', '.join(missing_optional_columns)}",
            ]
        )

    lines.extend(
        [
            "",
            "## 2. Binary Mapping Rule",
            "",
            "- Safe remains Safe.",
            "- Unsafe remains Unsafe.",
            "- Controversial is counted as Unsafe.",
        ]
    )


def _append_evaluation_sections(
    lines: list[str],
    evaluation: EvaluationResult,
    max_samples: int,
    heading_level: int,
) -> None:
    """Append metrics, confusion matrix, group metrics, and errors."""

    heading = "#" * heading_level
    confusion = evaluation.confusion_matrix
    metrics = evaluation.metrics
    errors = evaluation.misclassified_samples
    false_positive_count = int((errors["error_type"] == "False Positive").sum()) if not errors.empty else 0
    false_negative_count = int((errors["error_type"] == "False Negative").sum()) if not errors.empty else 0

    lines.extend(
        [
            "",
            f"{heading} Metrics",
            "",
            "| Metric | Value |",
            "| --- | ---: |",
        ]
    )

    for metric_name in ["Accuracy", "Precision", "Recall", "F1 Score", "FPR", "FNR"]:
        lines.append(f"| {metric_name} | {_format_metric(metrics[metric_name])} |")

    lines.extend(
        [
            "",
            f"{heading} Confusion Matrix",
            "",
            "| Actual \\ Predicted | Safe | Unsafe |",
            "| --- | ---: | ---: |",
            f"| Safe | {confusion['TN']} | {confusion['FP']} |",
            f"| Unsafe | {confusion['FN']} | {confusion['TP']} |",
            "",
            f"{heading} Group Analysis",
            "",
        ]
    )

    if evaluation.group_metrics:
        for group_column, group_table in evaluation.group_metrics.items():
            lines.extend(
                [
                    f"#### By `{group_column}`",
                    "",
                ]
            )
            lines.extend(_dataframe_to_markdown(group_table))
            lines.append("")
    else:
        lines.append("No group columns were available.")

    lines.extend(
        [
            "",
            f"{heading} Error Analysis",
            "",
            f"- False Positive count: {false_positive_count}",
            f"- False Negative count: {false_negative_count}",
            "",
            f"{heading} Misclassified Samples",
            "",
        ]
    )

    if errors.empty:
        lines.append("No misclassified samples were found.")
    else:
        report_errors = errors.head(max_samples)
        if len(errors) > max_samples:
            lines.append(f"Only the first {max_samples} misclassified samples are shown.")
            lines.append("")
        lines.extend(_dataframe_to_markdown(report_errors))

    lines.extend(
        [
            "",
            f"{heading} Notes",
            "",
            "Controversial samples are counted as Unsafe in binary evaluation.",
        ]
    )


def _format_metric(value: float) -> str:
    """Format a metric with four decimal places."""

    return f"{value:.4f}"


def _dataframe_to_markdown(data: pd.DataFrame) -> list[str]:
    """Convert a DataFrame to a simple Markdown table without extra dependencies."""

    if data.empty:
        return []

    columns = list(data.columns)
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join(["---"] * len(columns)) + " |",
    ]

    for _, row in data.iterrows():
        values = [_escape_markdown_cell(row[column]) for column in columns]
        lines.append("| " + " | ".join(values) + " |")

    return lines


def _escape_markdown_cell(value: object) -> str:
    """Escape basic Markdown table separators in cell values."""

    if isinstance(value, float):
        text = _format_metric(value)
    else:
        text = "" if value is None else str(value)
    return text.replace("|", "\\|").replace("\n", " ").replace("\r", " ")
