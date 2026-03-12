# Reversible Recuperated Brayton Cycle

This folder contains the reversible recuperated Brayton cycle solver, plotting workflow, and SQLite-backed sensitivity-analysis tools.

## Contents

- `reversible-recup-brayton.py` — main cycle solver
- `config.json` — baseline cycle configuration
- `plots/` — generated cycle plots
- `analysis/dual_mode_sqlite_io.py` — SQLite I/O pipeline for dual-mode runs
- `analysis/lhsmdu_sweep_config.json` — LHSMDU sweep settings
- `analysis/cycle_sensitivity.db` — SQLite database for sensitivity results

---

## 1. Basic cycle solve

Run the current configuration:

```powershell
.\.venv\Scripts\python.exe .\reversible-recup-br\reversible-recup-brayton.py --config .\reversible-recup-br\config.json
```

Override the mode:

```powershell
.\.venv\Scripts\python.exe .\reversible-recup-br\reversible-recup-brayton.py --config .\reversible-recup-br\config.json --mode charge
```

Generate plots for the current mode:

```powershell
.\.venv\Scripts\python.exe .\reversible-recup-br\reversible-recup-brayton.py --config .\reversible-recup-br\config.json --plot
```

Generate plots for both charge and discharge:

```powershell
.\.venv\Scripts\python.exe .\reversible-recup-br\reversible-recup-brayton.py --config .\reversible-recup-br\config.json --plot-both
```

---

## 2. Cycle outputs currently reported

Each cycle solve reports:

- `net_work` (positive = power out)
- `Q_hot`
- `Q_cold`
- `eta_thermal` in discharge mode or `COP_heating` in charge mode
- `exergetic_efficiency`
- `cycle_isentropic_efficiency`
- `isentropic_reference_net_work`
- `total_exergy_destruction`

Component summaries also report:

- `machine_A`: `W_dot`, `X_dest`
- `machine_B`: `W_dot`, `X_dest`
- `recuperator`: `Q_dot`, `X_dest`
- `hot_hx`: `Q_dot`, `X_dest`
- `cold_hx`: `Q_dot`, `X_dest`

---

## 3. SQLite dual-mode I/O workflow

The analysis pipeline is designed so that **one parameter set becomes one database row**, and that row stores:

- all essential input parameters
- the full resolved input configuration in `input_config_json`
- charge-mode outputs
- discharge-mode outputs
- objective columns comparing charge and discharge exergetic performance

### Standard baseline run

Write a baseline row into the essential results table:

```powershell
.\.venv\Scripts\python.exe .\reversible-recup-br\analysis\dual_mode_sqlite_io.py --config .\reversible-recup-br\config.json --db .\reversible-recup-br\analysis\cycle_sensitivity.db --output-table cycle_dual_mode_results_essential --seed-baseline --reset-output-table
```

### Essential results table

The default essential output table is:

- `cycle_dual_mode_results_essential`

It contains:

- input columns like `input_p_low_pa`, `input_eta_a`, `input_eps_recup`, etc.
- `input_notes_json`
- `input_config_json`
- charge summary columns
- discharge summary columns
- objective columns such as:
  - `objective_ex_eff_min_both`
  - `objective_ex_eff_product`
  - `objective_ex_eff_delta_discharge_minus_charge`
  - `objective_ex_eff_harmonic_mean`
  - `objective_round_trip_proxy`

---

## 4. LHSMDU sweep workflow

The file `analysis/lhsmdu_sweep_config.json` controls the Latin-hypercube-style sweep.

### Run the sweep

```powershell
.\.venv\Scripts\python.exe .\reversible-recup-br\analysis\dual_mode_sqlite_io.py --run-lhsmdu --lhsmdu-config .\reversible-recup-br\analysis\lhsmdu_sweep_config.json
```

Start fresh by recreating result tables:

```powershell
.\.venv\Scripts\python.exe .\reversible-recup-br\analysis\dual_mode_sqlite_io.py --run-lhsmdu --lhsmdu-config .\reversible-recup-br\analysis\lhsmdu_sweep_config.json --reset-output-table
```

Run a smaller smoke test first:

```powershell
.\.venv\Scripts\python.exe .\reversible-recup-br\analysis\dual_mode_sqlite_io.py --run-lhsmdu --lhsmdu-config .\reversible-recup-br\analysis\lhsmdu_sweep_config.json --lhsmdu-samples 10 --reset-output-table
```

### What the sweep config controls

`analysis/lhsmdu_sweep_config.json` defines:

- `n_samples` — number of sampled parameter sets
- `seed` — reproducibility
- `fixed` — non-swept inputs, such as `fluid` and `expander_mode`
- `numeric_bounds` — min/max bounds for swept numeric parameters
- `constraints` — feasibility filters and dome-avoidance rules
- `solver_profiles` — user-defined solver settings

### Solver-profile-specific result tables

Each solver profile writes to its own SQLite table using an automatic slug. Example names:

- `results_solv_mi100_tol0p01_htol10_rel0p5`
- `results_solv_mi150_tol0p001_htol5_rel0p4`

This keeps solver sensitivity separate from thermodynamic-parameter sensitivity.

---

## 5. Notes about LHSMDU generation

The sweep runner will:

