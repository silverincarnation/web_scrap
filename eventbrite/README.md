# Eventbrite Scraper

Scrapes events from Eventbrite search pages with **BeautifulSoup** (reads the JSON-LD
structured data embedded in each page) and exports them to CSV. Same CSV columns as the
Ticketmaster version in `webscrap`.

## Usage

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Open `run.py` and edit the settings at the top (`CITY`, `COUNTRY_CODE`, `START`, `END`).
3. Run it:

```bash
python run.py
```

CSV files are written to `events_data/`.

## run.py

`run.py` works the **same way as the Ticketmaster `run.py`** — same settings and the same
loop. The only difference: Eventbrite filters by date only (no hourly granularity), so it
produces **one CSV per day** instead of one per hour.

## Files

- `run.py` — edit the settings here, then run.
- `eventbrite_download.py` — the actual logic: `download(config)` fetches the pages, parses
  them with BeautifulSoup, and writes the CSV.

## CSV columns

```
name, description, location_name, latitude, longitude, address,
start_time, end_time, city, primary_category, secondary_categories,
thumbnail_image, additional_images, external_link, is_paid
```

## Note

Eventbrite has no free public search API, so this scrapes web pages. Please respect
Eventbrite's robots.txt and terms of service, keep the request rate low, and use it for
personal / learning purposes only.
