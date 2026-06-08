"""Metric calculation and error analysis for safety classification results."""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from safetyevaluator.loader import DEFAULT_PREDICTION_COLUMN, get_prediction_columns


NEGATIVE_CLASS = "Safe"
POSITIVE_CLASS = "Unsafe"
GROUP_COLUMNS = ["category", "source"]


@dataclass
class EvaluationResult:
    """Structured result returned by the evaluator."""

    detector_name: str
    prediction_column: str
    total_samples: int
    raw_label_counts: dict[str, int]
    confusion_matrix: dict[str, int]
    metrics: dict[str, float]
    misclassified_samples: pd.DataFrame
    group_metrics: dict[str, pd.DataFrame] = field(default_factory=dict)


@dataclass
class DetectorComparisonResult:
    """Evaluation result for one or more detector prediction columns."""

    prediction_columns: list[str]
    evaluations: dict[str, EvaluationResult]
    comparison_table: pd.DataFrame


def safe_divide(numerator: float, denominator: float) -> float:
    """Divide two numbers and return 0 when the denominator is 0."""

    if denominator == 0:
        return 0.0
    return numerator / denominator


def to_binary_label(label: str) -> str:
    """Map labels to the binary evaluation space.

    Controversial samples are counted as Unsafe in binary evaluation.
    """

    return NEGATIVE_CLASS if label == NEGATIVE_CLASS else POSITIVE_CLASS


def calculate_metrics(
    data: pd.DataFrame,
    prediction_column: str = DEFAULT_PREDICTION_COLUMN,
    group_by_columns: list[str] | None = None,
) -> EvaluationResult:
    """Calculate binary safety metrics and identify misclassified samples."""

    if prediction_column not in data.columns:
        raise ValueError(f"Missing prediction column: {prediction_column}")

    working = data.copy()
    working["label_binary"] = working["label"].map(to_binary_label)
    working["prediction_binary"] = working[prediction_column].map(to_binary_label)

    tp = int(((working["label_binary"] == POSITIVE_CLASS) & (working["prediction_binary"] == POSITIVE_CLASS)).sum())
    tn = int(((working["label_binary"] == NEGATIVE_CLASS) & (working["prediction_binary"] == NEGATIVE_CLASS)).sum())
    fp = int(((working["label_binary"] == NEGATIVE_CLASS) & (working["prediction_binary"] == POSITIVE_CLASS)).sum())
    fn = int(((working["label_binary"] == POSITIVE_CLASS) & (working["prediction_binary"] == NEGATIVE_CLASS)).sum())
    total = int(len(working))

    precision = safe_divide(tp, tp + fp)
    recall = safe_divide(tp, tp + fn)
    f1 = safe_divide(2 * precision * recall, precision + recall)

    metrics = {
        "Accuracy": safe_divide(tp + tn, total),
        "Precision": precision,
        "Recall": recall,
        "F1 Score": f1,
        "FPR": safe_divide(fp, fp + tn),
        "FNR": safe_divide(fn, fn + tp),
    }

    raw_label_counts = {
        "Safe": int((working["label"] == "Safe").sum()),
        "Unsafe": int((working["label"] == "Unsafe").sum()),
        "Controversial": int((working["label"] == "Controversial").sum()),
    }

    errors = working[working["label_binary"] != working["prediction_binary"]].copy()
    errors["error_type"] = errors.apply(_classify_error_type, axis=1)
    errors["prediction"] = errors[prediction_column]

    display_columns = ["id", "input", "label", "prediction", "error_type"]
    for optional_column in ["source", "category"]:
        if optional_column in errors.columns:
            display_columns.append(optional_column)
    misclassified_samples = errors[display_columns].reset_index(drop=True)
    selected_group_columns = GROUP_COLUMNS if group_by_columns is None else group_by_columns
    group_metrics = calculate_group_metrics(data, prediction_column, selected_group_columns)

    return EvaluationResult(
        detector_name=_detector_name(prediction_column),
        prediction_column=prediction_column,
        total_samples=total,
        raw_label_counts=raw_label_counts,
        confusion_matrix={"TP": tp, "TN": tn, "FP": fp, "FN": fn},
        metrics=metrics,
        misclassified_samples=misclassified_samples,
        group_metrics=group_metrics,
    )


