#!/usr/bin/env python
"""
20_compute_real_world_costs.py — per-role gas summary and USD cost across networks.

Reads a raw gas-simulation CSV (one row per call), aggregates gas per wallet
by role within each scenario, computes mean/median/min/max across wallets,
and multiplies each statistic by per-network (gas_price, native_token_USD)
factors to produce USD costs.

The model is network-agnostic. Any EVM-compatible chain - L1, sidechain, or
L2 rollup - is added simply by passing a --network spec. On L2 rollups
(Arbitrum, Optimism, Base, …) the displayed gas_price already incorporates
the L1 data-publishing surcharge, so the standard model
    cost_USD = gas_used * gas_price_gwei * 1e-9 * native_token_usd
applies unchanged.

Historical gas-price references (median over a chosen year is recommended
for thesis reproducibility):
  - Ethereum:   https://etherscan.io/chart/gasprice
  - Polygon:    https://polygonscan.com/chart/gasprice
  - Arbitrum:   https://arbiscan.io/chart/gasprice
  - Optimism:   https://optimistic.etherscan.io/chart/gasprice
  - Base:       https://basescan.org/chart/gasprice
  - Gnosis:     https://gnosisscan.io/chart/gasprice
  - BSC:        https://bscscan.com/chart/gasprice

Native-token USD historical references (use the same observation period as
the gas-price snapshot):
  - CoinGecko historical:  https://www.coingecko.com/en/coins/<token>
                           (Tab "Historical Data" → CSV download)

Usage:
    python 20_compute_real_world_costs.py raw.csv \\
        --network "Ethereum mainnet:25.5:2400" \\
        --network "Polygon PoS:35.0:0.50" \\
        --network "Arbitrum One:0.1:2400" \\
        --network "Gnosis Chain:1.5:1.0" \\
        [--scenario 1000 1000] \\
        [--export-tex tables/realworld_costs.tex]

Network format: "Display Name:gas_price_gwei:native_token_usd"
The colon-separated form is intentionally minimal: it parses unambiguously,
fits on a single CLI line, and survives shell quoting without escaping.
"""

import argparse
import os
import sys
from typing import NamedTuple, Optional

import pandas as pd


# ---------------------------------------------------------------------------
# Network model
# ---------------------------------------------------------------------------

class Network(NamedTuple):
    """A single EVM-compatible network with its pricing snapshot."""
    name: str
    gas_price_gwei: float
    token_usd: float

    @property
    def usd_per_gas(self) -> float:
        """USD cost of one gas unit on this network."""
        return self.gas_price_gwei * 1e-9 * self.token_usd


def parse_network(spec: str) -> Network:
    """Parse a 'Name:gas_price_gwei:token_usd' string.

    Uses `rsplit(':', 2)` so the network name itself may contain colons
    (e.g. "Polygon PoS: mainnet:35.0:0.50") — unlikely in practice but
    correct.
    """
    parts = spec.rsplit(":", 2)
    if len(parts) != 3:
        raise argparse.ArgumentTypeError(
            f"--network must be 'name:gas_price_gwei:token_usd'; got: {spec!r}"
        )
    name, gas_str, token_str = parts
    try:
        gas = float(gas_str)
        token = float(token_str)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"--network numeric fields must be floats; got: {spec!r}"
        )
    if gas <= 0 or token <= 0:
        raise argparse.ArgumentTypeError(
            f"--network gas_price and token_usd must be positive; got: {spec!r}"
        )
    return Network(name=name.strip(), gas_price_gwei=gas, token_usd=token)


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def aggregate_per_wallet(df: pd.DataFrame) -> pd.DataFrame:
    """Sum gas per (role, role_index) wallet.

    Each (role, role_index) identifies a unique participant in the scenario.
    Summing across `operation` and `call_index` yields the total gas that
    participant would have spent over the campaign.
    """
    return (
        df.groupby(["role", "role_index"])["gas"]
        .sum()
        .reset_index()
        .rename(columns={"gas": "total_gas"})
    )


def role_stats(per_wallet: pd.DataFrame, role: str) -> Optional[dict]:
    """Return mean/median/min/max/count of total_gas for the given role,
    or None if no wallet of that role exists in the scenario."""
    role_df = per_wallet[per_wallet["role"] == role]
    if role_df.empty:
        return None
    g = role_df["total_gas"]
    return {
        "count": int(len(g)),
        "mean": float(g.mean()),
        "median": float(g.median()),
        "min": float(g.min()),
        "max": float(g.max()),
    }


