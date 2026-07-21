"""Data-cleaning pipeline: result/ CSVs  ->  data/events.json (Lovable-ready).

Each step is a standalone function; run_pipeline() chains them and writes a
quality report so every dropped/merged row is accounted for.

Usage:
    python clean_pipeline.py                    # default: 2026-08-01, 3 cities
    python clean_pipeline.py 2026-07-22         # other date(s)
    python clean_pipeline.py 2026-07-22 2026-08-01 --cities New_York_US

Output:
    data/events.json     one file: {"meta": {...}, "events": [...]}
    data/clean_report.txt
"""

import argparse
import csv
import datetime
import hashlib
import html
import json
import os
import re
import sys
import unicodedata
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.abspath(__file__))
RESULT_DIR = os.path.join(ROOT, "result")
OUT_DIR = os.path.join(ROOT, "data")

COLUMNS = [
    "name", "description", "location_name", "latitude", "longitude", "address",
    "start_time", "end_time", "city", "primary_category", "secondary_categories",
    "thumbnail_image", "additional_images", "external_link", "is_paid",
]

# Folder name -> canonical city / timezone / rough bounding box (lat lo/hi, lon lo/hi)
CITIES = {
    "New_York_US": ("New York", "America/New_York", (40.2, 41.4, -75.0, -73.0)),
    "Mexico_City_MX": ("Mexico City", "America/Mexico_City", (18.8, 20.0, -99.8, -98.5)),
    "Los_Angeles_US": ("Los Angeles", "America/Los_Angeles", (33.0, 35.0, -119.5, -116.8)),
}

SOURCE_LABELS = {
    "eventbrite": "Eventbrite", "ticketmaster": "Ticketmaster", "ra": "Resident Advisor",
    "songkick": "Songkick", "nyc_events": "NYC Events Calendar", "nyc_parks": "NYC Parks",
}
# When merging cross-source duplicates, richer/structured sources win field-by-field.
SOURCE_PRIORITY = ["ticketmaster", "eventbrite", "ra", "songkick", "nyc_events", "nyc_parks"]

REPORT = []


def log(msg):
    REPORT.append(str(msg))
    print(msg)


# --------------------------------------------------------------------------- #
# Step 1 — load
# --------------------------------------------------------------------------- #
def load_csvs(dates, city_folders):
    """Read result/<city>/<date>/<site>.csv into tagged raw rows."""
    rows = []
    for folder in city_folders:
        for date in dates:
            d = os.path.join(RESULT_DIR, folder, date)
            if not os.path.isdir(d):
                continue
            for f in sorted(os.listdir(d)):
                if not f.endswith(".csv"):
                    continue
                site = f[:-4]
                with open(os.path.join(d, f), newline="", encoding="utf-8") as fh:
                    for r in csv.DictReader(fh):
                        r["_source"] = site
                        r["_cityfolder"] = folder
                        r["_date"] = date
                        rows.append(r)
    log(f"[1 load]      {len(rows)} rows from {len(city_folders)} cities x {len(dates)} date(s)")
    return rows


# --------------------------------------------------------------------------- #
# Step 2 — schema check
# --------------------------------------------------------------------------- #
def validate_schema(rows):
    """Drop rows missing required basics (name + start_time + link)."""
    out, dropped = [], 0
    for r in rows:
        if all(c in r for c in COLUMNS) and (r.get("name") or "").strip() \
                and (r.get("start_time") or "").strip():
            out.append(r)
        else:
            dropped += 1
    log(f"[2 schema]    kept {len(out)}, dropped {dropped} malformed/empty rows")
    return out


# --------------------------------------------------------------------------- #
# Step 3 — text cleaning
# --------------------------------------------------------------------------- #
_TAG_RE = re.compile(r"<[^>]+>")
_CTRL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def _fix_mojibake(s):
    """Repair UTF-8-read-as-latin1 artifacts (e.g. 'MÃ©xico' -> 'México')."""
    if not re.search(r"[ÃÂâ€]", s):
        return s
    try:
        fixed = s.encode("latin-1").decode("utf-8")
        return fixed if fixed != s else s
    except (UnicodeEncodeError, UnicodeDecodeError):
        return s


