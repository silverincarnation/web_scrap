"""Self-contained Streamlit event scraper.

Launch:   streamlit run run.py        (or just:  python run.py)

Finds the sibling ``Scrap/`` folder, lists every ``Scrap/<site>_download.py``,
runs the selected ones for a city + date(s), and saves one CSV per site/day to
``result/<Location>/<YYYY-MM-DD>/<site>.csv``.

API keys (e.g. Ticketmaster) are read from the environment / a local ``.env``
as ``<SITE>_API_KEY`` (e.g. ``TICKETMASTER_API_KEY``).

Needs: streamlit, pandas, and beautifulsoup4 (Eventbrite only).
"""

import datetime
import importlib.util
import os
import re
import subprocess
import sys

import streamlit as st

ROOT = os.path.dirname(os.path.abspath(__file__))
RESULT_DIR = os.path.join(ROOT, "result")
SUFFIX = "_download.py"

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


def location_folder(city, country):
    """'New York','US' -> 'New_York_US'."""
    part = re.sub(r"[^A-Za-z0-9]+", "_", city.strip()).strip("_") or "Location"
    part = "_".join(w.capitalize() if w.islower() else w for w in part.split("_"))
    tail = re.sub(r"[^A-Za-z0-9]+", "_", country.strip().upper()).strip("_")
    return f"{part}_{tail}" if tail else part


def build_config(site, city, country, date, out):
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo("America/New_York")
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
                           default=[s for s in ("eventbrite",) if s in scrapers])
    c1, c2 = st.columns(2)
    city = c1.text_input("Location (city)", "New York")
    country = c2.text_input("Country code", "US", max_chars=2)
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
    results = []
    done = 0
    for date in dates:
        out_dir = os.path.join(base, date)
        os.makedirs(out_dir, exist_ok=True)
        for site in sites:
            done += 1
            out = os.path.join(out_dir, f"{site}.csv")
            try:
                rows = load_download(scrapers[site])(
                    build_config(site, city, country, date, out))
                results.append({"Site": site, "Date": date,
                                "Rows": len(rows or []), "Status": "ok",
                                "File": os.path.relpath(out, ROOT)})
            except Exception as e:
                results.append({"Site": site, "Date": date, "Rows": 0,
                                "Status": f"{type(e).__name__}: {e}",
                                "File": os.path.relpath(out, ROOT)})
            bar.progress(done / total)

    ok = sum(1 for r in results if r["Status"] == "ok")
    total_rows = sum(r["Rows"] for r in results)
    (st.success if ok == total else st.warning)(
        f"Done — {ok}/{total} files, {total_rows} rows total.")
    st.dataframe(results, use_container_width=True, hide_index=True)
    st.caption(f"Saved under: {base}")
