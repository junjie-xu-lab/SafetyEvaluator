"""CSV loading and validation helpers for SafetyEvaluator."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import IO

import pandas as pd


REQUIRED_COLUMNS = ["id", "input", "label"]
OPTIONAL_COLUMNS = ["source", "category"]
DEFAULT_PREDICTION_COLUMN = "prediction"
PREDICTION_COLUMN_PREFIX = "prediction_"
STANDARD_COLUMNS = REQUIRED_COLUMNS + [DEFAULT_PREDICTION_COLUMN] + OPTIONAL_COLUMNS
SUPPORTED_LABELS = {"safe": "Safe", "unsafe": "Unsafe", "controversial": "Controversial"}
MAPPABLE_COLUMNS = REQUIRED_COLUMNS + OPTIONAL_COLUMNS


@dataclass
class CsvLoadResult:
    """Container for a loaded CSV and validation metadata."""

    data: pd.DataFrame
    missing_optional_columns: list[str]
    prediction_columns: list[str]
    invalid_labels: pd.DataFrame


def normalize_label(value: object, label_mapping: Mapping[str, str] | None = None) -> str | None:
    """Normalize a safety label to its canonical form.

    Returns None when the label is not supported.
    """

    text = "" if value is None else str(value).strip()
    lookup = _build_label_lookup(label_mapping)
    return lookup.get(text.lower())


def read_evaluation_csv(file: str | Path | IO[bytes]) -> pd.DataFrame:
    """Read a SafetyEvaluator CSV file without validating required fields."""

    data = pd.read_csv(file, encoding="utf-8-sig", dtype=str).fillna("")

    data.columns = [str(column).strip().lstrip("\ufeff") for column in data.columns]
    return data


def read_evaluation_excel(file: str | Path | IO[bytes]) -> pd.DataFrame:
    """Read the first sheet from an Excel workbook without validating required fields."""

    data = pd.read_excel(file, dtype=str).fillna("")
    data.columns = [str(column).strip().lstrip("\ufeff") for column in data.columns]
    return data


def read_evaluation_text(text: str) -> pd.DataFrame:
    """Read pasted CSV or TSV text without validating required fields."""

    if not text.strip():
        raise ValueError("Pasted data is empty.")

    attempts = [
        {"sep": None, "engine": "python"},
        {"sep": "\t"},
        {"sep": ","},
    ]
    last_error: Exception | None = None
    for options in attempts:
        try:
            data = pd.read_csv(StringIO(text), dtype=str, **options).fillna("")
            data.columns = [str(column).strip().lstrip("\ufeff") for column in data.columns]
            if len(data.columns) > 1:
                return data
        except Exception as exc:
            last_error = exc

    if last_error is not None:
        raise ValueError(f"Could not parse pasted data: {last_error}") from last_error
    raise ValueError("Could not parse pasted data as CSV or TSV.")


def read_evaluation_file(file: str | Path | IO[bytes], filename: str | None = None) -> pd.DataFrame:
    """Read an uploaded evaluation file by extension."""

    source_name = filename or getattr(file, "name", "") or str(file)
    suffix = Path(source_name).suffix.lower()
    if suffix == ".xlsx":
        return read_evaluation_excel(file)
    if suffix == ".csv":
        return read_evaluation_csv(file)
    raise ValueError("Unsupported file type. Upload a .csv or .xlsx file.")


def load_evaluation_csv(
    file: str | Path | IO[bytes],
    column_mapping: Mapping[str, str | None] | None = None,
    prediction_columns: list[str] | None = None,
    label_mapping: Mapping[str, str] | None = None,
) -> CsvLoadResult:
    """Read and validate a SafetyEvaluator CSV file.

    Required columns are checked strictly. Optional columns are added as empty
    strings when absent. Labels are normalized in a case-insensitive way.
    """

    data = read_evaluation_csv(file)
    return load_evaluation_data(
        data,
        column_mapping=column_mapping,
        prediction_columns=prediction_columns,
        label_mapping=label_mapping,
    )


def load_evaluation_data(
    data: pd.DataFrame,
    column_mapping: Mapping[str, str | None] | None = None,
    prediction_columns: list[str] | None = None,
    label_mapping: Mapping[str, str] | None = None,
) -> CsvLoadResult:
    """Validate an evaluation table with optional column and label mappings."""

    data = data.copy().fillna("")
    data.columns = [str(column).strip().lstrip("\ufeff") for column in data.columns]
    column_mapping = column_mapping or {}
    _validate_column_mapping(data, column_mapping)

    missing_required = [
        column
        for column in REQUIRED_COLUMNS
        if not _resolve_mapped_column(data, column_mapping, column)
    ]
    if missing_required:
        joined = ", ".join(missing_required)
        raise ValueError(f"Missing required column(s): {joined}")

    selected_prediction_columns = prediction_columns if prediction_columns is not None else get_prediction_columns(data)
    _validate_prediction_columns(data, selected_prediction_columns)
    if not selected_prediction_columns:
        raise ValueError("Missing prediction column(s): add 'prediction' or one or more 'prediction_*' columns")

    data, missing_optional = _apply_column_mapping(data, column_mapping)

    invalid_rows: list[dict[str, object]] = []
    for label_column in ["label", *selected_prediction_columns]:
        normalized_values: list[str] = []
        for row_index, value in data[label_column].items():
            normalized = normalize_label(value, label_mapping)
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

    standard_columns = REQUIRED_COLUMNS + selected_prediction_columns + OPTIONAL_COLUMNS
    ordered_columns = standard_columns + [column for column in data.columns if column not in standard_columns]
    data = data[ordered_columns]
    invalid_labels = pd.DataFrame(invalid_rows, columns=["csv_row", "column", "value"])

    return CsvLoadResult(
        data=data,
        missing_optional_columns=missing_optional,
        prediction_columns=selected_prediction_columns,
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


def _build_label_lookup(label_mapping: Mapping[str, str] | None = None) -> dict[str, str]:
    """Build a case-insensitive lookup for canonical labels and aliases."""

    lookup = dict(SUPPORTED_LABELS)
    for alias, canonical_label in (label_mapping or {}).items():
        alias_text = str(alias).strip()
        normalized_canonical = SUPPORTED_LABELS.get(str(canonical_label).strip().lower())
        if not alias_text or normalized_canonical is None:
            continue
        lookup[alias_text.lower()] = normalized_canonical
    return lookup


def _validate_column_mapping(data: pd.DataFrame, column_mapping: Mapping[str, str | None]) -> None:
    """Validate that configured source columns exist."""

    unknown_targets = [column for column in column_mapping if column not in MAPPABLE_COLUMNS]
    if unknown_targets:
        joined = ", ".join(unknown_targets)
        raise ValueError(f"Unsupported mapped column(s): {joined}")

    missing_sources = [
        str(source_column)
        for source_column in column_mapping.values()
        if source_column and source_column not in data.columns
    ]
    if missing_sources:
        joined = ", ".join(missing_sources)
        raise ValueError(f"Mapped source column(s) not found: {joined}")


def _validate_prediction_columns(data: pd.DataFrame, prediction_columns: list[str]) -> None:
    """Validate manually selected detector columns."""

    missing_prediction_columns = [column for column in prediction_columns if column not in data.columns]
    if missing_prediction_columns:
        joined = ", ".join(missing_prediction_columns)
        raise ValueError(f"Prediction column(s) not found: {joined}")


def _apply_column_mapping(
    data: pd.DataFrame,
    column_mapping: Mapping[str, str | None],
) -> tuple[pd.DataFrame, list[str]]:
    """Copy mapped source columns into the standard SafetyEvaluator names."""

    data = data.copy()
    for column in REQUIRED_COLUMNS:
        source_column = _resolve_mapped_column(data, column_mapping, column)
        if source_column and source_column != column:
            data[column] = data[source_column]

    missing_optional: list[str] = []
    for column in OPTIONAL_COLUMNS:
        source_column = _resolve_mapped_column(data, column_mapping, column)
        if source_column:
            if source_column != column:
                data[column] = data[source_column]
        else:
            data[column] = ""
            missing_optional.append(column)

    return data, missing_optional


def _resolve_mapped_column(
    data: pd.DataFrame,
    column_mapping: Mapping[str, str | None],
    target_column: str,
) -> str | None:
    """Resolve a standard column to either a configured or default source column."""

    mapped_column = column_mapping.get(target_column)
    if mapped_column:
        return str(mapped_column)
    if target_column in data.columns:
        return target_column
    return None
