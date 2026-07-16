import csv
import sys
import re
import os
import glob as globmod
import json
import time
import urllib.request
import urllib.parse
from datetime import datetime

try:
    from timezonefinder import TimezoneFinder
    import pytz
    HAS_TZ = True
except ImportError:
    HAS_TZ = False
    print("WARNING: timezonefinder or pytz not installed. UTC conversion disabled. Install with: pip install timezonefinder pytz")

try:
    from dateutil import parser as dateutil_parser
    HAS_DATEUTIL = True
except ImportError:
    HAS_DATEUTIL = False

tf = TimezoneFinder() if HAS_TZ else None

SOURCE_FIELDS = [
    "name", "description", "location_name", "latitude", "longitude",
    "address", "start_time", "end_time", "city", "primary_category",
    "secondary_categories", "thumbnail_image", "additional_images",
    "external_link", "is_paid",
]

TARGET_FIELDS = [
    "id", "name", "description", "location_name", "address",
    "latitude", "longitude", "start_time", "end_time", "city",
    "primary_category", "tags", "thumbnail_image", "additional_images",
    "external_link", "is_paid",
]

CATEGORY_KEYWORDS = [
    ("Food & Drink", [
        "food", "drink", "cooking", "chef", "cuisine", "tasting", "brewery",
        "wine", "beer", "cocktail", "dinner", "lunch", "brunch", "restaurant",
        "culinary", "cheese", "pizza", "taco", "ice cream", "chocolate",
        "bakery", "pastry", "coffee", "tea", "mixology", "dining", "bake",
        "baking", "supper", "feast", "foodie", "noodles", "sushi", "vegan",
        "vegetarian", "pickle", "farfalle", "cooking class", "food tour",
        "steak dinner", "bar", "dessert", "gourmet",
    ]),
    ("Music", [
        "concert", "live music", "band", "dj", "festival", "gig", "show",
        "music", "acoustic", "electronic", "rock", "jazz", "hip hop", "rap",
        "indie", "pop", "classical", "opera", "symphony", "orchestra",
        "karaoke", "open mic", "session", "vinyl", "record", "album",
        "reggaeton", "cumbia", "salsa", "banda", "norteño", "corrido",
        "mariachi", "ranchera", "banda sinaloense", "grupero",
    ]),
    ("Arts & Theatre", [
        "theatre", "theater", "play", "musical", "opera", "ballet", "dance",
        "comedy", "improv", "standup", "stand-up", "performance", "art",
        "exhibition", "gallery", "museum", "workshop", "class", "course",
        "painting", "drawing", "sculpture", "photography", "film", "cinema",
    ]),
    ("Sports & Fitness", [
        "sport", "fitness", "yoga", "running", "marathon", "cycling", "hiking",
        "climbing", "swimming", "gym", "workout", "training", "bootcamp",
        "crossfit", "pilates", "martial arts", "boxing", "mma", "wrestling",
        "soccer", "football", "basketball", "baseball", "tennis", "golf",
    ]),
    ("Nightlife", [
        "club", "nightclub", "bar", "pub", "lounge", "rooftop", "speakeasy",
        "afterparty", "after-party", "late night", "dance", "edm", "techno",
        "house", "trance", "dnb", "drum and bass", "reggaeton", "perreo",
    ]),
    ("Tech & Business", [
        "tech", "technology", "startup", "business", "networking", "conference",
        "workshop", "meetup", "hackathon", "coding", "programming", "ai",
        "machine learning", "data science", "blockchain", "crypto", "fintech",
    ]),
    ("Health & Wellness", [
        "health", "wellness", "meditation", "mindfulness", "therapy",
        "counseling", "psychology", "mental health", "spa", "massage",
        "holistic", "alternative medicine", "herbal", "naturopathy",
    ]),
    ("Travel & Outdoor", [
        "travel", "tour", "hiking", "camping", "backpacking", "adventure",
        "excursion", "day trip", "weekend getaway", "road trip", "vanlife",
    ]),
    ("Community & Social", [
        "community", "social", "meetup", "gathering", "volunteer", "charity",
        "fundraiser", "nonprofit", "ngo", "activism", "protest", "march",
        "community service", "neighborhood",
    ]),
    ("Family & Kids", [
        "kids", "children", "family", "infantil", "niños", "niñas", "familia",
        "kinder", "guardería", "taller infantil", "cuentacuentos", "payaso",
    ]),
]

CATEGORY_KEYWORDS_FLAT = [(cat, kw.lower()) for cat, kws in CATEGORY_KEYWORDS for kw in kws]

NY_TZ = pytz.timezone("America/New_York") if HAS_TZ else None
UTC_TZ = pytz.UTC if HAS_TZ else None


def load_csv(path):
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def parse_dt(dt_str):
    if not dt_str or not dt_str.strip():
        return None
    dt_str = dt_str.strip()
    if HAS_DATEUTIL:
        try:
            return dateutil_parser.parse(dt_str)
        except Exception:
            pass
    fmts = [
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ]
    for fmt in fmts:
        try:
            return datetime.strptime(dt_str, fmt)
        except ValueError:
            pass
    return None


