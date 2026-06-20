"""
Shared utilities for gas simulation plotting scripts.

Responsibilities:
  - CSV loading for both aggregated and raw results
  - Consistent matplotlib styling (thesis-quality, PDF-ready)
  - Output path management
  - Common filtering helpers

Usage:
  python scripts/plots/plot_X.py path/to/raw.csv path/to/aggregated.csv
"""

import sys
import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

FIGURES_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "figures", "generated")


def ensure_output_dir() -> str:
    os.makedirs(FIGURES_DIR, exist_ok=True)
    return FIGURES_DIR


def save_figure(fig: plt.Figure, name: str) -> None:
    """Save figure as PDF (vector, LaTeX-native) and PNG (preview)."""
    out = ensure_output_dir()
    pdf_path = os.path.join(out, f"{name}.pdf")
    png_path = os.path.join(out, f"{name}.png")
    fig.savefig(pdf_path, bbox_inches="tight")
    fig.savefig(png_path, bbox_inches="tight", dpi=150)
    print(f"  Saved: {pdf_path}")
    print(f"  Saved: {png_path}")
    plt.close(fig)


RAW_COLUMNS = [
    "senders", "verifiers", "operation", "call_index", "gas", "role", "role_index"
]

AGGREGATED_COLUMNS = [
    "senders", "verifiers", "operation", "count",
    "first_call_gas", "avg_subsequent_gas",
    "min_gas", "max_gas", "total_gas", "per_wallet_detail"
]


def load_raw_csv(path: str) -> pd.DataFrame:
    """Load the per-call raw CSV."""
    df = pd.read_csv(path, names=RAW_COLUMNS, header=0)
    df["gas"] = pd.to_numeric(df["gas"], errors="coerce")
    df["call_index"] = pd.to_numeric(df["call_index"], errors="coerce")
    df["senders"] = pd.to_numeric(df["senders"], errors="coerce")
    df["verifiers"] = pd.to_numeric(df["verifiers"], errors="coerce")
    df["role_index"] = pd.to_numeric(df["role_index"], errors="coerce")
    return df.dropna(subset=["gas"])


def load_aggregated_csv(path: str) -> pd.DataFrame:
    """Load the aggregated CSV (one row per operation per scenario)."""
    df = pd.read_csv(path, names=AGGREGATED_COLUMNS, header=0)
    for col in ["first_call_gas", "avg_subsequent_gas", "min_gas", "max_gas", "total_gas"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["senders"] = pd.to_numeric(df["senders"], errors="coerce")
    df["verifiers"] = pd.to_numeric(df["verifiers"], errors="coerce")
    df["count"] = pd.to_numeric(df["count"], errors="coerce")
    return df


def filter_scenario(df: pd.DataFrame, senders: int, verifiers: int) -> pd.DataFrame:
    return df[(df["senders"] == senders) & (df["verifiers"] == verifiers)]


def filter_operation(df: pd.DataFrame, operation: str) -> pd.DataFrame:
    return df[df["operation"] == operation]


def get_scenarios(df: pd.DataFrame) -> list[tuple[int, int]]:
    """Return sorted list of unique (senders, verifiers) pairs."""
    pairs = df[["senders", "verifiers"]].drop_duplicates()
    return sorted(pairs.itertuples(index=False, name=None))


def pick_representative_scenario(df: pd.DataFrame) -> tuple[int, int]:
    """Pick a mid-range scenario for single-scenario plots.
    Prefers 100×100, falls back to the median available."""
    scenarios = get_scenarios(df)
    for s, v in scenarios:
        if s == 100 and v == 100:
            return (s, v)
    return scenarios[len(scenarios) // 2]



def apply_thesis_style() -> None:
    """Configure matplotlib for thesis-quality figures.

    Choices:
      - serif font (matches LaTeX Computer Modern)
      - white background (clean for print)
      - no top/right spines (less clutter)
      - grid on y-axis only (helps read values without noise)
    """
    plt.rcParams.update({
        "font.family": "serif",
        "font.size": 10,
        "axes.titlesize": 12,
        "axes.labelsize": 11,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.fontsize": 9,
        "figure.figsize": (7, 4.5),
        "figure.dpi": 150,
        "axes.grid": True,
        "grid.alpha": 0.3,
        "grid.linewidth": 0.5,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "lines.linewidth": 1.2,
        "lines.markersize": 3,
        "savefig.pad_inches": 0.1,
    })


def format_gas_axis(ax: plt.Axes, axis: str = "y") -> None:
    """Format axis to show gas values in thousands (e.g., '150k')."""
    fmt = ticker.FuncFormatter(lambda x, _: f"{x / 1000:.0f}k" if x >= 1000 else f"{x:.0f}")
    if axis == "y":
        ax.yaxis.set_major_formatter(fmt)
    else:
        ax.xaxis.set_major_formatter(fmt)



def parse_args(need_raw: bool = True, need_agg: bool = False) -> dict:
    """Parse command-line arguments for CSV paths.

    Usage patterns:
      python script.py raw.csv              (raw only)
      python script.py raw.csv agg.csv      (both)
      python script.py --agg agg.csv        (aggregated only)
    """
    args = {"raw": None, "agg": None}
    positional = [a for a in sys.argv[1:] if not a.startswith("--")]

    if need_raw and need_agg:
        if len(positional) < 2:
            print(f"Usage: python {sys.argv[0]} <raw_csv> <aggregated_csv>")
            sys.exit(1)
        args["raw"] = positional[0]
        args["agg"] = positional[1]
    elif need_raw:
        if len(positional) < 1:
            print(f"Usage: python {sys.argv[0]} <raw_csv>")
            sys.exit(1)
        args["raw"] = positional[0]
    elif need_agg:
        if len(positional) < 1:
            print(f"Usage: python {sys.argv[0]} <aggregated_csv>")
            sys.exit(1)
        args["agg"] = positional[0]

    return args
