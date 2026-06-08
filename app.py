"""Streamlit entry point for SafetyEvaluator."""

from __future__ import annotations

import streamlit as st

from safetyevaluator.loader import (
    OPTIONAL_COLUMNS,
    REQUIRED_COLUMNS,
    get_prediction_columns,
    load_evaluation_data,
    read_evaluation_file,
    read_evaluation_text,
)
from safetyevaluator.metrics import calculate_detector_comparison
from safetyevaluator.report import (
    build_misclassified_samples_table,
    generate_multi_detector_excel_report,
    generate_multi_detector_html_report,
    generate_multi_detector_markdown_report,
    generate_multi_detector_pdf_report,
    generate_multi_detector_word_report,
)
from safetyevaluator.visualize import create_confusion_matrix_figure, create_label_distribution_figure


st.set_page_config(page_title="SafetyEvaluator", layout="wide")


def main() -> None:
    """Render the SafetyEvaluator web app."""

    st.title("SafetyEvaluator")
    st.caption("A lightweight safety evaluation tool for binary and controversial safety classification.")

    st.markdown(
        """
        SafetyEvaluator reads table-based safety classification results, calculates binary evaluation metrics,
        analyzes misclassified samples, and generates downloadable reports.
        """
    )

    with st.expander("Input format", expanded=True):
        st.markdown(
            f"""
            SafetyEvaluator supports CSV upload, Excel `.xlsx` upload, and pasted CSV or TSV text.

            Required columns: `{", ".join(REQUIRED_COLUMNS)}`

            Optional columns: `{", ".join(OPTIONAL_COLUMNS)}`

            Prediction columns: `prediction` or one or more `prediction_*` columns

            Supported labels: `Safe`, `Unsafe`, `Controversial`

            `Controversial` samples are counted as `Unsafe` in binary evaluation.

            If your data uses different names, open the advanced input configuration after loading it.
            """
        )

    raw_data = _load_raw_input()
    if raw_data is None:
        return

    column_mapping, selected_prediction_columns, label_mapping = _render_input_configuration(raw_data)

    if not selected_prediction_columns:
        st.warning("Select at least one detector column.")
        return

    try:
        load_result = load_evaluation_data(
            raw_data,
            column_mapping=column_mapping,
            prediction_columns=selected_prediction_columns,
            label_mapping=label_mapping,
        )
    except Exception as exc:
        st.error(f"Could not prepare the evaluation data: {exc}")
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

    all_errors = build_misclassified_samples_table(comparison)
    st.subheader("Error Explorer")
    filtered_errors = _render_error_explorer(all_errors)

    report_text = generate_multi_detector_markdown_report(
        comparison=comparison,
        missing_optional_columns=load_result.missing_optional_columns,
    )
    excel_report = generate_multi_detector_excel_report(
        comparison=comparison,
        missing_optional_columns=load_result.missing_optional_columns,
    )
    html_report = generate_multi_detector_html_report(
        comparison=comparison,
        missing_optional_columns=load_result.missing_optional_columns,
    )
    try:
        pdf_report = generate_multi_detector_pdf_report(
            comparison=comparison,
            missing_optional_columns=load_result.missing_optional_columns,
        )
        pdf_error = ""
    except RuntimeError as exc:
        pdf_report = b""
        pdf_error = str(exc)
    try:
        word_report = generate_multi_detector_word_report(
            comparison=comparison,
            missing_optional_columns=load_result.missing_optional_columns,
        )
        word_error = ""
    except RuntimeError as exc:
        word_report = b""
        word_error = str(exc)

    st.subheader("Report Preview")
    with st.expander("Markdown report preview", expanded=True):
        preview_limit = 8000
        st.markdown(report_text[:preview_limit])
        if len(report_text) > preview_limit:
            st.caption("Preview truncated. Download the Markdown report for the full content.")

    report_download_columns = st.columns(3)
    with report_download_columns[0]:
        st.download_button(
            label="Download Markdown Report",
            data=report_text,
            file_name="safety_evaluation_report.md",
            mime="text/markdown",
        )
    with report_download_columns[1]:
        st.download_button(
            label="Download HTML Report",
            data=html_report,
            file_name="safety_evaluation_report.html",
            mime="text/html",
        )
    with report_download_columns[2]:
        if word_error:
            st.caption(word_error)
        else:
            st.download_button(
                label="Download Word Report",
                data=word_report,
                file_name="safety_evaluation_report.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )

    data_download_columns = st.columns(3)
    with data_download_columns[0]:
        st.download_button(
            label="Download Excel Report",
            data=excel_report,
            file_name="safety_evaluation_report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    with data_download_columns[1]:
        if pdf_error:
            st.caption(pdf_error)
        else:
            st.download_button(
                label="Download PDF Report",
                data=pdf_report,
                file_name="safety_evaluation_report.pdf",
                mime="application/pdf",
            )
    with data_download_columns[2]:
        st.download_button(
            label="Download Filtered Error CSV",
            data=filtered_errors.to_csv(index=False).encode("utf-8-sig"),
            file_name="misclassified_samples_filtered.csv",
            mime="text/csv",
        )


def _format_metric_table(data):
    """Format metric columns for Streamlit display."""

    metric_columns = ["Accuracy", "Precision", "Recall", "F1 Score", "FPR", "FNR"]
    existing_metric_columns = [column for column in metric_columns if column in data.columns]
    return data.style.format({column: "{:.4f}" for column in existing_metric_columns})


def _load_raw_input():
    """Render input controls and return the raw evaluation table."""

    input_method = st.radio(
        "Input method",
        options=["Upload CSV or Excel", "Paste CSV or TSV"],
        horizontal=True,
    )

    if input_method == "Upload CSV or Excel":
        uploaded_file = st.file_uploader("Upload a CSV or Excel file", type=["csv", "xlsx"])
        if uploaded_file is None:
            st.info("Upload a CSV or Excel file to start. You can use data/demo.csv from this project for a quick demo.")
            return None
        try:
            return read_evaluation_file(uploaded_file, uploaded_file.name)
        except Exception as exc:
            st.error(f"Could not read the uploaded file: {exc}")
            return None

    pasted_text = st.text_area(
        "Paste CSV or TSV data",
        value="",
        height=220,
        placeholder="id,input,label,prediction\n1,hello,Safe,Safe",
    )
    if not pasted_text.strip():
        st.info("Paste CSV or TSV text to start. The first row should contain column names.")
        return None
    try:
        return read_evaluation_text(pasted_text)
    except Exception as exc:
        st.error(f"Could not read the pasted data: {exc}")
        return None


def _render_input_configuration(raw_data):
    """Render optional input configuration controls."""

    columns = list(raw_data.columns)
    automatic_prediction_columns = get_prediction_columns(raw_data)

    with st.expander("Advanced input configuration", expanded=False):
        st.caption("Leave these settings unchanged when your CSV already uses the default SafetyEvaluator format.")

        st.subheader("Column mapping")
        mapping_columns = st.columns(3)
        id_column = _column_select(
            mapping_columns[0],
            "ID column",
            columns,
            preferred="id",
            key="id_column",
            optional=False,
        )
        input_column = _column_select(
            mapping_columns[1],
            "Input column",
            columns,
            preferred="input",
            key="input_column",
            optional=False,
        )
        label_column = _column_select(
            mapping_columns[2],
            "Label column",
            columns,
            preferred="label",
            key="label_column",
            optional=False,
        )

        optional_columns = st.columns(2)
        source_column = _column_select(
            optional_columns[0],
            "Source column",
            columns,
            preferred="source",
            key="source_column",
            optional=True,
        )
        category_column = _column_select(
            optional_columns[1],
            "Category column",
            columns,
            preferred="category",
            key="category_column",
            optional=True,
        )

        reserved_columns = {
            column
            for column in [id_column, input_column, label_column, source_column, category_column]
            if column
        }
        detector_options = [column for column in columns if column not in reserved_columns]
        default_detectors = [column for column in automatic_prediction_columns if column in detector_options]
        selected_prediction_columns = st.multiselect(
            "Detector columns",
            options=detector_options,
            default=default_detectors,
            help="Choose one or more prediction columns. By default, SafetyEvaluator uses prediction and prediction_*.",
        )

        st.subheader("Label mapping")
        st.caption("Aliases are additive and case-insensitive. The default labels still work.")
        label_columns = st.columns(3)
        safe_aliases = label_columns[0].text_area(
            "Safe aliases",
            value="",
            placeholder="benign, 0",
            height=90,
        )
        unsafe_aliases = label_columns[1].text_area(
            "Unsafe aliases",
            value="",
            placeholder="harmful, 1",
            height=90,
        )
        controversial_aliases = label_columns[2].text_area(
            "Controversial aliases",
            value="",
            placeholder="disputed, borderline",
            height=90,
        )

    column_mapping = {
        "id": id_column,
        "input": input_column,
        "label": label_column,
        "source": source_column,
        "category": category_column,
    }
    label_mapping = _parse_label_aliases(
        {
            "Safe": safe_aliases,
            "Unsafe": unsafe_aliases,
            "Controversial": controversial_aliases,
        }
    )

    return column_mapping, selected_prediction_columns, label_mapping


def _render_error_explorer(errors):
    """Render filter controls for the combined error table."""

    if errors.empty:
        st.success("No misclassified samples were found across the selected detectors.")
        st.dataframe(errors, use_container_width=True, hide_index=True)
        return errors

    filter_columns = st.columns(4)
    filtered = errors.copy()

    filtered = _apply_multiselect_filter(
        filter_columns[0],
        filtered,
        "Detector",
        "Filter detectors",
    )
    filtered = _apply_multiselect_filter(
        filter_columns[1],
        filtered,
        "error_type",
        "Filter error types",
    )
    filtered = _apply_multiselect_filter(
        filter_columns[2],
        filtered,
        "category",
        "Filter categories",
    )
    filtered = _apply_multiselect_filter(
        filter_columns[3],
        filtered,
        "source",
        "Filter sources",
    )

    st.dataframe(filtered, use_container_width=True, hide_index=True)
    return filtered


def _apply_multiselect_filter(container, data, column, label):
    """Apply an all-selected multiselect filter when a column exists."""

    if column not in data.columns:
        container.caption(f"{label}: unavailable")
        return data

    options = sorted(value for value in data[column].dropna().astype(str).unique() if value)
    if not options:
        container.caption(f"{label}: unavailable")
        return data

    selected = container.multiselect(label, options=options, default=options)
    if not selected:
        return data.iloc[0:0].copy()
    return data[data[column].astype(str).isin(selected)]


def _column_select(container, label, columns, preferred, key, optional):
    """Render a column select box with default SafetyEvaluator names selected when present."""

    empty_option = "(not selected)"
    options = [empty_option] + columns
    preferred_index = options.index(preferred) if preferred in options else 0
    if optional and preferred not in columns:
        preferred_index = 0

    selected = container.selectbox(label, options=options, index=preferred_index, key=key)
    return None if selected == empty_option else selected


def _parse_label_aliases(alias_text_by_label):
    """Parse comma, semicolon, or newline separated label aliases."""

    label_mapping = {}
    for canonical_label, alias_text in alias_text_by_label.items():
        for alias in alias_text.replace(";", ",").replace("\n", ",").split(","):
            cleaned_alias = alias.strip()
            if cleaned_alias:
                label_mapping[cleaned_alias] = canonical_label
    return label_mapping


if __name__ == "__main__":
    main()
