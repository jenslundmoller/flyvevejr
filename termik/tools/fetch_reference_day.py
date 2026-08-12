#!/usr/bin/env python3
"""Fetch actual radiation and cloud values for a single reference day.

Used to calibrate the radiation gate and the cirrus caps against days a
pilot has actually flown. Not part of the production pipeline; run by hand.

Tries the regular forecast endpoint with past_days first, since the ERA5
archive typically lags about five days behind. Falls back to the archive
endpoint when the day is out of reach or the forecast call comes back
without it.

The two sources are not interchangeable. The forecast endpoint replays the
same best_match blend production runs on, while the archive serves ecmwf_ifs
for days ERA5 has not reached yet; on 2026-08-08 the two disagreed by up to
250 W/m². Only the forecast endpoint reproduced the scores production
actually published, so prefer it whenever it reaches the day.

See USAGE below for how to call it.
"""

import sys
from datetime import date

import requests

from termik.config import TIMEZONE

USAGE = (
    "Usage: python3 -m termik.tools.fetch_reference_day <lat> <lon> <YYYY-MM-DD>\n"
    "Example: python3 -m termik.tools.fetch_reference_day "
    "55.451748 11.642456 2026-08-08"
)

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

# Open-Meteo rejects past_days above this on the forecast endpoint.
MAX_PAST_DAYS = 92

# Daylight window: outside it every radiation field is zero and the rows
# only make the table harder to read.
FIRST_HOUR = 6
LAST_HOUR = 21

# (API field, column header, column width). Order defines column order.
COLUMNS = [
    ("shortwave_radiation", "SW", 6),
    ("direct_radiation", "direct", 7),
    ("cloud_cover", "cc", 4),
    ("cloud_cover_low", "low", 4),
    ("cloud_cover_mid", "mid", 4),
    ("cloud_cover_high", "high", 5),
    ("boundary_layer_height", "BL_m", 7),
    ("temperature_2m", "T", 6),
    ("wind_direction_10m", "dir", 5),
    ("surface_pressure", "hPa", 8),
]
HOURLY_PARAMS = [field for field, _, _ in COLUMNS]


def parse_day(text: str) -> date:
    """Parse a YYYY-MM-DD argument, or exit with a usage-level error."""
    try:
        return date.fromisoformat(text)
    except ValueError:
        raise SystemExit(f"ERROR: not a YYYY-MM-DD date: {text!r}")


def parse_coord(text: str, name: str) -> float:
    """Parse a decimal-degree argument, or exit with a usage-level error."""
    try:
        return float(text)
    except ValueError:
        raise SystemExit(f"ERROR: {name} is not a number: {text!r}")


def build_urls(lat: float, lon: float, day: date, today: date) -> list[tuple[str, str]]:
    """Build (source name, URL) pairs to try, forecast endpoint first.

    The forecast endpoint is skipped when past_days cannot reach the day,
    so a day far in the past goes straight to the archive.
    """
    query = (
        f"?latitude={lat}&longitude={lon}"
        f"&hourly={','.join(HOURLY_PARAMS)}"
        f"&timezone={TIMEZONE}"
    )
    urls = []
    days_back = (today - day).days
    if 0 <= days_back <= MAX_PAST_DAYS:
        urls.append(
            ("forecast", f"{FORECAST_URL}{query}&past_days={days_back}&forecast_days=1")
        )
    urls.append(
        ("archive", f"{ARCHIVE_URL}{query}&start_date={day}&end_date={day}")
    )
    return urls


def fetch_hourly(url: str) -> dict:
    """GET the URL and return its "hourly" block."""
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    payload = response.json()
    hourly = payload.get("hourly")
    if not hourly or not hourly.get("time"):
        raise ValueError(f"no hourly data in response: {str(payload)[:200]}")
    return hourly


def day_indices(hourly: dict, day: date) -> list[int]:
    """Indices of the daylight hours belonging to `day`, in time order."""
    prefix = day.isoformat()
    return [
        i
        for i, t in enumerate(hourly["time"])
        if t.startswith(prefix) and FIRST_HOUR <= int(t[11:13]) <= LAST_HOUR
    ]


def fetch_day(lat: float, lon: float, day: date, today: date) -> tuple[str, dict, list[int]]:
    """Fetch `day` from the first endpoint that actually returns it.

    Returns (source name, hourly block, row indices). Exits with a report of
    every attempt when no endpoint delivers the day, so an empty table is
    never printed as if it were data.
    """
    problems = []
    for source, url in build_urls(lat, lon, day, today):
        try:
            hourly = fetch_hourly(url)
        except (requests.RequestException, ValueError) as e:
            problems.append(f"  {source}: request failed: {e}")
            continue
        indices = day_indices(hourly, day)
        if indices:
            return source, hourly, indices
        problems.append(
            f"  {source}: returned {hourly['time'][0]} to {hourly['time'][-1]}, "
            f"which does not cover {day}"
        )
    raise SystemExit(f"ERROR: no data for {day}:\n" + "\n".join(problems))


def format_cell(value, width: int) -> str:
    """Right-align a value, showing a missing field as "-" instead of crashing."""
    return f"{'-' if value is None else value:>{width}}"


def print_table(hourly: dict, indices: list[int]) -> None:
    """Print one row per hour, tab-free and aligned for pasting into a referat."""
    header = f"{'kl':>5} " + " ".join(
        f"{name:>{width}}" for _, name, width in COLUMNS
    )
    print(header)
    for i in indices:
        cells = " ".join(
            format_cell(hourly[field][i], width) for field, _, width in COLUMNS
        )
        print(f"{hourly['time'][i][11:16]:>5} {cells}")


def main(argv: list[str]) -> None:
    """Fetch and print one day for one point. argv excludes the program name."""
    if len(argv) != 3:
        raise SystemExit(USAGE)
    lat = parse_coord(argv[0], "latitude")
    lon = parse_coord(argv[1], "longitude")
    day = parse_day(argv[2])

    source, hourly, indices = fetch_day(lat, lon, day, date.today())
    print(f"{day} at {lat},{lon} ({TIMEZONE}, source: {source})")
    print_table(hourly, indices)


if __name__ == "__main__":
    main(sys.argv[1:])
