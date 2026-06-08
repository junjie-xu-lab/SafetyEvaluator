"""Report generation for SafetyEvaluator."""

from __future__ import annotations

from html import escape
from io import BytesIO
from xml.sax.saxutils import escape as escape_xml

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


def generate_multi_detector_excel_report(
    comparison: DetectorComparisonResult,
    missing_optional_columns: list[str] | None = None,
    max_samples: int = 1000,
) -> bytes:
    """Generate an Excel workbook report for one or more detector evaluations."""

    missing_optional_columns = missing_optional_columns or []
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        _build_summary_table(comparison, missing_optional_columns).to_excel(
            writer,
            sheet_name="Summary",
            index=False,
        )
        comparison.comparison_table.to_excel(writer, sheet_name="Detector Comparison", index=False)
        _build_metrics_table(comparison).to_excel(writer, sheet_name="Metrics", index=False)
        _build_confusion_matrix_table(comparison).to_excel(writer, sheet_name="Confusion Matrix", index=False)
        _build_group_analysis_table(comparison).to_excel(writer, sheet_name="Group Analysis", index=False)
        build_misclassified_samples_table(comparison, max_samples=max_samples).to_excel(
            writer,
            sheet_name="Misclassified Samples",
            index=False,
        )
        _format_excel_workbook(writer)

    return output.getvalue()


def generate_multi_detector_html_report(
    comparison: DetectorComparisonResult,
    missing_optional_columns: list[str] | None = None,
    max_samples: int = 100,
) -> str:
    """Generate a self-contained HTML report for one or more detector evaluations."""

    missing_optional_columns = missing_optional_columns or []
    first_evaluation = next(iter(comparison.evaluations.values()))
    counts = first_evaluation.raw_label_counts
    missing_note = ""
    if missing_optional_columns:
        missing_note = (
            "<li>Missing optional columns filled with empty strings: "
            + escape(", ".join(missing_optional_columns))
            + "</li>"
        )

    sections = [
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>Safety Evaluation Report</title>",
        "<style>",
        _html_report_css(),
        "</style>",
        "</head>",
        "<body>",
        "<main>",
        "<h1>Safety Evaluation Report</h1>",
        "<section>",
        "<h2>1. Dataset Summary</h2>",
        "<ul>",
        f"<li>Total samples: {first_evaluation.total_samples}</li>",
        f"<li>Safe: {counts.get('Safe', 0)}</li>",
        f"<li>Unsafe: {counts.get('Unsafe', 0)}</li>",
        f"<li>Controversial: {counts.get('Controversial', 0)}</li>",
        f"<li>Detector count: {len(comparison.evaluations)}</li>",
        missing_note,
        "</ul>",
        "</section>",
        "<section>",
        "<h2>2. Binary Mapping Rule</h2>",
        "<ul>",
        "<li>Safe remains Safe.</li>",
        "<li>Unsafe remains Unsafe.</li>",
        "<li>Controversial is counted as Unsafe.</li>",
        "</ul>",
        "</section>",
        "<section>",
        "<h2>Detector Comparison</h2>",
        _dataframe_to_html(comparison.comparison_table),
        "</section>",
    ]

    for evaluation in comparison.evaluations.values():
        sections.extend(_evaluation_to_html_sections(evaluation, max_samples=max_samples))

    sections.extend(["</main>", "</body>", "</html>"])
    return "\n".join(section for section in sections if section != "")


