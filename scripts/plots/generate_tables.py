#!/usr/bin/env python
"""
generate_tables.py — produce LaTeX tables for the Gas Cost Analysis chapter.

Given the aggregated CSVs from PFC, FIFO, and PSC gas simulations, this script
generates the three numerical tables referenced in chapter 4:

  Table 1 - Per-operation cost summary of PFC, averaged across the 16
            simulated scenarios with range and first-call gas    -> §4.1.2
  Table 2 - Worst-case verification_submit gas of PFC vs FIFO,
            per scenario, with feasibility ratio against the
            EIP-7825 per-transaction cap                         -> §4.1.3
  Table 3 - Per-operation PFC vs PSC overhead in the configurable
            scenario (default 1000x1000), including operations
            exclusive to PSC                                     -> §4.1.4

Each table is written as a standalone .tex file ready to be \\input{}-ed into
the thesis. A separate `preview.tex` includes all tables in a single article
document; compiling it produces a multi-page PDF for review.

Usage:
    python generate_tables.py PFC.csv FIFO.csv PSC.csv \\
        [--out-dir tables/generated] \\
        [--compile-pdf] \\
        [--scenario-for-overhead 1000 1000]
"""

import argparse
import os
import shutil
import subprocess
import sys

import pandas as pd


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EIP_7825_CAP = 16_777_216  # 2^24, per-tx gas cap introduced by Fusaka

OPERATIONS_PFC_BASELINE = [
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

# For the PSC vs PFC overhead table we also include deployment, since the
# 15.8% bytecode delta is part of the protocol's story.
OPERATIONS_PSC_COMMON = ["contract_deployment"] + OPERATIONS_PFC_BASELINE

OPERATIONS_PSC_ONLY = [
    "owner_notify_key_ready",
    "owner_deliver_bundle",
    "owner_kick_verifier",
]


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def tex_label(op: str) -> str:
    """LaTeX-safe representation of an operation identifier."""
    escaped = op.replace("_", r"\_")
    return rf"\texttt{{{escaped}}}"


def fmt_gas(value) -> str:
    """Format an integer gas amount with thousand separator."""
    if value is None or pd.isna(value):
        return "---"
    return f"{int(round(value)):,}"


def fmt_int_signed(value) -> str:
    """Signed integer with thousand separator (for absolute deltas)."""
    if value is None or pd.isna(value):
        return "---"
    v = int(round(value))
    sign = "+" if v >= 0 else ""
    return f"{sign}{v:,}"


def fmt_pct(value) -> str:
    """Signed percentage with one decimal."""
    if value is None or pd.isna(value):
        return "---"
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.1f}\\%"


def fmt_ratio(value) -> str:
    """Ratio formatted as `12.3$\\times$`."""
    if value is None or pd.isna(value):
        return "---"
    return f"{value:.1f}$\\times$"


def scenario_label(senders: int, verifiers: int) -> str:
    """LaTeX scenario label like `1\\,S \\times 2\\,V`."""
    return rf"${senders}\,\text{{S}} \times {verifiers}\,\text{{V}}$"


def representative_gas(df: pd.DataFrame, senders: int, verifiers: int, op: str):
    """Return the representative per-call gas for an operation in a scenario.

    Uses `avg_subsequent_gas` for repeated operations; falls back to
    `first_call_gas` for one-shot operations (count == 1), where
    `avg_subsequent_gas` is 0 by convention.
    """
    row = df[
        (df["senders"] == senders)
        & (df["verifiers"] == verifiers)
        & (df["operation"] == op)
    ]
    if row.empty:
        return None
    r = row.iloc[0]
    avg = float(r["avg_subsequent_gas"])
    if pd.isna(avg) or avg == 0:
        first = float(r["first_call_gas"])
        return first if not pd.isna(first) else None
    return avg


# ---------------------------------------------------------------------------
# Table 1 - PFC per-operation summary
# ---------------------------------------------------------------------------

