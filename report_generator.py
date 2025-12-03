import os
import sqlite3

import pandas as pd

import matplotlib
matplotlib.use("Agg")  

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

def load_tabular_file(path: str) -> pd.DataFrame:
    """
    Load csv, tsv/txt, excel, html, json, sqlite, sql → pandas DataFrame
    """
    ext = os.path.splitext(path)[1].lower()

    if ext == ".csv":
        return pd.read_csv(path)

    elif ext in {".tsv", ".txt"}:
        # Try a sequence of increasingly permissive parsing strategies.
        # Some TXT files contain inconsistent rows (extra/missing fields)
        # which cause pandas' C engine to raise a ParserError. We'll try
        # the python engine with sep sniffing, explicit delimiters, and
        # finally fall back to skipping bad lines so the report can still
        # be generated.
        import csv
        from pandas.errors import ParserError

        # 1) Let pandas try to sniff a separator (python engine)
        try:
            return pd.read_csv(path, sep=None, engine="python")
        except ParserError:
            pass
        except Exception:
            # any other read error — continue to other strategies
            pass

        # Read a sample to let csv.Sniffer try to detect delimiter
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                sample = f.read(4096)
            delimiters = [",", "\t", ";", "|", ":"]
            dialect = csv.Sniffer().sniff(sample, delimiters=delimiters)
            detected = dialect.delimiter
        except Exception:
            detected = None

        # 2) If a delimiter was detected, try reading with it (python engine)
        if detected:
            try:
                return pd.read_csv(path, sep=detected, engine="python")
            except ParserError:
                pass
            except Exception:
                pass

        # 3) Try whitespace-delimited parsing (common for space-separated TXT)
        try:
            return pd.read_csv(path, delim_whitespace=True, engine="python")
        except ParserError:
            pass
        except Exception:
            pass

        # 4) Last resort: read with the C engine but skip malformed lines
        # (pandas >=1.3 supports on_bad_lines). Use 'warn' so user sees a notice.
        try:
            return pd.read_csv(path, engine="python", on_bad_lines="warn")
        except TypeError:
            # Older pandas may not support on_bad_lines; try with error_bad_lines fallback
            try:
                return pd.read_csv(path, engine="python", error_bad_lines=False, warn_bad_lines=True)
            except Exception:
                pass
        except Exception:
            pass

        # If everything failed, raise a helpful error
        raise ValueError(f"Could not parse tabular text file: {path}")

    elif ext in {".xlsx", ".xls"}:
        return pd.read_excel(path)

    elif ext == ".json":
        return pd.read_json(path)

    elif ext in {".html", ".htm"}:
        tables = pd.read_html(path)
        if not tables:
            raise ValueError("No HTML tables found.")
        return tables[0]

    elif ext in {".db", ".sqlite"}:
        conn = sqlite3.connect(path)
        try:
            tables = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table';", conn)["name"].tolist()
            if not tables:
                raise ValueError("No tables found in DB.")
            df = pd.read_sql(f"SELECT * FROM {tables[0]}", conn)
        finally:
            conn.close()
        return df

    elif ext == ".sql":
        conn = sqlite3.connect(":memory:")
        try:
            with open(path, "r", encoding="utf-8") as f:
                conn.executescript(f.read())
            tables = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table';", conn)["name"].tolist()
            if not tables:
                raise ValueError("No tables in SQL script.")
            df = pd.read_sql(f"SELECT * FROM {tables[0]}", conn)
        finally:
            conn.close()
        return df

    else:
        raise ValueError(f"Unsupported file type: {ext}")


def generate_pdf_report(data_path: str, output_pdf: str | None = None, sample_rows: int = 10) -> str:

    df = load_tabular_file(data_path)

    if output_pdf is None:
        base = os.path.splitext(os.path.basename(data_path))[0]
        output_pdf = f"{base}_report.pdf"

    out_dir = os.path.dirname(output_pdf)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    n_rows, n_cols = df.shape
    dtypes = df.dtypes.astype(str)

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    categorical_cols = df.select_dtypes(exclude="number").columns.tolist()

    with PdfPages(output_pdf) as pdf:

        # Page 1
        fig, ax = plt.subplots(figsize=(8.27, 11.69))
        ax.axis("off")

        text_lines = [
            "Auto-Generated Data Report",
            "",
            f"Source file: {os.path.abspath(data_path)}",
            f"Rows: {n_rows}",
            f"Columns: {n_cols}",
            "",
            "Column Types:",
        ]
        for col in df.columns:
            text_lines.append(f"  • {col}: {dtypes[col]}")

        ax.text(0.05, 0.95, "\n".join(text_lines), va="top", ha="left", fontsize=10, wrap=True)
        pdf.savefig(fig)
        plt.close(fig)

        # Page 2: Data sample
        fig, ax = plt.subplots(figsize=(11.69, 8.27))
        ax.set_axis_off()
        sample_df = df.head(sample_rows)
        table = ax.table(cellText=sample_df.values, colLabels=sample_df.columns, loc="center")
        table.auto_set_font_size(False)
        table.set_fontsize(8)
        table.auto_set_column_width(col=list(range(len(sample_df.columns))))
        ax.set_title("Sample Data (first rows)", pad=20)
        pdf.savefig(fig)
        plt.close(fig)

        # Page 3: Missing values
        missing = df.isna().sum()
        missing = missing[missing > 0].sort_values(ascending=False)
        if not missing.empty:
            fig, ax = plt.subplots(figsize=(8, 6))
            missing.plot(kind="bar", ax=ax)
            ax.set_title("Missing Values per Column")
            ax.set_ylabel("Count")
            plt.xticks(rotation=45, ha="right")
            plt.tight_layout()
            pdf.savefig(fig)
            plt.close(fig)

        # Page 4: Numeric stats + histograms
        if numeric_cols:
            # Summary
            fig, ax = plt.subplots(figsize=(11.69, 8.27))
            ax.set_axis_off()
            summary = df[numeric_cols].describe().T.round(3)
            table = ax.table(cellText=summary.values, rowLabels=summary.index, colLabels=summary.columns, loc="center")
            table.auto_set_font_size(False)
            table.set_fontsize(8)
            table.auto_set_column_width(col=list(range(len(summary.columns))))
            ax.set_title("Numeric Columns – Summary Statistics", pad=20)
            pdf.savefig(fig)
            plt.close(fig)

            # Histograms
            for col in numeric_cols:
                fig, ax = plt.subplots(figsize=(8, 6))
                df[col].dropna().plot(kind="hist", bins=20, ax=ax)
                ax.set_title(f"Distribution of {col}")
                plt.tight_layout()
                pdf.savefig(fig)
                plt.close(fig)

        # Categorical
        for col in categorical_cols:
            vc = df[col].value_counts().head(15)
            if vc.empty:
                continue
            fig, ax = plt.subplots(figsize=(8, 6))
            vc.sort_values().plot(kind="barh", ax=ax)
            ax.set_title(f"Top Values for {col}")
            plt.tight_layout()
            pdf.savefig(fig)
            plt.close(fig)

    print(f"[DeepInsight] Report saved: {output_pdf}")
    return output_pdf
