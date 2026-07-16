from ticketmaster_download import download
import os
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo


def load_env(path=".env"):
    env = {}
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                env[key.strip()] = value.strip()
    return env


env = load_env()

CITY = "New York"
COUNTRY_CODE = "US"
TIMEZONE = "America/New_York"
OUT_DIR = "events_data"
START = "2026-06-20T00:00:00"
END   = "2026-07-23T23:59:59"


def to_utc(local_dt):
    return local_dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_one_hour(start):
    end = start + timedelta(hours=1) - timedelta(seconds=1)

    os.makedirs(OUT_DIR, exist_ok=True)
    label = start.strftime("%Y-%m-%d_%Hh")
    filename = f"{COUNTRY_CODE}_{CITY}_{label}.csv"
    config = {
        "apikey": env.get("TICKETMASTER_API_KEY"),
        "start_time": to_utc(start),
        "end_time": to_utc(end),
        "city": CITY,
        "country_code": COUNTRY_CODE,
        "out": os.path.join(OUT_DIR, filename),
        "size": 200,
        "max_pages": None,
    }
    print(f"{start.strftime('%Y-%m-%d %H:%M')} ({TIMEZONE}) -> UTC {config['start_time']} ~ {config['end_time']}")
    download(config)


def run_hourly(start_local, end_local):
    tz = ZoneInfo(TIMEZONE)
    current = datetime.fromisoformat(start_local).replace(tzinfo=tz)
    end = datetime.fromisoformat(end_local).replace(tzinfo=tz)
    while current <= end:
        run_one_hour(current)
        current += timedelta(hours=1)
        time.sleep(0.5)  


if __name__ == "__main__":
    run_hourly(START, END)


"""

config = {
    "apikey": env.get("TICKETMASTER_API_KEY"),
    "start_time": "2025-06-01T00:00:00Z",
    "end_time": "2025-06-01T23:59:59Z",
    "city": "London",
    "country_code": "GB",
    "keyword": "",
    "out": "events.csv",
    "size": 100,
    "max_pages": 5,
}

if __name__ == "__main__":
    download(config)
"""
