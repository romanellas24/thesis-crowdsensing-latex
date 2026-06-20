"""
Shared utilities for gas simulation plotting scripts.

Responsibilities:
  - CSV loading for both aggregated and raw results, single or multi-contract
  - Consistent matplotlib styling (thesis-quality, PDF-ready)
  - Output path management with contract-name prefix to avoid overwrites
  - Filtering and scenario-selection helpers

Usage:
  Single-contract scripts:
    python scripts/plots/1_*.py path/to/raw.csv [path/to/aggregated.csv]
  Multi-contract scripts:
    python scripts/plots/6_*.py path/to/pfc_*.csv path/to/fifo_*.csv [path/to/psc_*.csv]
"""

import sys
import os
import re
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

FIGURES_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "figures", "generated")

# EIP-7825 per-transaction gas cap, active from Fusaka.
# Cited in the thesis as the cap that makes FIFO infeasible on mainnet.
EIP_7825_CAP = 16_777_216

# Canonical color palette, shared across all plots.
# Contracts get distinct hues; operations re-use a smaller subset.
COLORS = {
    "pfc":  "#2563eb",  # blue
    "fifo": "#dc2626",  # red
    "psc":  "#16a34a",  # green
    "owner":    "#f59e0b",  # amber
    "sender":   "#2563eb",
    "verifier": "#dc2626",
    "first":      "#2563eb",
    "subsequent": "#64748b",  # slate
    "spike":      "#dc2626",
    "regular":    "#64748b",
    "highlight":  "#dc2626",
    "cap_line":   "#7c3aed",  # purple, for EIP-7825 horizontal line
}


# ---------------------------------------------------------------------------
# Output management
# ---------------------------------------------------------------------------

def ensure_output_dir() -> str:
    os.makedirs(FIGURES_DIR, exist_ok=True)
    return FIGURES_DIR


def save_figure(fig: plt.Figure, name: str, prefix: str = "") -> None:
    """Save figure as PDF (vector, LaTeX-native) and PNG (preview).

    If `prefix` is provided (e.g., "pfc", "fifo", "psc"), it is prepended
    to the filename so that running the same script with different CSVs
    doesn't overwrite previous outputs.
    """
    out = ensure_output_dir()
    fname = f"{prefix}_{name}" if prefix else name
    pdf_path = os.path.join(out, f"{fname}.pdf")
    png_path = os.path.join(out, f"{fname}.png")
    fig.savefig(pdf_path, bbox_inches="tight")
    fig.savefig(png_path, bbox_inches="tight", dpi=150)
    print(f"  Saved: {pdf_path}")
    print(f"  Saved: {png_path}")
    plt.close(fig)


def extract_contract_label(csv_path: str) -> str:
    """Heuristically extract the contract name from a CSV filename.

    Looks for 'pfc', 'fifo', or 'psc' as a token in the filename.
    Returns empty string if no match (caller can fall back to empty prefix).
    """
    base = os.path.basename(csv_path).lower()
    for label in ("pfc", "fifo", "psc"):
        if re.search(rf"\b{label}\b|(?:^|[_-]){label}(?:[_-]|$)", base):
            return label
    return ""


# ---------------------------------------------------------------------------
# CSV loading
# ---------------------------------------------------------------------------

RAW_COLUMNS = [
    "senders", "verifiers", "operation", "call_index", "gas", "role", "role_index"
]

AGGREGATED_COLUMNS = [
    "senders", "verifiers", "operation", "count",
    "first_call_gas", "avg_subsequent_gas",
    "min_gas", "max_gas", "total_gas", "per_wallet_detail"
]


