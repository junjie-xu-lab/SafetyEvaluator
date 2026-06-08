# SafetyEvaluator

SafetyEvaluator is a lightweight local Streamlit web app for safety classification evaluation.
It reads table-based evaluation data, computes binary safety metrics, analyzes misclassified samples,
visualizes results, and generates downloadable reports.

The project is intentionally model-agnostic. It is not tied to any specific large language model,
guard model, API provider, database, IDE, or operating system.

## Project Highlights

- Local Streamlit web app for Windows, macOS, and Linux.
- Generic table-based workflow for safety classification results.
- Supports CSV upload, Excel `.xlsx` upload, and pasted CSV / TSV text.
- Supports `Safe`, `Unsafe`, and `Controversial` labels.
- Counts `Controversial` as `Unsafe` in binary evaluation.
- Computes Accuracy, Precision, Recall, F1 Score, FPR, and FNR.
- Compares multiple detector prediction columns in one CSV.
- Slices metrics by `category` and `source` to locate weak areas.
- Displays a confusion matrix and raw label distribution chart with matplotlib.
- Shows false positives and false negatives in a readable error table.
- Exports Markdown reports, Excel reports, and filtered error-sample CSV files from the browser.
- Includes a fictional demo dataset for quick testing.

## Features

- CSV upload in the Streamlit interface.
- Excel `.xlsx` upload in the Streamlit interface.
- Pasted CSV / TSV input in the Streamlit interface.
- Required column validation.
- Optional column auto-fill for missing fields.
- Optional column mapping for files that use custom names such as `prompt`, `gold`, or `model_a`.
- Optional label alias mapping for values such as `benign` / `harmful` or `0` / `1`.
- Case-insensitive label normalization.
- Friendly unsupported-label diagnostics with CSV row numbers.
- Binary safety evaluation with safe division for zero-denominator cases.
- Multi-detector comparison for `prediction`, `prediction_*`, or manually selected detector columns.
- Group analysis by `category` and `source`.
- Misclassified sample analysis.
- Filterable error explorer by detector, error type, category, and source.
- Markdown report preview before download.
- Markdown report download.
- Excel report download with separate sheets for summary, detector comparison, metrics, group analysis, and errors.
- Filtered misclassified-sample CSV download.

## Input Format

SafetyEvaluator supports three input methods:

- Upload a CSV file.
- Upload an Excel `.xlsx` file.
- Paste CSV or TSV text directly into the web page.

Example columns:

```text
id,input,label,prediction,prediction_baseline,prediction_strict,source,category
```

Required columns:

```text
id,input,label
```

Optional columns:

```text
source,category
```

Prediction columns:

```text
prediction
prediction_*
```

At least one prediction column is required. The default single-detector format still uses `prediction`.
For multi-detector comparisons, add columns such as `prediction_baseline`, `prediction_strict`, or
`prediction_guard_v2`.

If optional columns are missing, SafetyEvaluator fills them with empty strings and shows a note in the app and report.

SafetyEvaluator v3 also includes an advanced input configuration panel in the web app. If your CSV already follows the
default format above, leave the panel unchanged. If your file uses different names, you can map source columns such as
`sample_id`, `prompt`, or `gold_label` to the standard `id`, `input`, and `label` fields.

The same panel also lets you select detector columns manually. This is useful when prediction columns are named
`baseline_guard`, `strict_guard`, `model_a`, or any other project-specific name instead of `prediction_*`.

Column meanings:

| Column | Meaning |
| --- | --- |
| `id` | Sample identifier |
| `input` | Evaluated content, such as a prompt, a single-turn input-output pair, or a serialized multi-turn conversation |
| `label` | Human-annotated ground-truth label |
| `prediction` | Predicted label from the default model, classifier, or safety detector |
| `prediction_*` | Additional detector prediction columns for side-by-side comparison |
| `source` | Dataset source, optional |
| `category` | Sample category, optional |

CSV files are read with UTF-8 / UTF-8-SIG compatibility to reduce issues with files exported from Windows Excel.
Excel `.xlsx` files are read from the first worksheet.

SafetyEvaluator treats `input` as the full content being evaluated. For prompt-only safety checks, put the prompt in
`input`. For input-output safety checks, put the combined conversation in `input`, for example
`User: ... Assistant: ...`. For multi-turn evaluations, serialize the full conversation into `input` with role labels
or another consistent delimiter. Free-form content fields such as `input` are displayed for review and error analysis,
but they are not used in metric formulas.

## Label Rules

Supported labels:

```text
Safe
Unsafe
Controversial
```

