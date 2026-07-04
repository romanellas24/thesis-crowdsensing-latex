"""
Plot 8: PSC vs PFC overhead - cost of the extended protocol's novel features.

PSC inherits PFC and adds three novel features (chapter 2.6):
  2.6.1 Trusted verifier flow - replaces in-contract storage of
        verifier decryption keys with an off-chain bundle delivery
        gated by `owner_notify_key_ready` + `owner_deliver_bundle`
  2.6.2 Reward decay - geometric decay of sender payouts every
        `maximumDataPerChunk` valid data, computed in publishIpfsCid
        via iterated Babylonian sqrt
  2.6.3 Verifier penalty bookkeeping - per-verifier vote tally,
        with `kickVerifier` and pardon-after-N-correct rules

Each feature has measurable per-operation gas implications:
  - data_submission: + reward decay computation (positive delta)
  - owner_send_kdec: - no on-chain key storage (large negative delta)
  - verification_submit: + bundle gate + vote bookkeeping (small +)
  - Plus three new operations entirely absent from PFC:
    owner_notify_key_ready, owner_deliver_bundle, owner_kick_verifier

This plot makes the per-operation deltas explicit. For each common
operation it shows PFC and PSC bars side-by-side, with the relative
percentage delta annotated on top. PSC-only operations are shown
in a separate panel because they have no PFC counterpart to compare
against.

Usage:
    python scripts/plots/8_plot_psc_vs_pfc_overhead.py \\
        path/to/pfc_..._results.csv path/to/psc_..._results.csv
"""

from commons import (
    apply_thesis_style, save_figure, parse_multi_args,
    load_multi_aggregated, shared_scenarios,
    format_gas_axis, COLORS,
)
import matplotlib.pyplot as plt
import numpy as np

COMMON_OPS = [
    "contract_deployment",
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

PSC_ONLY_OPS = [
    "owner_notify_key_ready",
    "owner_deliver_bundle",
    "owner_kick_verifier",
]

OPERATION_LABELS = {
    "contract_deployment":    "Deploy",
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


def _avg_for_op(df, senders, verifiers, op):
    """Pick the most representative single-value gas metric per operation.

    For one-time ops (contract_deployment, initial_supply) `avg_subsequent_gas`
    is 0, so fall back to `first_call_gas`. Otherwise use `avg_subsequent_gas`.
    """
    row = df[
        (df["senders"] == senders) &
        (df["verifiers"] == verifiers) &
        (df["operation"] == op)
    ]
    if row.empty:
        return None
    avg = float(row.iloc[0]["avg_subsequent_gas"])
    if avg == 0:
        return float(row.iloc[0]["first_call_gas"])
    return avg


def plot_common_ops_overhead(aggs, senders, verifiers):
    """For each common op, PFC vs PSC bar with % delta annotation."""
    if "pfc" not in aggs or "psc" not in aggs:
        print("  Need both pfc and psc aggregated CSVs; skipping")
        return

    pfc_vals = []
    psc_vals = []
    labels = []
    deltas = []

    for op in COMMON_OPS:
        p = _avg_for_op(aggs["pfc"], senders, verifiers, op)
        q = _avg_for_op(aggs["psc"], senders, verifiers, op)
        if p is None or q is None:
            continue
        pfc_vals.append(p)
        psc_vals.append(q)
        labels.append(OPERATION_LABELS.get(op, op))
        deltas.append(100.0 * (q - p) / p if p > 0 else 0)

    if not labels:
        print(f"  No common-op data for {senders}S x {verifiers}V; skipping")
        return

    x = np.arange(len(labels))
    width = 0.4
    fig_w = max(10, 0.85 * len(labels) + 3)
    fig, ax = plt.subplots(figsize=(fig_w, 5.5))

    ax.bar(x - width / 2, pfc_vals, width, label="PFC", color=COLORS["pfc"])
    ax.bar(x + width / 2, psc_vals, width, label="PSC", color=COLORS["psc"])

    # Delta annotations above each pair
    y_max = max(max(pfc_vals), max(psc_vals))
    for i, d in enumerate(deltas):
        top = max(pfc_vals[i], psc_vals[i])
        sign = "+" if d >= 0 else ""
        color = COLORS["highlight"] if abs(d) > 5 else "#475569"
        ax.text(i, top * 1.05, f"{sign}{d:.1f}%",
                ha="center", va="bottom", fontsize=8, color=color)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_xlabel("Operation (common to PFC and PSC)")
    ax.set_ylabel("Gas consumed")
    ax.set_title(f"PSC overhead vs PFC, per operation "
                 f"({senders}S x {verifiers}V)")
    ax.legend(loc="upper left")
    ax.set_ylim(top=y_max * 1.3)
    format_gas_axis(ax)

    save_figure(fig, f"psc_vs_pfc_overhead_{senders}s_{verifiers}v")


def plot_psc_only_ops(aggs, senders, verifiers):
    """The three operations that exist only in PSC.

    Shows the absolute cost of features that PFC does not provide.
    No comparison possible - bars stand alone.
    """
    if "psc" not in aggs:
        return

    vals = []
    labels = []
    for op in PSC_ONLY_OPS:
        v = _avg_for_op(aggs["psc"], senders, verifiers, op)
        if v is None:
            continue
        vals.append(v)
        labels.append(OPERATION_LABELS.get(op, op))

    if not labels:
        return

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(range(len(labels)), vals, color=COLORS["psc"], width=0.5)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylabel("Gas consumed")
    ax.set_title(f"PSC-only operations, absolute cost "
                 f"({senders}S x {verifiers}V)")
    format_gas_axis(ax)
    for i, v in enumerate(vals):
        ax.text(i, v * 1.02, f"{v:,.0f}",
                ha="center", va="bottom", fontsize=8)

    ax.set_ylim(top=max(vals) * 1.15)
    save_figure(fig, f"psc_only_operations_{senders}s_{verifiers}v")


def main():
    apply_thesis_style()
    paths = parse_multi_args(min_paths=2)
    aggs = load_multi_aggregated(paths)
    print(f"Contracts loaded: {list(aggs.keys())}")

    if "pfc" not in aggs or "psc" not in aggs:
        print("Need both PFC and PSC aggregated CSVs. Aborting.")
        return

    # Plot for every scenario shared between PFC and PSC.
    shared = shared_scenarios({k: aggs[k] for k in ("pfc", "psc")})
    if not shared:
        print("  No shared scenarios between PFC and PSC; aborting")
        return

    for s, v in shared:
        print(f"Scenario: {s}S x {v}V")
        plot_common_ops_overhead(aggs, s, v)
        plot_psc_only_ops(aggs, s, v)


if __name__ == "__main__":
    main()
