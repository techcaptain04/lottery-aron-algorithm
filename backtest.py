"""
Backtest category hits for ALL midday & evening winners in a date range, based on midday/evening pairing.

Rules (as requested):
1) If the target number appears as MIDDAY on date D,
   then "predict" the category of the EVENING number on the same date D.
2) If the target number appears as EVENING on date D,
   then "predict" the category of the MIDDAY number on the NEXT calendar date (D+1).

Category definition:
- Category is the duplicate-count bucket produced by the existing generator logic:
  Build all match windows for rows where (midday==target OR evening==target),
  collect all window values, drop values equal to target, digit-sort each value,
  count occurrences, and keep only digit-sorted values with count >= 2.
  If a digit-sorted value has count = K, then its category is K.

Output:
- Writes results to `results/analyse/backtest/backtest_YYYY_MM_DD_to_YYYY_MM_DD.csv`.
- Prints category statistics to console.
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
DRAWS_PER_DAY = 2


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
    rows: list[DrawRow] = []
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise SystemExit("CSV header is missing.")
        mid_col, eve_col = detect_number_columns(reader.fieldnames)
        for r in reader:
            date_text = (r.get("Draw Date") or "").strip()
            if date_text == "":
                continue
            rows.append(
                DrawRow(
                    date_text=date_text,
                    date=datetime.strptime(date_text, "%m/%d/%Y"),
                    midday=parse_optional_int(r.get(mid_col)),
                    evening=parse_optional_int(r.get(eve_col)),
                )
            )
    return rows


def date_key(dt: datetime) -> str:
    return dt.strftime("%m/%d/%Y")


def sorted_digits_asc_str(n: int) -> str:
    # Example: 620 -> "26", 379 -> "379" -> sorted digits => "379" (already sorted), 452 -> "245"
    return str(int("".join(sorted(str(n)))))


def row_has_target(row: DrawRow, target: int) -> bool:
    return (row.midday is not None and row.midday == target) or (
        row.evening is not None and row.evening == target
    )


def group_for_match_index(draws: list[DrawRow], i: int) -> list[int | None]:
    # Same window logic as generators: match row plus the 9 rows above it in the CSV.
    # (Pick3/Pick4 CSV is newest-first.)
    start = max(0, i - 9)
    vals: list[int | None] = []
    for j in range(start, i + 1):
        vals.extend([draws[j].midday, draws[j].evening])
    return vals


def build_category_data(
    draws: list[DrawRow], target: int
) -> tuple[dict[str, int], dict[str, set[int]]]:
    """Return (digit_sorted_value->category, digit_sorted_value->distinct raw numbers)."""
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
    return value_to_cat, dict(sources_for)


def category_for_winner(cat_map: dict[str, int], winner: int | None) -> str:
    if winner is None:
        return ""
    key = sorted_digits_asc_str(winner)
    cat = cat_map.get(key)
    return "" if cat is None else str(cat)


def real_number_count_for_winner(sources_for: dict[str, set[int]], winner: int | None) -> str:
    """Distinct raw draw numbers for this winner's digit-sorted form (e.g. 457 -> 3)."""
    if winner is None:
        return ""
    key = sorted_digits_asc_str(winner)
    raws = sources_for.get(key)
    if not raws:
        return ""
    return str(len(raws))


def candidates_count_for_category(
    cat_map: dict[str, int], sources_for: dict[str, set[int]], category: int
) -> int:
    """Sum real_count for every digit-sorted value in this duplicate-count bucket."""
    total = 0
    for value, cnt in cat_map.items():
        if cnt == category:
            total += len(sources_for.get(value, set()))
    return total


def days_in_range(start_dt: datetime, end_dt: datetime) -> int:
    return (end_dt - start_dt).days + 1


def default_out_path(start_dt: datetime, end_dt: datetime) -> Path:
    start_part = start_dt.strftime("%Y_%m_%d")
    end_part = end_dt.strftime("%Y_%m_%d")
    return Path("results") / "analyse" / "backtest" / f"backtest_{start_part}_to_{end_part}.csv"