SafetyEvaluator cleans labels by trimming spaces and using case-insensitive matching. For example, `safe`, `SAFE`,
and `Safe` are all normalized to `Safe`.

The advanced input configuration panel can add label aliases without changing the default label rules. For example:

| Alias values | Canonical label |
| --- | --- |
| `benign`, `0` | `Safe` |
| `harmful`, `1` | `Unsafe` |
| `borderline` | `Controversial` |

Unsupported labels are reported clearly in the Streamlit page with row numbers and column names. This validation applies
to the ground-truth `label` column and every detected prediction column.

## Controversial Handling

Raw dataset statistics keep the number of `Controversial` samples.

For binary evaluation:

| Original Label | Binary Label |
| --- | --- |
| `Safe` | `Safe` |
| `Unsafe` | `Unsafe` |
| `Controversial` | `Unsafe` |

Controversial samples are counted as Unsafe in binary evaluation.

## Metrics

In binary evaluation:

- `Safe` is the negative class.
- `Unsafe` is the positive class.
- `Controversial` is mapped to `Unsafe`.

Confusion matrix definitions:

| Term | Meaning |
| --- | --- |
| TP | True `Unsafe`, predicted `Unsafe` |
| TN | True `Safe`, predicted `Safe` |
| FP | True `Safe`, predicted `Unsafe` |
| FN | True `Unsafe`, predicted `Safe` |

Calculated metrics:

| Metric | Formula |
| --- | --- |
| Accuracy | `(TP + TN) / total` |
| Precision | `TP / (TP + FP)` |
| Recall | `TP / (TP + FN)` |
| F1 Score | `2 * Precision * Recall / (Precision + Recall)` |
| FPR | `FP / (FP + TN)` |
| FNR | `FN / (FN + TP)` |

When a denominator is zero, the metric value is shown as `0`.

## Multi-Detector Comparison

SafetyEvaluator can compare several detector prediction columns from the same CSV. By default, it automatically detects:

- `prediction`
- Columns beginning with `prediction_`

Each detector gets its own metrics, confusion matrix, group analysis, and misclassified sample table. The app also shows
a detector comparison table sorted by F1 Score, FNR, and FPR. Detector-specific classifications should be stored in
`prediction_*` columns when you want zero-configuration loading.

In v3, detector columns can also be selected manually in the advanced input configuration panel. This preserves the
default workflow while supporting datasets that use custom detector names.

## Group Analysis

When `category` or `source` columns are available, SafetyEvaluator calculates per-group metrics for each detector.
This helps identify concentrated failure areas, such as a detector with high false negatives in `jailbreak` samples or
high false positives in `privacy` samples.

## Installation

You can download the project either by cloning the GitHub repository or by downloading the ZIP archive from GitHub.

Prerequisite:

```text
Python 3.11+
```

Clone with Git:

```bash
git clone https://github.com/junjie-xu-lab/SafetyEvaluator.git
cd SafetyEvaluator
```

Or download ZIP:

1. Open the GitHub repository page.
2. Click `Code`.
3. Click `Download ZIP`.
4. Extract the ZIP file.
5. Open a terminal in the extracted `SafetyEvaluator` folder.

For most users, continue to the Run section and use `python start.py`.

If you prefer manual setup, create a virtual environment:

```bash
python -m venv .venv
```

Install dependencies without activating the environment.

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Windows CMD:

