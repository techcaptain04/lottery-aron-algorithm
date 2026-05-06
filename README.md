# Pick number groups (Pick 3 and Pick 4)

This repo includes two scripts with the same behavior:

- `pick3_number_generator.py` for Pick 3 CSV data
- `pick4_number_generator.py` for Pick 4 CSV data

Each script finds every **20-number window** tied to a chosen winning result and prints each window value after **sorting its digits in ascending order** (one line per number; leading zeros drop, e.g. `620` -> `26`).

The CSV must list draws with **the newest date first**. For every row where your target appears in the chosen **midday** or **evening** column, the script takes that row and the **nine rows above it** (nine more recent draws), then walks midday then evening for those ten rows in file order. Empty cells are skipped.

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

**All arguments are required:** the CSV path, `-d` / `--draw`, and `-n` / `--number`. There are no defaults.

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
| `--draw`     | `-d`  | `midday` or `evening`: the column that must equal the target. |
| `--number`   | `-n`  | Target winning number (integer, e.g. `531`). |

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
2. For each integer `n`, it **sorts its decimal digits from smallest to largest**, joins them, converts to `int` (so leading zeros disappear), then prints that with `str`. Examples: `352` → `235`, `736` → `367`, `878` → `788`, `620` → `26`, `98` → `89`.
3. Missing midday/evening cells are skipped.

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

The `YYYY_MM_DD` part is based on the **target number's latest matched draw date** in the CSV (for the selected draw column), not just today's date.  
Example: if `531` matches midday on `05/05/2026`, file is `pick3_2026_05_05_midday.csv`.

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
