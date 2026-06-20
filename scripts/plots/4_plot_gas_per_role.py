"""
Plot 4: Gas consumption per role, by scenario size.

A privacy-preserving crowdsensing campaign distributes cost across three
roles: campaign owner (B), senders (S), and verifiers (V).

The owner pays a one-time cost (contract deployment, initial supply,
plus one-per-actor key publication operations). Senders pay a fixed cost
per piece of data submitted, plus the bond. Verifiers pay a per-check
fixed cost plus the bond.

Two cuts of the data:
  - vs senders: holding the verifier count fixed, how does the per-actor
    cost change as we add more senders? Expectation: flat (each sender
    is independent of the others).
  - vs verifiers: holding the sender count fixed, how does the
    per-verifier cost change? Expectation: per-verifier average cost
    *drops* - the verification workload (TOTAL_CIDS * MAJORITY = 20 000
    checks) is distributed across more verifiers, so each one does
    fewer calls.

The third plot (heatmap) shows total system gas across the 16 scenarios,
giving a single-glance view of where the workload is dominated.

Usage:
    python scripts/plots/4_plot_gas_per_role.py \\
        path/to/<contract>_gas_simulation_results.csv
"""

from commons import (
    apply_thesis_style, save_figure, parse_args,
    load_aggregated_csv, get_scenarios, extract_contract_label,
    COLORS,
)
import matplotlib.pyplot as plt
import numpy as np


def extract_role_data(df_agg) -> list[dict]:
    """Extract ROLE_TOTAL_* rows into a structured list."""
    role_rows = df_agg[df_agg["operation"].str.startswith("ROLE_TOTAL_")]
    out = []
    for _, row in role_rows.iterrows():
        out.append({
            "senders": int(row["senders"]),
            "verifiers": int(row["verifiers"]),
            "role": row["operation"].replace("ROLE_TOTAL_", ""),
            "total": float(row["total_gas"]),
            # `avg_subsequent_gas` for ROLE_TOTAL is the per-actor average.
            "avg_per_actor": float(row["avg_subsequent_gas"]),
        })
    return out


def _gather_role_series(role_data, target_scenarios):
    """For a fixed list of scenarios, build owner/sender/verifier series."""
    owner_total = []
    sender_avg = []
    verifier_avg = []
    for s, v in target_scenarios:
        for rd in role_data:
            if rd["senders"] != s or rd["verifiers"] != v:
                continue
            if rd["role"] == "owner":
                owner_total.append(rd["total"])
            elif rd["role"] == "sender":
                sender_avg.append(rd["avg_per_actor"])
            elif rd["role"] == "verifier":
                verifier_avg.append(rd["avg_per_actor"])
    return owner_total, sender_avg, verifier_avg


def plot_avg_gas_vs_senders(df_agg, prefix):
    """Fix verifier count, vary senders. Per-actor cost is expected to be flat."""
    role_data = extract_role_data(df_agg)
    all_scenarios = get_scenarios(df_agg)

    verifier_counts = [v for _, v in all_scenarios]
    most_common_v = max(set(verifier_counts), key=verifier_counts.count)

    target = sorted([(s, v) for s, v in all_scenarios if v == most_common_v])
    if len(target) < 2:
        target = sorted(all_scenarios)

    sender_values = [s for s, _ in target]
    owner_total, sender_avg, verifier_avg = _gather_role_series(role_data, target)

    fig, ax = plt.subplots()
    x = range(len(sender_values))
    labels = [str(s) for s in sender_values]

    if owner_total:
        ax.plot(x, owner_total, marker="s", color=COLORS["owner"],
                label="Owner (total)", linewidth=2)
    if sender_avg:
        ax.plot(x, sender_avg, marker="o", color=COLORS["sender"],
                label="Sender (avg)", linewidth=2)
    if verifier_avg:
        ax.plot(x, verifier_avg, marker="^", color=COLORS["verifier"],
                label="Verifier (avg)", linewidth=2)

    ax.set_xlabel("Number of senders")
    ax.set_ylabel("Gas consumed")
    ax.set_title(f"Gas per role vs sender count (verifiers = {most_common_v})")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels)
    ax.set_yscale("log")
    ax.legend()
    ax.grid(True, which="both", alpha=0.3)

    save_figure(fig, f"gas_per_role_vs_senders_v{most_common_v}", prefix=prefix)


