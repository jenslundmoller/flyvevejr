"""Fetch weather data from Open-Meteo and produce thermal forecast JSON."""

import json
import os
import time
import requests
from datetime import datetime, timezone

from termik.config import (
    API_BASE_URL,
    API_BATCH_SIZE,
    FORECAST_DAYS,
    TIMEZONE,
    HOURLY_PARAMS,
    DATA_DIR,
)
from termik.scoring import compute_thermal_score
from termik.comments import generate_comment
from termik.locations import ALL_POINTS, AIRFIELDS


def build_api_url(points: list[dict]) -> str:
    """Build Open-Meteo forecast URL for a list of points.

    Comma-separates latitudes and longitudes; includes all HOURLY_PARAMS,
    forecast_days=3, timezone=Europe/Berlin, wind_speed_unit=kn.
    """
    lats = ",".join(str(p["lat"]) for p in points)
    lons = ",".join(str(p["lon"]) for p in points)
    params = ",".join(HOURLY_PARAMS)
    return (
        f"{API_BASE_URL}"
        f"?latitude={lats}"
        f"&longitude={lons}"
        f"&hourly={params}"
        f"&forecast_days={FORECAST_DAYS}"
        f"&timezone={TIMEZONE}"
        f"&wind_speed_unit=kn"
    )


def parse_api_response(raw) -> list[dict]:
    """Normalize API response: wrap a single-location dict in a list."""
    if isinstance(raw, dict):
        return [raw]
    return raw


def fetch_batch(points: list[dict], max_retries: int = 3) -> list[dict]:
    """Call the Open-Meteo API for a batch of points and return parsed data.

    Retries up to max_retries times on transient errors (5xx, timeouts)
    with exponential backoff.
    """
    url = build_api_url(points)
    for attempt in range(max_retries + 1):
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return parse_api_response(response.json())
        except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError,
                requests.exceptions.Timeout) as e:
            is_server_error = (
                isinstance(e, requests.exceptions.HTTPError)
                and e.response is not None
                and e.response.status_code >= 500
            )
            is_rate_limited = (
                isinstance(e, requests.exceptions.HTTPError)
                and e.response is not None
                and e.response.status_code == 429
            )
            is_transient = is_server_error or is_rate_limited or not isinstance(e, requests.exceptions.HTTPError)
            if not is_transient or attempt == max_retries:
                raise
            wait = 2 ** attempt * 15  # 15s, 30s, 60s
            print(f"API request failed ({e}), retrying in {wait}s (attempt {attempt + 1}/{max_retries})...")
            time.sleep(wait)


def calculate_precip_last_6h(precip_values: list, hour_index: int) -> float:
    """Sum precipitation for the 6 hours before hour_index (inclusive of start)."""
    start = max(0, hour_index - 5)
    return sum(v for v in precip_values[start:hour_index + 1] if v is not None)


def calculate_pressure_trend(pressures: list, hour_index: int) -> float:
    """Return pressure change over the last 3 hours. 0 if insufficient data."""
    if hour_index < 3:
        return 0
    current = pressures[hour_index]
    previous = pressures[hour_index - 3]
    if current is None or previous is None:
        return 0
    return current - previous


def calculate_temp_850_trend(temps: list, hour_index: int) -> float:
    """Return 850 hPa temperature change over the last 3 hours. 0 if insufficient data."""
    if hour_index < 3:
        return 0
    current = temps[hour_index]
    previous = temps[hour_index - 3]
    if current is None or previous is None:
        return 0
    return current - previous


