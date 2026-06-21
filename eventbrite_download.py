import csv
import json
import re
import time
import urllib.parse
import urllib.request
import urllib.error

from bs4 import BeautifulSoup

SEARCH_URL = "https://www.eventbrite.com/d/{place}/{slug}/"

COLUMNS = [
    "name", "description", "location_name", "latitude", "longitude", "address",
    "start_time", "end_time", "city", "primary_category", "secondary_categories",
    "thumbnail_image", "additional_images", "external_link", "is_paid",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def get(d, *keys, default=""):
    for k in keys:
        if not isinstance(d, dict):
            return default
        d = d.get(k)
        if d is None:
            return default
    return d if d is not None else default


def _date_only(t):
    if not t:
        return ""
    return str(t).split("T")[0]


def _place_slug(config):
    if config.get("place"):
        return config["place"]
    city = (config.get("city") or "").strip().lower().replace(" ", "-")
    country = (config.get("country_code") or "").strip().lower()
    if city and country:
        return f"{country}--{city}"
    return city or "online"


def build_url(config, page):
    place = _place_slug(config)
    slug = config.get("slug", "all-events")
    params = {"page": page}
    q = config.get("q") or config.get("keyword")
    if q:
        params["q"] = q
    start_date = config.get("start_date") or _date_only(config.get("start_time"))
    end_date = config.get("end_date") or _date_only(config.get("end_time"))
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date
    url = SEARCH_URL.format(place=place, slug=slug)
    return url + "?" + urllib.parse.urlencode(params)


def fetch_html(url, retries=6):
    req = urllib.request.Request(url, headers=HEADERS)
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read().decode("utf-8", "ignore")
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and attempt < retries - 1:
                # respect Retry-After if the server sends it, else exponential backoff
                retry_after = e.headers.get("Retry-After") if e.headers else None
                if retry_after and str(retry_after).isdigit():
                    wait = int(retry_after)
                else:
                    wait = min(60, 10 * (2 ** attempt))
                print(f"  rate limited ({e.code}), waiting {wait}s then retrying...")
                time.sleep(wait)
                continue
            raise
    return ""


def extract_events_from_html(html):
    soup = BeautifulSoup(html, "html.parser")
    events = []
    for tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = tag.string or tag.get_text() or ""
        raw = raw.strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue

        candidates = data if isinstance(data, list) else [data]
        for obj in candidates:
            if not isinstance(obj, dict):
                continue
            t = obj.get("@type", "")
            if t == "ItemList":
                for el in obj.get("itemListElement", []):
                    item = el.get("item", el) if isinstance(el, dict) else {}
                    if isinstance(item, dict) and "Event" in str(item.get("@type", "")):
                        events.append(item)
            elif "Event" in str(t):
                events.append(obj)
    return events


def _join_address(address):
    if isinstance(address, str):
        return address, "", ""
    line = get(address, "streetAddress")
    city = get(address, "addressLocality")
    return line, city, address


def _to_utc(dt):
    if not dt:
        return ""
    if dt.endswith("Z"):
        return dt
    m = re.match(r"(.*T\d{2}:\d{2}:\d{2})([+-]\d{2}:\d{2})$", dt)
    if m and m.group(2) == "+00:00":
        return m.group(1) + "Z"
    return dt


def map_event(event):
    location = event.get("location") or {}
    if isinstance(location, list):
        location = location[0] if location else {}

    line, city, _ = _join_address(location.get("address", {}))
    geo = location.get("geo", {}) or {}

    image = event.get("image", "")
    if isinstance(image, list):
        image = image[0] if image else ""
    elif isinstance(image, dict):
        image = image.get("url", "")

    offers = event.get("offers", {})
    if isinstance(offers, list):
        offers = offers[0] if offers else {}
    price = None
    if isinstance(offers, dict):
        if "price" in offers:
            price = offers["price"]
        elif "lowPrice" in offers:
            price = offers["lowPrice"]
    # No price info found -> leave blank (unknown). Only fill when we actually know.
    is_paid = ""
    if price is not None and str(price).strip() != "":
        try:
            is_paid = "true" if float(price) > 0 else "false"
        except (TypeError, ValueError):
            is_paid = ""

    return {
        "name": event.get("name", ""),
        "description": (event.get("description", "") or "").strip(),
        "location_name": location.get("name", "") if isinstance(location, dict) else "",
        "latitude": get(geo, "latitude"),
        "longitude": get(geo, "longitude"),
        "address": line,
        "start_time": _to_utc(event.get("startDate", "")),
        "end_time": _to_utc(event.get("endDate", "")),
        "city": (city or "").lower(),
        "primary_category": event.get("@type", "") if event.get("@type") != "Event" else "",
        "secondary_categories": "",
        "thumbnail_image": image,
        "additional_images": "",
        "external_link": event.get("url", ""),
        "is_paid": is_paid,
    }


def fetch_events(config):
    events = []
    seen = set()
    max_pages = config.get("max_pages") or 50  # None -> crawl until no new events (cap 50 pages)
    delay = config.get("delay", 2.0)
    for page in range(1, max_pages + 1):
        url = build_url(config, page)
        try:
            html = fetch_html(url)
        except urllib.error.HTTPError as e:
            # rate limited / server error even after retries: stop this day,
            # keep what we already collected instead of crashing the whole run.
            print(f"  stopped at page {page}: HTTP {e.code}, keeping {len(events)} events so far")
            break
        time.sleep(delay)
        batch = extract_events_from_html(html)
        new = 0
        for ev in batch:
            key = ev.get("url") or ev.get("name")
            if key and key in seen:
                continue
            seen.add(key)
            events.append(ev)
            new += 1
        print(f"  page {page}: {len(batch)} found, {new} new (total {len(events)})")
        if new == 0:
            break
    return events


def download(config):
    print("pull events..")
    events = fetch_events(config)
    rows = [map_event(e) for e in events]
    out = config.get("out", "events.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Finish: {len(rows)} rows -> {out}")
    return rows