def plot_avg_gas_vs_verifiers(df_agg, prefix):
    """Fix sender count, vary verifiers. Per-verifier avg cost is expected to fall."""
    role_data = extract_role_data(df_agg)
    all_scenarios = get_scenarios(df_agg)

    sender_counts = [s for s, _ in all_scenarios]
    most_common_s = max(set(sender_counts), key=sender_counts.count)

    target = sorted([(s, v) for s, v in all_scenarios if s == most_common_s])
    if len(target) < 2:
        target = sorted(all_scenarios)

    verifier_values = [v for _, v in target]
    owner_total, sender_avg, verifier_avg = _gather_role_series(role_data, target)

    fig, ax = plt.subplots()
    x = range(len(verifier_values))
    labels = [str(v) for v in verifier_values]

    if owner_total:
        ax.plot(x, owner_total, marker="s", color=COLORS["owner"],
                label="Owner (total)", linewidth=2)
    if sender_avg:
        ax.plot(x, sender_avg, marker="o", color=COLORS["sender"],
                label="Sender (avg)", linewidth=2)
    if verifier_avg:
        ax.plot(x, verifier_avg, marker="^", color=COLORS["verifier"],
                label="Verifier (avg)", linewidth=2)

    ax.set_xlabel("Number of verifiers")
    ax.set_ylabel("Gas consumed")
    ax.set_title(f"Gas per role vs verifier count (senders = {most_common_s})")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels)
    ax.set_yscale("log")
    ax.legend()
    ax.grid(True, which="both", alpha=0.3)

    save_figure(fig, f"gas_per_role_vs_verifiers_s{most_common_s}", prefix=prefix)


def plot_heatmap(df_agg, prefix):
    """Heatmap: total gas (all roles) across the 4x4 (senders, verifiers) grid."""
    role_data = extract_role_data(df_agg)
    all_scenarios = get_scenarios(df_agg)

    sender_set = sorted(set(s for s, _ in all_scenarios))
    verifier_set = sorted(set(v for _, v in all_scenarios))

    matrix = np.zeros((len(sender_set), len(verifier_set)))
    for rd in role_data:
        s, v = rd["senders"], rd["verifiers"]
        if s in sender_set and v in verifier_set:
            si = sender_set.index(s)
            vi = verifier_set.index(v)
            matrix[si][vi] += rd["total"]

    fig, ax = plt.subplots(figsize=(8, 6))
    im = ax.imshow(matrix, cmap="YlOrRd", aspect="auto")

    ax.set_xticks(range(len(verifier_set)))
    ax.set_yticks(range(len(sender_set)))
    ax.set_xticklabels([str(v) for v in verifier_set])
    ax.set_yticklabels([str(s) for s in sender_set])
    ax.set_xlabel("Verifiers")
    ax.set_ylabel("Senders")
    ax.set_title("Total gas consumption per scenario (sum of all roles)")

    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("Total gas")

    for i in range(len(sender_set)):
        for j in range(len(verifier_set)):
            val = matrix[i][j]
            label = f"{val / 1e9:.1f}G" if val >= 1e9 else \
                    f"{val / 1e6:.1f}M" if val >= 1e6 else \
                    f"{val / 1e3:.0f}k"
            ax.text(j, i, label, ha="center", va="center",
                    fontsize=7, color="black")

    save_figure(fig, "gas_heatmap_total", prefix=prefix)


def main():
    apply_thesis_style()
    args = parse_args(need_raw=False, need_agg=True)
    prefix = extract_contract_label(args["agg"])
    print(f"Contract label: {prefix or '(unknown - no prefix)'}")

    df = load_aggregated_csv(args["agg"])

    plot_avg_gas_vs_senders(df, prefix)
    plot_avg_gas_vs_verifiers(df, prefix)
    plot_heatmap(df, prefix)


if __name__ == "__main__":
    main()
