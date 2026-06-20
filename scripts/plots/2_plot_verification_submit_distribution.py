"""
Plot 2: verification_submit gas, two-regime distribution.

submitVerifyResult has two distinct cost regimes:

  REGULAR submit: the verifier registers a vote but the datum has not
      yet reached the majority threshold. Only a few storage writes
      (`_registerVerifierResponse`). Cheap: ~50 kgas in PFC.

  MAJORITY-TRIGGERING submit: the verifier's vote pushes the datum to
      VALID or INVALID. Now the function additionally executes:
        - _determinateVerifiersDecision (one branch)
        - _removeFromPending(dataId)
        - _rewardCorrectVerifiers (loops over assignedChecks)
        - _checkCampaignCompletion
      Much more expensive: ~100-300 kgas in PFC, but in the FIFO baseline
      _removeFromPending alone can push the call to tens of millions of
      gas due to the O(n) left-shift over the pending array.

This plot makes both regimes visible: a dense baseline cloud + a sparser
band of spikes at higher gas values. The histogram view further confirms
the bimodal distribution.

For PFC, the spike band is moderate (the swap-and-pop optimization keeps
removal cheap). For FIFO, the spikes are dramatic. The plot is most
useful for comparing the two side-by-side (see script 6 for the overlay).

Usage:
    python scripts/plots/2_plot_verification_submit_distribution.py \\
        path/to/<contract>_gas_simulation_results_raw.csv
"""

from commons import (
    apply_thesis_style, save_figure, parse_args,
    load_raw_csv, filter_scenario, filter_operation,
    pick_extreme_scenarios, extract_contract_label,
    format_gas_axis, annotate_eip7825_cap, EIP_7825_CAP, COLORS,
)
import matplotlib.pyplot as plt
import numpy as np


def classify_regimes(gas_values: np.ndarray) -> np.ndarray:
    """Classify each submit as REGULAR or MAJORITY-TRIGGERING.

    Heuristic: the regular regime is well-clustered around the minimum
    (a fixed cost from `_registerVerifierResponse`). Anything above
    1.5 x the minimum is a majority-triggering call.

    This is more robust than median+std on bimodal data, where the std
    is inflated by the spikes themselves.
    """
    min_gas = gas_values.min()
    threshold = 1.5 * min_gas
    return gas_values > threshold


def plot_submit_distribution(df_raw, senders, verifiers, prefix):
    """Scatter showing the two regimes by colour."""
    data = filter_scenario(df_raw, senders, verifiers)
    data = filter_operation(data, "verification_submit")

    if data.empty:
        print(f"  No verification_submit data for {senders}S x {verifiers}V, skipping")
        return

    gas = data["gas"].values
    call_idx = data["call_index"].values
    is_majority = classify_regimes(gas)

    fig, ax = plt.subplots()

    ax.scatter(
        call_idx[~is_majority], gas[~is_majority],
        alpha=0.3, s=2, color=COLORS["regular"],
        label=f"Regular submit ({(~is_majority).sum()} calls)",
    )
    ax.scatter(
        call_idx[is_majority], gas[is_majority],
        alpha=0.7, s=8, color=COLORS["spike"],
        label=f"Majority triggered ({is_majority.sum()} calls)",
    )

    # If any call exceeds EIP-7825, annotate the cap explicitly.
    if gas.max() > EIP_7825_CAP:
        annotate_eip7825_cap(ax)
        ax.set_yscale("log")

    ax.set_xlabel("verification_submit call index")
    ax.set_ylabel("Gas consumed")
    ax.set_title(f"verification_submit, two-regime cost ({senders}S x {verifiers}V)")
    ax.legend(markerscale=3)
    format_gas_axis(ax)

    save_figure(fig, f"verification_submit_distribution_{senders}s_{verifiers}v", prefix=prefix)


def plot_submit_histogram(df_raw, senders, verifiers, prefix):
    """Histogram view: confirms the bimodal distribution."""
    data = filter_scenario(df_raw, senders, verifiers)
    data = filter_operation(data, "verification_submit")

    if data.empty:
        return

    gas = data["gas"].values

    # If the span is large (FIFO case), log-scale bins are clearer.
    use_log = (gas.max() / max(gas.min(), 1)) > 100
    if use_log:
        bins = np.logspace(np.log10(gas.min()), np.log10(gas.max()), 60)
    else:
        bins = 50

    fig, ax = plt.subplots()
    ax.hist(gas, bins=bins, color=COLORS["pfc"], alpha=0.75, edgecolor="white")

    if use_log:
        ax.set_xscale("log")

    if gas.max() > EIP_7825_CAP:
        ax.axvline(
            x=EIP_7825_CAP, color=COLORS["cap_line"], linestyle="--",
            linewidth=1.2, alpha=0.8, label="EIP-7825 cap",
        )
        ax.legend()

    ax.set_xlabel("Gas consumed (per call)")
    ax.set_ylabel("Frequency")
    ax.set_title(f"verification_submit gas distribution ({senders}S x {verifiers}V)")
    format_gas_axis(ax, axis="x")

    save_figure(fig, f"verification_submit_histogram_{senders}s_{verifiers}v", prefix=prefix)


def main():
    apply_thesis_style()
    args = parse_args(need_raw=True)
    prefix = extract_contract_label(args["raw"])
    print(f"Contract label: {prefix or '(unknown - no prefix)'}")

    df = load_raw_csv(args["raw"])

    for s, v in pick_extreme_scenarios(df):
        print(f"Scenario: {s}S x {v}V")
        plot_submit_distribution(df, s, v, prefix)
        plot_submit_histogram(df, s, v, prefix)


if __name__ == "__main__":
    main()
