"""
Analyze draw dates in a date range and map next-day winners to hit categories.

Category = duplicate count from the same logic as pick3/pick4_number_generator
(e.g. 258: 4 time(s) -> category 4).

For each target date in [start, end]:
- Use that date's midday/evening numbers as targets (one row per target number).
- Build duplicate categories for the target across the full CSV (no month cutoff).
- Next date = target date + 1 calendar day.
- hit_1_category = category for next-day midday (digit-sorted duplicate count).
- hit_2_category = category for next-day evening.

Writes results/analyse/date/date_analyse_YYYY_MM_DD_to_YYYY_MM_DD.csv with statistics at the end.
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

COST_PER_NUMBER = 1.0
STRAIGHT_PAYOUT = 500.0
DRAWS_PER_DAY = 2  # midday + evening (~60 games per 30-day month)


@dataclass
class DrawRow:
    date_text: str
    date: datetime
    midday: int | None
    evening: int | None


def parse_date(s: str, label: str) -> datetime:
    try:
        return datetime.strptime(s.strip(), "%m/%d/%Y")
    except ValueError as e:
        raise SystemExit(f"Invalid {label} (use MM/DD/YYYY): {s}") from e


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
    return (row.midday is not None and row.midday == target) or (
        row.evening is not None and row.evening == target
    )


def sorted_digits_asc_str(n: int) -> str:
    return str(int("".join(sorted(str(n)))))


def group_for_match_index(draws: list[DrawRow], i: int) -> list[int | None]:
    start = max(0, i - 9)
    vals: list[int | None] = []
    for j in range(start, i + 1):
        vals.extend([draws[j].midday, draws[j].evening])
    return vals


def build_category_data(draws: list[DrawRow], target: int) -> tuple[dict[str, int], dict[int, int]]:
    """Return (value->category, category->total distinct raw numbers to play in that bucket)."""
    transformed: list[str] = []
    sources_for: dict[str, set[int]] = defaultdict(set)
    for i, row in enumerate(draws):
        if not row_has_target(row, target):
            continue
        for x in group_for_match_index(draws, i):
            if x is None or x == target:
                continue
            t = sorted_digits_asc_str(x)
            transformed.append(t)
            sources_for[t].add(x)
    counts = Counter(transformed)
    value_to_cat = {value: cnt for value, cnt in counts.items() if cnt >= 2}
    real_per_cat: dict[int, int] = defaultdict(int)
    for value, cat in value_to_cat.items():
        real_per_cat[cat] += len(sources_for[value])
    return value_to_cat, dict(real_per_cat)


def category_for_winner(cat_map: dict[str, int], winner: int | None) -> str:
    if winner is None:
        return ""
    key = sorted_digits_asc_str(winner)
    cat = cat_map.get(key)
    return str(cat) if cat is not None else ""


def date_key(dt: datetime) -> str:
    return dt.strftime("%m/%d/%Y")


def file_date_part(dt: datetime) -> str:
    return dt.strftime("%Y_%m_%d")


def default_output_path(start: datetime, end: datetime) -> Path:
    return (
        Path("results")
        / "analyse"
        / "date"
        / f"date_analyse_{file_date_part(start)}_to_{file_date_part(end)}.csv"
    )


def games_in_range(start_dt: datetime, end_dt: datetime) -> int:
    days = (end_dt - start_dt).days + 1
    return days * DRAWS_PER_DAY


def avg_real_numbers_in_category(real_counts_by_cat: dict[int, list[int]], category: int) -> int:
    """Average total distinct raw numbers to play per target for this category bucket."""
    sizes = real_counts_by_cat.get(category, [])
    if not sizes:
        return 0
    return round(sum(sizes) / len(sizes))


def write_results(
    path: Path,
    rows: list[dict[str, str]],
    stats: Counter[int],
    blank_count: int,
    *,
    start_dt: datetime,
    end_dt: datetime,
    real_counts_by_cat: dict[int, list[int]],
    cost_per_number: float,
    straight_payout: float,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "target_date",
        "target_number",
        "next_date",
        "next_midday_raw",
        "next_evening_raw",
        "next_midday_transformed",
        "next_evening_transformed",
        "hit_1_category",
        "hit_2_category",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        dw = csv.DictWriter(f, fieldnames=fieldnames)
        dw.writeheader()
        dw.writerows(rows)

        # Use plain csv.writer below so all statistics/profit columns are written correctly.
        w = csv.writer(f)
        w.writerow([])
        w.writerow(["STATISTICS"])
        w.writerow(["category", "count"])
        for cat in sorted(stats.keys(), reverse=True):
            w.writerow([f"category_{cat}", stats[cat]])
        w.writerow(["category_blank", blank_count])

        games = games_in_range(start_dt, end_dt)
        days = (end_dt - start_dt).days + 1
        w.writerow([])
        w.writerow(["PROFIT_ANALYSIS"])
        w.writerow(["start_date", start_dt.strftime("%m/%d/%Y")])
        w.writerow(["end_date", end_dt.strftime("%m/%d/%Y")])
        w.writerow(["calendar_days", days])
        w.writerow(["total_games", games])
        w.writerow(["cost_per_number", f"{cost_per_number:.2f}"])
        example_cost = 3 * cost_per_number
        w.writerow(
            [
                "cost_per_game_formula",
                f"real_number_count x cost_per_number (e.g. 3 numbers x ${cost_per_number:.2f} = ${example_cost:.2f} per game)",
            ]
        )
        w.writerow(["straight_payout", f"{straight_payout:.2f}"])
        w.writerow([])
        w.writerow(
            [
                "category",
                "real_number_count",
                "cost_per_game",
                "total_games",
                "total_cost",
                "straight_hits",
                "total_payout",
                "profit",
            ]
        )
        all_cats = sorted(set(stats.keys()) | set(real_counts_by_cat.keys()), reverse=True)
        for cat in all_cats:
            hits = stats.get(cat, 0)
            numbers = avg_real_numbers_in_category(real_counts_by_cat, cat)
            # e.g. 3 numbers at $1 each -> $3.00 cost per game
            cost_per_game = numbers * cost_per_number
            total_cost = cost_per_game * games
            total_payout = hits * straight_payout
            profit = total_payout - total_cost
            w.writerow(
                [
                    f"category_{cat}",
                    numbers,
                    f"{cost_per_game:.2f}",
                    games,
                    f"{total_cost:.2f}",
                    hits,
                    f"{total_payout:.2f}",
                    f"{profit:.2f}",
                ]
            )


def main() -> None:
    p = argparse.ArgumentParser(
        description="Analyse date range: map next-day winners to duplicate-count categories.",
    )
    p.add_argument("csv", type=Path, help="Path to Pick3/Pick4 CSV file")
    p.add_argument(
        "--start-date",
        required=True,
        metavar="MM/DD/YYYY",
        help="First target date to analyse (inclusive)",
    )
    p.add_argument(
        "--end-date",
        required=True,
        metavar="MM/DD/YYYY",
        help="Last target date to analyse (inclusive)",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output CSV path (default: results/analyse/date/date_analyse_START_to_END.csv)",
    )
    p.add_argument(
        "--cost-per-number",
        type=float,
        default=COST_PER_NUMBER,
        help=f"Cost to play one number per draw (default: {COST_PER_NUMBER})",
    )
    p.add_argument(
        "--straight-payout",
        type=float,
        default=STRAIGHT_PAYOUT,
        help=f"Payout for one straight win (default: {STRAIGHT_PAYOUT})",
    )
    args = p.parse_args()

    if not args.csv.is_file():
        raise SystemExit(f"CSV not found: {args.csv}")

    start_dt = parse_date(args.start_date, "--start-date")
    end_dt = parse_date(args.end_date, "--end-date")
    if start_dt > end_dt:
        raise SystemExit("--start-date must be on or before --end-date")

    out_path = args.out or default_output_path(start_dt, end_dt)

    draws = load_draws(args.csv)
    if not draws:
        raise SystemExit("No draw rows found in CSV.")

    draws_by_date = {date_key(r.date): r for r in draws}
    category_cache: dict[int, dict[str, int]] = {}
    real_counts_by_cat: dict[int, list[int]] = defaultdict(list)

    analysis_rows: list[dict[str, str]] = []
    stats: Counter[int] = Counter()
    blank_count = 0

    for row in draws:
        if row.date < start_dt or row.date > end_dt:
            continue

        next_row = draws_by_date.get(date_key(row.date + timedelta(days=1)))
        if next_row is None:
            continue

        target_numbers = sorted({x for x in (row.midday, row.evening) if x is not None})
        for target in target_numbers:
            if target not in category_cache:
                cat_map, real_per_cat = build_category_data(draws, target)
                category_cache[target] = cat_map
                for cat, real_total in real_per_cat.items():
                    real_counts_by_cat[cat].append(real_total)
            cat_map = category_cache[target]

            hit_1 = category_for_winner(cat_map, next_row.midday)
            hit_2 = category_for_winner(cat_map, next_row.evening)

            if hit_1:
                stats[int(hit_1)] += 1
            elif next_row.midday is not None:
                blank_count += 1
            if hit_2:
                stats[int(hit_2)] += 1
            elif next_row.evening is not None:
                blank_count += 1

            analysis_rows.append(
                {
                    "target_date": row.date_text,
                    "target_number": str(target),
                    "next_date": next_row.date_text,
                    "next_midday_raw": "" if next_row.midday is None else str(next_row.midday),
                    "next_evening_raw": "" if next_row.evening is None else str(next_row.evening),
                    "next_midday_transformed": ""
                    if next_row.midday is None
                    else sorted_digits_asc_str(next_row.midday),
                    "next_evening_transformed": ""
                    if next_row.evening is None
                    else sorted_digits_asc_str(next_row.evening),
                    "hit_1_category": hit_1,
                    "hit_2_category": hit_2,
                }
            )

    write_results(
        out_path,
        analysis_rows,
        stats,
        blank_count,
        start_dt=start_dt,
        end_dt=end_dt,
        real_counts_by_cat=real_counts_by_cat,
        cost_per_number=args.cost_per_number,
        straight_payout=args.straight_payout,
    )

    games = games_in_range(start_dt, end_dt)
    print(f"Saved analysis CSV: {out_path.resolve()}")
    print(f"Date range: {args.start_date} to {args.end_date} ({games} games, ${args.cost_per_number:.2f}/number)")
    print(f"Rows written: {len(analysis_rows)}")
    print("Category statistics (hit_1 + hit_2):")
    if stats:
        winner_cat, winner_cnt = stats.most_common(1)[0]
        print(f"Most frequent category: {winner_cat} (count={winner_cnt})")
        for cat, cnt in sorted(stats.items(), key=lambda t: (-t[1], -t[0])):
            print(f"  category_{cat}: {cnt}")
    else:
        print("  (no numeric category hits)")
    print(f"  category_blank: {blank_count}")
    print("Profit analysis (total_cost = numbers * cost_per_number * games; profit = hits * payout - total_cost):")
    for cat in sorted(stats.keys(), reverse=True):
        numbers = avg_real_numbers_in_category(real_counts_by_cat, cat)
        hits = stats[cat]
        total_cost = numbers * args.cost_per_number * games
        total_payout = hits * args.straight_payout
        profit = total_payout - total_cost
        print(
            f"  category_{cat}: numbers={numbers}, hits={hits}, "
            f"cost=${total_cost:.2f}, payout=${total_payout:.2f}, profit=${profit:.2f}"
        )


if __name__ == "__main__":
    main()
