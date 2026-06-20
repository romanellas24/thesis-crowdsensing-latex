"""
Plot 2: verification_submit gas vs call_index.

Shows periodic spikes when a submission triggers majority consensus.
At that point _rewardCorrectVerifiers iterates all completed slots and
executes DST transfers, causing significantly higher gas than normal
submissions.

Usage:
    python scripts/plots/plot_verification_submit_spikes.py path/to/raw.csv
"""

from commons import (
    apply_thesis_style, save_figure, parse_args,
    load_raw_csv, filter_scenario, filter_operation,
    pick_representative_scenario, format_gas_axis,
)
import matplotlib.pyplot as plt
import numpy as np


def plot_submit_spikes(df_raw, senders, verifiers):
    """Scatter plot showing gas spikes when majority is triggered."""
    data = filter_scenario(df_raw, senders, verifiers)
    data = filter_operation(data, "verification_submit")

    if data.empty:
        print(f"  No verification_submit data for {senders}S×{verifiers}V, skipping")
        return

    gas = data["gas"].values
    call_idx = data["call_index"].values

    # Classify: spike if gas > median + 2*std
    median_gas = np.median(gas)
    std_gas = np.std(gas)
    threshold = median_gas + 2 * std_gas
    is_spike = gas > threshold

    fig, ax = plt.subplots()

    # Normal points
    ax.scatter(
        call_idx[~is_spike], gas[~is_spike],
        alpha=0.3, s=2, color="#64748b", label="Regular submit"
    )
    # Spikes
    ax.scatter(
        call_idx[is_spike], gas[is_spike],
        alpha=0.7, s=8, color="#dc2626", label="Majority triggered"
    )

    ax.axhline(y=threshold, color="#dc2626", linestyle="--", linewidth=0.8, alpha=0.5)

    ax.set_xlabel("Verification submit call index")
    ax.set_ylabel("Gas consumed")
    ax.set_title(f"verification_submit gas spikes ({senders}S × {verifiers}V)")
    ax.legend(markerscale=3)
    format_gas_axis(ax)

    save_figure(fig, f"verification_submit_spikes_{senders}s_{verifiers}v")


def plot_submit_histogram(df_raw, senders, verifiers):
    """Histogram showing bimodal distribution: regular vs majority-triggering."""
    data = filter_scenario(df_raw, senders, verifiers)
    data = filter_operation(data, "verification_submit")

    if data.empty:
        return

    fig, ax = plt.subplots()
    ax.hist(data["gas"], bins=50, color="#2563eb", alpha=0.7, edgecolor="white")
    ax.set_xlabel("Gas consumed")
    ax.set_ylabel("Frequency")
    ax.set_title(f"verification_submit gas distribution ({senders}S × {verifiers}V)")
    format_gas_axis(ax, axis="x")

    save_figure(fig, f"verification_submit_histogram_{senders}s_{verifiers}v")


def main():
    apply_thesis_style()
    args = parse_args(need_raw=True)
    df = load_raw_csv(args["raw"])

    s, v = pick_representative_scenario(df)
    print(f"Representative scenario: {s}S × {v}V")
    plot_submit_spikes(df, s, v)
    plot_submit_histogram(df, s, v)


if __name__ == "__main__":
    main()
