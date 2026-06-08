"""Tests for SafetyEvaluator CSV loading."""

from io import BytesIO

from safetyevaluator.loader import load_evaluation_csv


def _csv_bytes(text: str) -> BytesIO:
    return BytesIO(text.encode("utf-8"))


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