def gen_table_1_pfc_summary(pfc: pd.DataFrame) -> str:
    """One row per operation, summary stats across the 16 scenarios.

    Columns: First call, Avg subsequent (mean across scenarios), Range [min, max].
    Confirms scale-invariance of per-call costs.
    """
    body = []
    body.append(r"\begin{table}[htbp]")
    body.append(r"    \centering")
    body.append(r"    \caption[Per-operation gas cost of PFC, averaged across the 16 simulated scenarios.]{%")
    body.append(r"        Per-operation gas cost of \texttt{PrivacyFirstContract}, summarised across")
    body.append(r"        the 16 simulated scenarios. The \emph{First call} column reports the gas")
    body.append(r"        consumed by the first invocation of each operation. The \emph{Avg subsequent}")
    body.append(r"        column reports the mean across scenarios of the per-scenario")
    body.append(r"        \texttt{avg\_subsequent\_gas}; the \emph{Range} column is the")
    body.append(r"        $[\min, \max]$ interval of that same metric. Scenarios in which the")
    body.append(r"        operation is invoked exactly once are excluded from the latter two")
    body.append(r"        columns, since \texttt{avg\_subsequent\_gas} is undefined in that case")
    body.append(r"        and reported as zero in the raw data. The narrow range confirms that")
    body.append(r"        per-call cost is a property of the contract, not of the workload.}")
    body.append(r"    \label{tab:pfc-per-operation-summary}")
    body.append(r"    \begin{tabular}{lrrr}")
    body.append(r"        \toprule")
    body.append(r"        Operation & First call (gas) & Avg subsequent (gas) & Range (gas) \\")
    body.append(r"        \midrule")

    for op in OPERATIONS_PFC_BASELINE:
        rows = pfc[pfc["operation"] == op]
        if rows.empty:
            continue
        # Restrict the avg/range computation to scenarios where the operation
        # is invoked more than once: in single-call scenarios `avg_subsequent_gas`
        # is 0 by convention and would skew the statistics. `first_call_gas`
        # is averaged on the same multi-call set for consistency, though it
        # is typically invariant across scenarios.
        multi = rows[rows["count"] >= 2]
        if multi.empty:
            # Op called only once in every scenario: report first_call only.
            first_call = rows["first_call_gas"].mean()
            body.append(
                f"        {tex_label(op)} & "
                f"{fmt_gas(first_call)} & --- & --- \\\\"
            )
            continue
        first_call = multi["first_call_gas"].mean()
        avg_mean = multi["avg_subsequent_gas"].mean()
        avg_min = multi["avg_subsequent_gas"].min()
        avg_max = multi["avg_subsequent_gas"].max()
        body.append(
            f"        {tex_label(op)} & "
            f"{fmt_gas(first_call)} & "
            f"{fmt_gas(avg_mean)} & "
            f"[{fmt_gas(avg_min)}, {fmt_gas(avg_max)}] \\\\"
        )

    body.append(r"        \bottomrule")
    body.append(r"    \end{tabular}")
    body.append(r"\end{table}")
    return "\n".join(body)


# ---------------------------------------------------------------------------
# Table 2 - PFC vs FIFO max verification_submit, per scenario
# ---------------------------------------------------------------------------

