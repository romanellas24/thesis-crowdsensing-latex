"""
Plot 9: Gas scaling for core operations across all three contracts.

Wraps up the comparative story by showing, for each core operation,
how average gas evolves as the workload grows. Three lines per
subplot, one per contract (PFC, FIFO, PSC).

Key observations the figure should evidence:

  data_submission: stable across all scenarios for every contract.
    O(1). FIFO is slightly cheaper (no _pendingIndex update). PSC
    is slightly more expensive (reward decay).

  verification_request: stable across all scenarios for PFC and PSC.
    Slight variation for FIFO due to the different ordering of
    _pendingDataIds (FIFO is order-preserving, the cooldown skip is
    contiguous in the loop instead of scattered).

  verification_submit: stable for PFC and PSC. For FIFO, the *average*
    is much higher (~14 Mgas), and stable across scenarios because
    the cost is driven by TOTAL_CIDS, not by senders/verifiers.

This subplot grid is the visual summary of section 4.1: per-operation,
per-contract, per-scale. It is the table that you can read at a glance.

Usage:
    python scripts/plots/9_plot_gas_scaling_three_contracts.py \\
        path/to/pfc_..._results.csv path/to/fifo_..._results.csv \\
        [path/to/psc_..._results.csv]
"""

from commons import (
    apply_thesis_style, save_figure, parse_multi_args,
    load_multi_aggregated, format_gas_axis, COLORS,
)
import matplotlib.pyplot as plt
import numpy as np

CORE_OPS = ["data_submission", "verification_request", "verification_submit"]

OP_TITLES = {
    "data_submission":      "data_submission (publishIpfsCid)",
    "verification_request": "verification_request (requestAuthToVerify)",
    "verification_submit":  "verification_submit (submitVerifyResult)",
}


def _series_by_scenario(df, op):
    """Return {(senders, verifiers): avg_subsequent_gas} for one operation."""
    rows = df[df["operation"] == op]
    out = {}
    for _, r in rows.iterrows():
        key = (int(r["senders"]), int(r["verifiers"]))
        out[key] = float(r["avg_subsequent_gas"])
    return out


def plot_scaling_grid(aggs):
    """One subplot per core operation; one line per contract."""
    contracts = [c for c in ("pfc", "fifo", "psc") if c in aggs]
    if not contracts:
        print("  No contracts loaded; skipping")
        return

    fig, axes = plt.subplots(1, len(CORE_OPS), figsize=(15, 4.5), sharex=True)
    if len(CORE_OPS) == 1:
        axes = [axes]

    for ax, op in zip(axes, CORE_OPS):
        # Union of scenarios across all loaded contracts (sorted).
        all_keys = set()
        for c in contracts:
            all_keys |= set(_series_by_scenario(aggs[c], op).keys())
        scenarios = sorted(all_keys)

        # Stable x-axis: total participants (s + v) as a proxy for "scale"
        x_vals = [s + v for s, v in scenarios]
        labels = [f"{s}+{v}" for s, v in scenarios]

        for c in contracts:
            series = _series_by_scenario(aggs[c], op)
            y_vals = [series.get(k, np.nan) for k in scenarios]
            ax.plot(
                range(len(x_vals)), y_vals,
                marker="o", color=COLORS[c],
                label=c.upper(), linewidth=1.8,
            )

        ax.set_title(OP_TITLES.get(op, op), fontsize=10)
        ax.set_xlabel("Scenario (senders + verifiers)")
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=7)

        # Log scale only when the range spans more than ~30x -
        # otherwise it compresses the comparison too much.
        valid = [v for v in [
            series.get(k, np.nan)
            for c in contracts
            for k in scenarios
            for series in [_series_by_scenario(aggs[c], op)]
        ] if not np.isnan(v) and v > 0]
        if valid and (max(valid) / min(valid)) > 30:
            ax.set_yscale("log")

        format_gas_axis(ax)
        ax.legend(loc="best", fontsize=8)

    axes[0].set_ylabel("Average gas (subsequent)")
    fig.suptitle("Core operations: gas scaling across contracts and scenarios",
                 fontsize=12, y=1.02)
    fig.tight_layout()

    save_figure(fig, "gas_scaling_three_contracts_grid")


def plot_scaling_per_op(aggs):
    """Also produce one standalone figure per core op (handy for LaTeX inclusion)."""
    contracts = [c for c in ("pfc", "fifo", "psc") if c in aggs]
    if not contracts:
        return

    for op in CORE_OPS:
        all_keys = set()
        for c in contracts:
            all_keys |= set(_series_by_scenario(aggs[c], op).keys())
        scenarios = sorted(all_keys)
        if not scenarios:
            continue
        labels = [f"{s}+{v}" for s, v in scenarios]

        fig, ax = plt.subplots(figsize=(8, 4.5))
        for c in contracts:
            series = _series_by_scenario(aggs[c], op)
            y_vals = [series.get(k, np.nan) for k in scenarios]
            ax.plot(
                range(len(scenarios)), y_vals,
                marker="o", color=COLORS[c],
                label=c.upper(), linewidth=1.8,
            )

        valid = [series.get(k, np.nan)
                 for c in contracts
                 for k in scenarios
                 for series in [_series_by_scenario(aggs[c], op)]]
        valid = [v for v in valid if not np.isnan(v) and v > 0]
        if valid and (max(valid) / min(valid)) > 30:
            ax.set_yscale("log")

        ax.set_title(OP_TITLES.get(op, op))
        ax.set_xlabel("Scenario (senders + verifiers)")
        ax.set_ylabel("Average gas (subsequent)")
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
        ax.legend(loc="best")
        format_gas_axis(ax)

        save_figure(fig, f"gas_scaling_{op}")


def main():
    apply_thesis_style()
    paths = parse_multi_args(min_paths=2)
    aggs = load_multi_aggregated(paths)
    print(f"Contracts loaded: {list(aggs.keys())}")

    plot_scaling_grid(aggs)
    plot_scaling_per_op(aggs)


if __name__ == "__main__":
    main()
