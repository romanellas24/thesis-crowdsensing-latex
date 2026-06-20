"""
Plot 3: Average gas per protocol operation (first call vs subsequent calls).

Solidity charges higher gas on the *first* SSTORE to each storage slot:
moving a slot from "zero" to "non-zero" is 22 100 gas (cold + zero-to-
non-zero), while subsequent updates pay only 5 000 gas (warm or warm
non-zero-to-non-zero).

This shows up clearly in operations that initialize new state:
  - sender_upload_pubkey / verifier_upload_pubkey: first call writes
    role mappings for the first time
  - sender_pay_bond / verifier_pay_bond: first DST transfer to the
    contract from each role
  - initial_supply: one-time
  - data_submission: each call writes to a fresh slot, so the FIRST
    call still pays a slot-creation premium even though subsequent
    calls are also writing to fresh slots - the premium is for
    initializing the per-sender `SenderInformation` mapping, not
    the DataEntry itself.

The grouped bar chart makes the first-call premium visible on every
operation. For the thesis, this justifies why we report both first_call
and avg_subsequent separately in tables: a one-shot deployment estimate
that ignores the first-call premium would underestimate worst-case cost.

The second plot (`core ops across scales`) shows that this cost
structure is independent of scenario size - a per-operation property
of the contract, not a property of the workload.

Usage:
    python scripts/plots/3_plot_gas_per_operation.py \\
        path/to/<contract>_gas_simulation_results.csv
"""

from commons import (
    apply_thesis_style, save_figure, parse_args,
    load_aggregated_csv, filter_scenario,
    get_scenarios, pick_representative_scenario, extract_contract_label,
    format_gas_axis, COLORS,
)
import matplotlib.pyplot as plt
import numpy as np

# Operations to show, in logical protocol-flow order.
OPERATIONS_ORDER = [
    "sender_upload_pubkey",
    "owner_send_kenc",
    "verifier_upload_pubkey",
    "owner_send_kdec",
    "sender_pay_bond",
    "verifier_pay_bond",
    "data_submission",
    "verification_request",
    "verification_submit",
]

# PSC-specific operations: shown only if present in the CSV.
PSC_OPERATIONS = [
    "owner_notify_key_ready",
    "owner_deliver_bundle",
    "owner_kick_verifier",
]

OPERATION_LABELS = {
    "sender_upload_pubkey":   "Sender\nPubKey",
    "owner_send_kenc":        "Owner\nSend Kenc",
    "verifier_upload_pubkey": "Verifier\nPubKey",
    "owner_send_kdec":        "Owner\nSend Kdec",
    "sender_pay_bond":        "Sender\nBond",
    "verifier_pay_bond":      "Verifier\nBond",
    "data_submission":        "Data\nSubmission",
    "verification_request":   "Verify\nRequest",
    "verification_submit":    "Verify\nSubmit",
    "owner_notify_key_ready": "Owner\nNotify Key",
    "owner_deliver_bundle":   "Owner\nDeliver Bundle",
    "owner_kick_verifier":    "Owner\nKick Verifier",
}


def plot_first_vs_subsequent(df_agg, senders, verifiers, prefix):
    """Grouped bar chart: first call vs avg subsequent for each operation."""
    data = filter_scenario(df_agg, senders, verifiers)

    # Include PSC-specific ops only if they are present in this CSV.
    present_ops = set(data["operation"].unique())
    ops_to_plot = [o for o in OPERATIONS_ORDER + PSC_OPERATIONS if o in present_ops]

    data = data[data["operation"].isin(ops_to_plot)]
    data = data.set_index("operation").loc[ops_to_plot].reset_index()

    if data.empty:
        print(f"  No aggregated data for {senders}S x {verifiers}V, skipping")
        return

    labels = [OPERATION_LABELS.get(op, op) for op in data["operation"]]
    first = data["first_call_gas"].values.astype(float)
    subsequent = data["avg_subsequent_gas"].values.astype(float)

    x = np.arange(len(labels))
    width = 0.35
    fig_w = max(9, 0.8 * len(labels) + 3)

    fig, ax = plt.subplots(figsize=(fig_w, 5))
    ax.bar(x - width / 2, first, width, label="First call",
           color=COLORS["first"])
    ax.bar(x + width / 2, subsequent, width, label="Subsequent (avg)",
           color=COLORS["subsequent"])

    ax.set_xlabel("Operation")
    ax.set_ylabel("Gas consumed")
    ax.set_title(f"Gas per operation: first call vs subsequent "
                 f"({senders}S x {verifiers}V)")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8)
    ax.legend()
    format_gas_axis(ax)

    save_figure(fig, f"gas_per_operation_{senders}s_{verifiers}v", prefix=prefix)


def plot_core_ops_across_scales(df_agg, prefix):
    """For the three core ops, show how avg gas changes with verifier count.

    Confirms that the per-operation cost is independent of scenario size -
    the cost is a contract property, not a workload property.
    """
    target_ops = ["data_submission", "verification_request", "verification_submit"]
    op_colors = {
        "data_submission": COLORS["pfc"],
        "verification_request": COLORS["fifo"],
        "verification_submit": COLORS["psc"],
    }

    data = df_agg[df_agg["operation"].isin(target_ops)]
    if data.empty:
        return

    fig, ax = plt.subplots()
    for op in target_ops:
        op_data = data[data["operation"] == op]
        # Average across sender counts for each verifier count
        grouped = op_data.groupby("verifiers")["avg_subsequent_gas"].mean()
        ax.plot(grouped.index, grouped.values, marker="o",
                color=op_colors[op], label=op)

    ax.set_xlabel("Number of verifiers")
    ax.set_ylabel("Average gas (subsequent calls)")
    ax.set_title("Core operations: avg gas vs verifier count "
                 "(stable across scales)")
    ax.set_xscale("log")
    ax.legend()
    format_gas_axis(ax)

    save_figure(fig, "gas_per_operation_vs_verifiers", prefix=prefix)


def main():
    apply_thesis_style()
    args = parse_args(need_raw=False, need_agg=True)
    prefix = extract_contract_label(args["agg"])
    print(f"Contract label: {prefix or '(unknown - no prefix)'}")

    df = load_aggregated_csv(args["agg"])

    s, v = pick_representative_scenario(df)
    print(f"Representative scenario: {s}S x {v}V")
    plot_first_vs_subsequent(df, s, v, prefix)
    plot_core_ops_across_scales(df, prefix)


if __name__ == "__main__":
    main()