def gen_table_2_pfc_vs_fifo_max(pfc: pd.DataFrame, fifo: pd.DataFrame) -> str:
    """One row per scenario. Columns: PFC max, FIFO max, ratio FIFO/PFC,
    ratio FIFO/EIP-7825 cap. The last column is the feasibility indicator
    on Fusaka-era chains."""
    pfc_submit = pfc[pfc["operation"] == "verification_submit"]
    fifo_submit = fifo[fifo["operation"] == "verification_submit"]

    scenarios = sorted({
        (int(s), int(v))
        for s, v in pd.concat([pfc_submit, fifo_submit])[
            ["senders", "verifiers"]
        ].itertuples(index=False, name=None)
    })

    body = []
    body.append(r"\begin{table}[htbp]")
    body.append(r"    \centering")
    body.append(r"    \caption[Worst-case \texttt{verification\_submit} gas: PFC vs FIFO.]{%")
    body.append(r"        Worst-case (\texttt{max\_gas}) of \texttt{verification\_submit} for")
    body.append(r"        \texttt{PrivacyFirstContract} (swap-and-pop, $\mathcal{O}(1)$ removal)")
    body.append(r"        and \texttt{PrivacyFirstContractFifo} (left-shift, $\mathcal{O}(n)$")
    body.append(r"        removal), per scenario. The last column is the FIFO worst-case as a")
    body.append(r"        multiple of the EIP-7825 cap ($2^{24}$\,gas): values above $1.0$")
    body.append(r"        indicate the transaction is unexecutable on a Fusaka-era chain.}")
    body.append(r"    \label{tab:pfc-vs-fifo-max-submit}")
    body.append(r"    \begin{tabular}{lrrrr}")
    body.append(r"        \toprule")
    body.append(r"        Scenario & PFC max (gas) & FIFO max (gas) & Ratio FIFO/PFC & FIFO/EIP-7825 \\")
    body.append(r"        \midrule")

    for s, v in scenarios:
        pfc_row = pfc_submit[(pfc_submit["senders"] == s) & (pfc_submit["verifiers"] == v)]
        fifo_row = fifo_submit[(fifo_submit["senders"] == s) & (fifo_submit["verifiers"] == v)]
        if pfc_row.empty or fifo_row.empty:
            continue
        pfc_max = float(pfc_row.iloc[0]["max_gas"])
        fifo_max = float(fifo_row.iloc[0]["max_gas"])
        ratio = fifo_max / pfc_max if pfc_max > 0 else float("nan")
        cap_ratio = fifo_max / EIP_7825_CAP
        body.append(
            f"        {scenario_label(s, v)} & "
            f"{fmt_gas(pfc_max)} & "
            f"{fmt_gas(fifo_max)} & "
            f"{fmt_ratio(ratio)} & "
            f"{fmt_ratio(cap_ratio)} \\\\"
        )

    body.append(r"        \bottomrule")
    body.append(r"    \end{tabular}")
    body.append(r"\end{table}")
    return "\n".join(body)


# ---------------------------------------------------------------------------
# Table 3 - PFC vs PSC overhead at a configurable scenario
# ---------------------------------------------------------------------------

def gen_table_3_psc_overhead(
    pfc: pd.DataFrame, psc: pd.DataFrame, senders: int, verifiers: int
) -> str:
    """Two-section table: common ops (PFC, PSC, abs delta, % delta) and
    PSC-only ops (PSC absolute cost only)."""
    body = []
    body.append(r"\begin{table}[htbp]")
    body.append(r"    \centering")
    body.append(
        r"    \caption[Per-operation PSC overhead over PFC at "
        + scenario_label(senders, verifiers)
        + r".]{%"
    )
    body.append(r"        Per-operation gas cost of \texttt{PrivacySecondContract} compared to")
    body.append(
        r"        \texttt{PrivacyFirstContract} in the "
        + scenario_label(senders, verifiers)
        + r" scenario."
    )
    body.append(r"        The upper section reports operations common to the two contracts;")
    body.append(r"        the lower section reports operations introduced by the extended")
    body.append(r"        protocol of Section~2.6 and absent from \texttt{PrivacyFirstContract}.}")
    body.append(rf"    \label{{tab:psc-overhead-{senders}s-{verifiers}v}}")
    body.append(r"    \begin{tabular}{lrrrr}")
    body.append(r"        \toprule")
    body.append(r"        Operation & PFC (gas) & PSC (gas) & $\Delta$ (gas) & $\Delta$ (\%) \\")
    body.append(r"        \midrule")
    body.append(r"        \multicolumn{5}{l}{\textit{Operations common to PFC and PSC}} \\")
    body.append(r"        \midrule")

    for op in OPERATIONS_PSC_COMMON:
        p = representative_gas(pfc, senders, verifiers, op)
        q = representative_gas(psc, senders, verifiers, op)
        if p is None or q is None:
            continue
        delta = q - p
        delta_pct = 100.0 * delta / p if p > 0 else float("nan")
        body.append(
            f"        {tex_label(op)} & "
            f"{fmt_gas(p)} & "
            f"{fmt_gas(q)} & "
            f"{fmt_int_signed(delta)} & "
            f"{fmt_pct(delta_pct)} \\\\"
        )

    body.append(r"        \midrule")
    body.append(r"        \multicolumn{5}{l}{\textit{Operations exclusive to PSC}} \\")
    body.append(r"        \midrule")

    for op in OPERATIONS_PSC_ONLY:
        q = representative_gas(psc, senders, verifiers, op)
        if q is None:
            continue
        body.append(
            f"        {tex_label(op)} & --- & {fmt_gas(q)} & --- & --- \\\\"
        )

    body.append(r"        \bottomrule")
    body.append(r"    \end{tabular}")
    body.append(r"\end{table}")
    return "\n".join(body)