```bat
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

macOS / Linux:

```bash
.venv/bin/python -m pip install -r requirements.txt
```

The traditional activation commands also work, but they are optional. On Windows PowerShell, `Activate.ps1` may be
blocked by the default execution policy. SafetyEvaluator does not require activation, so use the commands above instead.

After manual setup, start the app without activating the environment.

Windows:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

macOS / Linux:

```bash
.venv/bin/python -m streamlit run app.py
```

The Excel input and Excel report features use `openpyxl`, which is included in `requirements.txt` and installed by the
helper scripts.

## Run

Recommended first run on Windows, macOS, or Linux:

```bash
python start.py
```

On Windows, if `python` is not recognized but the Python launcher is installed, use:

```powershell
py start.py
```

`start.py` creates a local `.venv` folder if needed, installs dependencies from `requirements.txt`, and starts the
Streamlit app. It does not use PowerShell activation scripts, so it avoids the common `Activate.ps1` execution-policy
block on Windows.

Streamlit will open the app in your browser. Upload a CSV or Excel file, paste CSV / TSV data, review the metrics and
charts, inspect error samples, and download reports.

If you prefer to manage the environment manually, start the local Streamlit app after activating the virtual environment:

```bash
python -m streamlit run app.py
```

On Windows, you can also run Streamlit through the project virtual environment without activating it first:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

If you see `No module named streamlit`, your terminal is using a Python environment where the dependencies are not
installed. Use `python start.py`, `py start.py`, or the `.venv\Scripts\python.exe` command above.

If PowerShell shows an error that `Activate.ps1` cannot be loaded because script execution is disabled, you do not need
administrator mode and you do not need to change the system execution policy. Use:

```powershell
python start.py
```

or:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Optional helper scripts are also provided:

Windows:

```bat
start_windows.bat
```

If Windows blocks the downloaded `.bat` file, use `python start.py` instead.

macOS / Linux:

```bash
sh start_unix.sh
```

These helper scripts create a local `.venv` folder if needed, install dependencies from `requirements.txt`,
and then start the Streamlit app.

The helper scripts are optional. The recommended cross-platform command is:

```bash
python start.py
```

## Demo Data

Fictional demo datasets are included:

```text
data/demo.csv
data/demo.xlsx
data/demo_custom.csv
```

`data/demo.csv` and `data/demo.xlsx` follow the default SafetyEvaluator column names. They contain examples of:

- Input-output style evaluated content stored in `input`.
- Correct `Safe` predictions.
- Correct `Unsafe` predictions.
- `Safe` to `Unsafe` false positives.
- `Unsafe` to `Safe` false negatives.
- `Controversial` labels and predictions.
- Multiple detector prediction columns.
- Category-level and source-level group analysis.

`data/demo_custom.csv` demonstrates v3 input configuration with custom column names, label aliases such as
`benign` / `harmful` / `1`, and manually selected detector columns.

The demo data does not contain real sensitive data.

## Output Results

The Streamlit page shows:

- Data preview.
- Raw label distribution.
- Detector comparison table.
- Binary metrics.
- Confusion matrix.
- Group analysis by `category` and `source`.
- Label count bar chart.
- Misclassified sample table.
- Filterable error explorer.
- Markdown report preview.
- Markdown report download button.
- Excel report download button.
- Filtered error-sample CSV download button.

The project includes `.streamlit/config.toml` to disable Streamlit usage-stat collection prompts for a smoother
first run.

The default output filenames are:

```text
safety_evaluation_report.md
safety_evaluation_report.xlsx
misclassified_samples_filtered.csv
```

The Markdown report includes:

- Dataset summary.
- Binary mapping rule.
- Detector comparison.
- Metrics.
- Confusion matrix table.
- Group analysis tables.
- False positive and false negative counts.
- Misclassified samples.
- Notes about `Controversial` handling.

The Excel report includes:

- `Summary`
- `Detector Comparison`
- `Metrics`
- `Confusion Matrix`
- `Group Analysis`
- `Misclassified Samples`

## Project Structure

```text
SafetyEvaluator/
|-- README.md
|-- LICENSE
|-- requirements.txt
|-- app.py
|-- start.py
|-- start_windows.bat
|-- start_unix.sh
|-- data/
|   |-- demo.csv
|   |-- demo.xlsx
|   `-- demo_custom.csv
|-- safetyevaluator/
|   |-- __init__.py
|   |-- loader.py
|   |-- metrics.py
|   |-- report.py
|   `-- visualize.py
|-- tests/
|   |-- test_loader.py
|   |-- test_metrics.py
|   `-- test_report.py
|-- .streamlit/
|   `-- config.toml
`-- outputs/
    `-- .gitkeep
```

## Testing

Run the test suite:

```bash
python -m pytest
```

The tests cover:

- All predictions correct.
- False positives.
- False negatives.
- `Controversial` mapped to `Unsafe`.
- Zero-denominator metric cases.
- Group metric calculation.
- Multi-detector comparison.
- Prediction column detection in CSV loading.
- Excel workbook input.
- Pasted CSV / TSV input.
- Custom column mapping.
- Label alias mapping.
- Manual detector column selection.
- Excel report generation.
- Combined misclassified-sample export.

## Current Scope

SafetyEvaluator is currently a local Streamlit web app.

It does not include:

- Command-line tool mode.
- Online deployment.
- External model or guard API integration.
- Database storage.
- User login.
- HTML export.
- EXE, DMG, desktop client, or installer packaging.

## License

This project is released under the MIT License. See `LICENSE` for details.

## Future Extensions

Possible next steps:

- Multi-class metric views.
- Additional report formats such as HTML or PDF.
- More configurable label mappings.
- GitHub Actions test workflow.
- Optional screenshots for README demonstration.
