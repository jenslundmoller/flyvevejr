"""Fetch weather data from Open-Meteo and produce thermal forecast JSON."""

import json
import os
import requests
from datetime import datetime

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


def fetch_batch(points: list[dict]) -> list[dict]:
    """Call the Open-Meteo API for a batch of points and return parsed data."""
    url = build_api_url(points)
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return parse_api_response(response.json())


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
    )

    comment = generate_comment(
        lapse_rate=result["lapse_rate"],
        spread=result["spread"],
        skybase_m=result["skybase_m"],
        wind_kt=wind_speed,
        cloud_cover=cloud_cover,
        cape=cape,
        precipitation=precipitation,
        seabreeze_risk=result["seabreeze_penalty"],
        pressure_trend=pressure_trend,
        score=result["score"],
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
        },
    }


def process_all_points() -> dict:
    """Fetch weather for all points and compute thermal scores.

    Batches ALL_POINTS into groups of API_BATCH_SIZE, calls fetch_batch
    for each group, processes every hour, and returns the full output dict.
    """
    all_results = []

    # Batch points
    for i in range(0, len(ALL_POINTS), API_BATCH_SIZE):
        batch_points = ALL_POINTS[i : i + API_BATCH_SIZE]
        batch_data = fetch_batch(batch_points)

        for point, hourly_response in zip(batch_points, batch_data):
            hourly_data = hourly_response["hourly"]
            num_hours = len(hourly_data["time"])

            hours = []
            for h in range(num_hours):
                # Derive month from the forecast hour timestamp
                time_str = hourly_data["time"][h]
                month = int(time_str[5:7])
                hour_result = process_point_hour(point, hourly_data, h, month)
                hours.append(hour_result)

            all_results.append(
                {
                    "id": point["id"],
                    "name": point.get("name", ""),
                    "type": "airfield" if "name" in point else "grid",
                    "lat": point["lat"],
                    "lon": point["lon"],
                    "region": point.get("region", ""),
                    "hours": hours,
                }
            )

    return {
        "generated": datetime.now().isoformat(),
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

    # current.json — everything
    with open(os.path.join(DATA_DIR, "current.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

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
    import time

    print(f"Termik forecast starting at {datetime.now().isoformat()}")
    start = time.time()
    data = process_all_points()
    write_output(data)
    elapsed = time.time() - start
    print(f"Done. {len(data['points'])} points processed in {elapsed:.1f}s")
    print(f"Output written to {DATA_DIR}/")


if __name__ == "__main__":
    main()
