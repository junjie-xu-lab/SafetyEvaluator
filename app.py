"""Streamlit entry point for SafetyEvaluator."""

from __future__ import annotations

import streamlit as st

from safetyevaluator.loader import OPTIONAL_COLUMNS, REQUIRED_COLUMNS, load_evaluation_csv
from safetyevaluator.metrics import calculate_metrics
from safetyevaluator.report import generate_markdown_report
from safetyevaluator.visualize import create_confusion_matrix_figure, create_label_distribution_figure


st.set_page_config(page_title="SafetyEvaluator", layout="wide")


def main() -> None:
    """Render the SafetyEvaluator web app."""

    st.title("SafetyEvaluator")
    st.caption("A lightweight safety evaluation tool for binary and controversial safety classification.")

    st.markdown(
        """
        SafetyEvaluator reads CSV safety classification results, calculates binary evaluation metrics,
        analyzes misclassified samples, and generates a downloadable Markdown report.
        """
    )

    with st.expander("CSV format", expanded=True):
        st.markdown(
            f"""
            First version supports CSV files only.

            Required columns: `{", ".join(REQUIRED_COLUMNS)}`

            Optional columns: `{", ".join(OPTIONAL_COLUMNS)}`

            Supported labels: `Safe`, `Unsafe`, `Controversial`

            `Controversial` samples are counted as `Unsafe` in binary evaluation.
            """
        )

    uploaded_file = st.file_uploader("Upload a CSV file", type=["csv"])

    if uploaded_file is None:
        st.info("Upload a CSV file to start. You can use data/demo.csv from this project for a quick demo.")
        return

    try:
        load_result = load_evaluation_csv(uploaded_file)
    except Exception as exc:
        st.error(f"Could not read the CSV file: {exc}")
        return

    data = load_result.data

    if load_result.missing_optional_columns:
        st.warning(
            "The following optional columns were missing and filled with empty strings: "
            + ", ".join(load_result.missing_optional_columns)
        )

    if not load_result.invalid_labels.empty:
        st.error("Unsupported labels were found. Please fix these rows before running the evaluation.")
        st.dataframe(load_result.invalid_labels, use_container_width=True)
        return

    st.subheader("Data Preview")
    st.dataframe(data.head(50), use_container_width=True)

    evaluation = calculate_metrics(data)

    st.subheader("Raw Label Distribution")
    label_counts = evaluation.raw_label_counts
    count_columns = st.columns(3)
    count_columns[0].metric("Safe", label_counts.get("Safe", 0))
    count_columns[1].metric("Unsafe", label_counts.get("Unsafe", 0))
    count_columns[2].metric("Controversial", label_counts.get("Controversial", 0))

    st.subheader("Binary Evaluation Metrics")
    metric_columns = st.columns(6)
    for column, (metric_name, metric_value) in zip(metric_columns, evaluation.metrics.items()):
        column.metric(metric_name, f"{metric_value:.4f}")

    chart_columns = st.columns(2)
    with chart_columns[0]:
        st.subheader("Confusion Matrix")
        st.pyplot(create_confusion_matrix_figure(evaluation.confusion_matrix))

    with chart_columns[1]:
        st.subheader("Label Count Bar Chart")
        st.pyplot(create_label_distribution_figure(evaluation.raw_label_counts))

    st.subheader("Error Analysis")
    errors = evaluation.misclassified_samples
    if errors.empty:
        st.success("No misclassified samples were found.")
    else:
        false_positive_count = int((errors["error_type"] == "False Positive").sum())
        false_negative_count = int((errors["error_type"] == "False Negative").sum())
        error_columns = st.columns(2)
        error_columns[0].metric("False Positive", false_positive_count)
        error_columns[1].metric("False Negative", false_negative_count)
        st.dataframe(errors, use_container_width=True)

    report_text = generate_markdown_report(
        evaluation=evaluation,
        missing_optional_columns=load_result.missing_optional_columns,
    )
    st.download_button(
        label="Download Markdown Report",
        data=report_text,
        file_name="safety_evaluation_report.md",
        mime="text/markdown",
    )


if __name__ == "__main__":
    main()
