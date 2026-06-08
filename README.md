# SafetyEvaluator

SafetyEvaluator is a lightweight local Streamlit web app for safety classification evaluation.
It reads CSV files, computes binary safety metrics, analyzes misclassified samples, visualizes results,
and generates a downloadable Markdown report.

The project is intentionally model-agnostic. It is not tied to any specific large language model,
guard model, API provider, database, IDE, or operating system.

## Project Highlights

- Local Streamlit web app for Windows, macOS, and Linux.
- Generic CSV-based workflow for safety classification results.
- Supports `Safe`, `Unsafe`, and `Controversial` labels.
- Counts `Controversial` as `Unsafe` in binary evaluation.
- Computes Accuracy, Precision, Recall, F1 Score, FPR, and FNR.
- Displays a confusion matrix and raw label distribution chart with matplotlib.
- Shows false positives and false negatives in a readable error table.
- Exports a Markdown report from the browser.
- Includes a fictional demo dataset for quick testing.

## Features

- CSV upload in the Streamlit interface.
- Required column validation.
- Optional column auto-fill for missing fields.
- Case-insensitive label normalization.
- Friendly unsupported-label diagnostics with CSV row numbers.
- Binary safety evaluation with safe division for zero-denominator cases.
- Misclassified sample analysis.
- Markdown report download.

## Input CSV Format

The first version supports CSV files only.

Standard columns:

```text
id,input,label,prediction,output,source,category
```

Required columns:

```text
id,input,label,prediction
```

Optional columns:

```text
output,source,category
```

If optional columns are missing, SafetyEvaluator fills them with empty strings and shows a note in the app and report.

Column meanings:

| Column | Meaning |
| --- | --- |
| `id` | Sample identifier |
| `input` | Input text, prompt, user question, instruction, or other evaluated content |
| `label` | Human-annotated ground-truth label |
| `prediction` | Predicted label from a model, classifier, or safety detector |
| `output` | Model response content, optional |
| `source` | Dataset source, optional |
| `category` | Sample category, optional |

CSV files are read with UTF-8 / UTF-8-SIG compatibility to reduce issues with files exported from Windows Excel.

## Label Rules

Supported labels:

```text
Safe
Unsafe
Controversial
```

SafetyEvaluator cleans labels by trimming spaces and using case-insensitive matching. For example, `safe`, `SAFE`,
and `Safe` are all normalized to `Safe`.

Unsupported labels are reported clearly in the Streamlit page with row numbers and column names.

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

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Activate it on Windows CMD:

```bat
.venv\Scripts\activate.bat
```

Activate it on macOS / Linux:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

## Run

Start the local Streamlit app:

```bash
python -m streamlit run app.py
```

Streamlit will open the app in your browser. Upload a CSV file, review the metrics and charts, inspect error samples,
and download the Markdown report.

Optional helper scripts are also provided:

Windows:

```bat
start_windows.bat
```

macOS / Linux:

```bash
sh start_unix.sh
```

These helper scripts create a local `.venv` folder if needed, install dependencies from `requirements.txt`,
and then start the Streamlit app.

The helper scripts are optional. The recommended cross-platform command remains:

```bash
python -m streamlit run app.py
```

## Demo Data

A fictional demo dataset is included:

```text
data/demo.csv
```

It contains examples of:

- Correct `Safe` predictions.
- Correct `Unsafe` predictions.
- `Safe` to `Unsafe` false positives.
- `Unsafe` to `Safe` false negatives.
- `Controversial` labels and predictions.

The demo data does not contain real sensitive data.

## Output Results

The Streamlit page shows:

- Data preview.
- Raw label distribution.
- Binary metrics.
- Confusion matrix.
- Label count bar chart.
- Misclassified sample table.
- Markdown report download button.

The project includes `.streamlit/config.toml` to disable Streamlit usage-stat collection prompts for a smoother
first run.

The report filename is:

```text
safety_evaluation_report.md
```

The Markdown report includes:

- Dataset summary.
- Binary mapping rule.
- Metrics.
- Confusion matrix table.
- False positive and false negative counts.
- Misclassified samples.
- Notes about `Controversial` handling.

## Project Structure

```text
SafetyEvaluator/
|-- README.md
|-- LICENSE
|-- requirements.txt
|-- app.py
|-- start_windows.bat
|-- start_unix.sh
|-- data/
|   `-- demo.csv
|-- safetyevaluator/
|   |-- __init__.py
|   |-- loader.py
|   |-- metrics.py
|   |-- report.py
|   `-- visualize.py
|-- tests/
|   `-- test_metrics.py
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

## First Version Scope

This first version is a local Streamlit web app.

It does not include:

- Command-line tool mode.
- Online deployment.
- External model or guard API integration.
- Database storage.
- User login.
- Excel or HTML export.
- EXE, DMG, desktop client, or installer packaging.

## License

This project is released under the MIT License. See `LICENSE` for details.

## Future Extensions

Possible next steps:

- Multi-class metric views.
- Dataset slicing by `source` or `category`.
- Additional report formats.
- More configurable label mappings.
- Batch comparison across multiple detectors.
- GitHub Actions test workflow.
- Optional screenshots for README demonstration.
