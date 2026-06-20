"""
Plot 1: verification_request gas vs call_index.

Demonstrates that requestAuthToVerify gas grows linearly because the
on-chain loop scans from `start` to `_dataCount`, skipping verified entries.
O(n) per call, O(n²) cumulative. This is the main scalability finding.

Usage:
    python scripts/plots/plot_verification_request_growth.py path/to/raw.csv
"""

from commons import (
    apply_thesis_style, save_figure, parse_args,
    load_raw_csv, filter_scenario, filter_operation,
    get_scenarios, pick_representative_scenario, format_gas_axis,
)
import matplotlib.pyplot as plt


def plot_single_scenario(df_raw, senders, verifiers):
    """Scatter plot for one scenario: call_index vs gas."""
    data = filter_scenario(df_raw, senders, verifiers)
    data = filter_operation(data, "verification_request")

    if data.empty:
        print(f"  No verification_request data for {senders}S×{verifiers}V, skipping")
        return

    fig, ax = plt.subplots()
    ax.scatter(data["call_index"], data["gas"], alpha=0.3, s=2, color="#2563eb")

    ax.set_xlabel("Verification request call index")
    ax.set_ylabel("Gas consumed")
    ax.set_title(f"verification_request gas scenario ({senders}S × {verifiers}V)")
    format_gas_axis(ax)

    save_figure(fig, f"verification_request_gas_{senders}s_{verifiers}v")


def plot_multi_scenario(df_raw, scenarios):
    """Overlay multiple scenarios to show the growth pattern is consistent."""
    fig, ax = plt.subplots()
    colors = ["#2563eb", "#dc2626", "#16a34a", "#f59e0b", "#8b5cf6", "#ec4899"]

    for i, (s, v) in enumerate(scenarios):
        data = filter_scenario(df_raw, s, v)
        data = filter_operation(data, "verification_request")
        if data.empty:
            continue
        color = colors[i % len(colors)]
        ax.scatter(
            data["call_index"], data["gas"],
            alpha=0.3, s=2, color=color, label=f"{s}S×{v}V"
        )

    ax.set_xlabel("Verification request call index")
    ax.set_ylabel("Gas consumed")
    ax.set_title("verification_request gas level by verifier count")
    ax.legend(markerscale=4)
    format_gas_axis(ax)

    save_figure(fig, "verification_request_growth_comparison")


def main():
    apply_thesis_style()
    args = parse_args(need_raw=True)
    df = load_raw_csv(args["raw"])

    # Single representative scenario
    s, v = pick_representative_scenario(df)
    print(f"Representative scenario: {s}S × {v}V")
    plot_single_scenario(df, s, v)

    # Multi-scenario comparison (pick up to 4 diverse scenarios)
    scenarios = get_scenarios(df)
    # Filter to scenarios with same sender count but different verifiers
    if len(scenarios) > 1:
        selected = scenarios[:min(4, len(scenarios))]
        plot_multi_scenario(df, selected)


    for s, v in [(1, 2), (10, 2)]:
        if (s, v) in [(x, y) for x, y in get_scenarios(df)]:
            print(f"Low-verifier scenario: {s}S × {v}V")
            plot_single_scenario(df, s, v)


if __name__ == "__main__":
    main()