1. generate a sample in the unit hypercube
2. map it into the configured numeric bounds
3. enforce feasibility constraints, including:
   - `P_high > P_low`
   - `T_source > T_sink`
   - optional CO2 critical-pressure / critical-temperature guards
4. run both `charge` and `discharge`
5. write one row containing both results

### Important practical note

The current default ranges are intentionally broad. This is useful for exploration, but it also means many sampled points may fail to converge or may represent poor/hostile cycle conditions.

Recommended workflow:

1. start with `--lhsmdu-samples 10`
2. inspect success/failure counts
3. tighten ranges if needed
4. scale to `100` or more samples later

---

## 6. Database inspection

### Option A — Use a SQLite extension in VS Code

Open:

- `reversible-recup-br/analysis/cycle_sensitivity.db`

and browse the result tables directly.

### Option B — Quick Python inspection

List tables:

```powershell
.\.venv\Scripts\python.exe -c "import sqlite3; conn=sqlite3.connect(r'reversible-recup-br\analysis\cycle_sensitivity.db'); cur=conn.cursor(); print(cur.execute(\"SELECT name FROM sqlite_master WHERE type='table' ORDER BY name\").fetchall()); conn.close()"
```

Preview a result table:

```powershell
.\.venv\Scripts\python.exe -c "import sqlite3, pandas as pd; conn=sqlite3.connect(r'reversible-recup-br\analysis\cycle_sensitivity.db'); df=pd.read_sql_query('SELECT * FROM cycle_dual_mode_results_essential LIMIT 5', conn); print(df.T); conn.close()"
```

Count successful rows in a solver-profile table:

```powershell
.\.venv\Scripts\python.exe -c "import sqlite3; conn=sqlite3.connect(r'reversible-recup-br\analysis\cycle_sensitivity.db'); cur=conn.cursor(); table='results_solv_mi100_tol0p01_htol10_rel0p5'; print(cur.execute(f'SELECT COUNT(*) FROM {table} WHERE status=\"ok\"').fetchone()); conn.close()"
```

---

## 7. Optimization intent

The current database layout is designed for future optimization and tradeoff studies where the goal is to compare:

- `charge_exergetic_efficiency`
- `discharge_exergetic_efficiency`

Useful objective columns already stored include:

- minimum of both exergetic efficiencies
- product of both exergetic efficiencies
- discharge-minus-charge delta
- harmonic mean of both exergetic efficiencies
- round-trip proxy based on discharge thermal efficiency and charge COP

This lets the raw results stay intact while optimization logic can be developed later in SQL or Python.

---

## 8. Fallback note on LHSMDU package

The sweep script attempts to use the `lhsmdu` package if available. If it is not installed, the script falls back to an internal Latin-hypercube-style generator so the sweep can still run.

---

## 9. Recommended next steps

- tighten `numeric_bounds` if many cases fail
- add stronger feasibility filters before solving
- add SQL ranking queries for best combined charge/discharge cases
- add downstream scripts for Pareto filtering and visualization

---

## 10. Export successful rows to per-row parquet metadata

You can export only successful rows (`status = "ok"`) from one existing results table into one parquet file per row.

```powershell
.\.venv\Scripts\python.exe .\reversible-recup-br\analysis\dual_mode_sqlite_io.py --export-success-parquet --db .\reversible-recup-br\analysis\cycle_sensitivity.db --export-table cycle_dual_mode_results_essential --export-root .\reversible-recup-br\analysis\metadata --metadata-name plot_metadata
```

Output layout:

- `reversible-recup-br/analysis/metadata/<table_name>/row_<case_id>/<metadata_name>.parquet`

Notes:

- only rows with `status = "ok"` are exported
- each parquet contains all columns from the selected SQLite row
- `--metadata-name` can be any string; `.parquet` is added automatically

### One-shot export + plotting

You can export successful rows and immediately generate charge/discharge cycle diagrams in the same command:

```powershell
.\.venv\Scripts\python.exe .\reversible-recup-br\analysis\dual_mode_sqlite_io.py --export-success-parquet --db .\reversible-recup-br\analysis\cycle_sensitivity.db --export-table cycle_dual_mode_results_essential --export-root .\reversible-recup-br\analysis\metadata --metadata-name plot_metadata --plot-after-export
```

Optional plot flags (used with `--plot-after-export`):

- `--plot-overwrite`
- `--plot-no-vapor-dome`
- `--plot-skip-drift-check`
- `--plot-drift-tolerance <value>`
- `--plot-limit <N>`

---

## 11. Plot cycle diagrams from exported parquet rows

Use the plotting runner to recurse the metadata export tree and generate charge/discharge cycle diagrams for each row parquet.

```powershell
.\.venv\Scripts\python.exe .\reversible-recup-br\analysis\plot_exported_cycle_diagrams.py --export-root .\reversible-recup-br\analysis\metadata --metadata-name plot_metadata
```

This writes plots next to each parquet row file:

- `.../row_<case_id>/charge_co2_cycle_diagrams.png`
- `.../row_<case_id>/discharge_co2_cycle_diagrams.png`

Useful options:

- `--table <table_folder_name>`: process one table folder under `metadata`
- `--overwrite`: regenerate plots even if png files already exist
- `--skip-drift-check`: skip stored-vs-recomputed metric drift warnings
- `--no-vapor-dome`: disable vapor-dome overlay in the diagrams