def process_point_hour(point: dict, hourly_data: dict, hour_index: int, month: int) -> dict:
    """Process one hour of forecast data for one point.

    Extracts values from hourly_data, computes derived fields, calls
    compute_thermal_score and generate_comment.  Returns the result dict.
    """
    # Extract raw values
    temp = hourly_data["temperature_2m"][hour_index]
    dewpoint = hourly_data["dewpoint_2m"][hour_index]
    temp_850 = hourly_data["temperature_850hPa"][hour_index]
    cloud_cover = hourly_data["cloud_cover"][hour_index]
    shortwave = hourly_data["shortwave_radiation"][hour_index]
    wind_speed = hourly_data["wind_speed_10m"][hour_index]
    wind_dir = hourly_data["wind_direction_10m"][hour_index]
    wind_gusts = hourly_data["wind_gusts_10m"][hour_index]
    precipitation = hourly_data["precipitation"][hour_index]
    cape = hourly_data["cape"][hour_index]
    pressure = hourly_data["surface_pressure"][hour_index]
    humidity = hourly_data["relative_humidity_2m"][hour_index]

    # Multi-level wind
    wind_speed_80m = hourly_data.get("wind_speed_80m", [None] * (hour_index + 1))[hour_index]
    wind_dir_80m = hourly_data.get("wind_direction_80m", [None] * (hour_index + 1))[hour_index]
    wind_speed_120m = hourly_data.get("wind_speed_120m", [None] * (hour_index + 1))[hour_index]
    wind_dir_120m = hourly_data.get("wind_direction_120m", [None] * (hour_index + 1))[hour_index]
    wind_speed_180m = hourly_data.get("wind_speed_180m", [None] * (hour_index + 1))[hour_index]
    wind_dir_180m = hourly_data.get("wind_direction_180m", [None] * (hour_index + 1))[hour_index]

    # Multi-level temperature
    temp_80m = hourly_data.get("temperature_80m", [None] * (hour_index + 1))[hour_index]
    temp_120m = hourly_data.get("temperature_120m", [None] * (hour_index + 1))[hour_index]
    temp_180m = hourly_data.get("temperature_180m", [None] * (hour_index + 1))[hour_index]

    # Boundary layer height
    bl_height = hourly_data.get("boundary_layer_height", [None] * (hour_index + 1))[hour_index]

    # Check for critical None values
    critical = [temp, dewpoint, temp_850, cloud_cover, wind_speed, wind_dir, pressure]
    if any(v is None for v in critical):
        return {
            "time": hourly_data["time"][hour_index],
            "score": 0,
            "label": "Data mangler",
            "comment": "",
            "data": {
                "temp": temp,
                "dewpoint": dewpoint,
                "spread": None,
                "skybase_m": None,
                "skybase_ft": None,
                "cloud_cover": cloud_cover,
                "wind_speed_kt": wind_speed,
                "wind_dir": wind_dir,
                "wind_gusts_kt": wind_gusts,
                "lapse_rate": None,
                "cape": cape,
                "precipitation": precipitation,
                "pressure": pressure,
                "relative_humidity": humidity,
                "wind_speed_80m_kt": wind_speed_80m,
                "wind_speed_120m_kt": wind_speed_120m,
                "wind_speed_180m_kt": wind_speed_180m,
                "wind_dir_80m": wind_dir_80m,
                "wind_dir_120m": wind_dir_120m,
                "wind_dir_180m": wind_dir_180m,
                "temp_80m": temp_80m,
                "temp_120m": temp_120m,
                "temp_180m": temp_180m,
                "boundary_layer_height": bl_height,
                "surface_lapse_rate": None,
            },
        }

    # Derived values
    precip_last_6h = calculate_precip_last_6h(
        hourly_data["precipitation"], hour_index
    )
    pressure_trend = calculate_pressure_trend(
        hourly_data["surface_pressure"], hour_index
    )
    temp_850_trend = calculate_temp_850_trend(
        hourly_data["temperature_850hPa"], hour_index
    )

    # Safe fallbacks for non-critical None values
    shortwave = shortwave if shortwave is not None else 0
    wind_gusts = wind_gusts if wind_gusts is not None else wind_speed
    precipitation = precipitation if precipitation is not None else 0
    cape = cape if cape is not None else 0

    result = compute_thermal_score(
        temp_2m=temp,
        dewpoint_2m=dewpoint,
        temp_850hpa=temp_850,
        cloud_cover=cloud_cover,
        shortwave_radiation=shortwave,
        wind_speed_kt=wind_speed,
        wind_dir=wind_dir,
        wind_gusts_kt=wind_gusts,
        precipitation=precipitation,
        precip_last_6h=precip_last_6h,
        cape=cape,
        surface_pressure=pressure,
        pressure_trend=pressure_trend,
        temp_850hpa_trend=temp_850_trend,
        coast_distance_km=point["coast_distance_km"],
        coast_direction_deg=point["coast_direction_deg"],
        month=month,
        temp_180m=temp_180m,
        wind_speed_80m_kt=wind_speed_80m,
        wind_speed_180m_kt=wind_speed_180m,
        boundary_layer_height=bl_height,
    )

    # Calculate wind shear for comments
    wind_shear_for_comment = None
    if wind_speed_80m is not None and wind_speed is not None:
        wind_shear_for_comment = abs(wind_speed_80m - wind_speed)

    comment = generate_comment(
        lapse_rate=result["lapse_rate"],
        spread=result["spread"],
        skybase_m=result["skybase_m"],
        wind_kt=wind_speed,
        wind_gusts_kt=wind_gusts,
        cloud_cover=cloud_cover,
        cape=cape,
        precipitation=precipitation,
        seabreeze_risk=result["seabreeze_penalty"],
        pressure_trend=pressure_trend,
        score=result["score"],
        wind_shear_kt=wind_shear_for_comment,
        boundary_layer_height=bl_height,
    )

    return {
        "time": hourly_data["time"][hour_index],
        "score": result["score"],
        "label": result["label"],
        "comment": comment,
        "data": {
            "temp": temp,
            "dewpoint": dewpoint,
            "spread": result["spread"],
            "skybase_m": result["skybase_m"],
            "skybase_ft": result["skybase_ft"],
            "cloud_cover": cloud_cover,
            "wind_speed_kt": wind_speed,
            "wind_dir": wind_dir,
            "wind_gusts_kt": wind_gusts,
            "lapse_rate": result["lapse_rate"],
            "cape": cape,
            "precipitation": precipitation,
            "pressure": pressure,
            "relative_humidity": humidity,
            "wind_speed_80m_kt": wind_speed_80m,
            "wind_speed_120m_kt": wind_speed_120m,
            "wind_speed_180m_kt": wind_speed_180m,
            "wind_dir_80m": wind_dir_80m,
            "wind_dir_120m": wind_dir_120m,
            "wind_dir_180m": wind_dir_180m,
            "temp_80m": temp_80m,
            "temp_120m": temp_120m,
            "temp_180m": temp_180m,
            "boundary_layer_height": bl_height,
            "surface_lapse_rate": result.get("surface_lapse_rate"),
        },
    }


