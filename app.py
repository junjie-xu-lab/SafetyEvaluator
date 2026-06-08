"""Streamlit entry point for SafetyEvaluator."""

from __future__ import annotations

import streamlit as st

from safetyevaluator.loader import OPTIONAL_COLUMNS, REQUIRED_COLUMNS, load_evaluation_csv
from safetyevaluator.metrics import calculate_detector_comparison
from safetyevaluator.report import generate_multi_detector_markdown_report
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
            SafetyEvaluator supports CSV files.

            Required columns: `{", ".join(REQUIRED_COLUMNS)}`

            Optional columns: `{", ".join(OPTIONAL_COLUMNS)}`

            Prediction columns: `prediction` or one or more `prediction_*` columns

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
    prediction_columns = load_result.prediction_columns

    if load_result.missing_optional_columns:
        st.warning(
            "The following optional columns were missing and filled with empty strings: "
            + ", ".join(load_result.missing_optional_columns)
        )

    if not load_result.invalid_labels.empty:
        st.error("Unsupported labels were found. Please fix these rows before running the evaluation.")
        st.dataframe(load_result.invalid_labels, use_container_width=True)
        return

    selected_prediction_columns = st.sidebar.multiselect(
        "Detector columns",
        options=prediction_columns,
        default=prediction_columns,
    )
    if not selected_prediction_columns:
        st.warning("Select at least one detector column.")
        return

    comparison = calculate_detector_comparison(data, selected_prediction_columns)

    st.subheader("Data Preview")
    st.dataframe(data.head(50), use_container_width=True)

    st.subheader("Raw Label Distribution")
    first_evaluation = next(iter(comparison.evaluations.values()))
    label_counts = first_evaluation.raw_label_counts
    count_columns = st.columns(3)
    count_columns[0].metric("Safe", label_counts.get("Safe", 0))
    count_columns[1].metric("Unsafe", label_counts.get("Unsafe", 0))
    count_columns[2].metric("Controversial", label_counts.get("Controversial", 0))

    st.subheader("Detector Comparison")
    st.dataframe(_format_metric_table(comparison.comparison_table), use_container_width=True, hide_index=True)

    with st.expander("Raw label chart"):
        st.pyplot(create_label_distribution_figure(first_evaluation.raw_label_counts))

    detector_tabs = st.tabs([comparison.evaluations[column].detector_name for column in selected_prediction_columns])
    for tab, prediction_column in zip(detector_tabs, selected_prediction_columns):
        evaluation = comparison.evaluations[prediction_column]
        with tab:
            st.caption(f"Prediction column: {prediction_column}")

            st.subheader("Binary Evaluation Metrics")
            metric_columns = st.columns(6)
            for column, (metric_name, metric_value) in zip(metric_columns, evaluation.metrics.items()):
                column.metric(metric_name, f"{metric_value:.4f}")

            chart_columns = st.columns(2)
            with chart_columns[0]:
                st.subheader("Confusion Matrix")
                st.pyplot(create_confusion_matrix_figure(evaluation.confusion_matrix))

            with chart_columns[1]:
                st.subheader("Error Summary")
                errors = evaluation.misclassified_samples
                false_positive_count = int((errors["error_type"] == "False Positive").sum()) if not errors.empty else 0
                false_negative_count = int((errors["error_type"] == "False Negative").sum()) if not errors.empty else 0
                error_columns = st.columns(2)
                error_columns[0].metric("False Positive", false_positive_count)
                error_columns[1].metric("False Negative", false_negative_count)

            st.subheader("Group Analysis")
            if evaluation.group_metrics:
                group_tabs = st.tabs([f"By {column}" for column in evaluation.group_metrics])
                for group_tab, (group_column, group_table) in zip(group_tabs, evaluation.group_metrics.items()):
                    with group_tab:
                        st.dataframe(_format_metric_table(group_table), use_container_width=True, hide_index=True)
            else:
                st.info("No category or source columns were available for group analysis.")

            st.subheader("Misclassified Samples")
            if errors.empty:
                st.success("No misclassified samples were found.")
            else:
                st.dataframe(errors, use_container_width=True)

    report_text = generate_multi_detector_markdown_report(
        comparison=comparison,
        missing_optional_columns=load_result.missing_optional_columns,
    )
    st.download_button(
        label="Download Markdown Report",
        data=report_text,
        file_name="safety_evaluation_report.md",
        mime="text/markdown",
    )


def _format_metric_table(data):
    """Format metric columns for Streamlit display."""

    metric_columns = ["Accuracy", "Precision", "Recall", "F1 Score", "FPR", "FNR"]
    existing_metric_columns = [column for column in metric_columns if column in data.columns]
    return data.style.format({column: "{:.4f}" for column in existing_metric_columns})


if __name__ == "__main__":
    main()
