#!/usr/bin/env bash
#
# run_all.sh - generate every figure for chapter 4 from the three CSV pairs.
#
# Expects the following file layout (adjust paths if your repo differs):
#   results/pfc_gas_simulation_results.csv
#   results/pfc_gas_simulation_results_raw.csv
#   results/fifo_gas_simulation_results.csv
#   results/fifo_gas_simulation_results_raw.csv
#   results/psc_gas_simulation_results.csv
#   results/psc_gas_simulation_results_raw.csv
#
# Output goes to figures/generated/ (PDF + PNG).

RESULTS="/home/romanellas/WebstormProjects/thesis-crowdsensing-contracts/results"

PFC_AGG="$RESULTS/pfc_gas_simulation_results.csv"
PFC_RAW="$RESULTS/pfc_gas_simulation_results_raw.csv"
FIFO_AGG="$RESULTS/fifo_gas_simulation_results.csv"
FIFO_RAW="$RESULTS/fifo_gas_simulation_results_raw.csv"
PSC_AGG="$RESULTS/psc_gas_simulation_results.csv"
PSC_RAW="$RESULTS/psc_gas_simulation_results_raw.csv"

have() { [[ -f "$1" ]]; }

echo "=== Single-contract plots ==="

for raw in "$PFC_RAW" "$FIFO_RAW" "$PSC_RAW"; do
    if have "$raw"; then
        echo ">>> $raw"
        python 1_plot_verification_request_stability.py "$raw"
        python 2_plot_verification_submit_distribution.py "$raw"
        python 5_plot_data_submission_constant.py "$raw"
    else
        echo "  skip (missing): $raw"
    fi
done

for agg in "$PFC_AGG" "$FIFO_AGG" "$PSC_AGG"; do
    if have "$agg"; then
        echo ">>> $agg"
        python 3_plot_gas_per_operation.py "$agg"
        python 4_plot_gas_per_role.py "$agg"
    else
        echo "  skip (missing): $agg"
    fi
done

echo
echo "=== Multi-contract plots ==="

if have "$PFC_RAW" && have "$FIFO_RAW"; then
    echo ">>> PFC vs FIFO (raw)"
    python 6_plot_pfc_vs_fifo_submit.py "$PFC_RAW" "$FIFO_RAW"
fi

if have "$PFC_AGG" && have "$FIFO_AGG"; then
    echo ">>> EIP-7825 feasibility"
    python 7_plot_eip7825_feasibility.py "$PFC_AGG" "$FIFO_AGG"
fi

if have "$PFC_AGG" && have "$PSC_AGG"; then
    echo ">>> PSC vs PFC overhead"
    python 8_plot_psc_vs_pfc_overhead.py "$PFC_AGG" "$PSC_AGG"
fi

# 9 runs with whatever is available (2 or 3 contracts)
SCALING_ARGS=()
have "$PFC_AGG"  && SCALING_ARGS+=("$PFC_AGG")
have "$FIFO_AGG" && SCALING_ARGS+=("$FIFO_AGG")
have "$PSC_AGG"  && SCALING_ARGS+=("$PSC_AGG")
if (( ${#SCALING_ARGS[@]} >= 2 )); then
    echo ">>> Three-contract scaling"
    python 9_plot_gas_scaling_three_contracts.py "${SCALING_ARGS[@]}"
fi

echo
echo "=== Done. Figures in figures/generated/ ==="