# ---------------------------------------------------------------------------
# Pretty-printing
# ---------------------------------------------------------------------------

def fmt_gas(value: float) -> str:
    return f"{int(round(value)):>14,}"


def fmt_usd(value: float) -> str:
    """Adapt precision to magnitude. Sub-cent values get more decimals;
    large values get thousand separators with no decimals."""
    if value < 0.01:
        return f"${value:>11.6f}"
    if value < 1.0:
        return f"${value:>11.4f}"
    if value < 1_000.0:
        return f"${value:>11.2f}"
    return f"${value:>11,.2f}"


def print_scenario(
    df_scen: pd.DataFrame, senders: int, verifiers: int, networks: list[Network]
) -> None:
    per_wallet = aggregate_per_wallet(df_scen)
    roles = ["owner", "sender", "verifier"]

    # Header for the scenario block, showing wallet counts for context.
    counts = {r: int((per_wallet["role"] == r).sum()) for r in roles}
    header_line = (
        f"Scenario: {senders}S x {verifiers}V  "
        f"|  owner: {counts['owner']}, sender: {counts['sender']}, "
        f"verifier: {counts['verifier']}"
    )
    sep = "=" * len(header_line)
    print(sep)
    print(header_line)
    print(sep)

    # One sub-table per network.
    for net in networks:
        print(
            f"\nNetwork: {net.name}  "
            f"(gas_price = {net.gas_price_gwei} Gwei, "
            f"native_token = {net.token_usd} USD)"
        )
        hr = "-" * 152
        print(hr)
        header = (
            f"{'Role':<10} "
            f"| {'Gas mean':>14} | {'Gas median':>14} | {'Gas min':>14} | {'Gas max':>14} "
            f"| {'USD mean':>12} | {'USD median':>12} | {'USD min':>12} | {'USD max':>12}"
        )
        print(header)
        print(hr)

        for role in roles:
            stats = role_stats(per_wallet, role)
            if stats is None:
                continue
            f = net.usd_per_gas
            print(
                f"{role:<10} "
                f"| {fmt_gas(stats['mean'])} "
                f"| {fmt_gas(stats['median'])} "
                f"| {fmt_gas(stats['min'])} "
                f"| {fmt_gas(stats['max'])} "
                f"| {fmt_usd(stats['mean']  * f)} "
                f"| {fmt_usd(stats['median']* f)} "
                f"| {fmt_usd(stats['min']   * f)} "
                f"| {fmt_usd(stats['max']   * f)}"
            )
    print()


# ---------------------------------------------------------------------------
# LaTeX export
# ---------------------------------------------------------------------------

def _tex_fmt_gas(v: float) -> str:
    return f"{int(round(v)):,}"


def _tex_fmt_usd(v: float) -> str:
    if v < 0.01:
        return f"\\${v:.6f}"
    if v < 1.0:
        return f"\\${v:.4f}"
    if v < 1_000.0:
        return f"\\${v:.2f}"
    return f"\\${v:,.2f}"


