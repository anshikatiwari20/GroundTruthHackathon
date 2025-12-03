import os
import argparse

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages


def generate_pdf_report(csv_path: str, output_pdf: str | None = None, sample_rows: int = 10):
    # ---------- Load data ----------
    df = pd.read_csv(csv_path)

    if output_pdf is None:
        base = os.path.splitext(os.path.basename(csv_path))[0]
        output_pdf = f"{base}_report.pdf"

    # Basic metadata
    n_rows, n_cols = df.shape
    dtypes = df.dtypes.astype(str)

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    categorical_cols = df.select_dtypes(exclude="number").columns.tolist()

    with PdfPages(output_pdf) as pdf:
        # ---------- Page 1: Overview ----------
        fig, ax = plt.subplots(figsize=(8.27, 11.69))  # A4 portrait
        ax.axis("off")

        text_lines = [
            "Auto-Generated Data Report",
            "",
            f"Source file: {os.path.abspath(csv_path)}",
            f"Rows: {n_rows}",
            f"Columns: {n_cols}",
            "",
            "Column Types:",
        ]
        for col in df.columns:
            text_lines.append(f"  • {col}: {dtypes[col]}")

        ax.text(
            0.01,
            0.99,
            "\n".join(text_lines),
            va="top",
            ha="left",
            fontsize=10,
            wrap=True,
        )
        pdf.savefig(fig)
        plt.close(fig)

        # ---------- Page 2: Sample rows ----------
        fig, ax = plt.subplots(figsize=(11.69, 8.27))  # A4 landscape
        ax.set_axis_off()

        sample_df = df.head(sample_rows)

        table = ax.table(
            cellText=sample_df.values,
            colLabels=sample_df.columns,
            loc="center",
        )
        table.auto_set_font_size(False)
        table.set_fontsize(8)
        table.auto_set_column_width(col=list(range(len(sample_df.columns))))

        ax.set_title("Sample Data (first rows)", pad=20)
        pdf.savefig(fig)
        plt.close(fig)

        # ---------- Page 3: Missing values ----------
        missing = df.isna().sum()
        missing = missing[missing > 0].sort_values(ascending=False)

        if not missing.empty:
            fig, ax = plt.subplots(figsize=(8, 6))
            missing.plot(kind="bar", ax=ax)
            ax.set_title("Missing Values per Column")
            ax.set_ylabel("Count")
            ax.set_xlabel("Column")
            plt.xticks(rotation=45, ha="right")
            plt.tight.tight_layout()
            pdf.savefig(fig)
            plt.close(fig)

        # ---------- Page 4: Numeric summary ----------
        if numeric_cols:
            num_df = df[numeric_cols]
            summary = num_df.describe().T.round(3)

            fig, ax = plt.subplots(figsize=(11.69, 8.27))
            ax.set_axis_off()

            table = ax.table(
                cellText=summary.values,
                rowLabels=summary.index,
                colLabels=summary.columns,
                loc="center",
            )
            table.auto_set_font_size(False)
            table.set_fontsize(8)
            table.auto_set_column_width(col=list(range(len(summary.columns))))

            ax.set_title("Numeric Columns – Summary Statistics", pad=20)
            pdf.savefig(fig)
            plt.close(fig)

        # ---------- Histograms for numeric columns ----------
        for col in numeric_cols:
            fig, ax = plt.subplots(figsize=(8, 6))
            df[col].dropna().plot(kind="hist", bins=20, ax=ax)
            ax.set_title(f"Distribution of {col}")
            ax.set_xlabel(col)
            ax.set_ylabel("Frequency")
            plt.tight_layout()
            pdf.savefig(fig)
            plt.close(fig)

        # ---------- Categorical columns: top categories ----------
        for col in categorical_cols:
            value_counts = df[col].value_counts().head(15)  # top 15
            if value_counts.empty:
                continue

            fig, ax = plt.subplots(figsize=(8, 6))
            value_counts.sort_values(ascending=True).plot(kind="barh", ax=ax)
            ax.set_title(f"Top Values for {col}")
            ax.set_xlabel("Count")
            plt.tight_layout()
            pdf.savefig(fig)
            plt.close(fig)

    print(f"Report saved to: {output_pdf}")


def main():
    parser = argparse.ArgumentParser(description="Generate PDF report from a CSV file.")
    parser.add_argument("csv_path", help="Path to the input CSV file.")
    parser.add_argument(
        "-o", "--output",
        help="Path to output PDF file (default: <csv_name>_report.pdf)",
        default=None,
    )
    parser.add_argument(
        "--sample-rows",
        type=int,
        default=10,
        help="Number of sample rows to show in the report.",
    )

    args = parser.parse_args()
    generate_pdf_report(args.csv_path, args.output, args.sample_rows)


if __name__ == "__main__":
    main()
