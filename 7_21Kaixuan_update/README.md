# Data Cleaning — Setup & What It Does

## 1. File placement

Both scripts must sit in the **project root** (`web_scrap\`), at the same level as the
`result\` folder — they locate input/output **relative to their own file location**,
so the terminal's current directory does not matter:

```
web_scrap\
├─ Scrap\                        # the six scrapers
├─ result\                       # scraper output (input of the cleaning)
│   ├─ New_York_US\<date>\<source>.csv
│   └─ Mexico_City_MX\<date>\<source>.csv
├─ clean_pipeline.py             # cleaning engine  → data\events.json
├─ clean_daily_csv.py            # companion script → data\clean_csv\<City>\<date>.csv
└─ data\                         # created automatically on first run
    ├─ events.json               # for the Lovable dashboard (with meta block)
    ├─ clean_report.txt          # step-by-step audit log
    └─ clean_csv\
        ├─ New_York_US\2026-08-01.csv
        └─ Mexico_City_MX\2026-08-01.csv
```

> `clean_daily_csv.py` **imports** `clean_pipeline.py` (no copied logic), so the two
> files must stay in the same folder. Keep them together.

## 2. How to run

```bash
# JSON for the dashboard (defaults: date 2026-08-01, New York + Mexico City)
python clean_pipeline.py
python clean_pipeline.py 2026-07-22                # other date(s)

# Cleaned CSVs, one per city per day (default: ALL dates found in result\)
python clean_daily_csv.py
python clean_daily_csv.py 2026-07-22               # only the given date(s)
python clean_daily_csv.py --cities New_York_US Mexico_City_MX Los_Angeles_US
```

Order matters: run the **scraper first**, then the cleaning — both scripts only read
what is already in `result\`, they never fetch from the web.

## 3. What gets cleaned (11 steps, shared by both outputs)

| # | Step | What it does |
|---|------|--------------|
| 1 | load | Reads `result\<City>\<Date>\*.csv`, tags each row with its source |
| 2 | schema check | Drops malformed rows (no name / no start time); count is logged, never silent |
| 3 | text | Fixes mojibake (`MÃ©xico → México`), decodes HTML entities (`&#174; → ®`), strips leftover tags/control chars, collapses double spaces, trims descriptions to 300 chars |
| 4 | time | Unifies 3 formats into venue-local ISO with UTC offset; Ticketmaster's UTC converted to city time (same instant, correct local day); date-only values keep the date and `startTime` stays **null** — no fabricated midnight |
| 5 | city | Adds `canonicalCity` (New York / Mexico City); raw messy value (`cdmx`, `brooklyn`…) kept as `venueArea` |
| 6 | categories | Primary + tags array, case-insensitive de-dupe, removes Ticketmaster's junk label "Undefined" |
| 7 | geo / urls | Coordinates → typed floats or null (0,0 = unknown); suburbs flagged `inCityArea=false` but kept; `http` → `https` |
| 8 | price | `isPaid` strict tri-state: `true / false / null` — unknown is null and is **never** shown as free |
| 9 | dedupe | Two-pass merge of the same event across sources: exact key first, then decorated-venue match guarded by identical start time + venue containment + coords within ~400 m; merged rows keep all origins in `sources` and fill each other's gaps |
| 10 | build | camelCase JSON records, real types, stable hash `id`, `meta` stats block |
| 11 | write | `data\events.json` + audit report with per-field fill rates (CSV variant writes `data\clean_csv\<City>\<date>.csv`, lists joined with `;`, null = empty cell) |

**Principle:** the pipeline copies, converts, de-noises, merges, and annotates —
it never invents values the sources did not publish. Unknown stays null.

**Latest run (Aug 1, NY + MX):** 1,332 rows in → 1,195 events out,
137 cross-source duplicates merged, 0 malformed rows, coordinates 96% filled.

## 4. Fields Never Available (source does not publish them)

These gaps are source-side — no scraping method can recover them.
They are stored as `null` (JSON) / empty cell (CSV), never guessed.

| Source | Never available |
|--------|-----------------|
| **Eventbrite** | — (all fields available) |
| **Ticketmaster** | `endTime` — organizers almost never publish end times (~90% absent) |
| **Resident Advisor** | additional images (single image only); coordinates for TBA/secret venues |
| **Songkick** | `endTime` (end date has no clock time); additional images |
| **NYC Events Calendar** | `latitude` / `longitude` — the API has no coordinates (recovered via merge with NYC Parks where possible) |
| **NYC Parks** | street `address` — the feed only gives the park name |