def export_tex(
    scenarios_data: list[tuple[int, int, pd.DataFrame]],
    networks: list[Network],
    out_path: str,
) -> None:
    """Write a LaTeX table per (scenario, network) into a single .tex file.

    The file is ready to be \\input{} in the thesis. Each table is a
    booktabs-styled tabular wrapped in a `table` environment with caption
    and label.
    """
    lines = []
    for s, v, df_scen in scenarios_data:
        per_wallet = aggregate_per_wallet(df_scen)
        for net in networks:
            net_slug = (
                net.name.lower()
                .replace(" ", "-")
                .replace(":", "")
                .replace(".", "")
            )
            label = f"tab:realworld-{s}s-{v}v-{net_slug}"
            f = net.usd_per_gas
            lines.append(r"\begin{table}[htbp]")
            lines.append(r"    \centering")
            lines.append(
                r"    \caption[Per-role gas and USD cost: " +
                f"{s}S$\\times${v}V on {net.name}." +
                r"]{%"
            )
            lines.append(
                r"        Per-role gas usage and USD cost for the "
                + f"${s}\\,\\text{{S}} \\times {v}\\,\\text{{V}}$ scenario on "
                + f"\\textbf{{{net.name}}}. Statistics are computed across the wallets "
                + r"of each role (mean, median, min, max). The USD cost is obtained as "
                + f"gas_used $\\times$ {net.gas_price_gwei}\\,Gwei $\\times$ "
                + f"{net.token_usd}\\,USD, where the gas price and native-token price "
                + r"are the chosen historical snapshot.}"
            )
            lines.append(f"    \\label{{{label}}}")
            lines.append(r"    \resizebox{\textwidth}{!}{%")
            lines.append(r"    \begin{tabular}{lrrrrrrrr}")
            lines.append(r"        \toprule")
            lines.append(
                r"        Role & Gas mean & Gas median & Gas min & Gas max "
                r"& USD mean & USD median & USD min & USD max \\"
            )
            lines.append(r"        \midrule")
            for role in ("owner", "sender", "verifier"):
                stats = role_stats(per_wallet, role)
                if stats is None:
                    continue
                lines.append(
                    f"        \\texttt{{{role}}} & "
                    f"{_tex_fmt_gas(stats['mean'])} & "
                    f"{_tex_fmt_gas(stats['median'])} & "
                    f"{_tex_fmt_gas(stats['min'])} & "
                    f"{_tex_fmt_gas(stats['max'])} & "
                    f"{_tex_fmt_usd(stats['mean']   * f)} & "
                    f"{_tex_fmt_usd(stats['median'] * f)} & "
                    f"{_tex_fmt_usd(stats['min']    * f)} & "
                    f"{_tex_fmt_usd(stats['max']    * f)} \\\\"
                )
            lines.append(r"        \bottomrule")
            lines.append(r"    \end{tabular}%")
            lines.append(r"    }")
            lines.append(r"\end{table}")
            lines.append("")

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    print(f"  LaTeX exported: {out_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    p = argparse.ArgumentParser(
        description="Per-role gas stats and USD costs across EVM networks.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "raw_csv",
        help="Raw per-call gas CSV (columns: senders, verifiers, operation, "
             "call_index, gas, role, role_index)",
    )
    p.add_argument(
        "--network", action="append", type=parse_network, required=True,
        metavar="NAME:GWEI:USD",
        help="Network spec, repeatable. Format: 'name:gas_price_gwei:token_usd'. "
             "Example: --network 'Ethereum mainnet:25.5:2400'",
    )
    p.add_argument(
        "--scenario", nargs=2, type=int, metavar=("SENDERS", "VERIFIERS"),
        help="Restrict analysis to one scenario. Omit to process all "
             "scenarios present in the CSV.",
    )
    p.add_argument(
        "--export-tex", metavar="PATH",
        help="Also write a LaTeX file with one booktabs table per "
             "(scenario, network), ready to \\input{} in the thesis.",
    )
    args = p.parse_args()

    df = pd.read_csv(args.raw_csv)

    required = {"senders", "verifiers", "gas", "role", "role_index"}
    missing = required - set(df.columns)
    if missing:
        print(f"ERROR: CSV is missing columns: {missing}", file=sys.stderr)
        return 2

    df["gas"] = pd.to_numeric(df["gas"], errors="coerce")
    df["role_index"] = pd.to_numeric(df["role_index"], errors="coerce").astype("Int64")
    df = df.dropna(subset=["gas", "role", "role_index"])

    if args.scenario:
        scenarios = [tuple(args.scenario)]
    else:
        pairs = df[["senders", "verifiers"]].drop_duplicates()
        scenarios = sorted({(int(s), int(v)) for s, v in pairs.itertuples(index=False, name=None)})

    scenarios_data = []
    for s, v in scenarios:
        df_scen = df[(df["senders"] == s) & (df["verifiers"] == v)]
        if df_scen.empty:
            print(f"WARNING: no rows for scenario {s}S x {v}V; skipping", file=sys.stderr)
            continue
        scenarios_data.append((s, v, df_scen))
        print_scenario(df_scen, s, v, args.network)

    if args.export_tex:
        export_tex(scenarios_data, args.network, args.export_tex)

    return 0


if __name__ == "__main__":
    sys.exit(main())