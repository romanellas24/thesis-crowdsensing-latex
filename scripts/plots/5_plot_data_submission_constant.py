"""
Plot 5: data_submission gas, constant O(1) per call.

publishIpfsCid performs a fixed amount of work per call:
  - DataEntry struct write (packed into one 32-byte slot)
  - _pendingDataIds.push and _pendingIndex update (or just .push in
    the FIFO baseline, which omits the index map)
  - One increment to `_dataCount`
  - One bond decrement
  - emit DataVerificationRequestedEvent

None of these depend on the size of any pre-existing collection - every
call writes to fresh slots indexed by the new dataId. The plot confirms
this empirically: a flat band of points, with a higher first call per
sender (the slot-creation premium when initializing that sender's
`SenderInformation` mapping for the first time).

The cost is also independent of the scenario size: the rolling average
plot makes the steady-state visible after the initial slot-init premium
fades.

This contrasts cleanly with verification_submit (plot 2), where the
spike-vs-regular regime structure is a function of when majority is
reached.

Usage:
    python scripts/plots/5_plot_data_submission_constant.py \\
        path/to/<contract>_gas_simulation_results_raw.csv
"""

from commons import (
    apply_thesis_style, save_figure, parse_args,
    load_raw_csv, filter_scenario, filter_operation,
    pick_extreme_scenarios, extract_contract_label,
    format_gas_axis, COLORS,
)
import matplotlib.pyplot as plt


def plot_submission_flat(df_raw, senders, verifiers, prefix):
    """Scatter showing first-per-sender vs subsequent submissions.

    The first call from each sender writes a fresh `SenderInformation`
    mapping entry, so it pays the cold-storage premium. Subsequent
    submissions from the same sender (and all submissions from senders
    that already exist) pay only the per-call constant.
    """
    data = filter_scenario(df_raw, senders, verifiers)
    data = filter_operation(data, "data_submission").copy()

    if data.empty:
        print(f"  No data_submission data for {senders}S x {verifiers}V, skipping")
        return

    fig, ax = plt.subplots()

    if "role_index" in data.columns and data["role_index"].notna().any():
        # Vectorized first-per-sender detection (no row-wise apply).
        first_idx = data.groupby("role_index")["call_index"].transform("min")
        is_first = data["call_index"].eq(first_idx)

        ax.scatter(
            data.loc[is_first, "call_index"], data.loc[is_first, "gas"],
            alpha=0.6, s=6, color=COLORS["first"],
            label=f"First per sender ({is_first.sum()} calls)",
        )
        ax.scatter(
            data.loc[~is_first, "call_index"], data.loc[~is_first, "gas"],
            alpha=0.3, s=2, color=COLORS["psc"],
            label=f"Subsequent ({(~is_first).sum()} calls)",
        )
    else:
        ax.scatter(
            data["call_index"], data["gas"],
            alpha=0.3, s=2, color=COLORS["psc"],
        )

    avg = data["gas"].mean()
    ax.axhline(y=avg, color=COLORS["highlight"], linestyle="--",
               linewidth=1, alpha=0.7, label=f"Average: {avg:,.0f}")

    ax.set_xlabel("data_submission call index")
    ax.set_ylabel("Gas consumed")
    ax.set_title(f"data_submission gas, constant O(1) ({senders}S x {verifiers}V)")
    ax.legend(loc="upper right")
    format_gas_axis(ax)

    save_figure(fig, f"data_submission_constant_{senders}s_{verifiers}v", prefix=prefix)


def plot_submission_rolling_average(df_raw, senders, verifiers, prefix):
    """Rolling average to smooth noise and highlight the initial premium.

    After the first few calls, the rolling average converges to the
    steady-state cost (~150-200 kgas depending on contract variant).
    """
    data = filter_scenario(df_raw, senders, verifiers)
    data = filter_operation(data, "data_submission").sort_values("call_index")

    if len(data) < 50:
        return

    window = max(50, len(data) // 100)
    rolling = data["gas"].rolling(window=window).mean()

    fig, ax = plt.subplots()
    ax.plot(data["call_index"].values, rolling.values,
            color=COLORS["psc"], linewidth=1.5,
            label=f"Rolling mean (window = {window})")

    first_call_gas = int(data["gas"].iloc[0])
    ax.scatter(
        data["call_index"].values[:1], data["gas"].values[:1],
        color=COLORS["highlight"], s=40, zorder=5,
        label=f"First call: {first_call_gas:,}",
    )

    ax.set_xlabel("data_submission call index")
    ax.set_ylabel("Gas (rolling average)")
    ax.set_title(f"data_submission gas convergence ({senders}S x {verifiers}V)")
    ax.legend()
    format_gas_axis(ax)

    save_figure(fig, f"data_submission_rolling_{senders}s_{verifiers}v", prefix=prefix)


def main():
    apply_thesis_style()
    args = parse_args(need_raw=True)
    prefix = extract_contract_label(args["raw"])
    print(f"Contract label: {prefix or '(unknown - no prefix)'}")

    df = load_raw_csv(args["raw"])

    for s, v in pick_extreme_scenarios(df):
        print(f"Scenario: {s}S x {v}V")
        plot_submission_flat(df, s, v, prefix)
        plot_submission_rolling_average(df, s, v, prefix)


if __name__ == "__main__":
    main()
