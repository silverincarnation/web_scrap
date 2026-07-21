"""Cleaned data as CSV -- one file per day (companion to clean_pipeline.py).

Runs the exact same 11-step cleaning by IMPORTING clean_pipeline.py (nothing
is copied or re-implemented, so the two can never drift apart), then writes
the deduped result as daily CSVs instead of JSON:

    data/clean_csv/<City_Folder>/<date>.csv     (mirrors result/'s layout)

clean_pipeline.py itself and its outputs (events.json / clean_report.txt)
are not touched.

Usage:
    python clean_daily_csv.py                     # ALL dates found under result/, NY + Mexico City
    python clean_daily_csv.py 2026-07-22          # only the given date(s)
    python clean_daily_csv.py --cities New_York_US Mexico_City_MX Los_Angeles_US
"""

import argparse
import csv
import os
import re

import clean_pipeline as cp

# Flattened events.json schema; lists join with ";", null becomes an empty cell.
CSV_FIELDS = ["id", "name", "description", "venue", "address", "city",
              "venueArea", "latitude", "longitude", "inCityArea", "date",
              "startTime", "endTime", "hasTime", "displayTime", "category",
              "tags", "image", "url", "isPaid", "sources"]


def discover_dates(city_folders):
    """Every YYYY-MM-DD folder present under result/<city>/ for these cities."""
    dates = set()
    for folder in city_folders:
        base = os.path.join(cp.RESULT_DIR, folder)
        if os.path.isdir(base):
            for name in os.listdir(base):
                if re.fullmatch(r"\d{4}-\d{2}-\d{2}", name) \
                        and os.path.isdir(os.path.join(base, name)):
                    dates.add(name)
    return sorted(dates)


def clean_events(dates, city_folders):
    """Steps 1-10 of clean_pipeline, reused verbatim; returns cleaned events."""
    rows = cp.load_csvs(dates, city_folders)
    rows = cp.validate_schema(rows)
    rows = cp.clean_text(rows)
    rows = cp.normalize_times(rows)
    rows = cp.normalize_city(rows)
    rows = cp.normalize_categories(rows)
    rows = cp.normalize_coords_urls(rows)
    rows = cp.normalize_price(rows)
    rows = cp.dedupe_cross_source(rows)
    return cp.build_json(rows)["events"]


def _flat(event, key):
    v = event.get(key)
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, list):
        return ";".join(str(x) for x in v)
    return v


# canonical city name ("New York") -> result folder name ("New_York_US")
_CITY_TO_FOLDER = {v[0]: k for k, v in cp.CITIES.items()}


def write_daily_csvs(events, out_dir):
    """Deduped, cleaned CSVs mirroring result/'s layout: <City>/<date>.csv."""
    groups = {}
    for e in events:
        folder = _CITY_TO_FOLDER.get(e["city"], e["city"].replace(" ", "_"))
        groups.setdefault((folder, e["date"]), []).append(e)
    written = []
    for (folder, date), evs in sorted(groups.items()):
        d = os.path.join(out_dir, folder)
        os.makedirs(d, exist_ok=True)
        path = os.path.join(d, f"{date}.csv")
        # utf-8-sig so Excel opens accents (México) correctly on double-click
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            w.writeheader()
            for e in evs:
                w.writerow({k: _flat(e, k) for k in CSV_FIELDS})
        print(f"[csv] {path}  ({len(evs)} events)")
        written.append(path)
    return written


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("dates", nargs="*",
                    help="dates to include (YYYY-MM-DD); omit to process ALL "
                         "dates found under result/")
    ap.add_argument("--cities", nargs="*",
                    default=["New_York_US", "Mexico_City_MX"],
                    help="city folder names under result/ "
                         "(add Los_Angeles_US explicitly when needed)")
    args = ap.parse_args()
    cities = [c for c in args.cities if c in cp.CITIES]
    dates = args.dates or discover_dates(cities)
    if not dates:
        raise SystemExit("no date folders found under result/ for " + ", ".join(cities))
    print(f"processing {len(dates)} date(s): {dates[0]} .. {dates[-1]}")
    events = clean_events(dates, cities)
    write_daily_csvs(events, os.path.join(cp.OUT_DIR, "clean_csv"))
