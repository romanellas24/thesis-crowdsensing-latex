"""
Plot 6: PFC vs FIFO, verification_submit gas - the money plot of section 4.1.3.

This is the single most important figure of the gas analysis chapter:
the empirical proof that swap-and-pop's O(1) removal versus FIFO's
O(n) shift produces a difference of two orders of magnitude on
verification_submit, the protocol's hottest function.

Plot structure:
  - x: call index of verification_submit (0 .. 20 000)
  - y: gas consumed (log scale, because the regimes span 50 kgas to
       tens of millions)
  - blue cloud: PFC (swap-and-pop). Tightly clustered around the
       baseline 50 kgas + moderate spikes (~200 kgas) when majority
       triggers _removeFromPending and reward distribution.
  - red cloud: FIFO (shift). Same baseline, but the majority-triggering
       spikes follow an envelope that scales linearly with the current
       pending-list size - the leading edge starts around 50 Mgas (early
       removals on a 10 000-long pending list) and decays as the list
       shrinks.

The EIP-7825 cap line (16.78 Mgas) sits between the two clouds: FIFO
spikes cross it routinely in the early phase, PFC never approaches it.
This is the empirical evidence that the swap-and-pop optimization is
not merely a gas saving but a *feasibility requirement* under Fusaka.

Usage:
    python scripts/plots/6_plot_pfc_vs_fifo_submit.py \\
        path/to/pfc_..._raw.csv path/to/fifo_..._raw.csv
"""

from commons import (
    apply_thesis_style, save_figure, parse_multi_args,
    load_multi_raw, filter_scenario, filter_operation,
    pick_extreme_scenarios, format_gas_axis,
    annotate_eip7825_cap, EIP_7825_CAP, COLORS,
)
import matplotlib.pyplot as plt
import numpy as np


def plot_overlay(raws, senders, verifiers):
    """Overlay verification_submit gas vs call_index for PFC and FIFO."""
    if "pfc" not in raws or "fifo" not in raws:
        print("  Need both pfc and fifo raw CSVs; skipping overlay")
        return

    fig, ax = plt.subplots(figsize=(8, 5))

    for label in ("pfc", "fifo"):
        data = filter_scenario(raws[label], senders, verifiers)
        data = filter_operation(data, "verification_submit")
        if data.empty:
            continue
        ax.scatter(
            data["call_index"], data["gas"],
            alpha=0.4 if label == "pfc" else 0.3,
            s=4 if label == "pfc" else 2,
            color=COLORS[label],
            label=label.upper(),
        )

    annotate_eip7825_cap(ax)

    ax.set_yscale("log")
    ax.set_xlabel("verification_submit call index")
    ax.set_ylabel("Gas consumed (log scale)")
    ax.set_title(f"PFC vs FIFO: verification_submit gas ({senders}S x {verifiers}V)")
    ax.legend(markerscale=3, loc="upper right")
    format_gas_axis(ax)

    save_figure(fig, f"pfc_vs_fifo_submit_overlay_{senders}s_{verifiers}v")


def plot_envelope_comparison(raws, senders, verifiers):
    """Rolling p99 envelope for both contracts, on log scale.

    The p99 hides the constant baseline and emphasises the upper tail -
    where FIFO is dramatically more expensive.
    """
    if "pfc" not in raws or "fifo" not in raws:
        return

    fig, ax = plt.subplots(figsize=(8, 5))

    for label in ("pfc", "fifo"):
        data = filter_scenario(raws[label], senders, verifiers)
        data = filter_operation(data, "verification_submit").sort_values("call_index")
        if len(data) < 100:
            continue
        window = max(100, len(data) // 50)
        rolling_p99 = data["gas"].rolling(window=window).quantile(0.99)
        ax.plot(
            data["call_index"].values, rolling_p99.values,
            color=COLORS[label], linewidth=1.8,
            label=f"{label.upper()} (rolling p99, window={window})",
        )

    annotate_eip7825_cap(ax)

    ax.set_yscale("log")
    ax.set_xlabel("verification_submit call index")
    ax.set_ylabel("Gas, rolling p99 (log scale)")
    ax.set_title(f"PFC vs FIFO: upper-tail envelope ({senders}S x {verifiers}V)")
    ax.legend(loc="lower left")
    format_gas_axis(ax)

    save_figure(fig, f"pfc_vs_fifo_submit_envelope_{senders}s_{verifiers}v")


def main():
    apply_thesis_style()
    paths = parse_multi_args(min_paths=2)
    raws = load_multi_raw(paths)
    print(f"Contracts loaded: {list(raws.keys())}")

    if "pfc" not in raws or "fifo" not in raws:
        print("Need both PFC and FIFO raw CSVs. Aborting.")
        return

    # Shared scenarios between PFC and FIFO
    pfc_scen = set([(int(s), int(v)) for s, v in raws["pfc"][["senders","verifiers"]].drop_duplicates().itertuples(index=False, name=None)])
    fifo_scen = set([(int(s), int(v)) for s, v in raws["fifo"][["senders","verifiers"]].drop_duplicates().itertuples(index=False, name=None)])
    shared = sorted(pfc_scen & fifo_scen)

    # Plot the extremes that best tell the story
    extremes = pick_extreme_scenarios(raws["pfc"])
    targets = [s for s in extremes if s in shared]

    for s, v in targets:
        print(f"Scenario: {s}S x {v}V")
        plot_overlay(raws, s, v)
        plot_envelope_comparison(raws, s, v)


if __name__ == "__main__":
    main()