def generate_multi_detector_pdf_report(
    comparison: DetectorComparisonResult,
    missing_optional_columns: list[str] | None = None,
    max_samples: int = 100,
) -> bytes:
    """Generate a PDF report for one or more detector evaluations."""

    try:
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "PDF report generation requires reportlab. Install dependencies with: "
            "python -m pip install -r requirements.txt"
        ) from exc

    missing_optional_columns = missing_optional_columns or []
    first_evaluation = next(iter(comparison.evaluations.values()))
    counts = first_evaluation.raw_label_counts
    output = BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=landscape(A4),
        rightMargin=0.45 * inch,
        leftMargin=0.45 * inch,
        topMargin=0.45 * inch,
        bottomMargin=0.45 * inch,
        title="Safety Evaluation Report",
    )
    styles = getSampleStyleSheet()
    elements = [
        Paragraph("Safety Evaluation Report", styles["Title"]),
        Spacer(1, 10),
        Paragraph("1. Dataset Summary", styles["Heading2"]),
        _pdf_key_value_table(
            [
                ("Total samples", first_evaluation.total_samples),
                ("Safe", counts.get("Safe", 0)),
                ("Unsafe", counts.get("Unsafe", 0)),
                ("Controversial", counts.get("Controversial", 0)),
                ("Detector count", len(comparison.evaluations)),
                (
                    "Missing optional columns filled with empty strings",
                    ", ".join(missing_optional_columns) if missing_optional_columns else "None",
                ),
            ],
            styles,
        ),
        Spacer(1, 10),
        Paragraph("2. Binary Mapping Rule", styles["Heading2"]),
        Paragraph("Safe stays Safe. Unsafe and Controversial count as Unsafe.", styles["BodyText"]),
        Spacer(1, 10),
        Paragraph("Detector Comparison", styles["Heading2"]),
        _dataframe_to_pdf_table(comparison.comparison_table, styles),
    ]

    for evaluation in comparison.evaluations.values():
        elements.extend(_evaluation_to_pdf_elements(evaluation, styles, max_samples=max_samples))

    document.build(elements)
    return output.getvalue()


def build_misclassified_samples_table(
    comparison: DetectorComparisonResult,
    max_samples: int | None = None,
) -> pd.DataFrame:
    """Return one combined misclassified-sample table across detectors."""

    frames: list[pd.DataFrame] = []
    for evaluation in comparison.evaluations.values():
        errors = evaluation.misclassified_samples.copy()
        if max_samples is not None:
            errors = errors.head(max_samples)
        if errors.empty:
            continue

        errors.insert(0, "Prediction Column", evaluation.prediction_column)
        errors.insert(0, "Detector", evaluation.detector_name)
        frames.append(errors)

    if frames:
        return pd.concat(frames, ignore_index=True)

    return pd.DataFrame(
        columns=[
            "Detector",
            "Prediction Column",
            "id",
            "input",
            "label",
            "prediction",
            "error_type",
            "source",
            "category",
        ]
    )


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


def _build_summary_table(
    comparison: DetectorComparisonResult,
    missing_optional_columns: list[str],
) -> pd.DataFrame:
    """Build a compact workbook summary table."""

    first_evaluation = next(iter(comparison.evaluations.values()))
    counts = first_evaluation.raw_label_counts
    rows = [
        {"Item": "Total samples", "Value": first_evaluation.total_samples},
        {"Item": "Safe", "Value": counts.get("Safe", 0)},
        {"Item": "Unsafe", "Value": counts.get("Unsafe", 0)},
        {"Item": "Controversial", "Value": counts.get("Controversial", 0)},
        {"Item": "Detector count", "Value": len(comparison.evaluations)},
        {"Item": "Binary mapping", "Value": "Safe stays Safe; Unsafe and Controversial count as Unsafe"},
    ]
    if missing_optional_columns:
        rows.append(
            {
                "Item": "Missing optional columns filled with empty strings",
                "Value": ", ".join(missing_optional_columns),
            }
        )
    return pd.DataFrame(rows)


def _build_metrics_table(comparison: DetectorComparisonResult) -> pd.DataFrame:
    """Build a long-form metrics table."""

    rows: list[dict[str, object]] = []
    for evaluation in comparison.evaluations.values():
        for metric_name, metric_value in evaluation.metrics.items():
            rows.append(
                {
                    "Detector": evaluation.detector_name,
                    "Prediction Column": evaluation.prediction_column,
                    "Metric": metric_name,
                    "Value": metric_value,
                }
            )
    return pd.DataFrame(rows)


