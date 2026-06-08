"""CSV loading and validation helpers for SafetyEvaluator."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import IO

import pandas as pd


REQUIRED_COLUMNS = ["id", "input", "label"]
OPTIONAL_COLUMNS = ["source", "category"]
DEFAULT_PREDICTION_COLUMN = "prediction"
PREDICTION_COLUMN_PREFIX = "prediction_"
STANDARD_COLUMNS = REQUIRED_COLUMNS + [DEFAULT_PREDICTION_COLUMN] + OPTIONAL_COLUMNS
SUPPORTED_LABELS = {"safe": "Safe", "unsafe": "Unsafe", "controversial": "Controversial"}


@dataclass
class CsvLoadResult:
    """Container for a loaded CSV and validation metadata."""

    data: pd.DataFrame
    missing_optional_columns: list[str]
    prediction_columns: list[str]
    invalid_labels: pd.DataFrame


def normalize_label(value: object) -> str | None:
    """Normalize a safety label to its canonical form.

    Returns None when the label is not supported.
    """

    text = "" if value is None else str(value).strip()
    return SUPPORTED_LABELS.get(text.lower())


def load_evaluation_csv(file: str | Path | IO[bytes]) -> CsvLoadResult:
    """Read and validate a SafetyEvaluator CSV file.

    Required columns are checked strictly. Optional columns are added as empty
    strings when absent. Labels are normalized in a case-insensitive way.
    """

    try:
        data = pd.read_csv(file, encoding="utf-8-sig", dtype=str).fillna("")
    except UnicodeDecodeError:
        data = pd.read_csv(file, encoding="utf-8", dtype=str).fillna("")

    data.columns = [str(column).strip().lstrip("\ufeff") for column in data.columns]

    missing_required = [column for column in REQUIRED_COLUMNS if column not in data.columns]
    if missing_required:
        joined = ", ".join(missing_required)
        raise ValueError(f"Missing required column(s): {joined}")

    prediction_columns = get_prediction_columns(data)
    if not prediction_columns:
        raise ValueError("Missing prediction column(s): add 'prediction' or one or more 'prediction_*' columns")

    missing_optional = [column for column in OPTIONAL_COLUMNS if column not in data.columns]
    for column in missing_optional:
        data[column] = ""

    invalid_rows: list[dict[str, object]] = []
    for label_column in ["label", *prediction_columns]:
        normalized_values: list[str] = []
        for row_index, value in data[label_column].items():
            normalized = normalize_label(value)
            if normalized is None:
                invalid_rows.append(
                    {
                        "csv_row": int(row_index) + 2,
                        "column": label_column,
                        "value": str(value).strip(),
                    }
                )
                normalized_values.append(str(value).strip())
            else:
                normalized_values.append(normalized)
        data[label_column] = normalized_values

    standard_columns = REQUIRED_COLUMNS + prediction_columns + OPTIONAL_COLUMNS
    ordered_columns = standard_columns + [column for column in data.columns if column not in standard_columns]
    data = data[ordered_columns]
    invalid_labels = pd.DataFrame(invalid_rows, columns=["csv_row", "column", "value"])

    return CsvLoadResult(
        data=data,
        missing_optional_columns=missing_optional,
        prediction_columns=prediction_columns,
        invalid_labels=invalid_labels,
    )


def get_prediction_columns(data: pd.DataFrame) -> list[str]:
    """Return supported detector prediction columns in display order."""

    columns = list(data.columns)
    prediction_columns: list[str] = []
    if DEFAULT_PREDICTION_COLUMN in columns:
        prediction_columns.append(DEFAULT_PREDICTION_COLUMN)

    prediction_columns.extend(
        column
        for column in columns
        if column.startswith(PREDICTION_COLUMN_PREFIX) and column != DEFAULT_PREDICTION_COLUMN
    )
    return prediction_columns
