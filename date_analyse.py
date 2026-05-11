"""
Analyze last N months of draw dates and evaluate category hits for next-day winners.

For each date in the analysis window:
- Take that date's winning numbers (midday/evening) as target numbers.
- Build groups for each target (same window logic as current generator scripts).
- Build duplicate categories from transformed values.
- Check which category contains the next date's winning number(s).

Writes detailed results to date_analyse.csv.
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path


@dataclass
class DrawRow:
    date_text: str
    date: datetime
    midday: int | None
    evening: int | None


def parse_optional_int(s: str | None) -> int | None:
    t = (s or "").strip()
    if t == "":
        return None
    return int(t)


def detect_number_columns(fieldnames: list[str]) -> tuple[str, str]:
    f = set(fieldnames)
    if "Midday Daily #" in f and "Evening Daily #" in f:
        return "Midday Daily #", "Evening Daily #"
    if "Midday Win 4 #" in f and "Evening Win 4 #" in f:
        return "Midday Win 4 #", "Evening Win 4 #"
    raise SystemExit("Unsupported CSV headers. Expected Pick3 or Pick4 columns.")


def load_draws(path: Path) -> list[DrawRow]:
    out: list[DrawRow] = []
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise SystemExit("CSV header is missing.")
        mid_col, eve_col = detect_number_columns(reader.fieldnames)
        for r in reader:
            date_text = (r.get("Draw Date") or "").strip()
            if date_text == "":
                continue
            out.append(
                DrawRow(
                    date_text=date_text,
                    date=datetime.strptime(date_text, "%m/%d/%Y"),
                    midday=parse_optional_int(r.get(mid_col)),
                    evening=parse_optional_int(r.get(eve_col)),
                )
            )
    return out


def row_has_target(row: DrawRow, target: int) -> bool:
    return (row.midday is not None and row.midday == target) or (row.evening is not None and row.evening == target)


def sorted_digits_asc_str(n: int) -> str:
    return str(int("".join(sorted(str(n)))))


def group_for_match_index(draws: list[DrawRow], i: int) -> list[int | None]:
    start = max(0, i - 9)
    vals: list[int | None] = []
    for j in range(start, i + 1):
        vals.extend([draws[j].midday, draws[j].evening])
    return vals


def groups_for_target(draws: list[DrawRow], target: int, cutoff: datetime) -> list[list[int | None]]:
    groups: list[list[int | None]] = []
    for i, row in enumerate(draws):
        if row.date < cutoff:
            continue
        if row_has_target(row, target):
            groups.append(group_for_match_index(draws, i))
    return groups


def category_map_for_target(draws: list[DrawRow], target: int, cutoff: datetime) -> dict[int, set[str]]:
    transformed: list[str] = []
    groups = groups_for_target(draws, target, cutoff)
    for g in groups:
        for x in g:
            if x is None or x == target:
                continue
            transformed.append(sorted_digits_asc_str(x))

    counts = Counter(transformed)
    cat_to_values: dict[int, set[str]] = defaultdict(set)
    for value, cnt in counts.items():
        if cnt >= 2:
            cat_to_values[cnt].add(value)
    return dict(cat_to_values)


def date_key(dt: datetime) -> str:
    return dt.strftime("%m/%d/%Y")


def write_grouped_export(path: Path, grouped_rows: list[dict[str, str]], categories: list[int]) -> None:
    fieldnames = [
        "target_date",
        "target_number",
        "next_date",
        "next_winners_raw",
        "next_winners_transformed",
        "hit_categories",
        "winner_category",
    ] + [f"cat_{c}" for c in categories]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(grouped_rows)


def main() -> None:
    p = argparse.ArgumentParser(description="Analyze last N months and detect category hits for next-day winners.")
    p.add_argument("csv", type=Path, help="Path to Pick3/Pick4 CSV file")
    p.add_argument("--months", type=int, default=3, help="Months to analyze (default: 3)")
    p.add_argument("--out", type=Path, default=Path("date_analyse.csv"), help="Detailed output CSV path (default: date_analyse.csv)")
    p.add_argument(
        "--grouped-out",
        type=Path,
        default=Path("date_analyse_grouped.csv"),
        help="Screenshot-style grouped output CSV path (default: date_analyse_grouped.csv)",
    )
    args = p.parse_args()

    if not args.csv.is_file():
        raise SystemExit(f"CSV not found: {args.csv}")

    draws = load_draws(args.csv)
    if not draws:
        raise SystemExit("No draw rows found in CSV.")

    latest = draws[0].date
    cutoff = latest - timedelta(days=30 * args.months)
    draws_by_date = {date_key(r.date): r for r in draws}

    analysis_rows: list[dict[str, str]] = []
    grouped_rows: list[dict[str, str]] = []
    category_hits = Counter()
    categories_seen: set[int] = set()

    for row in draws:
        if row.date < cutoff:
            continue

        next_date_dt = row.date + timedelta(days=1)
        next_row = draws_by_date.get(date_key(next_date_dt))
        if next_row is None:
            # No draw exists for the exact next calendar date in current file.
            continue

        next_winners = [x for x in (next_row.midday, next_row.evening) if x is not None]
        target_numbers = sorted({x for x in (row.midday, row.evening) if x is not None})

        for target in target_numbers:
            cat_map = category_map_for_target(draws, target, cutoff)
            for c in cat_map:
                categories_seen.add(c)
            hit_categories: set[int] = set()
            hit_values: list[str] = []
            for nw in next_winners:
                tnw = sorted_digits_asc_str(nw)
                for cat, vals in cat_map.items():
                    if tnw in vals:
                        hit_categories.add(cat)
                        hit_values.append(tnw)

            for c in hit_categories:
                category_hits[c] += 1

            analysis_rows.append(
                {
                    "target_date": row.date_text,
                    "target_number": str(target),
                    "next_date": next_row.date_text,
                    "next_winners_raw": " ".join(str(x) for x in next_winners),
                    "next_winners_transformed": " ".join(sorted_digits_asc_str(x) for x in next_winners),
                    "hit_categories": " ".join(str(c) for c in sorted(hit_categories, reverse=True)),
                    "hit_values": " ".join(sorted(hit_values, key=lambda s: int(s))),
                    "category_count": str(len(cat_map)),
                }
            )

            grouped_row: dict[str, str] = {
                "target_date": row.date_text,
                "target_number": str(target),
                "next_date": next_row.date_text,
                "next_winners_raw": " ".join(str(x) for x in next_winners),
                "next_winners_transformed": " ".join(sorted_digits_asc_str(x) for x in next_winners),
                "hit_categories": " ".join(str(c) for c in sorted(hit_categories, reverse=True)),
                "winner_category": str(max(cat_map, key=lambda c: len(cat_map[c]))) if cat_map else "",
            }
            for cat, values in cat_map.items():
                grouped_row[f"cat_{cat}"] = " ".join(sorted(values, key=lambda s: int(s)))
            grouped_rows.append(grouped_row)

    args.out.parent.mkdir(parents=True, exist_ok=True) if args.out.parent != Path("") else None
    with args.out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "target_date",
                "target_number",
                "next_date",
                "next_winners_raw",
                "next_winners_transformed",
                "hit_categories",
                "hit_values",
                "category_count",
            ],
        )
        w.writeheader()
        w.writerows(analysis_rows)

    args.grouped_out.parent.mkdir(parents=True, exist_ok=True) if args.grouped_out.parent != Path("") else None
    category_cols = sorted([c for c in categories_seen if c >= 2], reverse=True)
    if not category_cols:
        category_cols = [6, 5, 4, 3, 2]
    write_grouped_export(args.grouped_out, grouped_rows, category_cols)

    print(f"Saved analysis CSV: {args.out.resolve()}")
    print(f"Saved grouped CSV: {args.grouped_out.resolve()}")
    print(f"Rows analyzed: {len(analysis_rows)}")
    if not category_hits:
        print("Winner category: none (no next-day hits found)")
    else:
        winner, score = category_hits.most_common(1)[0]
        print(f"Winner category: {winner} (hits={score})")
        print("Category hit counts:")
        for cat, cnt in sorted(category_hits.items(), key=lambda t: (-t[1], -t[0])):
            print(f"  category {cat}: {cnt}")


if __name__ == "__main__":
    main()

