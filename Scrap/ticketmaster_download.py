"""ticketmaster.com scraper -- official Discovery API (needs an API key).

Self-contained: same structure as the standalone repo version, plus a date-window
filter so the output only contains events on the requested day(s) (de-duplicated,
city backfilled). scrape_runner passes the key in as config["apikey"] (.env).
"""

import csv
import datetime
import re
import time
import urllib.parse
import urllib.request
import urllib.error

API_URL = "https://app.ticketmaster.com/discovery/v2/events.json"

COLUMNS = [
    "name", "description", "location_name", "latitude", "longitude", "address",
    "start_time", "end_time", "city", "primary_category", "secondary_categories",
    "thumbnail_image", "additional_images", "external_link", "is_paid",
]


def get(d, *keys, default=""):
    for k in keys:
        if not isinstance(d, dict):
            return default
        d = d.get(k)
        if d is None:
            return default
    return d if d is not None else default


# The Discovery API's free-text `city` filter is unreliable for non-US metros
# (Ticketmaster stores Mexican cities in Spanish / by borough), so for known
# cities we search by geo radius instead. "lat,long" per Discovery's `latlong`.
CITY_LATLONG = {
    "mexico city": "19.4326,-99.1332", "cdmx": "19.4326,-99.1332",
    "ciudad de mexico": "19.4326,-99.1332", "ciudad de méxico": "19.4326,-99.1332",
}

# Country -> timezone, so the local-date filter matches the venue's day (an
# evening CDMX show in UTC must not be bucketed into the next NY day).
COUNTRY_TZ = {
    "MX": "America/Mexico_City", "US": "America/New_York",
    "CA": "America/Toronto", "GB": "Europe/London", "ES": "Europe/Madrid",
    "AR": "America/Argentina/Buenos_Aires",
}


def _latlong(config):
    v = str(config.get("latlong") or "").strip()
    if v:
        return v
    return CITY_LATLONG.get((config.get("city") or "").strip().lower())


def build_params(config, page, extra=None):
    params = {
        "apikey": config["apikey"],
        "size": config.get("size", 100),
        "page": page,
    }
    mapping = {
        "start_time": "startDateTime",
        "end_time": "endDateTime",
        "country_code": "countryCode",
        "keyword": "keyword",
    }
    for key, api_name in mapping.items():
        if config.get(key):
            params[api_name] = config[key]
    for k, v in (extra or {}).items():
        if v not in (None, ""):
            params[k] = v
    return params


def fetch_json(url):
    import json
    for attempt in range(5):
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code in (429, 502, 503, 504) and attempt < 4:
                time.sleep(5 * (attempt + 1))
                continue
            raise
    return {}


def _fetch_pages(config, extra):
    events = []
    size = config.get("size", 100)
    page_cap = max(1, 1000 // size)
    max_pages = config.get("max_pages") or 10**9
    max_pages = min(max_pages, page_cap)

    page = 0
    data = {}
    while page < max_pages:
        url = API_URL + "?" + urllib.parse.urlencode(build_params(config, page, extra))
        data = fetch_json(url)
        time.sleep(0.25)
        batch = get(data, "_embedded", "events", default=[])
        events.extend(batch)

        total_pages = get(data, "page", "totalPages", default=1)
        page += 1
        if not batch or page >= total_pages:
            break

    total = get(data, "page", "totalElements", default=len(events))
    if total > 1000:
        print("  ticketmaster: API caps at 1000 results; narrow the date range.")
    return events


def fetch_events(config):
    """Try geo radius, then the city string, then country-wide -- return the
    first attempt that yields events. Each attempt is logged, so 0 rows is
    always explainable (empty API result vs. filtered out later)."""
    strategies = []
    ll = _latlong(config)
    if ll:
        strategies.append(("geo radius " + ll,
                           {"latlong": ll, "radius": config.get("radius", 100),
                            "unit": config.get("unit", "km")}))
    if config.get("city"):
        strategies.append(("city=%s" % config["city"], {"city": config["city"]}))
    strategies.append(("countryCode only", {}))

    for label, extra in strategies:
        events = _fetch_pages(config, extra)
        print(f"  ticketmaster: {len(events)} events via {label}")
        if events:
            return events
    return []


def map_event(event):
    venue = get(event, "_embedded", "venues", default=[{}])[0]
    cls = (event.get("classifications") or [{}])[0]
    image_urls = [img["url"] for img in event.get("images", []) if img.get("url")]
    thumbnail = image_urls[0] if image_urls else ""
    additional = ",".join(image_urls[1:])

    return {
        "name": event.get("name", ""),
        "description": event.get("info", ""),
        "location_name": venue.get("name", ""),
        "latitude": get(venue, "location", "latitude"),
        "longitude": get(venue, "location", "longitude"),
        "address": get(venue, "address", "line1"),
        "start_time": get(event, "dates", "start", "dateTime"),
        "end_time": get(event, "dates", "end", "dateTime"),
        "city": get(venue, "city", "name").lower(),
        "primary_category": get(cls, "segment", "name"),
        "secondary_categories": get(cls, "genre", "name"),
        "thumbnail_image": thumbnail,
        "additional_images": additional,
        "external_link": event.get("url", ""),
        "is_paid": "true" if event.get("priceRanges") else "",
    }


# --------------------------------------------------------------------------- #
# Date-window filter + de-dupe + city back-fill (the "current" functionality)
# --------------------------------------------------------------------------- #
def keep_on_dates(rows, start_date=None, end_date=None, city="",
                  tz_name="America/New_York"):
    def zone():
        try:
            from zoneinfo import ZoneInfo
            return ZoneInfo(tz_name)
        except Exception:
            return datetime.timezone.utc

    def local_date(value):
        s = str(value or "").strip()
        if not s:
            return None
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
            try:
                return datetime.date.fromisoformat(s)
            except ValueError:
                return None
        iso = s[:-1] + "+00:00" if s.endswith("Z") else s
        try:
            dt = datetime.datetime.fromisoformat(iso)
        except ValueError:
            m = re.match(r"(\d{4}-\d{2}-\d{2})", s)
            return datetime.date.fromisoformat(m.group(1)) if m else None
        if dt.tzinfo is not None:
            dt = dt.astimezone(zone())
        return dt.date()

    start = datetime.date.fromisoformat(start_date) if start_date else None
    end = datetime.date.fromisoformat(end_date) if end_date else start
    if start and end and end < start:
        start, end = end, start
    city = (city or "").strip().lower()

    out, seen = [], set()
    for row in rows:
        day = local_date(row.get("start_time"))
        if day is None:
            if start or end:
                continue
        else:
            if start and day < start:
                continue
            if end and day > end:
                continue
        if city and not str(row.get("city") or "").strip():
            row = dict(row, city=city)
        key = (str(row.get("name") or "").strip().lower(),
               str(row.get("location_name") or "").strip().lower(),
               day.isoformat() if day else "")
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def download(config):
    if not config.get("apikey"):
        raise ValueError("config lack apikey")
    print("pull events..")
    events = fetch_events(config)
    rows = [map_event(e) for e in events]
    tz = COUNTRY_TZ.get((config.get("country_code") or "").strip().upper(),
                        "America/New_York")
    rows = keep_on_dates(rows, config.get("start_date"), config.get("end_date"),
                         config.get("city", ""), tz_name=tz)
    print(f"  ticketmaster: {len(events)} from API -> {len(rows)} rows after "
          f"date filter (tz {tz})")
    out = config.get("out", "events.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Finish: {len(rows)} rows -> {out}")
    return rows
