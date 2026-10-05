#!/usr/bin/env python3
"""Fetch terrain elevation for every forecast point, once, by hand.

The parcel calculation in compute_thermal_top needs the height the 2 m
temperature belongs to. Elevation never changes, so production does not ask
for it: airfields carry a hardcoded elevation_m in locations.AIRFIELDS and the
grid reads termik/grid_elevations.json. This tool produced both and is only
needed again when points are added or moved.

The values come from Open-Meteo's own elevation endpoint (Copernicus 90 m
DEM) on purpose. The forecast API downscales temperature_2m to exactly that
terrain height, so a different DEM, or the airfield's published AIP
elevation, would put the parcel's start a few metres away from where its
temperature is valid.

Usage: python3 -m termik.tools.fetch_elevations
Prints the airfield values to paste into locations.py and rewrites
termik/grid_elevations.json.
"""

import json
import os

import requests

from termik.locations import AIRFIELDS, GRID_ELEVATIONS_PATH, GRID_POINTS

ELEVATION_URL = "https://api.open-meteo.com/v1/elevation"

# The endpoint accepts at most 100 coordinates per request.
BATCH_SIZE = 100


def fetch_elevations(points: list[dict]) -> dict[str, int]:
    """Return {point id: elevation in whole metres} for the given points."""
    result = {}
    for start in range(0, len(points), BATCH_SIZE):
        batch = points[start:start + BATCH_SIZE]
        response = requests.get(
            ELEVATION_URL,
            params={
                "latitude": ",".join(str(p["lat"]) for p in batch),
                "longitude": ",".join(str(p["lon"]) for p in batch),
            },
            timeout=60,
        )
        response.raise_for_status()
        elevations = response.json()["elevation"]
        for point, elevation in zip(batch, elevations):
            # Sea cells come back negative or as 0; the parcel starts at sea
            # level there, never below it.
            result[point["id"]] = max(0, round(elevation))
    return result


def main() -> None:
    airfields = fetch_elevations(AIRFIELDS)
    for point in AIRFIELDS:
        print(f"{point['id']:<18} {airfields[point['id']]:>4} m")

    grid = fetch_elevations(GRID_POINTS)
    with open(GRID_ELEVATIONS_PATH, "w") as f:
        json.dump(grid, f, indent=0, sort_keys=True)
        f.write("\n")
    print(f"Wrote {len(grid)} grid elevations to {os.path.relpath(GRID_ELEVATIONS_PATH)}")


if __name__ == "__main__":
    main()
