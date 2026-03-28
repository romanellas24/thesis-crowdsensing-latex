"""
Plot 3: Average gas per operation (first call vs subsequent calls).

Grouped bar chart showing how the first call of each function is more
expensive due to storage initialization.

Usage:
    python scripts/plots/plot_gas_per_operation.py path/to/aggregated.csv
"""

from commons import (
    apply_thesis_style, save_figure, parse_args,
    load_aggregated_csv, filter_scenario,
    get_scenarios, pick_representative_scenario, format_gas_axis,
)
import matplotlib.pyplot as plt
import numpy as np

# Operations to show, in logical order (excludes ROLE_TOTAL_* and PER_WALLET_*)
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

# Short labels for the x-axis
OPERATION_LABELS = {
    "sender_upload_pubkey":  "Sender\nPubKey",
    "owner_send_kenc":       "Owner\nSend Kenc",
    "verifier_upload_pubkey":"Verifier\nPubKey",
    "owner_send_kdec":       "Owner\nSend Kdec",
    "sender_pay_bond":       "Sender\nBond",
    "verifier_pay_bond":     "Verifier\nBond",
    "data_submission":       "Data\nSubmission",
    "verification_request":  "Verify\nRequest",
    "verification_submit":   "Verify\nSubmit",
}


def plot_first_vs_subsequent(df_agg, senders, verifiers):
    """Grouped bar chart: first call vs average subsequent for each operation."""
    data = filter_scenario(df_agg, senders, verifiers)

    # Filter to protocol operations only
    data = data[data["operation"].isin(OPERATIONS_ORDER)]
    # Sort by logical order
    data = data.set_index("operation").loc[OPERATIONS_ORDER].reset_index()

    if data.empty:
        print(f"  No aggregated data for {senders}S×{verifiers}V, skipping")
        return

    labels = [OPERATION_LABELS.get(op, op) for op in data["operation"]]
    first = data["first_call_gas"].values.astype(float)
    subsequent = data["avg_subsequent_gas"].values.astype(float)

    x = np.arange(len(labels))
    width = 0.35

    fig, ax = plt.subplots(figsize=(9, 5))
    bars1 = ax.bar(x - width / 2, first, width, label="First call", color="#2563eb")
    bars2 = ax.bar(x + width / 2, subsequent, width, label="Subsequent (avg)", color="#64748b")

    ax.set_xlabel("Operation")
    ax.set_ylabel("Gas consumed")
    ax.set_title(f"Gas per operation: first call vs subsequent ({senders}S × {verifiers}V)")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8)
    ax.legend()
    format_gas_axis(ax)

    save_figure(fig, f"gas_per_operation_{senders}s_{verifiers}v")


def plot_operation_comparison_across_scales(df_agg):
    """For core operations, show how avg gas changes with verifier count."""
    target_ops = ["data_submission", "verification_request", "verification_submit"]
    colors = {"data_submission": "#2563eb", "verification_request": "#dc2626", "verification_submit": "#16a34a"}

    data = df_agg[
        (df_agg["operation"].isin(target_ops)) &
        (~df_agg["operation"].str.startswith("ROLE_")) &
        (~df_agg["operation"].str.startswith("PER_"))
    ]
    if data.empty:
        return

    # Group by sender count, one subplot per sender count
    sender_counts = sorted(data["senders"].unique())

    fig, ax = plt.subplots()
    for op in target_ops:
        op_data = data[data["operation"] == op]
        # Average across sender counts for each verifier count
        grouped = op_data.groupby("verifiers")["avg_subsequent_gas"].mean()
        ax.plot(grouped.index, grouped.values, marker="o", color=colors[op], label=op)

    ax.set_xlabel("Number of verifiers")
    ax.set_ylabel("Avg subsequent gas")
    ax.set_title("Core operations: average gas vs verifier count")
    ax.set_xscale("log")
    ax.legend()
    format_gas_axis(ax)

    save_figure(fig, "gas_per_operation_vs_verifiers")


def main():
    apply_thesis_style()
    args = parse_args(need_raw=False, need_agg=True)
    df = load_aggregated_csv(args["agg"])

    s, v = pick_representative_scenario(df)
    print(f"Representative scenario: {s}S × {v}V")
    plot_first_vs_subsequent(df, s, v)
    plot_operation_comparison_across_scales(df)


if __name__ == "__main__":
    main()