def process_all_points() -> dict:
    """Fetch weather for all points and compute thermal scores.

    Batches ALL_POINTS into groups of API_BATCH_SIZE, calls fetch_batch
    for each group, processes every hour, and returns the full output dict.
    """
    all_results = []
    failed_batches = 0
    total_batches = (len(ALL_POINTS) + API_BATCH_SIZE - 1) // API_BATCH_SIZE

    # Batch points
    for batch_num, i in enumerate(range(0, len(ALL_POINTS), API_BATCH_SIZE)):
        if batch_num > 0:
            time.sleep(5)  # Avoid rate limiting between batches
        batch_points = ALL_POINTS[i : i + API_BATCH_SIZE]
        try:
            batch_data = fetch_batch(batch_points)
        except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError,
                requests.exceptions.Timeout) as e:
            failed_batches += 1
            print(f"Batch {batch_num + 1}/{total_batches} failed permanently: {e}")
            continue

        for point, hourly_response in zip(batch_points, batch_data):
            hourly_data = hourly_response["hourly"]
            num_hours = len(hourly_data["time"])
            is_airfield = "name" in point

            hours = []
            for h in range(num_hours):
                # Derive month from the forecast hour timestamp
                time_str = hourly_data["time"][h]
                month = int(time_str[5:7])
                hour_result = process_point_hour(point, hourly_data, h, month)
                # Grid points only feed the heat-map: keep just time + score so
                # the JSON payload stays small. Airfields keep the full payload
                # for their popup display.
                if not is_airfield:
                    hour_result = {
                        "time": hour_result["time"],
                        "score": hour_result["score"],
                    }
                hours.append(hour_result)

            entry = {
                "id": point["id"],
                "type": "airfield" if is_airfield else "grid",
                "lat": point["lat"],
                "lon": point["lon"],
                "hours": hours,
            }
            if is_airfield:
                entry["name"] = point.get("name", "")
                entry["region"] = point.get("region", "")
            all_results.append(entry)

    if failed_batches:
        print(f"WARNING: {failed_batches}/{total_batches} batches failed. "
              f"Output contains {len(all_results)} of {len(ALL_POINTS)} points.")

    return {
        "generated": datetime.now(timezone.utc).isoformat(),
        "forecast_days": FORECAST_DAYS,
        "points": all_results,
    }


def write_output(data: dict):
    """Write forecast data to JSON files in DATA_DIR.

    Produces:
      - current.json  — full forecast for all points
      - airfields.json — airfield-only subset
      - meta.json — generation metadata
    """
    os.makedirs(DATA_DIR, exist_ok=True)

    # current.json — everything (compact: no indent, to minimise transfer size)
    with open(os.path.join(DATA_DIR, "current.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))

    # airfields.json — only airfield points
    airfield_ids = {a["id"] for a in AIRFIELDS}
    airfield_data = {
        "generated": data["generated"],
        "forecast_days": data["forecast_days"],
        "points": [p for p in data["points"] if p["id"] in airfield_ids],
    }
    with open(os.path.join(DATA_DIR, "airfields.json"), "w", encoding="utf-8") as f:
        json.dump(airfield_data, f, ensure_ascii=False, indent=2)

    # meta.json
    hour_count = sum(len(p["hours"]) for p in data["points"])
    meta = {
        "generated": data["generated"],
        "point_count": len(data["points"]),
        "hour_count": hour_count,
    }
    with open(os.path.join(DATA_DIR, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


def main():
    print(f"Termik forecast starting at {datetime.now().isoformat()}")
    start = time.time()
    data = process_all_points()
    if not data["points"]:
        print("ERROR: All batches failed, no data to write.")
        raise SystemExit(1)
    write_output(data)
    elapsed = time.time() - start
    print(f"Done. {len(data['points'])} points processed in {elapsed:.1f}s")
    print(f"Output written to {DATA_DIR}/")


if __name__ == "__main__":
    main()
