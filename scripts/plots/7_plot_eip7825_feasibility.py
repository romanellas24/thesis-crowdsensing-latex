"""
Plot 7: PFC vs FIFO, max gas vs EIP-7825 cap - feasibility argument.

Plot 6 shows the distribution; plot 7 makes a single binary claim
visually unmistakable: in every scenario, FIFO's worst-case
verification_submit exceeds the EIP-7825 per-transaction cap
(2^24 ≈ 16.78 Mgas, active from Ethereum's Fusaka hard fork). PFC's
worst case stays orders of magnitude below the cap.

This is the *feasibility* argument for the swap-and-pop optimization.
Without it, the contract is not just inefficient - it cannot be
deployed on mainnet at this workload scale. Calls that exceed the
cap revert at protocol level, not at gas-limit level: no amount of
sending more gas can rescue them.

The bars show max(verification_submit gas) per scenario, side by side
for PFC and FIFO. The cap is annotated as a horizontal reference line.
A second chart shows the same data normalised to "multiples of the
cap" - a single number that captures how badly FIFO blows past the
limit.

Usage:
    python scripts/plots/7_plot_eip7825_feasibility.py \\
        path/to/pfc_..._results.csv path/to/fifo_..._results.csv
"""

from commons import (
    apply_thesis_style, save_figure, parse_multi_args,
    load_multi_aggregated, shared_scenarios,
    format_gas_axis, EIP_7825_CAP, COLORS,
)
import matplotlib.pyplot as plt
import numpy as np


def _extract_max_submit(df_agg, scenarios):
    """For each scenario, return max_gas of verification_submit."""
    out = []
    for s, v in scenarios:
        row = df_agg[
            (df_agg["senders"] == s) &
            (df_agg["verifiers"] == v) &
            (df_agg["operation"] == "verification_submit")
        ]
        if row.empty:
            out.append(np.nan)
        else:
            out.append(float(row.iloc[0]["max_gas"]))
    return out


def plot_max_submit_bars(aggs):
    """Grouped bar chart of max verification_submit gas per scenario,
    with the EIP-7825 cap drawn as a horizontal reference line.
    """
    if "pfc" not in aggs or "fifo" not in aggs:
        print("  Need both pfc and fifo aggregated CSVs; skipping")
        return

    scenarios = shared_scenarios({k: aggs[k] for k in ("pfc", "fifo")})
    if not scenarios:
        print("  No shared scenarios; skipping")
        return

    pfc_max = _extract_max_submit(aggs["pfc"], scenarios)
    fifo_max = _extract_max_submit(aggs["fifo"], scenarios)

    labels = [f"{s}x{v}" for s, v in scenarios]
    x = np.arange(len(scenarios))
    width = 0.4

    fig_w = max(10, 0.55 * len(labels) + 3)
    fig, ax = plt.subplots(figsize=(fig_w, 5))

    ax.bar(x - width / 2, pfc_max, width, label="PFC", color=COLORS["pfc"])
    ax.bar(x + width / 2, fifo_max, width, label="FIFO", color=COLORS["fifo"])

    ax.axhline(y=EIP_7825_CAP, color=COLORS["cap_line"], linestyle="--",
               linewidth=1.5, alpha=0.9,
               label=f"EIP-7825 cap ({EIP_7825_CAP / 1e6:.2f} Mgas)")

    ax.set_yscale("log")
    ax.set_xlabel("Scenario (senders x verifiers)")
    ax.set_ylabel("Max verification_submit gas (log scale)")
    ax.set_title("Worst-case verification_submit gas vs EIP-7825 cap")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
    ax.legend(loc="upper left")
    format_gas_axis(ax)

    save_figure(fig, "eip7825_feasibility_bars")


def plot_max_submit_normalized(aggs):
    """Same data as `plot_max_submit_bars` but normalised: max_gas / cap.

    Values > 1.0 are scenarios where the contract is INFEASIBLE under
    Fusaka. PFC bars should be far below 1.0; FIFO bars should be
    consistently above 1.0.
    """
    if "pfc" not in aggs or "fifo" not in aggs:
        return

    scenarios = shared_scenarios({k: aggs[k] for k in ("pfc", "fifo")})
    if not scenarios:
        return

    pfc_norm = [g / EIP_7825_CAP if not np.isnan(g) else 0
                for g in _extract_max_submit(aggs["pfc"], scenarios)]
    fifo_norm = [g / EIP_7825_CAP if not np.isnan(g) else 0
                 for g in _extract_max_submit(aggs["fifo"], scenarios)]

    labels = [f"{s}x{v}" for s, v in scenarios]
    x = np.arange(len(scenarios))
    width = 0.4

    fig_w = max(10, 0.55 * len(labels) + 3)
    fig, ax = plt.subplots(figsize=(fig_w, 5))

    ax.bar(x - width / 2, pfc_norm, width, label="PFC", color=COLORS["pfc"])
    ax.bar(x + width / 2, fifo_norm, width, label="FIFO", color=COLORS["fifo"])

    ax.axhline(y=1.0, color=COLORS["cap_line"], linestyle="--",
               linewidth=1.5, alpha=0.9, label="EIP-7825 cap")

    ax.set_yscale("log")
    ax.set_xlabel("Scenario (senders x verifiers)")
    ax.set_ylabel("max(verification_submit) / EIP-7825 cap")
    ax.set_title("Feasibility ratio: above 1.0 means infeasible on Fusaka")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
    ax.legend(loc="upper left")

    save_figure(fig, "eip7825_feasibility_normalized")


def main():
    apply_thesis_style()
    paths = parse_multi_args(min_paths=2)
    aggs = load_multi_aggregated(paths)
    print(f"Contracts loaded: {list(aggs.keys())}")

    plot_max_submit_bars(aggs)
    plot_max_submit_normalized(aggs)


if __name__ == "__main__":
    main()
