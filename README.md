# Pick number groups (Pick 3 and Pick 4)

This repo includes two scripts with the same behavior:

- `pick3_number_generator.py` for Pick 3 CSV data
- `pick4_number_generator.py` for Pick 4 CSV data

Each script finds every **20-number window** tied to a chosen target number and prints each window value after **sorting its digits in ascending order** (one line per number; leading zeros drop, e.g. `620` -> `26`).

The CSV must list draws with **the newest date first**. A row **matches** if your target appears in **midday or evening** (or both). For each match, the script takes that row and the **nine rows above it in the file** (nine draws that appear earlier in the CSV = more recent dates when the sheet is newest-first), then walks midday then evening for those ten rows in file order. That is the same 20-number window as before; it is **not** “only numbers after 531 in calendar order” unless your sheet order matches that layout.

After building each window, every cell equal to the **search target** (`-n`, e.g. `531`) is **removed** before digit-sorting, console output, and duplicate analysis. Other numbers are kept even if they share digits with the target.

The `-d` / `--draw` flag does **not** filter which column is searched; it only labels the **export CSV filename** and the `draw` column in that file (`midday` vs `evening`).

## Requirements

- **Python 3.9 or newer** (standard library only; no `pip install`).

Optional: create a virtual environment if you like; there are still no packages to install into it.

## Installation

1. Clone or copy this project folder to your machine.
2. Place your CSV anywhere you want; you pass its path on every run.

No dependency install step. Optional venv on Windows:

