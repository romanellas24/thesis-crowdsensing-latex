"""
Plot 4: Gas consumption per role vs number of participants.

Three lines: owner total, sender average, verifier average.
Demonstrates that per-participant cost decreases as the system scales,
justifying the protocol's economic viability.

Uses ROLE_TOTAL_* rows from the aggregated CSV.

Usage:
    python scripts/plots/plot_gas_per_role.py path/to/aggregated.csv
"""

from commons import (
    apply_thesis_style, save_figure, parse_args,
    load_aggregated_csv, get_scenarios, format_gas_axis,
)
import matplotlib.pyplot as plt
import numpy as np


def extract_role_data(df_agg):
    """Extract role summary rows into a structured dict."""
    role_rows = df_agg[df_agg["operation"].str.startswith("ROLE_TOTAL_")]

    scenarios = []
    for _, row in role_rows.iterrows():
        s, v, op = int(row["senders"]), int(row["verifiers"]), row["operation"]
        role = op.replace("ROLE_TOTAL_", "")
        total = row["total_gas"]
        avg = row["avg_subsequent_gas"]  # per-actor average for sender/verifier
        scenarios.append({
            "senders": s, "verifiers": v,
            "role": role, "total": total, "avg_per_actor": avg
        })

    return scenarios


def plot_avg_gas_vs_senders(df_agg):
    """Fix verifier count, vary senders. Show avg gas per sender decreasing."""
    role_data = extract_role_data(df_agg)
    all_scenarios = get_scenarios(df_agg)

    # Find the most common verifier count
    verifier_counts = [v for _, v in all_scenarios]
    most_common_v = max(set(verifier_counts), key=verifier_counts.count)

    # Filter scenarios with that verifier count
    target_scenarios = sorted([(s, v) for s, v in all_scenarios if v == most_common_v])
    if len(target_scenarios) < 2:
        # Fall back: use all scenarios
        target_scenarios = sorted(all_scenarios)

    sender_values = [s for s, _ in target_scenarios]

    owner_gas = []
    sender_avg = []
    verifier_avg = []

    for s, v in target_scenarios:
        for rd in role_data:
            if rd["senders"] == s and rd["verifiers"] == v:
                if rd["role"] == "owner":
                    owner_gas.append(float(rd["total"]))
                elif rd["role"] == "sender":
                    sender_avg.append(float(rd["avg_per_actor"]))
                elif rd["role"] == "verifier":
                    verifier_avg.append(float(rd["avg_per_actor"]))

    fig, ax = plt.subplots()

    x = range(len(sender_values))
    labels = [str(s) for s in sender_values]

    if owner_gas:
        ax.plot(x, owner_gas, marker="s", color="#f59e0b", label="Owner (total)", linewidth=2)
    if sender_avg:
        ax.plot(x, sender_avg, marker="o", color="#2563eb", label="Sender (avg)", linewidth=2)
    if verifier_avg:
        ax.plot(x, verifier_avg, marker="^", color="#dc2626", label="Verifier (avg)", linewidth=2)

    ax.set_xlabel("Number of senders")
    ax.set_ylabel("Gas consumed")
    ax.set_title(f"Gas per role vs sender count (verifiers={most_common_v})")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_yscale("log")
    ax.legend()
    ax.grid(True, which="both", alpha=0.3)

    save_figure(fig, f"gas_per_role_vs_senders_v{most_common_v}")


def plot_avg_gas_vs_verifiers(df_agg):
    """Fix sender count, vary verifiers. Show avg gas per verifier decreasing."""
    role_data = extract_role_data(df_agg)
    all_scenarios = get_scenarios(df_agg)

    sender_counts = [s for s, _ in all_scenarios]
    most_common_s = max(set(sender_counts), key=sender_counts.count)

    target_scenarios = sorted([(s, v) for s, v in all_scenarios if s == most_common_s])
    if len(target_scenarios) < 2:
        target_scenarios = sorted(all_scenarios)

    verifier_values = [v for _, v in target_scenarios]

    owner_gas = []
    sender_avg = []
    verifier_avg = []

    for s, v in target_scenarios:
        for rd in role_data:
            if rd["senders"] == s and rd["verifiers"] == v:
                if rd["role"] == "owner":
                    owner_gas.append(float(rd["total"]))
                elif rd["role"] == "sender":
                    sender_avg.append(float(rd["avg_per_actor"]))
                elif rd["role"] == "verifier":
                    verifier_avg.append(float(rd["avg_per_actor"]))

    fig, ax = plt.subplots()

    x = range(len(verifier_values))
    labels = [str(v) for v in verifier_values]

    if owner_gas:
        ax.plot(x, owner_gas, marker="s", color="#f59e0b", label="Owner (total)", linewidth=2)
    if sender_avg:
        ax.plot(x, sender_avg, marker="o", color="#2563eb", label="Sender (avg)", linewidth=2)
    if verifier_avg:
        ax.plot(x, verifier_avg, marker="^", color="#dc2626", label="Verifier (avg)", linewidth=2)

    ax.set_xlabel("Number of verifiers")
    ax.set_ylabel("Gas consumed")
    ax.set_title(f"Gas per role vs verifier count (senders={most_common_s})")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_yscale("log")
    ax.legend()
    ax.grid(True, which="both", alpha=0.3)

    save_figure(fig, f"gas_per_role_vs_verifiers_s{most_common_s}")


def plot_heatmap(df_agg):
    """Heatmap: total gas (all roles) per scenario."""
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
            matrix[si][vi] += float(rd["total"])

    fig, ax = plt.subplots(figsize=(8, 6))
    im = ax.imshow(matrix, cmap="YlOrRd", aspect="auto")

    ax.set_xticks(range(len(verifier_set)))
    ax.set_yticks(range(len(sender_set)))
    ax.set_xticklabels([str(v) for v in verifier_set])
    ax.set_yticklabels([str(s) for s in sender_set])
    ax.set_xlabel("Verifiers")
    ax.set_ylabel("Senders")
    ax.set_title("Total gas consumption by scenario")

    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("Total gas")

    # Annotate cells
    for i in range(len(sender_set)):
        for j in range(len(verifier_set)):
            val = matrix[i][j]
            label = f"{val / 1e6:.1f}M" if val >= 1e6 else f"{val / 1e3:.0f}k"
            ax.text(j, i, label, ha="center", va="center", fontsize=7, color="black")

    save_figure(fig, "gas_heatmap_total")


def main():
    apply_thesis_style()
    args = parse_args(need_raw=False, need_agg=True)
    df = load_aggregated_csv(args["agg"])

    plot_avg_gas_vs_senders(df)
    plot_avg_gas_vs_verifiers(df)
    plot_heatmap(df)


if __name__ == "__main__":
    main()
