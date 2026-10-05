#!/usr/bin/env python3
"""Pick the sea cell whose temperature each coastal point's sea breeze reads.

The sea breeze penalty compares land with the water the onshore wind comes
over. Production reads that water's measured surface temperature from
Open-Meteo's marine API, once per run, for a fixed list of sea cells. This
tool chooses the cells and writes termik/sea_points.json; like the
elevations, it is only needed again when points are added or moved.

For every point inside the sea breeze range it walks out along the point's
coast direction (coast_direction_deg), past the coast, until the marine API
answers with a sea temperature. Cells are rounded to 0.1 degree and shared,
so ~260 points need far fewer cells and the production call stays small.
Points the walk cannot place (an inner fjord the marine model does not
resolve) are left out and fall back to the climatology.

Usage: python3 -m termik.tools.fetch_sea_points
"""

import json
import math
import time

import requests

from termik.config import SEABREEZE_MAX_DISTANCE_KM
from termik.locations import ALL_POINTS, SEA_POINTS_PATH

MARINE_URL = "https://marine-api.open-meteo.com/v1/marine"

# Kilometres past the coast to try, nearest first. Close enough to be the
# water the breeze actually comes from, far enough to leave the coastline
# cells the marine model treats as land.
STEPS_PAST_COAST_KM = (8, 15, 25, 40)

BATCH_SIZE = 100


def _destination(lat: float, lon: float, bearing_deg: float, km: float) -> tuple[float, float]:
    """Great-circle point km away from (lat, lon) along bearing_deg."""
    r = 6371.0
    b = math.radians(bearing_deg)
    la = math.radians(lat)
    lo = math.radians(lon)
    d = km / r
    la2 = math.asin(math.sin(la) * math.cos(d) + math.cos(la) * math.sin(d) * math.cos(b))
    lo2 = lo + math.atan2(
        math.sin(b) * math.sin(d) * math.cos(la), math.cos(d) - math.sin(la) * math.sin(la2)
    )
    return math.degrees(la2), math.degrees(lo2)


def _has_sea_temperature(coords: list[tuple[float, float]]) -> list[bool]:
    """Ask the marine API which coordinates resolve to water."""
    found = []
    for start in range(0, len(coords), BATCH_SIZE):
        batch = coords[start:start + BATCH_SIZE]
        response = requests.get(
            MARINE_URL,
            params={
                "latitude": ",".join(f"{la:.1f}" for la, _ in batch),
                "longitude": ",".join(f"{lo:.1f}" for _, lo in batch),
                "current": "sea_surface_temperature",
            },
            timeout=60,
        )
        response.raise_for_status()
        body = response.json()
        results = body if isinstance(body, list) else [body]
        found.extend(r["current"]["sea_surface_temperature"] is not None for r in results)
        time.sleep(1)
    return found


def main() -> None:
    pending = [p for p in ALL_POINTS if p["coast_distance_km"] < SEABREEZE_MAX_DISTANCE_KM]
    chosen: dict[str, tuple[float, float]] = {}
    for extra in STEPS_PAST_COAST_KM:
        candidates = []
        for p in pending:
            la, lo = _destination(
                p["lat"], p["lon"], p["coast_direction_deg"], p["coast_distance_km"] + extra
            )
            candidates.append((round(la, 1), round(lo, 1)))
        unique = sorted(set(candidates))
        answers = dict(zip(unique, _has_sea_temperature(unique)))
        still = []
        for p, cell in zip(pending, candidates):
            if answers[cell]:
                chosen[p["id"]] = cell
            else:
                still.append(p)
        pending = still
        print(f"+{extra} km: {len(chosen)} placed, {len(pending)} left")

    cells = sorted(set(chosen.values()))
    index = {cell: i for i, cell in enumerate(cells)}
    out = {
        "cells": [list(c) for c in cells],
        "by_point": {pid: index[cell] for pid, cell in sorted(chosen.items())},
    }
    with open(SEA_POINTS_PATH, "w") as f:
        json.dump(out, f, indent=0)
        f.write("\n")
    print(f"Wrote {len(cells)} sea cells for {len(chosen)} points; "
          f"unplaced: {', '.join(p['id'] for p in pending) or 'none'}")


if __name__ == "__main__":
    main()