def _clean_str(s, limit=None):
    s = _fix_mojibake(str(s or ""))
    s = unicodedata.normalize("NFC", s)
    s = _TAG_RE.sub(" ", s)
    s = html.unescape(html.unescape(s))   # twice: handles '&amp;#174;'
    s = _CTRL_RE.sub("", s)
    s = re.sub(r"[ \t]+", " ", s).strip()
    if limit and len(s) > limit:
        cut = s[:limit].rsplit(" ", 1)[0]
        s = cut + "…"
    return s


def clean_text(rows):
    """Mojibake, HTML remnants, double spaces, control chars; trim description."""
    for r in rows:
        r["name"] = _clean_str(r["name"])
        r["description"] = _clean_str(r["description"], limit=300)
        r["location_name"] = _clean_str(r["location_name"])
        r["address"] = _clean_str(r["address"])
    log(f"[3 text]      cleaned name/description/venue/address on {len(rows)} rows")
    return rows


# --------------------------------------------------------------------------- #
# Step 4 — time normalization
# --------------------------------------------------------------------------- #
def _parse_dt(s, tz):
    """'...Z' (UTC) / naive local / date-only  ->  (aware dt | None, has_time)."""
    s = (s or "").strip()
    if not s:
        return None, False
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        d = datetime.date.fromisoformat(s)
        return datetime.datetime.combine(d, datetime.time.min, tzinfo=tz), False
    iso = s[:-1] + "+00:00" if s.endswith("Z") else s
    try:
        dt = datetime.datetime.fromisoformat(iso)
    except ValueError:
        m = re.match(r"(\d{4}-\d{2}-\d{2})", s)
        if not m:
            return None, False
        d = datetime.date.fromisoformat(m.group(1))
        return datetime.datetime.combine(d, datetime.time.min, tzinfo=tz), False
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz)          # naive strings are venue-local
    else:
        dt = dt.astimezone(tz)              # UTC (Ticketmaster) -> local
    return dt, True


def normalize_times(rows):
    """Unify TM-UTC / naive-local / date-only into local ISO with offset."""
    unparseable = 0
    for r in rows:
        tz = ZoneInfo(CITIES[r["_cityfolder"]][1])
        start, has_time = _parse_dt(r["start_time"], tz)
        end, end_has = _parse_dt(r["end_time"], tz)
        if start is None:
            unparseable += 1
        r["_start"] = start
        r["_end"] = end if (end and end_has) else None
        r["_has_time"] = has_time
    rows = [r for r in rows if r["_start"] is not None]
    log(f"[4 time]      normalized to city-local ISO; dropped {unparseable} unparseable")
    return rows


# --------------------------------------------------------------------------- #
# Step 5 — city canonicalization
# --------------------------------------------------------------------------- #
def normalize_city(rows):
    """canonicalCity from folder; raw city value kept as venueArea."""
    for r in rows:
        r["_canonical_city"] = CITIES[r["_cityfolder"]][0]
        raw = _clean_str(r.get("city"))
        r["_venue_area"] = raw.title() if raw else ""
    log(f"[5 city]      canonical city set; raw value preserved as venueArea")
    return rows


# --------------------------------------------------------------------------- #
# Step 6 — categories
# --------------------------------------------------------------------------- #
def normalize_categories(rows):
    """Split, case-dedupe, cap tags; backfill empty primary from tags."""
    for r in rows:
        tags, seen = [], set()
        for part in (r.get("secondary_categories") or "").split(","):
            t = _clean_str(part)
            if t and t.lower() not in seen and t.lower() != "undefined":
                seen.add(t.lower())
                tags.append(t)
        primary = _clean_str(r.get("primary_category"))
        if primary.lower() == "undefined":        # Ticketmaster's junk label
            primary = ""
        if not primary and tags:
            primary = tags.pop(0)
        if primary.lower() in seen:
            tags = [t for t in tags if t.lower() != primary.lower()]
        r["_primary"] = primary
        r["_tags"] = tags[:8]
    log(f"[6 category]  split + case-deduped tags, primary backfilled")
    return rows


