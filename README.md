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

## New client analysis feature

Use this new command to analyze the **last 3 months** of draw dates and find which category wins most often for the **next date**:

```powershell
python date_analyse.py Pick_3.csv --months 3 --out date_analyse.csv --grouped-out date_analyse_grouped.csv
```

For Pick 4:

```powershell
python date_analyse.py Pick4.csv --months 3 --out date_analyse.csv --grouped-out date_analyse_grouped.csv
```

What it does:

1. Loops through draw dates in the last N months (`--months`, default 3).
2. For each date, uses that date's winning numbers as targets.
3. Builds categories using the same transformation/grouping logic as current scripts.
4. Looks at the **next calendar date (+1 day)** winner(s) and records which category they land in.  
   (If the exact next day is missing in the CSV, that row is skipped.)
5. Saves detailed rows to `date_analyse.csv`.
6. Saves a client-friendly grouped export to `date_analyse_grouped.csv` with category columns (`cat_6`, `cat_5`, `cat_4`, `cat_3`, `cat_2`, etc.) so it is easier to read like the screenshot style.
7. Prints the overall winner category summary.

This is a **new feature script** and does not change the existing `pick3_number_generator.py` / `pick4_number_generator.py` workflow.

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
- `digit_sorted_value`
- `count`
- `from_raw` (comma-separated original numbers that map to that digit-sorted value)

## File reference

| File                         | Role |
|------------------------------|------|
| `pick3_number_generator.py` | CLI tool |
| `pick4_number_generator.py` | CLI tool |
| `Pick_3.csv`                | Example data (newest draw first) |
| `Pick4.csv`                 | Example data (newest draw first) |