def to_ny_iso(dt):
    if dt is None:
        return ""
    if HAS_TZ:
        if dt.tzinfo is None:
            dt = NY_TZ.localize(dt)
        else:
            dt = dt.astimezone(NY_TZ)
        return dt.strftime("%-m/%-d/%Y  %I:%M:%S %p")
    else:
        return dt.strftime("%-m/%-d/%Y  %I:%M:%S %p")


def infer_category(name, desc, primary_cat, secondary_cats):
    text = " ".join(filter(None, [name, desc, primary_cat, secondary_cats])).lower()
    for cat, kw in CATEGORY_KEYWORDS_FLAT:
        if kw in text:
            return cat
    cat = (primary_cat or "Other").strip().lower()
    if cat in ("undefined", "unknown", "n/a", "na", "none", ""):
        return "Other"
    return cat


def build_tags(primary_cat, secondary_cats):
    tags = []
    if primary_cat:
        tags.append(primary_cat.strip())
    if secondary_cats:
        for tag in secondary_cats.split(","):
            tag = tag.strip()
            if tag:
                tags.append(tag)
    return ", ".join(dict.fromkeys(tags))


def dedup_key(row):
    name = row.get("name", "").strip().lower()
    start = row.get("start_time", "").strip()
    loc = row.get("location_name", "").strip().lower()
    return f"{name}|{start}|{loc}"


def map_row(row):
    start_dt = parse_dt(row.get("start_time", ""))
    end_dt = parse_dt(row.get("end_time", ""))

    return {
        "id": "",
        "name": row.get("name", "").strip(),
        "description": row.get("description", "").strip(),
        "location_name": row.get("location_name", "").strip(),
        "address": row.get("address", "").strip(),
        "latitude": row.get("latitude", "").strip(),
        "longitude": row.get("longitude", "").strip(),
        "start_time": to_ny_iso(start_dt),
        "end_time": to_ny_iso(end_dt),
        "city": "New York",
        "primary_category": infer_category(
            row.get("name", ""),
            row.get("description", ""),
            row.get("primary_category", ""),
            row.get("secondary_categories", "")
        ),
        "tags": build_tags(
            row.get("primary_category", ""),
            row.get("secondary_categories", "")
        ),
        "thumbnail_image": row.get("thumbnail_image", "").strip(),
        "additional_images": row.get("additional_images", "").strip(),
        "external_link": row.get("external_link", "").strip(),
        "is_paid": row.get("is_paid", "").strip().lower() in ("true", "1", "yes", "true"),
    }


def geocode(address, city):
    if not HAS_TZ:
        return None, None
    query = f"{address}, {city}, New York, USA"
    url = f"https://nominatim.openstreetmap.org/search?{urllib.parse.urlencode({'q': query, 'format': 'json', 'limit': 1})}"
    req = urllib.request.Request(url, headers={"User-Agent": "EventCleaner/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            if data:
                return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception:
        pass
    return None, None


def main():
    if len(sys.argv) < 3:
        print("Usage: python clean_ny_events.py <output.csv> <input_dir_or_csv> [--geocode]")
        sys.exit(1)

    output_path = sys.argv[1]
    input_arg = sys.argv[2]
    do_geocode = "--geocode" in sys.argv

    if os.path.isdir(input_arg):
        input_paths = sorted(globmod.glob(os.path.join(input_arg, "**", "*.csv"), recursive=True))
        if not input_paths:
            print(f"No CSV files found in {input_arg}")
            sys.exit(1)
    else:
        input_paths = [a for a in sys.argv[2:] if not a.startswith("--")]

    all_rows = []
    for path in input_paths:
        all_rows.extend(load_csv(path))

    seen = {}
    unique = []
    for row in all_rows:
        key = dedup_key(row)
        if key not in seen:
            seen[key] = True
            unique.append(map_row(row))

    print(f"Read {len(all_rows)} rows, kept {len(unique)} after dedup", flush=True)

    if do_geocode:
        missing = [r for r in unique if not r.get("latitude", "").strip() or r.get("latitude", "").strip() == "0"]
        print(f"Geocoding {len(missing)} events missing lat/long...", flush=True)
        geocoded = 0
        for i, r in enumerate(missing):
            lat, lon = geocode(r.get("address", ""), r.get("city", ""))
            if lat is not None:
                r["latitude"] = str(lat)
                r["longitude"] = str(lon)
                geocoded += 1
            if (i + 1) % 50 == 0:
                print(f"  {i + 1}/{len(missing)} done ({geocoded} geocoded)", flush=True)
            time.sleep(1)
        print(f"Geocoded {geocoded}/{len(missing)} events", flush=True)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=TARGET_FIELDS)
        writer.writeheader()
        writer.writerows(unique)

    print(f"Wrote {output_path}", flush=True)


if __name__ == "__main__":
    main()