# --------------------------------------------------------------------------- #
# Step 7 — coordinates & urls
# --------------------------------------------------------------------------- #
def normalize_coords_urls(rows):
    """Coords -> float|None (0,0 invalid); bbox flag; https-fix links."""
    out_of_area = 0
    for r in rows:
        lat = lon = None
        try:
            lat, lon = float(r["latitude"]), float(r["longitude"])
            if lat == 0 and lon == 0:
                lat = lon = None
        except (TypeError, ValueError):
            lat = lon = None
        r["_lat"], r["_lon"] = lat, lon
        a, b, c, d = CITIES[r["_cityfolder"]][2]
        r["_in_city"] = (a <= lat <= b and c <= lon <= d) if lat is not None else None
        if r["_in_city"] is False:
            out_of_area += 1
        url = (r.get("external_link") or "").strip()
        if url.startswith("http://"):
            url = "https://" + url[7:]
        r["_url"] = url if url.startswith("https://") else ""
        imgs = [u.strip() for u in [r.get("thumbnail_image") or ""]
                + (r.get("additional_images") or "").split(",") if u.strip().startswith("http")]
        r["_images"] = imgs[:4]
    log(f"[7 geo/url]   coords typed; {out_of_area} rows flagged inCityArea=false (suburbs kept)")
    return rows


# --------------------------------------------------------------------------- #
# Step 8 — price tri-state
# --------------------------------------------------------------------------- #
def normalize_price(rows):
    """'true'/'false'/'' -> True/False/None (unknown stays unknown, not free)."""
    for r in rows:
        v = (r.get("is_paid") or "").strip().lower()
        r["_is_paid"] = True if v == "true" else False if v == "false" else None
    log(f"[8 price]     isPaid tri-state: paid {sum(1 for r in rows if r['_is_paid'] is True)}, "
        f"free {sum(1 for r in rows if r['_is_paid'] is False)}, "
        f"unknown {sum(1 for r in rows if r['_is_paid'] is None)}")
    return rows


# --------------------------------------------------------------------------- #
# Step 9 — cross-source dedupe/merge
# --------------------------------------------------------------------------- #
def _norm_key(s):
    s = unicodedata.normalize("NFKD", (s or "").lower())
    return re.sub(r"[^a-z0-9]+", "", s)


def _match_key(r):
    """(city, date, name, venue). Songkick names embed the venue ('X @ Venue')."""
    name = r["name"]
    if r["_source"] == "songkick" and " @ " in name:
        name = name.split(" @ ")[0]
    return (r["_canonical_city"], r["_start"].date().isoformat(),
            _norm_key(name), _norm_key(r["location_name"]))


def _fill_score(r):
    return sum(1 for c in COLUMNS if (r.get(c) or "").strip()) \
        + (2 if r["_lat"] is not None else 0)


def _merge_into(base, other):
    """Fill base's gaps from other; union images/tags/sources. No overwrites."""
    for c in ["description", "address", "end_time"]:
        if not (base.get(c) or "").strip() and (other.get(c) or "").strip():
            base[c] = other[c]
    if base["_lat"] is None and other["_lat"] is not None:
        base["_lat"], base["_lon"] = other["_lat"], other["_lon"]
        base["_in_city"] = other["_in_city"]
    if base["_end"] is None and other["_end"] is not None:
        base["_end"] = other["_end"]
    if base["_is_paid"] is None and other["_is_paid"] is not None:
        base["_is_paid"] = other["_is_paid"]
    for img in other["_images"]:
        if img not in base["_images"] and len(base["_images"]) < 4:
            base["_images"].append(img)
    for t in other["_tags"]:
        if t.lower() not in {x.lower() for x in base["_tags"]} and len(base["_tags"]) < 8:
            base["_tags"].append(t)
    base["_srcset"] = base.get("_srcset", {base["_source"]}) \
        | other.get("_srcset", {other["_source"]})