def calculate_detector_comparison(
    data: pd.DataFrame,
    prediction_columns: list[str] | None = None,
    group_by_columns: list[str] | None = None,
) -> DetectorComparisonResult:
    """Calculate metrics for all requested detector prediction columns."""

    selected_columns = prediction_columns or get_prediction_columns(data)
    if not selected_columns:
        raise ValueError("No prediction columns were found.")

    evaluations = {
        prediction_column: calculate_metrics(data, prediction_column, group_by_columns)
        for prediction_column in selected_columns
    }
    comparison_table = _build_comparison_table(evaluations)

    return DetectorComparisonResult(
        prediction_columns=selected_columns,
        evaluations=evaluations,
        comparison_table=comparison_table,
    )


def calculate_group_metrics(
    data: pd.DataFrame,
    prediction_column: str,
    group_by_columns: list[str],
) -> dict[str, pd.DataFrame]:
    """Calculate per-group metrics for available grouping columns."""

    group_results: dict[str, pd.DataFrame] = {}
    for group_column in group_by_columns:
        if group_column not in data.columns:
            continue

        rows: list[dict[str, object]] = []
        grouped = data.copy()
        grouped[group_column] = grouped[group_column].map(_format_group_value)
        for group_value, group_data in grouped.groupby(group_column, dropna=False, sort=True):
            result = calculate_metrics(group_data, prediction_column, group_by_columns=[])
            confusion = result.confusion_matrix
            rows.append(
                {
                    group_column: group_value,
                    "Samples": result.total_samples,
                    "Safe": result.raw_label_counts.get("Safe", 0),
                    "Unsafe": result.raw_label_counts.get("Unsafe", 0),
                    "Controversial": result.raw_label_counts.get("Controversial", 0),
                    "Accuracy": result.metrics["Accuracy"],
                    "Precision": result.metrics["Precision"],
                    "Recall": result.metrics["Recall"],
                    "F1 Score": result.metrics["F1 Score"],
                    "FPR": result.metrics["FPR"],
                    "FNR": result.metrics["FNR"],
                    "TP": confusion["TP"],
                    "TN": confusion["TN"],
                    "FP": confusion["FP"],
                    "FN": confusion["FN"],
                }
            )

        table = pd.DataFrame(rows)
        if not table.empty:
            table = table.sort_values(["FNR", "FPR", "Samples"], ascending=[False, False, False]).reset_index(
                drop=True
            )
        group_results[group_column] = table

    return group_results


def _classify_error_type(row: pd.Series) -> str:
    """Return a human-readable error type for a misclassified row."""

    if row["label_binary"] == NEGATIVE_CLASS and row["prediction_binary"] == POSITIVE_CLASS:
        return "False Positive"
    return "False Negative"


def _build_comparison_table(evaluations: dict[str, EvaluationResult]) -> pd.DataFrame:
    """Build a compact detector comparison table."""

    rows: list[dict[str, object]] = []
    for prediction_column, result in evaluations.items():
        confusion = result.confusion_matrix
        rows.append(
            {
                "Detector": result.detector_name,
                "Prediction Column": prediction_column,
                "Samples": result.total_samples,
                "Accuracy": result.metrics["Accuracy"],
                "Precision": result.metrics["Precision"],
                "Recall": result.metrics["Recall"],
                "F1 Score": result.metrics["F1 Score"],
                "FPR": result.metrics["FPR"],
                "FNR": result.metrics["FNR"],
                "TP": confusion["TP"],
                "TN": confusion["TN"],
                "FP": confusion["FP"],
                "FN": confusion["FN"],
            }
        )

    return pd.DataFrame(rows).sort_values(["F1 Score", "FNR", "FPR"], ascending=[False, True, True]).reset_index(
        drop=True
    )


def _detector_name(prediction_column: str) -> str:
    """Create a readable detector name from a prediction column."""

    if prediction_column == DEFAULT_PREDICTION_COLUMN:
        return "Default"
    return prediction_column.removeprefix("prediction_").replace("_", " ").title()


def _format_group_value(value: object) -> str:
    """Return a display value for group labels."""

    text = "" if value is None else str(value).strip()
    return text or "Unspecified"
