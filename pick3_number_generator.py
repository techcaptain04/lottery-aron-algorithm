"""
Read Pick_3-style CSV (newest draw first) and build 20-number groups for each
match on the midday or evening column: the match row plus the nine draws
listed above it in the file (10 rows × Midday + Evening = 20 values).

For each window value, prints one line: the digits sorted ascending (e.g.
620→26). Then prints a duplicate report: values that appear more than once in
that full list, with counts and which raw draw numbers produced each value.
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Literal

DrawKind = Literal["midday", "evening"]


def parse_optional_int(s: str | None) -> int | None:
    t = (s or "").strip()
    if t == "":
        return None
    return int(t)


def load_draws(path: Path) -> list[tuple[str, int | None, int | None]]:
    rows: list[tuple[str, int | None, int | None]] = []
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for r in reader:
            date = (r.get("Draw Date") or "").strip()
            mid = parse_optional_int(r.get("Midday Daily #"))
            eve = parse_optional_int(r.get("Evening Daily #"))
            rows.append((date, mid, eve))
    return rows


def group_for_match_index(draws: list[tuple[str, int | None, int | None]], i: int) -> list[int | None]:
    start = max(0, i - 9)
    out: list[int | None] = []
    for j in range(start, i + 1):
        _, mid, eve = draws[j]
        out.extend([mid, eve])
    return out


def value_for_draw(date_mid_eve: tuple[str, int | None, int | None], draw: DrawKind) -> int | None:
    _, mid, eve = date_mid_eve
    return mid if draw == "midday" else eve


def groups_for_target(
    draws: list[tuple[str, int | None, int | None]],
    target: int,
    draw: DrawKind,
) -> list[dict]:
    results: list[dict] = []
    for i, row in enumerate(draws):
        date = row[0]
        v = value_for_draw(row, draw)
        if v is None or v != target:
            continue
        numbers = group_for_match_index(draws, i)
        start = max(0, i - 9)
        window_dates = [draws[j][0] for j in range(start, i + 1)]
        results.append(
            {
                "match_row_index": i,
                "match_date": date,
                "date_from": window_dates[0],
                "date_to": window_dates[-1],
                "numbers": numbers,
            }
        )
    return results


def sorted_digits_asc_str(n: int) -> str:
    """Sort decimal digits ascending, then normalize as int string (620 -> 26, 352 -> 235)."""
    return str(int("".join(sorted(str(n)))))


def build_duplicate_items(transformed: list[str]) -> list[tuple[str, int]]:
    counts = Counter(transformed)
    dup_items = [(k, c) for k, c in counts.items() if c >= 2]
    dup_items.sort(key=lambda item: (item[1], int(item[0])))
    return dup_items


def print_duplicate_report(dup_items: list[tuple[str, int]], sources_for: dict[str, set[int]]) -> None:
    print()
    print("--- Duplicates (digit-sorted value appears 2+ times in the list above) ---")
    print("--- Sorted by duplicate count ascending, then value ascending ---")
    if not dup_items:
        print("(none)")
        return
    for key, cnt in dup_items:
        raw_list = sorted(sources_for[key])
        raw_part = ", ".join(str(x) for x in raw_list)
        print(f"{key}: {cnt} time(s)  |  from raw: {raw_part}")


def export_duplicates_csv(
    dup_items: list[tuple[str, int]],
    sources_for: dict[str, set[int]],
    groups: list[dict],
    draw: DrawKind,
    target: int,
) -> Path:
    if groups:
        # groups are built in CSV order (newest first), so first match is the latest target date
        date_text = groups[0]["match_date"]
        date_part = datetime.strptime(date_text, "%m/%d/%Y").strftime("%Y_%m_%d")
    else:
        date_part = datetime.now().strftime("%Y_%m_%d")
    out_path = Path(f"pick3_{date_part}_{draw}.csv")
    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["draw", "target", "digit_sorted_value", "count", "from_raw"])
        for key, cnt in dup_items:
            raw_list = sorted(sources_for[key])
            raw_part = ", ".join(str(x) for x in raw_list)
            w.writerow([draw, target, key, cnt, raw_part])
    return out_path


def main() -> None:
    p = argparse.ArgumentParser(
        description="Extract 20-number windows for each midday or evening winning-number match.",
    )
    p.add_argument(
        "csv",
        type=Path,
        help="Path to the CSV file",
    )
    p.add_argument(
        "-d",
        "--draw",
        choices=("midday", "evening"),
        required=True,
        help="Which draw column must equal the target number",
    )
    p.add_argument(
        "-n",
        "--number",
        type=int,
        required=True,
        metavar="N",
        help="Winning number to search for in the chosen draw column",
    )
    args = p.parse_args()
    path = args.csv
    if not path.is_file():
        raise SystemExit(f"CSV not found: {path}")
    draw: DrawKind = args.draw

    draws = load_draws(path)
    groups = groups_for_target(draws, args.number, draw)

    transformed: list[str] = []
    sources_for: dict[str, set[int]] = defaultdict(set)

    for g in groups:
        for x in g["numbers"]:
            if x is None:
                continue
            t = sorted_digits_asc_str(x)
            transformed.append(t)
            sources_for[t].add(x)
            print(t)

    dup_items = build_duplicate_items(transformed)
    print_duplicate_report(dup_items, sources_for)
    out_file = export_duplicates_csv(dup_items, sources_for, groups, draw, args.number)
    print()
    print(f"Saved duplicate report CSV: {out_file.resolve()}")


if __name__ == "__main__":
    main()