```powershell
cd path\to\pick3
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

## Build `.exe` (Windows)

Install PyInstaller (one-time):

```powershell
python -m pip install pyinstaller
```

Build both executables from the project root:

```powershell
pyinstaller --onefile --name pick3_number_generator pick3_number_generator.py
pyinstaller --onefile --name pick4_number_generator pick4_number_generator.py
```

Generated files:

- `dist\pick3_number_generator.exe`
- `dist\pick4_number_generator.exe`

Run examples:

```powershell
.\dist\pick3_number_generator.exe Pick_3.csv -d midday -n 531
.\dist\pick4_number_generator.exe Pick4.csv -d evening -n 6976
```

## Date analysis (`date_analyse.py`)

Analyse a **date range** and map each target’s **next-day** winners to hit categories (same duplicate-count logic as `pick3_number_generator.py`, e.g. `258: 4 time(s)` → category **4**).

```powershell
python date_analyse.py Pick_3.csv --start-date 04/08/2025 --end-date 01/04/2026
```

Pick 4:

```powershell
python date_analyse.py Pick4.csv --start-date 04/08/2025 --end-date 01/04/2026
```

### Arguments

| Argument | Description |
|----------|-------------|
| `csv` | Pick3 or Pick4 CSV path |
| `--start-date` | First target date to analyse (inclusive), `MM/DD/YYYY` |
| `--end-date` | Last target date to analyse (inclusive), `MM/DD/YYYY` |
| `--out` | Optional output path (default: auto-named under `results/analyse/date/`) |

Default output file:

`results/analyse/date/date_analyse_YYYY_MM_DD_to_YYYY_MM_DD.csv`

Example: `--start-date 04/08/2025 --end-date 01/04/2026` →  
`results/analyse/date/date_analyse_2025_04_08_to_2026_01_04.csv`

### What it does

1. For each draw date in the range, uses that date’s **midday** and **evening** as separate target numbers.
2. Builds categories from the **full CSV** using the same window + digit-sort + duplicate rules as the generator (category = duplicate count: 2, 3, 4, …).
3. **Next date** = target date **+ 1 calendar day** (skipped if that day is missing in the CSV).
4. **`hit_1_category`** = category for next-day **midday** (transformed winner).
5. **`hit_2_category`** = category for next-day **evening** (transformed winner).
6. Appends a **STATISTICS** section at the bottom: `category_4`, `50`, etc., plus **`category_blank`** (next-day winner had no matching duplicate category in `hit_1_category` / `hit_2_category`).
7. Appends a **PROFIT_ANALYSIS** section for the same date range:
   - **total_games** = calendar days × 2 (midday + evening; ~60 games per 30 days)
   - **real_number_count** = average distinct raw numbers to play in that category bucket (sum of `from raw` counts per digit-sorted value in the bucket; e.g. `457` → 3 raws even when category `count` is 4)
   - **cost_per_number** = $1.00 per number played (default)
   - **cost_per_game** = `numbers_in_category × cost_per_number` (example: 3 numbers × $1 = **$3.00 per game**)
   - **total_cost** = `cost_per_game × total_games` (example: $3 × 60 games = $180)
   - **straight_hits** = how many times that category hit (`hit_1` + `hit_2`)
   - **total_payout** = `straight_hits × straight_payout` (default $500.00)
   - **profit** = `total_payout - total_cost`

Optional flags: `--cost-per-number 1.0` and `--straight-payout 500.0`.

This script does not change `pick3_number_generator.py` / `pick4_number_generator.py`.

## New feature: backtest pair (`backtest.py`)

This script backtests a **fixed target number** and checks which category the paired winner lands in:

- If the target number appears as **MIDDAY on date D**, then evaluate the **EVENING** number on the **same date D**.
- If the target number appears as **EVENING on date D**, then evaluate the **MIDDAY** number on the **next calendar date (D+1)**.

The category definition is the **same** duplicate-count category logic as the generator scripts.

### Command

Pick 3:

```powershell
python backtest.py Pick_3.csv --months 3
```

Pick 4:

```powershell
python backtest.py Pick4.csv --months 3
```

To use exact dates instead of `--months`:

```powershell
python backtest.py Pick_3.csv --start-date 04/08/2025 --end-date 01/04/2026
```

### Output

It saves an auto-named CSV to `results/analyse/backtest/` (e.g. `backtest_2025_04_08_to_2026_01_04.csv`) and prints:
- winner category (most hits)
- `category_blank` count (when the paired winner does not fall into any duplicate category)

Each backtest row includes:
- **`hit_category`** — duplicate-count bucket the partner winner landed in
- **`real_number_count`** — distinct raw numbers for the **partner’s** digit-sorted value only (e.g. `678` → **3** raws)
- **`candidates_count`** — sum of `real_count` for **every** digit-sorted value in that `hit_category` bucket in the target’s duplicate pool (same as summing `real_count` on all `3 time(s)` lines in the generator report)

The **STATISTICS** section adds:
- **`sum_real_number_count`** — sum of row `real_number_count` for hits in that category
- **`candidates_count`** — sum of row `candidates_count` for hits in that category (total playable numbers across those category buckets)
- **`avg_candidates_count`** — `candidates_count ÷ count` (rounded), average pool size per hit in that category
- **`total_cost`** — `sum_real_number_count × cost_per_number` (default **$1.00** per number)
- **`profit_1`** — `count × straight_payout − total_cost × date_range × 2`
- **`profit_2`** — `count × straight_payout − avg_candidates_count × date_range × 2` (`date_range` = inclusive calendar days, ×2 = midday + evening; default payout **$500**)

Optional flags: `--cost-per-number 1.0`, `--straight-payout 500.0`.

Optional: to filter to a single target number:

```powershell
python backtest.py Pick_3.csv -n 905 --start-date 04/08/2025 --end-date 01/04/2026
```

## CSV format

### Pick 3 (`pick3_number_generator.py`)

Expected columns:

| Column name       | Meaning        |
|-------------------|----------------|
| `Draw Date`       | Draw date      |
| `Midday Daily #`  | Midday result  |
| `Evening Daily #` | Evening result |

### Pick 4 (`pick4_number_generator.py`)

Expected columns:

| Column name        | Meaning        |
|--------------------|----------------|
| `Draw Date`        | Draw date      |
| `Midday Win 4 #`   | Midday result  |
| `Evening Win 4 #`  | Evening result |

Some historical rows may have an empty midday or evening field; those rows stay in the file so row positions match the sheet. Empty fields are **not** treated as matching your target number.

## Running

**Required arguments:** CSV path, `-d` / `--draw` (export label only), and `-n` / `--number`.  
Optional: `--months` (default `3`) to analyze only the latest N months.