def _build_confusion_matrix_table(comparison: DetectorComparisonResult) -> pd.DataFrame:
    """Build a long-form confusion matrix table."""

    rows: list[dict[str, object]] = []
    for evaluation in comparison.evaluations.values():
        confusion = evaluation.confusion_matrix
        rows.extend(
            [
                {
                    "Detector": evaluation.detector_name,
                    "Prediction Column": evaluation.prediction_column,
                    "Actual": "Safe",
                    "Predicted Safe": confusion["TN"],
                    "Predicted Unsafe": confusion["FP"],
                },
                {
                    "Detector": evaluation.detector_name,
                    "Prediction Column": evaluation.prediction_column,
                    "Actual": "Unsafe",
                    "Predicted Safe": confusion["FN"],
                    "Predicted Unsafe": confusion["TP"],
                },
            ]
        )
    return pd.DataFrame(rows)


def _build_group_analysis_table(comparison: DetectorComparisonResult) -> pd.DataFrame:
    """Build a combined group-analysis table."""

    frames: list[pd.DataFrame] = []
    for evaluation in comparison.evaluations.values():
        for group_column, group_table in evaluation.group_metrics.items():
            table = group_table.copy()
            table.insert(0, "Group Column", group_column)
            table.insert(0, "Prediction Column", evaluation.prediction_column)
            table.insert(0, "Detector", evaluation.detector_name)
            frames.append(table)

    if frames:
        return pd.concat(frames, ignore_index=True)
    return pd.DataFrame(columns=["Detector", "Prediction Column", "Group Column"])


