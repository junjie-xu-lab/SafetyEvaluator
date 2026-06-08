"""Tests for SafetyEvaluator CSV loading."""

from io import BytesIO

import pandas as pd
import pytest

from safetyevaluator.loader import load_evaluation_csv, read_evaluation_excel, read_evaluation_text


def _csv_bytes(text: str) -> BytesIO:
    return BytesIO(text.encode("utf-8"))


def _xlsx_bytes(data: pd.DataFrame) -> BytesIO:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        data.to_excel(writer, index=False)
    output.seek(0)
    return output


def test_loader_detects_default_and_named_prediction_columns() -> None:
    csv = """id,input,label,prediction,prediction_strict
1,hello,safe,unsafe,safe
"""

    result = load_evaluation_csv(_csv_bytes(csv))

    assert result.prediction_columns == ["prediction", "prediction_strict"]
    assert result.data.loc[0, "label"] == "Safe"
    assert result.data.loc[0, "prediction"] == "Unsafe"
    assert result.data.loc[0, "prediction_strict"] == "Safe"


def test_loader_requires_at_least_one_prediction_column() -> None:
    csv = """id,input,label
1,hello,Safe
"""

    try:
        load_evaluation_csv(_csv_bytes(csv))
    except ValueError as exc:
        assert "Missing prediction column" in str(exc)
    else:
        raise AssertionError("Expected a ValueError for missing prediction columns")


def test_loader_supports_custom_column_mapping_and_manual_detector_columns() -> None:
    csv = """sample_id,prompt,gold,baseline_guard,strict_guard
1,hello,benign,harmful,benign
2,attack,harmful,harmful,harmful
"""

    result = load_evaluation_csv(
        _csv_bytes(csv),
        column_mapping={"id": "sample_id", "input": "prompt", "label": "gold"},
        prediction_columns=["baseline_guard", "strict_guard"],
        label_mapping={"benign": "Safe", "harmful": "Unsafe"},
    )

    assert result.prediction_columns == ["baseline_guard", "strict_guard"]
    assert result.data.loc[0, "id"] == "1"
    assert result.data.loc[0, "input"] == "hello"
    assert result.data.loc[0, "label"] == "Safe"
    assert result.data.loc[0, "baseline_guard"] == "Unsafe"
    assert result.data.loc[0, "strict_guard"] == "Safe"


def test_loader_supports_numeric_label_aliases() -> None:
    csv = """id,input,label,detector_a
1,hello,0,1
2,attack,1,1
"""

    result = load_evaluation_csv(
        _csv_bytes(csv),
        prediction_columns=["detector_a"],
        label_mapping={"0": "Safe", "1": "Unsafe"},
    )

    assert result.data.loc[0, "label"] == "Safe"
    assert result.data.loc[0, "detector_a"] == "Unsafe"
    assert result.data.loc[1, "label"] == "Unsafe"


def test_loader_reads_pasted_csv_and_tsv_text() -> None:
    csv_data = read_evaluation_text("id,input,label,prediction\n1,hello,Safe,Safe\n")
    tsv_data = read_evaluation_text("id\tinput\tlabel\tprediction\n1\thello\tSafe\tSafe\n")

    assert list(csv_data.columns) == ["id", "input", "label", "prediction"]
    assert list(tsv_data.columns) == ["id", "input", "label", "prediction"]
    assert tsv_data.loc[0, "input"] == "hello"


def test_loader_reads_excel_workbook() -> None:
    pytest.importorskip("openpyxl")

    source = pd.DataFrame(
        [
            {"id": "1", "input": "hello", "label": "Safe", "prediction": "Safe"},
        ]
    )

    result = read_evaluation_excel(_xlsx_bytes(source))

    assert list(result.columns) == ["id", "input", "label", "prediction"]
    assert result.loc[0, "label"] == "Safe"
