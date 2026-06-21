import csv
import json
import os
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


def build_params(config, page):
    params = {
        "apikey": config["apikey"],
        "size": config.get("size", 100),
        "page": page,
    }
    mapping = {
        "start_time": "startDateTime",
        "end_time": "endDateTime",
        "city": "city",
        "country_code": "countryCode",
        "keyword": "keyword",
    }
    for key, api_name in mapping.items():
        if config.get(key):
            params[api_name] = config[key]
    return params


def fetch_json(url):
    for attempt in range(5):
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 4:
                wait = 5 * (attempt + 1)
                time.sleep(wait)
                continue
            raise
    return {}


def fetch_events(config):
    events = []
    size = config.get("size", 100)
    page_cap = 1000 // size
    max_pages = config.get("max_pages") or 10**9
    max_pages = min(max_pages, page_cap)

    page = 0
    while page < max_pages:
        url = API_URL + "?" + urllib.parse.urlencode(build_params(config, page))
        data = fetch_json(url)
        time.sleep(0.25)
        batch = get(data, "_embedded", "events", default=[])
        events.extend(batch)

        total = get(data, "page", "totalElements", default=len(events))
        total_pages = get(data, "page", "totalPages", default=1)

        page += 1
        if not batch or page >= total_pages:
            break

    total = get(data, "page", "totalElements", default=len(events))
    if total > 1000:
        print(f"API can only catch 1000 events")
    return events


def map_event(event):
    venue = get(event, "_embedded", "venues", default=[{}])[0]
    cls = (event.get("classifications") or [{}])[0]
    image_urls = [img["url"] for img in event.get("images", []) if img.get("url")]
    thumbnail = image_urls[0] if image_urls else ""
    additional = ",".join(image_urls[1:])
    primary = get(cls, "segment", "name")
    secondary = get(cls, "genre", "name")

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
        "primary_category": primary,
        "secondary_categories": secondary,
        "thumbnail_image": thumbnail,
        "additional_images": additional,
        "external_link": event.get("url", ""),
        "is_paid": "true" if event.get("priceRanges") else "false",
    }


def download(config):
    if not config.get("apikey"):
        raise ValueError("config lack apikey")
    print("pull events..")
    events = fetch_events(config)
    rows = [map_event(e) for e in events]
    out = config.get("out", "events.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Finish： {len(rows)} rows -> {out}")
    return rows