def main() -> None:
    p = argparse.ArgumentParser(
        description="Backtest which duplicate-count category the paired winner lands in for midday/evening targets.",
    )
    p.add_argument("csv", type=Path, help="Pick3/Pick4 CSV path")
    p.add_argument(
        "-n",
        "--number",
        type=int,
        required=False,
        metavar="N",
        help="Optional: filter to only this target winning number (default: analyze all targets in range)",
    )
    p.add_argument(
        "--months",
        type=int,
        default=3,
        help="Analyze target dates from the latest CSV date back N months (default: 3).",
    )
    p.add_argument(
        "--start-date",
        type=str,
        default=None,
        metavar="MM/DD/YYYY",
        help="Optional: first target date (inclusive). Overrides --months.",
    )
    p.add_argument(
        "--end-date",
        type=str,
        default=None,
        metavar="MM/DD/YYYY",
        help="Optional: last target date (inclusive). Overrides --months.",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output CSV path (default: results/analyse/backtest/backtest_START_to_END.csv)",
    )
    p.add_argument(
        "--cost-per-number",
        type=float,
        default=COST_PER_NUMBER,
        help=f"Cost per number played (default: {COST_PER_NUMBER}); total_cost = sum_real_number_count x this",
    )
    p.add_argument(
        "--straight-payout",
        type=float,
        default=STRAIGHT_PAYOUT,
        help=f"Straight win payout per hit (default: {STRAIGHT_PAYOUT})",
    )
    args = p.parse_args()

    if not args.csv.is_file():
        raise SystemExit(f"CSV not found: {args.csv}")

    draws = load_draws(args.csv)
    if not draws:
        raise SystemExit("No draw rows found in CSV.")

    latest_dt = draws[0].date
    if args.start_date and args.end_date:
        start_dt = parse_date(args.start_date, "--start-date")
        end_dt = parse_date(args.end_date, "--end-date")
        if start_dt > end_dt:
            raise SystemExit("--start-date must be on or before --end-date")
    else:
        start_dt = latest_dt - timedelta(days=30 * args.months)
        end_dt = latest_dt

    out_path = args.out or default_out_path(start_dt, end_dt)
    date_range = days_in_range(start_dt, end_dt)

    draws_by_date = {date_key(r.date): r for r in draws}
    category_cache: dict[int, tuple[dict[str, int], dict[str, set[int]]]] = {}

    rows_out: list[list[str]] = []
    # stats over mapped categories
    stats: Counter[int] = Counter()
    real_sum_by_cat: Counter[int] = Counter()
    candidates_sum_by_cat: Counter[int] = Counter()
    blank_count = 0

    for row in draws:
        if row.date < start_dt or row.date > end_dt:
            continue

        # Target = MIDDAY winner on date D -> evaluate SAME-DAY EVENING
        if row.midday is not None and row.evening is not None:
            target = row.midday
            if args.number is not None and target != args.number:
                target = None
            if target is not None:
                if target not in category_cache:
                    category_cache[target] = build_category_data(draws, target)
                cat_map, sources_for = category_cache[target]
                cat = category_for_winner(cat_map, row.evening)
                real_cnt = real_number_count_for_winner(sources_for, row.evening)
                candidates_cnt = ""
                if cat != "":
                    cat_n = int(cat)
                    candidates_cnt = str(
                        candidates_count_for_category(cat_map, sources_for, cat_n)
                    )
                    stats[cat_n] += 1
                    if real_cnt:
                        real_sum_by_cat[cat_n] += int(real_cnt)
                    candidates_sum_by_cat[cat_n] += int(candidates_cnt)
                else:
                    blank_count += 1
                rows_out.append(
                    [
                        row.date_text,
                        "midday_target",
                        str(target),
                        row.date_text,
                        "evening",
                        str(row.evening),
                        sorted_digits_asc_str(row.evening),
                        cat,
                        real_cnt,
                        candidates_cnt,
                    ]
                )

        # Target = EVENING winner on date D -> evaluate NEXT-DAY MIDDAY
        if row.evening is not None:
            target = row.evening
            if args.number is not None and target != args.number:
                target = None
            if target is not None:
                next_key = date_key(row.date + timedelta(days=1))
                next_row = draws_by_date.get(next_key)
                winner_midday = None if next_row is None else next_row.midday
                if next_row is None or winner_midday is None:
                    continue
                if target not in category_cache:
                    category_cache[target] = build_category_data(draws, target)
                cat_map, sources_for = category_cache[target]
                cat = category_for_winner(cat_map, winner_midday)
                real_cnt = real_number_count_for_winner(sources_for, winner_midday)
                candidates_cnt = ""
                if cat != "":
                    cat_n = int(cat)
                    candidates_cnt = str(
                        candidates_count_for_category(cat_map, sources_for, cat_n)
                    )
                    stats[cat_n] += 1
                    if real_cnt:
                        real_sum_by_cat[cat_n] += int(real_cnt)
                    candidates_sum_by_cat[cat_n] += int(candidates_cnt)
                else:
                    blank_count += 1
                rows_out.append(
                    [
                        row.date_text,
                        "evening_target",
                        str(target),
                        next_row.date_text,
                        "midday",
                        str(winner_midday),
                        sorted_digits_asc_str(winner_midday),
                        cat,
                        real_cnt,
                        candidates_cnt,
                    ]
                )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "target_date",
                "target_slot",
                "target_number",
                "partner_date",
                "partner_slot",
                "partner_raw",
                "partner_transformed",
                "hit_category",
                "real_number_count",
                "candidates_count",
            ]
        )
        w.writerows(rows_out)

        w.writerow([])
        w.writerow(["STATISTICS"])
        w.writerow(
            [
                "category",
                "count",
                "sum_real_number_count",
                "candidates_count",
                "avg_candidates_count",
                "total_cost",
                "profit_1",
                "profit_2",
            ]
        )
        w.writerow(["cost_per_number", f"{args.cost_per_number:.2f}", "", "", "", "", "", ""])
        w.writerow(["date_range", date_range, "", "", "", "", "", ""])
        w.writerow(["straight_payout", f"{args.straight_payout:.2f}", "", "", "", "", "", ""])
        for cat in sorted(stats.keys(), reverse=True):
            real_sum = real_sum_by_cat[cat]
            candidates_sum = candidates_sum_by_cat[cat]
            total_cost = real_sum * args.cost_per_number
            hit_count = stats[cat]
            avg_candidates = round(candidates_sum / hit_count)
            profit_1 = (
                hit_count * args.straight_payout
                - total_cost * date_range * DRAWS_PER_DAY
            )
            profit_2 = (
                hit_count * args.straight_payout
                - avg_candidates * date_range * DRAWS_PER_DAY
            )
            w.writerow(
                [
                    f"category_{cat}",
                    hit_count,
                    real_sum,
                    candidates_sum,
                    avg_candidates,
                    f"{total_cost:.2f}",
                    f"{profit_1:.2f}",
                    f"{profit_2:.2f}",
                ]
            )
        w.writerow(["category_blank", blank_count, "", "", "", "", "", ""])

    print(f"Saved backtest CSV: {out_path.resolve()}")
    print(f"Target date range: {start_dt.strftime('%m/%d/%Y')} to {end_dt.strftime('%m/%d/%Y')}")
    print(f"Cost per number: ${args.cost_per_number:.2f}")
    print(f"Date range (days): {date_range}")
    print(f"Straight payout: ${args.straight_payout:.2f}")
    if not stats:
        print("Winner category: none (no non-blank category hits)")
    else:
        winner, hits = stats.most_common(1)[0]
        print(f"Winner category: {winner} (hits={hits})")
    print(f"category_blank: {blank_count}")
    if stats:
        print(
            "Category totals (profit_1 = count x straight_payout - total_cost x date_range x 2; "
            "profit_2 = count x straight_payout - avg_candidates_count x date_range x 2):"
        )
        for cat in sorted(stats.keys(), reverse=True):
            real_sum = real_sum_by_cat[cat]
            candidates_sum = candidates_sum_by_cat[cat]
            avg_candidates = round(candidates_sum / stats[cat])
            total_cost = real_sum * args.cost_per_number
            hit_count = stats[cat]
            profit_1 = (
                hit_count * args.straight_payout
                - total_cost * date_range * DRAWS_PER_DAY
            )
            profit_2 = (
                hit_count * args.straight_payout
                - avg_candidates * date_range * DRAWS_PER_DAY
            )
            print(
                f"  category_{cat}: hits={hit_count}, "
                f"sum_real_number_count={real_sum}, candidates_count={candidates_sum}, "
                f"avg_candidates_count={avg_candidates}, "
                f"total_cost=${total_cost:.2f}, profit_1=${profit_1:.2f}, profit_2=${profit_2:.2f}"
            )


if __name__ == "__main__":
    main()

