"""
Plot 5: data_submission gas vs call_index.

Demonstrates that data submission is O(1) — each call writes to a fresh
storage slot, no iteration over existing entries. First call is slightly
higher due to storage initialization, then flat.

Designed as a direct contrast with plot 1 (verification_request which grows).
Can also overlay both operations in a single figure for maximum impact.

Usage:
    python scripts/plots/plot_data_submission_constant.py path/to/raw.csv
"""

from commons import (
    apply_thesis_style, save_figure, parse_args,
    load_raw_csv, filter_scenario, filter_operation,
    pick_representative_scenario, format_gas_axis,
)
import matplotlib.pyplot as plt
import numpy as np


def plot_submission_flat(df_raw, senders, verifiers):
    """Scatter plot showing constant gas per data submission."""
    data = filter_scenario(df_raw, senders, verifiers)
    data = filter_operation(data, "data_submission")

    if data.empty:
        print(f"  No data_submission data for {senders}S×{verifiers}V, skipping")
        return

    fig, ax = plt.subplots()

    if "role_index" in data.columns:
        first_per_sender = data.groupby("role_index")["call_index"].min()
        is_first = data.apply(
            lambda r: r["call_index"] == first_per_sender.get(r["role_index"], -1), axis=1
        )
        ax.scatter(data.loc[is_first, "call_index"], data.loc[is_first, "gas"],
                   alpha=0.5, s=4, color="#dc2626", label="First per sender")
        ax.scatter(data.loc[~is_first, "call_index"], data.loc[~is_first, "gas"],
                   alpha=0.3, s=2, color="#16a34a", label="Subsequent")
    else:
        ax.scatter(data["call_index"], data["gas"], alpha=0.3, s=2, color="#16a34a")



    # Add average line
    avg = data["gas"].mean()
    ax.axhline(y=avg, color="#dc2626", linestyle="--", linewidth=1, alpha=0.7,
               label=f"Average: {avg:,.0f}")

    ax.set_xlabel("Data submission call index")
    ax.set_ylabel("Gas consumed")
    ax.set_title(f"data_submission gas — constant O(1) ({senders}S × {verifiers}V)")
    ax.legend()
    format_gas_axis(ax)

    save_figure(fig, f"data_submission_constant_{senders}s_{verifiers}v")


def plot_submission_vs_verification(df_raw, senders, verifiers):
    """Side-by-side: data_submission (flat) vs verification_request (growing).
    This is the most impactful comparison for the thesis."""
    scenario = filter_scenario(df_raw, senders, verifiers)
    sub_data = filter_operation(scenario, "data_submission")
    ver_data = filter_operation(scenario, "verification_request")

    if sub_data.empty or ver_data.empty:
        print(f"  Missing data for comparison in {senders}S×{verifiers}V, skipping")
        return

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.5))

    # Left: data_submission
    ax1.scatter(sub_data["call_index"], sub_data["gas"], alpha=0.3, s=2, color="#16a34a")
    avg_sub = sub_data["gas"].mean()
    ax1.axhline(y=avg_sub, color="#dc2626", linestyle="--", linewidth=1, alpha=0.7)
    ax1.set_xlabel("Call index")
    ax1.set_ylabel("Gas consumed")
    ax1.set_title("data_submission — O(1)")
    format_gas_axis(ax1)

    # Right: verification_request
    ax2.scatter(ver_data["call_index"], ver_data["gas"], alpha=0.3, s=2, color="#2563eb")
    ax2.set_xlabel("Call index")
    ax2.set_ylabel("Gas consumed")
    ax2.set_title("verification_request")
    format_gas_axis(ax2)

    fig.suptitle(f"Submission vs verification gas scaling ({senders}S × {verifiers}V)",
                 fontsize=12, y=1.02)
    fig.tight_layout()

    save_figure(fig, f"submission_vs_verification_{senders}s_{verifiers}v")


def plot_submission_rolling_average(df_raw, senders, verifiers):
    """Rolling average to smooth out noise and highlight the first-call spike."""
    data = filter_scenario(df_raw, senders, verifiers)
    data = filter_operation(data, "data_submission").sort_values("call_index")

    if len(data) < 50:
        return

    window = max(50, len(data) // 100)
    rolling = data["gas"].rolling(window=window).mean()

    fig, ax = plt.subplots()
    ax.plot(data["call_index"].values, rolling.values, color="#16a34a", linewidth=1.5)
    ax.scatter(data["call_index"].values[:1], data["gas"].values[:1],
               color="#dc2626", s=30, zorder=5, label=f"First call: {data['gas'].values[0]:,}")

    ax.set_xlabel("Call index")
    ax.set_ylabel(f"Gas (rolling avg, window={window})")
    ax.set_title(f"data_submission rolling average ({senders}S × {verifiers}V)")
    ax.legend()
    format_gas_axis(ax)

    save_figure(fig, f"data_submission_rolling_{senders}s_{verifiers}v")


def main():
    apply_thesis_style()
    args = parse_args(need_raw=True)
    df = load_raw_csv(args["raw"])

    s, v = pick_representative_scenario(df)
    print(f"Representative scenario: {s}S × {v}V")
    plot_submission_flat(df, s, v)
    plot_submission_vs_verification(df, s, v)
    plot_submission_rolling_average(df, s, v)

    s = 1
    v = 2
    print(f"Base scenario: {s}S × {v}V")

    plot_submission_flat(df, s, v)
    plot_submission_vs_verification(df, s, v)
    plot_submission_rolling_average(df, s, v)


if __name__ == "__main__":
    main()