Pick 3:

```text
python pick3_number_generator.py <csv> -d {midday|evening} -n <N> [--months 3]
```

Pick 4:

```text
python pick4_number_generator.py <csv> -d {midday|evening} -n <N> [--months 3]
```

You can put the CSV path first or last; for example, both of these are valid:

```powershell
python pick3_number_generator.py Pick_3.csv -d midday -n 531
python pick4_number_generator.py Pick4.csv -d evening -n 6976
```

### Help

```powershell
python pick3_number_generator.py -h
python pick4_number_generator.py -h
```

### Arguments

| Argument     | Short | Description |
|--------------|-------|-------------|
| `csv`        | —     | Path to the CSV file. It must exist or the program exits with an error. |
| `--draw`     | `-d`  | `midday` or `evening`: used only for the export filename and CSV `draw` column (matching uses **both** columns). |
| `--number`   | `-n`  | Target number (integer); a row matches if midday **or** evening equals this value. |
| `--months`   | —     | Keep only the latest N months of matched rows before grouping (default: `3`). |

### Examples

Midday `531` with the sample file:

```powershell
cd path\to\pick3
python pick3_number_generator.py Pick_3.csv -d midday -n 531
```

Pick 4 evening `6976` with the sample file:

```powershell
python pick4_number_generator.py Pick4.csv -d evening -n 6976
```

Another file path:

```powershell
python pick4_number_generator.py D:\data\Pick4.csv -d midday -n 5081
```

macOS / Linux (use `python3` if that is your command):

```bash
cd /path/to/pick3
python3 pick3_number_generator.py Pick_3.csv -d evening -n 270
python3 pick4_number_generator.py Pick4.csv -d evening -n 6976
```

### Common errors

- Omitting `csv`, `-d`, or `-n` → argparse prints usage and lists missing arguments.
- Path that is not a file → `CSV not found: <path>`.

## Output

Console output now shows **grouped numbers only** (no raw collected-number list).

Processing flow:

1. Build 20-value windows from matched rows (target found in midday or evening).
2. Keep only matches in the latest `--months` window (default: 3 months).
3. Remove values equal to the search target (`-n`).
4. Convert each remaining value to ascending-digit form (e.g. `352` → `235`).
5. Keep duplicates (occurrence >= 2), then group by duplicate count category.

Console section:

- `Category 6: ...`
- `Category 5: ...`
- `Category 4: ...`
- ...

Categories are shown high-to-low (like your client screenshot), and each category line contains the grouped numbers for that duplicate count.

Then it prints:

- `Winner category (most numbers): X (count=Y)`

**3 — CSV export (automatic)**

Each run also saves the duplicate section to a CSV file in the current working directory:

- Pick 3 script: `pick3_YYYY_MM_DD_midday.csv` or `pick3_YYYY_MM_DD_evening.csv`
- Pick 4 script: `pick4_YYYY_MM_DD_midday.csv` or `pick4_YYYY_MM_DD_evening.csv`

The `YYYY_MM_DD` part is based on the **latest matched draw date** in the CSV (first match row when reading newest-first), not just today's date.  
Example: if the newest row where `531` appears in midday or evening is `05/05/2026`, and you passed `-d midday`, the file is `pick3_2026_05_05_midday.csv`.

If there are no matches for that target/draw, it falls back to today's date.

CSV columns are:

- `draw` (`midday` or `evening`)
- `target` (number you passed with `-n`)
- `digit_sorted_value` (digit-sorted form, e.g. `457`)
- `count` (how many times that value appeared in the pooled windows — the **category**)
- `real_number_count` (how many **distinct** raw draw numbers map to it, e.g. `574, 745, 754` → **3** even when `count` is 4)
- `from_raw` (comma-separated original numbers that map to that digit-sorted value)

## File reference

| File                         | Role |
|------------------------------|------|
| `pick3_number_generator.py` | CLI tool |
| `pick4_number_generator.py` | CLI tool |
| `Pick_3.csv`                | Example data (newest draw first) |
| `Pick4.csv`                 | Example data (newest draw first) |
