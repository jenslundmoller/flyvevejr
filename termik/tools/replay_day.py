#!/usr/bin/env python3
"""Replay one airfield-day through the real scoring path, hour by hour.

Calibration needs to see what production *would* publish for a day a pilot
has actually flown, without waiting three hours for the next cron run. This
fetches the raw hourly data for one airfield and one day and pushes every
daylight hour through process_point_hour, the same function the production
fetch calls, so the printed score is the score.

Deliberately forecast-endpoint only, with no archive fallback. The archive
serves ecmwf_ifs for days ERA5 has not reached, a different model from the
best_match blend production runs on; on 2026-08-08 the two disagreed by up to
253 W/m², enough to move published scores by two whole tiers. A silent
fallback would therefore calibrate the gate against numbers production never
saw. When the day is out of the forecast endpoint's reach, this exits instead.

See USAGE below for how to call it.
"""

import sys
from datetime import date

from termik.config import (
    API_BASE_URL,
    HOURLY_PARAMS,
    TIMEZONE,
)
from termik.fetch_weather import calculate_trailing_window, process_point_hour
from termik.locations import AIRFIELDS
from termik.scoring import effective_radiation
from termik.tools.fetch_reference_day import MAX_PAST_DAYS, fetch_hourly, parse_day

USAGE = (
    "Usage: python3 -m termik.tools.replay_day <airfield-id> <YYYY-MM-DD>\n"
    "Example: python3 -m termik.tools.replay_day ringsted 2026-08-08"
)

# Daylight window. Outside it every radiation field is zero and the rows only
# make the table harder to read.
FIRST_HOUR = 6
LAST_HOUR = 21


def resolve_airfield(airfield_id: str) -> dict:
    """Look up one airfield by id, or exit listing what is available."""
    for point in AIRFIELDS:
        if point["id"] == airfield_id:
            return point
    known = ", ".join(sorted(p["id"] for p in AIRFIELDS))
    raise SystemExit(f"ERROR: unknown airfield {airfield_id!r}.\nKnown ids: {known}")


def build_url(point: dict, day: date, today: date) -> str:
    """Build the production forecast request, narrowed to one point and day.

    Mirrors build_api_url in fetch_weather, including wind_speed_unit=kn and
    the full HOURLY_PARAMS list, so the replay sees exactly the fields the
    scoring expects. past_days reaches back to the requested day.
    """
    days_back = (today - day).days
    if days_back < 0:
        raise SystemExit(f"ERROR: {day} is in the future, nothing to replay.")
    if days_back > MAX_PAST_DAYS:
        raise SystemExit(
            f"ERROR: {day} is {days_back} days back, beyond the forecast "
            f"endpoint's limit of {MAX_PAST_DAYS}. The archive endpoint reaches "
            f"it but runs a different model, so replaying against it would not "
            f"reproduce what production published. See this module's docstring."
        )
    return (
        f"{API_BASE_URL}"
        f"?latitude={point['lat']}"
        f"&longitude={point['lon']}"
        f"&hourly={','.join(HOURLY_PARAMS)}"
        f"&past_days={days_back}"
        f"&forecast_days=1"
        f"&timezone={TIMEZONE}"
        f"&wind_speed_unit=kn"
    )


def day_hour_indices(hourly: dict, day: date) -> list[int]:
    """Indices of the daylight hours belonging to `day`, in time order."""
    prefix = day.isoformat()
    return [
        i
        for i, t in enumerate(hourly["time"])
        if t.startswith(prefix) and FIRST_HOUR <= int(t[11:13]) <= LAST_HOUR
    ]


def _cell(value, width: int, decimals: int = 0) -> str:
    """Right-align a value, showing a missing field as "-" instead of crashing."""
    if value is None:
        return f"{'-':>{width}}"
    if isinstance(value, float):
        return f"{value:>{width}.{decimals}f}"
    return f"{value:>{width}}"


def replay(point: dict, hourly: dict, day: date) -> dict[int, float]:
    """Score every daylight hour of `day` and print one row each.

    Returns {hour: score} so a caller can assert on it. The effective-radiation
    column is what the radiation gate actually tests, which is not the SW
    column next to it whenever the heat memory applies.
    """
    print(
        f"{'kl':>5}{'score':>7}  {'label':<20}"
        f"{'SW':>6}{'effSW':>7}{'BL_m':>7}"
        f"{'cc':>5}{'low':>5}{'mid':>5}{'high':>5}{'lapse':>7}"
    )
    scores = {}
    for i in day_hour_indices(hourly, day):
        timestamp = hourly["time"][i]
        result = process_point_hour(point, hourly, i, month=int(timestamp[5:7]))
        data = result["data"]
        hour = int(timestamp[11:13])
        scores[hour] = result["score"]

        shortwave = hourly["shortwave_radiation"][i]
        effective = effective_radiation(
            shortwave if shortwave is not None else 0,
            calculate_trailing_window(hourly["shortwave_radiation"], i),
            hourly["cloud_cover"][i],
            calculate_trailing_window(hourly["cloud_cover"], i),
        )
        print(
            f"{timestamp[11:16]:>5}{_cell(result['score'], 7, 1)}  "
            f"{result['label']:<20}"
            f"{_cell(shortwave, 6)}{_cell(effective, 7)}"
            f"{_cell(data['boundary_layer_height'], 7)}"
            f"{_cell(data['cloud_cover'], 5)}{_cell(data['cloud_cover_low'], 5)}"
            f"{_cell(data['cloud_cover_mid'], 5)}{_cell(data['cloud_cover_high'], 5)}"
            f"{_cell(data['lapse_rate'], 7, 2)}"
        )
    return scores


def main(argv: list[str]) -> None:
    """Replay one airfield-day. argv excludes the program name."""
    if len(argv) != 2:
        raise SystemExit(USAGE)
    point = resolve_airfield(argv[0])
    day = parse_day(argv[1])

    hourly = fetch_hourly(build_url(point, day, date.today()))
    if not day_hour_indices(hourly, day):
        covered = f"{hourly['time'][0]} to {hourly['time'][-1]}"
        raise SystemExit(f"ERROR: response covers {covered}, which does not cover {day}")

    print(f"{point['name']} ({point['id']}) on {day}, {TIMEZONE}, forecast endpoint")
    replay(point, hourly, day)


if __name__ == "__main__":
    main(sys.argv[1:])