def _rank(r):
    return (-_fill_score(r), SOURCE_PRIORITY.index(r["_source"])
            if r["_source"] in SOURCE_PRIORITY else 99)


_PAREN_RE = re.compile(r"\s*\([^)]*\)\s*$")


def _venue_variants(r):
    """Full venue key + parenthetical-suffix-stripped key ('X (in Y Park)' -> 'X')."""
    v = r["location_name"]
    out = {_norm_key(v)}
    stripped = _PAREN_RE.sub("", v)
    if stripped != v:
        out.add(_norm_key(stripped))
    return {x for x in out if len(x) >= 4}


def _same_event(a, b):
    """Second-pass guard: identical start moment + compatible venue + close coords.

    Protects same-name-different-park programs (e.g. one class held at two
    parks the same morning) from being wrongly merged: generic venue names
    only pass when both coordinates agree within ~400 m.
    """
    if a["_start"] != b["_start"]:
        return False
    va, vb = _venue_variants(a), _venue_variants(b)
    if not any(x == y or x in y or y in x for x in va for y in vb):
        return False
    if a["_lat"] is not None and b["_lat"] is not None:
        if abs(a["_lat"] - b["_lat"]) > 0.004 or abs(a["_lon"] - b["_lon"]) > 0.005:
            return False
    return True


def dedupe_cross_source(rows):
    """Merge the same event listed by multiple sources.

    Pass 1: exact (city, date, name, venue) key.
    Pass 2: same (city, date, name) where venues differ only by decoration
            ('Park House' vs 'Park House (in Baisley Pond Park)') -- requires
            identical start time, venue substring match and coord agreement.
    """
    groups = {}
    for r in rows:
        r["_srcset"] = {r["_source"]}
        groups.setdefault(_match_key(r), []).append(r)
    pass1, merged1 = [], 0
    for grp in groups.values():
        grp.sort(key=_rank)
        base = grp[0]
        for other in grp[1:]:
            _merge_into(base, other)
            merged1 += 1
        pass1.append(base)

    by_name = {}
    for r in pass1:
        by_name.setdefault(_match_key(r)[:3], []).append(r)
    merged_rows, merged2 = [], 0
    for grp in by_name.values():
        grp.sort(key=_rank)
        kept = []
        for r in grp:
            target = next((k for k in kept if _same_event(k, r)), None)
            if target is not None:
                _merge_into(target, r)
                merged2 += 1
            else:
                kept.append(r)
        merged_rows.extend(kept)
    for r in merged_rows:
        r["_sources"] = sorted(r["_srcset"])
    log(f"[9 dedupe]    {len(rows)} -> {len(merged_rows)} events "
        f"({merged1} exact + {merged2} fuzzy cross-source duplicates merged)")
    return merged_rows


