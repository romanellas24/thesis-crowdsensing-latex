# Gas Simulation Plotting Scripts

Generate thesis-quality PDF figures from gas simulation CSV data.

## Setup

```bash
pip install -r scripts/plots/requirements.txt
```

## Usage

Each script reads CSV files produced by the simulation and writes
PDF + PNG figures to `figures/generated/`.

```bash
# Plot 1: verification_request gas growth (O(n) finding)
python scripts/plots/1_plot_verification_request_growth.py results/gas_simulation_results_raw.csv

# Plot 2: verification_submit spikes (majority consensus cost)
python scripts/plots/2_plot_verification_submit_spikes.py results/gas_simulation_results_raw.csv

# Plot 3: Gas per operation first vs subsequent (Table I extension)
python scripts/plots/3_plot_gas_per_operation.py results/gas_simulation_results.csv

# Plot 4: Gas per role vs scale (economic viability)
python scripts/plots/4_plot_gas_per_role.py results/gas_simulation_results.csv

# Plot 5: data_submission constant gas (O(1) vs O(n) contrast)
python scripts/plots/5_plot_data_submission_constant.py results/gas_simulation_results_raw.csv
```

## Output

All figures are saved to `figures/generated/` as both PDF (for LaTeX)
and PNG (for preview).

## LaTeX integration

```latex
\includegraphics[width=\textwidth]{figures/generated/submission_vs_verification_100s_100v.pdf}
```