def _format_excel_workbook(writer: pd.ExcelWriter) -> None:
    """Apply lightweight formatting to all workbook sheets."""

    from openpyxl.styles import Font, PatternFill

    workbook = writer.book
    for worksheet in workbook.worksheets:
        worksheet.freeze_panes = "A2"
        for cell in worksheet[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(fill_type="solid", fgColor="1F4E79")
        for column_cells in worksheet.columns:
            column_letter = column_cells[0].column_letter
            max_length = max(len(str(cell.value or "")) for cell in column_cells)
            worksheet.column_dimensions[column_letter].width = min(max(max_length + 2, 12), 60)


def _html_report_css() -> str:
    """Return compact CSS for the standalone HTML report."""

    return """
body {
    margin: 0;
    background: #f6f7f9;
    color: #1f2933;
    font-family: Arial, Helvetica, sans-serif;
    line-height: 1.45;
}
main {
    max-width: 1180px;
    margin: 0 auto;
    padding: 32px 24px 48px;
}
h1, h2, h3, h4 {
    color: #102a43;
}
section {
    margin: 22px 0;
    padding: 20px;
    background: #ffffff;
    border: 1px solid #d9e2ec;
    border-radius: 6px;
}
.table-wrap {
    overflow-x: auto;
}
table {
    width: 100%;
    border-collapse: collapse;
    margin: 12px 0;
    font-size: 14px;
}
th, td {
    border: 1px solid #d9e2ec;
    padding: 8px 10px;
    text-align: left;
    vertical-align: top;
}
th {
    background: #1f4e79;
    color: #ffffff;
}
tr:nth-child(even) td {
    background: #f8fafc;
}
.muted {
    color: #52606d;
}
""".strip()


def _evaluation_to_html_sections(evaluation: EvaluationResult, max_samples: int) -> list[str]:
    """Return HTML sections for one detector evaluation."""

    confusion = evaluation.confusion_matrix
    metrics_table = pd.DataFrame(
        [
            {"Metric": metric_name, "Value": _format_metric(evaluation.metrics[metric_name])}
            for metric_name in _metric_order()
        ]
    )
    confusion_table = pd.DataFrame(
        [
            {"Actual \\ Predicted": "Safe", "Safe": confusion["TN"], "Unsafe": confusion["FP"]},
            {"Actual \\ Predicted": "Unsafe", "Safe": confusion["FN"], "Unsafe": confusion["TP"]},
        ]
    )
    errors = evaluation.misclassified_samples
    false_positive_count = int((errors["error_type"] == "False Positive").sum()) if not errors.empty else 0
    false_negative_count = int((errors["error_type"] == "False Negative").sum()) if not errors.empty else 0

    sections = [
        "<section>",
        f"<h2>Detector: {escape(evaluation.detector_name)}</h2>",
        f'<p class="muted">Prediction column: <code>{escape(evaluation.prediction_column)}</code></p>',
        "<h3>Metrics</h3>",
        _dataframe_to_html(metrics_table),
        "<h3>Confusion Matrix</h3>",
        _dataframe_to_html(confusion_table),
        "<h3>Group Analysis</h3>",
    ]
    if evaluation.group_metrics:
        for group_column, group_table in evaluation.group_metrics.items():
            sections.extend([f"<h4>By <code>{escape(group_column)}</code></h4>", _dataframe_to_html(group_table)])
    else:
        sections.append('<p class="muted">No group columns were available.</p>')

    sections.extend(
        [
            "<h3>Error Analysis</h3>",
            "<ul>",
            f"<li>False Positive count: {false_positive_count}</li>",
            f"<li>False Negative count: {false_negative_count}</li>",
            "</ul>",
            "<h3>Misclassified Samples</h3>",
        ]
    )

    if errors.empty:
        sections.append('<p class="muted">No misclassified samples were found.</p>')
    else:
        report_errors = errors.head(max_samples)
        if len(errors) > max_samples:
            sections.append(f'<p class="muted">Only the first {max_samples} misclassified samples are shown.</p>')
        sections.append(_dataframe_to_html(report_errors))

    sections.extend(
        [
            "<h3>Notes</h3>",
            "<p>Controversial samples are counted as Unsafe in binary evaluation.</p>",
            "</section>",
        ]
    )
    return sections


def _dataframe_to_html(data: pd.DataFrame) -> str:
    """Convert a DataFrame to an escaped HTML table."""

    if data.empty:
        return '<p class="muted">No data available.</p>'

    header_cells = "".join(f"<th>{escape(str(column))}</th>" for column in data.columns)
    rows = []
    for _, row in data.iterrows():
        cells = "".join(f"<td>{_format_html_cell(row[column])}</td>" for column in data.columns)
        rows.append(f"<tr>{cells}</tr>")

    return (
        '<div class="table-wrap">'
        "<table>"
        f"<thead><tr>{header_cells}</tr></thead>"
        f"<tbody>{''.join(rows)}</tbody>"
        "</table>"
        "</div>"
    )


def _format_html_cell(value: object) -> str:
    """Format and escape one HTML table cell."""

    if isinstance(value, float):
        text = _format_metric(value)
    else:
        text = "" if value is None else str(value)
    return escape(text)


def _evaluation_to_pdf_elements(evaluation: EvaluationResult, styles, max_samples: int) -> list:
    """Return ReportLab flowables for one detector evaluation."""

    from reportlab.platypus import Paragraph, Spacer

    confusion = evaluation.confusion_matrix
    metrics_table = pd.DataFrame(
        [
            {"Metric": metric_name, "Value": _format_metric(evaluation.metrics[metric_name])}
            for metric_name in _metric_order()
        ]
    )
    confusion_table = pd.DataFrame(
        [
            {"Actual \\ Predicted": "Safe", "Safe": confusion["TN"], "Unsafe": confusion["FP"]},
            {"Actual \\ Predicted": "Unsafe", "Safe": confusion["FN"], "Unsafe": confusion["TP"]},
        ]
    )
    errors = evaluation.misclassified_samples
    false_positive_count = int((errors["error_type"] == "False Positive").sum()) if not errors.empty else 0
    false_negative_count = int((errors["error_type"] == "False Negative").sum()) if not errors.empty else 0

    elements = [
        Spacer(1, 12),
        Paragraph(f"Detector: {_pdf_text(evaluation.detector_name)}", styles["Heading2"]),
        Paragraph(f"Prediction column: {_pdf_text(evaluation.prediction_column)}", styles["BodyText"]),
        Spacer(1, 6),
        Paragraph("Metrics", styles["Heading3"]),
        _dataframe_to_pdf_table(metrics_table, styles),
        Spacer(1, 6),
        Paragraph("Confusion Matrix", styles["Heading3"]),
        _dataframe_to_pdf_table(confusion_table, styles),
        Spacer(1, 6),
        Paragraph("Group Analysis", styles["Heading3"]),
    ]

    if evaluation.group_metrics:
        for group_column, group_table in evaluation.group_metrics.items():
            elements.extend(
                [
                    Paragraph(f"By {_pdf_text(group_column)}", styles["Heading4"]),
                    _dataframe_to_pdf_table(group_table, styles),
                    Spacer(1, 6),
                ]
            )
    else:
        elements.append(Paragraph("No group columns were available.", styles["BodyText"]))

    elements.extend(
        [
            Paragraph("Error Analysis", styles["Heading3"]),
            _pdf_key_value_table(
                [
                    ("False Positive count", false_positive_count),
                    ("False Negative count", false_negative_count),
                ],
                styles,
            ),
            Spacer(1, 6),
            Paragraph("Misclassified Samples", styles["Heading3"]),
        ]
    )

    if errors.empty:
        elements.append(Paragraph("No misclassified samples were found.", styles["BodyText"]))
    else:
        elements.append(_dataframe_to_pdf_table(errors.head(max_samples), styles))
        if len(errors) > max_samples:
            elements.append(
                Paragraph(f"Only the first {max_samples} misclassified samples are shown.", styles["BodyText"])
            )

    elements.extend(
        [
            Spacer(1, 6),
            Paragraph("Notes", styles["Heading3"]),
            Paragraph("Controversial samples are counted as Unsafe in binary evaluation.", styles["BodyText"]),
        ]
    )
    return elements


def _pdf_key_value_table(rows: list[tuple[str, object]], styles):
    """Build a compact ReportLab key-value table."""

    data = [[_pdf_paragraph(key, styles), _pdf_paragraph(value, styles)] for key, value in rows]
    return _styled_pdf_table(data, has_header=False)


def _dataframe_to_pdf_table(data: pd.DataFrame, styles):
    """Convert a DataFrame to a ReportLab table."""

    if data.empty:
        return _pdf_paragraph("No data available.", styles)

    table_rows = [[_pdf_paragraph(column, styles) for column in data.columns]]
    for _, row in data.iterrows():
        table_rows.append([_pdf_paragraph(row[column], styles) for column in data.columns])
    return _styled_pdf_table(table_rows, has_header=True)


def _styled_pdf_table(data: list[list[object]], has_header: bool):
    """Apply shared PDF table styling."""

    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.platypus import Table, TableStyle

    column_count = max(len(data[0]), 1)
    available_width = 10.6 * inch
    table = Table(data, repeatRows=1 if has_header else 0, colWidths=[available_width / column_count] * column_count)
    commands = [
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D9E2EC")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if has_header:
        commands.extend(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E79")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ]
        )
    table.setStyle(TableStyle(commands))
    return table


def _pdf_paragraph(value: object, styles):
    """Return a safe ReportLab paragraph for table cells."""

    from reportlab.platypus import Paragraph

    if isinstance(value, float):
        text = _format_metric(value)
    else:
        text = "" if value is None else str(value)
    if len(text) > 500:
        text = text[:497] + "..."
    return Paragraph(_pdf_text(text), styles["BodyText"])


def _pdf_text(value: object) -> str:
    """Escape text for ReportLab paragraph XML."""

    return escape_xml("" if value is None else str(value))


def _metric_order() -> list[str]:
    """Return the standard metric display order."""

    return ["Accuracy", "Precision", "Recall", "F1 Score", "FPR", "FNR"]


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
