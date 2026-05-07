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

**All arguments are required:** the CSV path, `-d` / `--draw` (export label only), and `-n` / `--number`. There are no defaults.

Pick 3:

```text
python pick3_number_generator.py <csv> -d {midday|evening} -n <N>
```

Pick 4:

```text
python pick4_number_generator.py <csv> -d {midday|evening} -n <N>
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

Output has two parts:

**1 — One line per window value (transformed)**

1. For each match (in file order), it walks that match’s 20 values in order (ten rows × midday then evening).
2. It **drops every value equal to the search target** (`-n`) from that list (only that integer; other values stay).
3. For each remaining integer `n`, it **sorts its decimal digits from smallest to largest**, joins them, converts to `int` (so leading zeros disappear), then prints that with `str`. Examples: `352` → `235`, `736` → `367`, `878` → `788`, `620` → `26`, `98` → `89`.
4. Missing midday/evening cells are skipped.

This is **ascending digit order**, not character reversal of the string (`352` → `235`, not `253`).

**2 — Duplicate report**

After those lines, it prints a section **Duplicates (digit-sorted value appears 2+ times)** listing only transformed values that occurred more than once in part 1, **sorted by duplicate count (low to high)** and then by numeric value (low to high) for ties. Each line shows:

- the digit-sorted value,
- how many times it appeared,
- **`from raw:`** the distinct original draw numbers from the CSV that map to that value after sorting digits (e.g. `135` may list `531`, `153`, …).

If nothing repeats, it prints `(none)`.

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
