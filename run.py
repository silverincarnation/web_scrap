"""Self-contained Streamlit event scraper.

Launch:   streamlit run run.py        (or just:  python run.py)

Finds the sibling ``Scrap/`` folder, lists every ``Scrap/<site>_download.py``,
runs the selected ones for a city + date(s), and saves one CSV per site/day to
``result/<Location>/<YYYY-MM-DD>/<site>.csv``.

Runs day by day: every selected site finishes for one day before the next day.
On a network timeout the site/day is retried after a wait; if a site simply has
no data for a day it is skipped and no CSV is written.

API keys (e.g. Ticketmaster) are read from the environment / a local ``.env``
as ``<SITE>_API_KEY`` (e.g. ``TICKETMASTER_API_KEY``).

Needs: streamlit, pandas, and beautifulsoup4 (Eventbrite only).
"""

import datetime
import importlib.util
import os
import re
import socket
import subprocess
import sys
import time

import streamlit as st

ROOT = os.path.dirname(os.path.abspath(__file__))
RESULT_DIR = os.path.join(ROOT, "result")
SUFFIX = "_download.py"

# Runs day by day: every selected site finishes for one day before the next day.
# On a network timeout we wait and retry; if a site simply has no data for a
# day (0 rows), no CSV is written for it.
MAX_ATTEMPTS = 4        # 1 initial try + up to 3 retries, timeouts only
RETRY_WAIT_SEC = 20     # base seconds between timeout retries (scaled by attempt)

# North American time zones offered in the UI dropdown.
NA_TIMEZONES = [
    "America/New_York", "America/Chicago", "America/Denver",
    "America/Phoenix", "America/Los_Angeles", "America/Anchorage",
    "Pacific/Honolulu", "America/Toronto", "America/Vancouver",
    "America/Mexico_City",
]
NA_TZ_LABELS = {
    "America/New_York": "Eastern — New York",
    "America/Chicago": "Central — Chicago",
    "America/Denver": "Mountain — Denver",
    "America/Phoenix": "Mountain — Phoenix (no DST)",
    "America/Los_Angeles": "Pacific — Los Angeles",
    "America/Anchorage": "Alaska — Anchorage",
    "Pacific/Honolulu": "Hawaii — Honolulu",
    "America/Toronto": "Eastern — Toronto (CA)",
    "America/Vancouver": "Pacific — Vancouver (CA)",
    "America/Mexico_City": "Central — Mexico City (MX)",
}

# Find the sibling Scrap/ folder (case-insensitive fallback).
SCRAP_DIR = next(
    (os.path.join(ROOT, n) for n in ("Scrap", "scrap", "scraping")
     if os.path.isdir(os.path.join(ROOT, n))),
    os.path.join(ROOT, "Scrap"),
)


# If launched with `python run.py`, relaunch under Streamlit and exit.
def _under_streamlit() -> bool:
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        return get_script_run_ctx() is not None
    except Exception:
        return False


if not _under_streamlit():
    sys.exit(subprocess.call(["streamlit", "run", os.path.abspath(__file__)]))


# Load a local .env (no third-party dependency).
_env = os.path.join(ROOT, ".env")
if os.path.exists(_env):
    for _line in open(_env, encoding="utf-8"):
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))


def discover():
    """{site: path} for every Scrap/<site>_download.py."""
    if not os.path.isdir(SCRAP_DIR):
        return {}
    return {f[: -len(SUFFIX)]: os.path.join(SCRAP_DIR, f)
            for f in sorted(os.listdir(SCRAP_DIR))
            if f.endswith(SUFFIX) and not f.startswith("_")}


