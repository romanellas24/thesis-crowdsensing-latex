"""
Plot 1: verification_request gas vs call_index - stability under the
swap-and-pop optimization.

A naive implementation of requestAuthToVerify would iterate the entire
data array [0 .. _dataCount), skipping verified entries. That would be
O(n) per call and O(n^2) cumulative over a campaign.

PFC avoids this by maintaining `_pendingDataIds`: a compact array of
data IDs still awaiting verification. When a datum reaches majority,
`_removeFromPending` uses swap-and-pop (O(1)) to remove it, keeping the
pending list compact and short throughout the campaign.

As a result, requestAuthToVerify gas is *bounded* and largely
independent of the call index. The small residual variability comes
from:
  - cooldown skips (verifier cannot re-verify the data it just voted on)
  - reassignment of expired slots in `_findAvailableSlot`
  - shape of the pending list (which fluctuates around a steady state)

The plot makes this stability empirically visible.

Usage:
    python scripts/plots/1_plot_verification_request_stability.py \\
        path/to/<contract>_gas_simulation_results_raw.csv
"""

from commons import (
    apply_thesis_style, save_figure, parse_args,
    load_raw_csv, filter_scenario, filter_operation,
    get_scenarios, pick_extreme_scenarios, extract_contract_label,
    format_gas_axis, COLORS,
)
import matplotlib.pyplot as plt


def plot_single_scenario(df_raw, senders, verifiers, prefix):
    """Scatter plot for one scenario: call_index vs gas.

    Expected shape: a dense band of points, no upward trend.
    """
    data = filter_scenario(df_raw, senders, verifiers)
    data = filter_operation(data, "verification_request")

    if data.empty:
        print(f"  No verification_request data for {senders}S x {verifiers}V, skipping")
        return

    fig, ax = plt.subplots()
    ax.scatter(
        data["call_index"], data["gas"],
        alpha=0.3, s=2, color=COLORS["pfc"],
    )

    # Annotate the band: median +/- IQR is informative when the cloud is flat.
    q25, q50, q75 = data["gas"].quantile([0.25, 0.5, 0.75])
    ax.axhline(y=q50, color=COLORS["highlight"], linestyle="--",
               linewidth=1, alpha=0.7, label=f"Median: {q50:,.0f}")
    ax.axhspan(q25, q75, color=COLORS["highlight"], alpha=0.08,
               label=f"IQR: [{q25:,.0f}, {q75:,.0f}]")

    ax.set_xlabel("verification_request call index")
    ax.set_ylabel("Gas consumed")
    ax.set_title(f"verification_request gas, bounded ({senders}S x {verifiers}V)")
    ax.legend(loc="upper right")
    format_gas_axis(ax)

    save_figure(fig, f"verification_request_stability_{senders}s_{verifiers}v", prefix=prefix)


def plot_multi_scenario(df_raw, scenarios, prefix):
    """Overlay multiple scenarios: shows the stability holds across scales."""
    fig, ax = plt.subplots()
    palette = [COLORS["pfc"], COLORS["fifo"], COLORS["psc"], COLORS["owner"]]

    for i, (s, v) in enumerate(scenarios):
        data = filter_scenario(df_raw, s, v)
        data = filter_operation(data, "verification_request")
        if data.empty:
            continue
        color = palette[i % len(palette)]
        ax.scatter(
            data["call_index"], data["gas"],
            alpha=0.3, s=2, color=color, label=f"{s}S x {v}V",
        )

    ax.set_xlabel("verification_request call index")
    ax.set_ylabel("Gas consumed")
    ax.set_title("verification_request gas across scenarios (bounded, no growth)")
    ax.legend(markerscale=4)
    format_gas_axis(ax)

    save_figure(fig, "verification_request_stability_overlay", prefix=prefix)


def main():
    apply_thesis_style()
    args = parse_args(need_raw=True)
    prefix = extract_contract_label(args["raw"])
    print(f"Contract label: {prefix or '(unknown - no prefix)'}")

    df = load_raw_csv(args["raw"])

    # Per-scenario plots for the extremes that tell the story best
    for s, v in pick_extreme_scenarios(df):
        print(f"Scenario: {s}S x {v}V")
        plot_single_scenario(df, s, v, prefix)

    # Overlay across a few scenarios - visual cross-check that the bound holds
    scenarios = get_scenarios(df)
    if len(scenarios) > 1:
        # Pick up to 4 well-spaced scenarios
        step = max(1, len(scenarios) // 4)
        selected = scenarios[::step][:4]
        plot_multi_scenario(df, selected, prefix)


if __name__ == "__main__":
    main()