# --------------------------------------------------------------------------- #
# Step 10 — build JSON
# --------------------------------------------------------------------------- #
def build_json(rows):
    """Emit Lovable-friendly camelCase records with real types + meta block."""
    events = []
    for r in rows:
        eid = hashlib.sha1("|".join(_match_key(r)).encode()).hexdigest()[:12]
        start = r["_start"]
        events.append({
            "id": eid,
            "name": r["name"],
            "description": r["description"] or None,
            "venue": r["location_name"] or None,
            "address": r["address"] or None,
            "city": r["_canonical_city"],
            "venueArea": r["_venue_area"] or None,
            "latitude": r["_lat"],
            "longitude": r["_lon"],
            "inCityArea": r["_in_city"],
            "date": start.date().isoformat(),
            # no fabricated values: if the source gave only a date (no clock
            # time), startTime is null -- the date lives in "date" above
            "startTime": start.isoformat() if r["_has_time"] else None,
            "endTime": r["_end"].isoformat() if r["_end"] else None,
            "hasTime": r["_has_time"],
            # portable 12-hour format ("%-I" is Linux-only, "%#I" is Windows-only)
            "displayTime": (f"{(start.hour % 12) or 12}:{start.minute:02d} "
                            f"{'AM' if start.hour < 12 else 'PM'}"
                            if r["_has_time"] else "All day"),
            "category": r["_primary"] or None,
            "tags": r["_tags"],
            "image": r["_images"][0] if r["_images"] else None,
            "images": r["_images"],
            "url": r["_url"] or None,
            "isPaid": r["_is_paid"],
            "sources": [SOURCE_LABELS.get(s, s) for s in r["_sources"]],
        })
    events.sort(key=lambda e: (e["city"], e["date"],
                               e["startTime"] or "", e["name"]))

    def count(fn):
        out = {}
        for e in events:
            k = fn(e)
            out[k] = out.get(k, 0) + 1
        return dict(sorted(out.items()))

    meta = {
        "generatedAt": datetime.datetime.now(datetime.timezone.utc)
                       .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "totalEvents": len(events),
        "cities": count(lambda e: e["city"]),
        "dates": count(lambda e: e["date"]),
        "sources": count(lambda e: e["sources"][0] if len(e["sources"]) == 1 else "Multiple"),
        "paid": sum(1 for e in events if e["isPaid"] is True),
        "free": sum(1 for e in events if e["isPaid"] is False),
        "priceUnknown": sum(1 for e in events if e["isPaid"] is None),
        "withCoordinates": sum(1 for e in events if e["latitude"] is not None),
        "schemaNote": "isPaid null = unknown (not free); endTime null = source "
                      "does not publish it; inCityArea false = suburb within "
                      "search radius",
    }
    log(f"[10 build]    {len(events)} events -> JSON with meta block")
    return {"meta": meta, "events": events}


# --------------------------------------------------------------------------- #
# Step 11 — write output + report
# --------------------------------------------------------------------------- #
def write_output(payload):
    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, "events.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    size_kb = os.path.getsize(out) // 1024
    log(f"[11 write]    {out}  ({size_kb} KB)")
    # field fill-rate summary for the report
    evs = payload["events"]
    for field in ["description", "venue", "address", "latitude", "endTime",
                  "category", "image", "url"]:
        filled = sum(1 for e in evs if e.get(field) not in (None, "", []))
        log(f"    fill {field:12s} {filled}/{len(evs)} ({100 * filled // max(1, len(evs))}%)")
    rp = os.path.join(OUT_DIR, "clean_report.txt")
    with open(rp, "w", encoding="utf-8") as f:
        f.write("\n".join(REPORT))
    return out


# --------------------------------------------------------------------------- #
def run_pipeline(dates, city_folders):
    rows = load_csvs(dates, city_folders)
    rows = validate_schema(rows)
    rows = clean_text(rows)
    rows = normalize_times(rows)
    rows = normalize_city(rows)
    rows = normalize_categories(rows)
    rows = normalize_coords_urls(rows)
    rows = normalize_price(rows)
    rows = dedupe_cross_source(rows)
    payload = build_json(rows)
    return write_output(payload)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("dates", nargs="*", default=["2026-08-01"],
                    help="dates to include (YYYY-MM-DD)")
    ap.add_argument("--cities", nargs="*",
                    default=["New_York_US", "Mexico_City_MX"],
                    help="city folder names under result/ "
                         "(add Los_Angeles_US explicitly when needed)")
    args = ap.parse_args()
    dates = args.dates or ["2026-08-01"]
    run_pipeline(dates, [c for c in args.cities if c in CITIES])