# ---------------------------------------------------------------------------
# Preview document
# ---------------------------------------------------------------------------

def gen_preview_tex(table_files: list[str]) -> str:
    """Standalone article including all tables, one per page."""
    body = []
    body.append(r"% Preview document. Includes the generated tables for review.")
    body.append(r"% Compile: pdflatex preview.tex")
    body.append(r"\documentclass[11pt,a4paper]{article}")
    body.append(r"\usepackage[utf8]{inputenc}")
    body.append(r"\usepackage[T1]{fontenc}")
    body.append(r"\usepackage{booktabs}")
    body.append(r"\usepackage{caption}")
    body.append(r"\usepackage[margin=2cm]{geometry}")
    body.append(r"\title{Gas Cost Analysis -- Generated Tables Preview}")
    body.append(r"\author{}\date{}")
    body.append(r"\begin{document}")
    body.append(r"\maketitle")
    body.append(r"")
    for tf in table_files:
        body.append(rf"\input{{{tf}}}")
        body.append(r"\clearpage")
    body.append(r"\end{document}")
    return "\n".join(body)


def compile_pdf(tex_path: str, out_dir: str):
    """Run pdflatex on `tex_path`. Returns the PDF path or None on failure."""
    if shutil.which("pdflatex") is None:
        print("  pdflatex not in PATH; skipping PDF compilation.")
        return None

    abs_tex = os.path.abspath(tex_path)
    abs_out = os.path.abspath(out_dir)

    try:
        # Two passes for any \label cross-references to settle.
        for _ in range(2):
            result = subprocess.run(
                ["pdflatex", "-interaction=nonstopmode",
                 "-output-directory", abs_out, abs_tex],
                capture_output=True, text=True, check=False, cwd=abs_out,
            )
    except Exception as exc:
        print(f"  pdflatex error: {exc}")
        return None

    pdf_path = os.path.splitext(abs_tex)[0] + ".pdf"
    if not os.path.exists(pdf_path):
        print("  pdflatex compilation failed (no PDF produced). Tail of log:")
        print(result.stdout[-1500:])
        return None

    # Clean up aux files
    for ext in (".aux", ".log", ".out"):
        aux = os.path.splitext(abs_tex)[0] + ext
        if os.path.exists(aux):
            os.remove(aux)
    return pdf_path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    p = argparse.ArgumentParser(
        description="Generate LaTeX tables for §4.1 of the thesis.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("pfc", help="PFC aggregated CSV (not raw)")
    p.add_argument("fifo", help="FIFO aggregated CSV (not raw)")
    p.add_argument("psc", help="PSC aggregated CSV (not raw)")
    p.add_argument("--out-dir", default="tables/generated", help="Output directory")
    p.add_argument("--compile-pdf", action="store_true",
                   help="Also compile preview.tex to PDF (requires pdflatex)")
    p.add_argument("--scenario-for-overhead", nargs=2, type=int, default=[1000, 1000],
                   metavar=("SENDERS", "VERIFIERS"),
                   help="Scenario for the PSC overhead table (default: 1000 1000)")
    args = p.parse_args()

    pfc = pd.read_csv(args.pfc)
    fifo = pd.read_csv(args.fifo)
    psc = pd.read_csv(args.psc)

    os.makedirs(args.out_dir, exist_ok=True)
    s, v = args.scenario_for_overhead

    tables = {
        "table_1_pfc_summary.tex":
            gen_table_1_pfc_summary(pfc),
        "table_2_pfc_vs_fifo_max.tex":
            gen_table_2_pfc_vs_fifo_max(pfc, fifo),
        "table_3_psc_overhead.tex":
            gen_table_3_psc_overhead(pfc, psc, s, v),
    }

    for name, content in tables.items():
        path = os.path.join(args.out_dir, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  Written: {path}")

    preview_path = os.path.join(args.out_dir, "preview.tex")
    with open(preview_path, "w", encoding="utf-8") as f:
        f.write(gen_preview_tex(list(tables.keys())))
    print(f"  Written: {preview_path}")

    if args.compile_pdf:
        pdf = compile_pdf(preview_path, args.out_dir)
        if pdf:
            print(f"  Compiled: {pdf}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
