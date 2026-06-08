"""Matplotlib visualizations for SafetyEvaluator."""

from __future__ import annotations

import matplotlib.pyplot as plt


def create_confusion_matrix_figure(confusion_matrix: dict[str, int]):
    """Create a simple binary confusion matrix figure."""

    matrix = [
        [confusion_matrix["TN"], confusion_matrix["FP"]],
        [confusion_matrix["FN"], confusion_matrix["TP"]],
    ]

    fig, ax = plt.subplots(figsize=(5, 4))
    image = ax.imshow(matrix, cmap="Blues")
    fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)

    ax.set_xticks([0, 1], labels=["Predicted Safe", "Predicted Unsafe"])
    ax.set_yticks([0, 1], labels=["Actual Safe", "Actual Unsafe"])
    ax.set_title("Confusion Matrix")

    for row_index, row in enumerate(matrix):
        for column_index, value in enumerate(row):
            ax.text(column_index, row_index, str(value), ha="center", va="center", color="black")

    fig.tight_layout()
    return fig


def create_label_distribution_figure(label_counts: dict[str, int]):
    """Create a bar chart for raw label counts."""

    labels = [label for label in ["Safe", "Unsafe", "Controversial"] if label_counts.get(label, 0) > 0]
    if not labels:
        labels = ["Safe", "Unsafe", "Controversial"]
    counts = [label_counts.get(label, 0) for label in labels]

    fig, ax = plt.subplots(figsize=(5, 4))
    bars = ax.bar(labels, counts, color=["#2E7D32", "#C62828", "#F9A825"][: len(labels)])
    ax.set_title("Raw Label Distribution")
    ax.set_ylabel("Count")
    ax.set_ylim(0, max(counts + [1]) * 1.2)

    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2, height, str(int(height)), ha="center", va="bottom")

    fig.tight_layout()
    return fig