def load_download(path):
    if SCRAP_DIR not in sys.path:
        sys.path.insert(0, SCRAP_DIR)
    spec = importlib.util.spec_from_file_location("scrap_mod", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.download


def _is_timeout(err):
    """True if the error looks like a network timeout (worth waiting + retrying)."""
    if isinstance(err, (TimeoutError, socket.timeout)):
        return True
    if isinstance(getattr(err, "reason", None), (TimeoutError, socket.timeout)):
        return True
    return "timed out" in str(err).lower() or "timeout" in str(err).lower()


def location_folder(city, country):
    """'New York','US' -> 'New_York_US'."""
    part = re.sub(r"[^A-Za-z0-9]+", "_", city.strip()).strip("_") or "Location"
    part = "_".join(w.capitalize() if w.islower() else w for w in part.split("_"))
    tail = re.sub(r"[^A-Za-z0-9]+", "_", country.strip().upper()).strip("_")
    return f"{part}_{tail}" if tail else part


def build_config(site, city, country, date, out, tz_name="America/New_York"):
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = datetime.timezone.utc
    d = datetime.date.fromisoformat(date)

    def utc(t):
        return datetime.datetime.combine(d, t, tzinfo=tz).astimezone(
            datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    cfg = {
        "city": city.strip(), "country_code": country.strip().upper(),
        "start_date": date, "end_date": date,
        "start_time": utc(datetime.time.min), "end_time": utc(datetime.time.max),
        "size": 200, "max_pages": 1000, "keyword": None, "out": out,
    }
    key = os.environ.get(f"{site.upper()}_API_KEY")
    if key:
        cfg["apikey"] = key
    return cfg


# --------------------------------------------------------------------------- #
# UI
# --------------------------------------------------------------------------- #
st.set_page_config(page_title="Event Scraper", page_icon="🎟️", layout="wide")
st.title("🎟️ Event Scraper")
st.caption("Pick sites, a location and date(s), then scrape. "
           "Each site/day is saved as its own CSV under `result/`.")

scrapers = discover()

with st.sidebar:
    st.header("Available scrapers")
    st.write("\n".join(f"- {s}" for s in scrapers) or "None found in Scrap/")

if not scrapers:
    st.error(f"No `*{SUFFIX}` modules found in {SCRAP_DIR}")
    st.stop()

with st.form("scrape"):
    sites = st.multiselect("Websites", list(scrapers),
                           default=[s for s in ("ra", "songkick", "eventbrite",
                                                "ticketmaster") if s in scrapers])
    c1, c2, c3 = st.columns(3)
    city = c1.text_input("Location (city)", "Mexico City")
    country = c2.text_input("Country code", "MX", max_chars=2)
    tz_name = c3.selectbox("Time zone", NA_TIMEZONES,
                           index=NA_TIMEZONES.index("America/Mexico_City"),
                           format_func=lambda z: NA_TZ_LABELS.get(z, z))
    today = datetime.date.today()
    picked = st.date_input("Date (or range)", (today, today))
    go = st.form_submit_button("Scrape", type="primary")

if go:
    if not sites:
        st.warning("Pick at least one website.")
        st.stop()
    if not city.strip():
        st.warning("Enter a location.")
        st.stop()

    start, end = (picked if isinstance(picked, (list, tuple)) else (picked, picked))
    start, end = min(start, end), max(start, end)
    dates = [(start + datetime.timedelta(days=i)).isoformat()
             for i in range((end - start).days + 1)]

    base = os.path.join(RESULT_DIR, location_folder(city, country))
    total = len(sites) * len(dates)
    st.info(f"Scraping {len(sites)} site(s) x {len(dates)} day(s) = {total} file(s)")

    bar = st.progress(0.0)
    status_area = st.empty()
    results = []
    done = 0
    # Day by day: finish every selected site for one day before the next day.
    for date in dates:
        out_dir = os.path.join(base, date)
        os.makedirs(out_dir, exist_ok=True)
        for site in sites:
            done += 1
            out = os.path.join(out_dir, f"{site}.csv")
            rows, status = None, None

            for attempt in range(1, MAX_ATTEMPTS + 1):
                try:
                    status_area.write(
                        f"⏳ {date} · **{site}** (attempt {attempt}/{MAX_ATTEMPTS})")
                    rows = load_download(scrapers[site])(
                        build_config(site, city, country, date, out, tz_name))
                    status = "ok"
                    break
                except Exception as e:
                    # Timeout -> wait and retry. Any other error -> stop, record it.
                    if _is_timeout(e) and attempt < MAX_ATTEMPTS:
                        wait = RETRY_WAIT_SEC * attempt
                        status_area.warning(
                            f"⏱️ {date} · {site} timed out — waiting {wait}s, "
                            f"then retry {attempt + 1}/{MAX_ATTEMPTS}…")
                        time.sleep(wait)
                        continue
                    status = ("TimeoutError: gave up after retries"
                              if _is_timeout(e) else f"{type(e).__name__}: {e}")
                    break

            n = len(rows or [])
            # No data for this site/day -> don't leave a (header-only) CSV behind.
            if n == 0 and os.path.exists(out):
                try:
                    os.remove(out)
                except OSError:
                    pass

            results.append({
                "Site": site, "Date": date, "Rows": n, "Status": status,
                "File": os.path.relpath(out, ROOT) if n else "— (no data, skipped)",
            })
            bar.progress(done / total)
    status_area.empty()

    ok = sum(1 for r in results if r["Status"] == "ok")
    total_rows = sum(r["Rows"] for r in results)
    (st.success if ok == total else st.warning)(
        f"Done — {ok}/{total} tasks ok, {total_rows} rows total.")
    st.dataframe(results, use_container_width=True, hide_index=True)
    st.caption(f"Saved under: {base}")