def load_raw_csv(path: str) -> pd.DataFrame:
    """Load the per-call raw CSV. Numeric columns coerced; bad rows dropped."""
    df = pd.read_csv(path, names=RAW_COLUMNS, header=0)
    for col in ["senders", "verifiers", "call_index", "gas", "role_index"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.dropna(subset=["gas"])


def load_aggregated_csv(path: str) -> pd.DataFrame:
    """Load the aggregated CSV (one row per operation per scenario)."""
    df = pd.read_csv(path, names=AGGREGATED_COLUMNS, header=0)
    for col in ["senders", "verifiers", "count",
                "first_call_gas", "avg_subsequent_gas",
                "min_gas", "max_gas", "total_gas"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def load_multi_aggregated(paths: list[str]) -> dict[str, pd.DataFrame]:
    """Load multiple aggregated CSVs, keyed by inferred contract label.

    Skips paths whose contract label is unknown (with a warning).
    """
    out = {}
    for p in paths:
        label = extract_contract_label(p)
        if not label:
            print(f"  Warning: cannot infer contract from {p}, skipping")
            continue
        out[label] = load_aggregated_csv(p)
    return out


def load_multi_raw(paths: list[str]) -> dict[str, pd.DataFrame]:
    """Multi-contract version of load_raw_csv."""
    out = {}
    for p in paths:
        label = extract_contract_label(p)
        if not label:
            print(f"  Warning: cannot infer contract from {p}, skipping")
            continue
        out[label] = load_raw_csv(p)
    return out


# ---------------------------------------------------------------------------
# Filtering and scenario selection
# ---------------------------------------------------------------------------

def filter_scenario(df: pd.DataFrame, senders: int, verifiers: int) -> pd.DataFrame:
    return df[(df["senders"] == senders) & (df["verifiers"] == verifiers)]


def filter_operation(df: pd.DataFrame, operation: str) -> pd.DataFrame:
    return df[df["operation"] == operation]


def get_scenarios(df: pd.DataFrame) -> list[tuple[int, int]]:
    """Sorted unique (senders, verifiers) pairs."""
    pairs = df[["senders", "verifiers"]].drop_duplicates()
    return sorted((int(s), int(v)) for s, v in pairs.itertuples(index=False, name=None))


def pick_representative_scenario(df: pd.DataFrame) -> tuple[int, int]:
    """A mid-range scenario for single-scenario plots.

    Prefers 100x100 (if present), else the median scenario by total participants.
    """
    scenarios = get_scenarios(df)
    if (100, 100) in scenarios:
        return (100, 100)
    return scenarios[len(scenarios) // 2]


def pick_extreme_scenarios(df: pd.DataFrame) -> list[tuple[int, int]]:
    """Selected scenarios that best illustrate the thesis findings:
      - smallest (1x2): bare-bones, isolates algorithmic cost
      - largest (1000x1000): stress test, reveals scaling behavior
      - mid (100x100): typical mid-range deployment
    Filters out scenarios not present in df.
    """
    available = set(get_scenarios(df))
    candidates = [(1, 2), (100, 100), (1000, 1000)]
    return [c for c in candidates if c in available]


def shared_scenarios(dfs: dict[str, pd.DataFrame]) -> list[tuple[int, int]]:
    """Scenarios present in ALL provided dataframes. Useful for fair multi-contract overlay."""
    if not dfs:
        return []
    shared = set(get_scenarios(next(iter(dfs.values()))))
    for df in dfs.values():
        shared &= set(get_scenarios(df))
    return sorted(shared)


# ---------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------

def apply_thesis_style() -> None:
    """Configure matplotlib for thesis-quality figures.

    Choices:
      - serif font (matches LaTeX Computer Modern)
      - white background (clean for print)
      - no top/right spines (less clutter)
      - subtle grid on y-axis only (helps read values without noise)
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
    """Format axis to show gas values in human-readable units (k or M)."""
    def fmt_fn(x, _):
        if x >= 1_000_000:
            return f"{x / 1_000_000:.1f}M"
        if x >= 1_000:
            return f"{x / 1_000:.0f}k"
        return f"{x:.0f}"
    fmt = ticker.FuncFormatter(fmt_fn)
    if axis == "y":
        ax.yaxis.set_major_formatter(fmt)
    else:
        ax.xaxis.set_major_formatter(fmt)


def annotate_eip7825_cap(ax: plt.Axes, label: str = "EIP-7825 cap (≈16.78M)") -> None:
    """Add a horizontal line at the EIP-7825 per-transaction gas cap.

    Used in plots where exceeding this line means the contract is infeasible
    on Ethereum mainnet post-Fusaka.
    """
    ax.axhline(
        y=EIP_7825_CAP, color=COLORS["cap_line"], linestyle="--",
        linewidth=1.2, alpha=0.8, label=label,
    )


# ---------------------------------------------------------------------------
# CLI argument parsing
# ---------------------------------------------------------------------------

def parse_args(need_raw: bool = True, need_agg: bool = False) -> dict:
    """Parse CLI args for single-contract scripts.

    Usage patterns:
      python script.py raw.csv              (raw only)
      python script.py raw.csv agg.csv      (both)
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


def parse_multi_args(min_paths: int = 2) -> list[str]:
    """Parse CLI args for multi-contract scripts: a list of CSV paths.

    The contract name is inferred from the filename via `extract_contract_label`.
    """
    positional = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(positional) < min_paths:
        print(f"Usage: python {sys.argv[0]} <csv1> <csv2> [<csv3>] ...")
        print(f"       (filenames must contain 'pfc', 'fifo', or 'psc')")
        sys.exit(1)
    return positional
