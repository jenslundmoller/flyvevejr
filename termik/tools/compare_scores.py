#!/usr/bin/env python3
"""Sammenlign gammel (v1) og ny (v2) score på en rigtig dag, time for time.

Henter dagen fra Open-Meteos historical-forecast-endpoint, som arkiverer den
samme best_match-blanding produktionen kører på (i modsætning til
archive-endpointets ERA5/ecmwf_ifs, se fetch_reference_day's docstring).
Begge versioner køres gennem process_point_hour, den ægte produktionssti,
ved at flippe config.SCORING_VERSION mellem de to kald.

Bemærk: historical-forecast-endpointet leverer ikke 80/120/180 m-temperatur
og enkelte trykniveauer (950/900/800 hPa). Begge versioner ser de samme
huller, så sammenligningen er fair; surface-lapse-gaten er blot inaktiv.

Usage: python3 -m termik.tools.compare_scores <airfield-id> <YYYY-MM-DD>
Example: python3 -m termik.tools.compare_scores arnborg 2026-06-15
"""

import sys
from datetime import date

import termik.config as config_module
from termik.config import HOURLY_PARAMS, TIMEZONE
from termik.fetch_weather import process_point_hour
from termik.tools.fetch_reference_day import fetch_hourly, parse_day
from termik.tools.replay_day import day_hour_indices, resolve_airfield

HISTORICAL_URL = "https://historical-forecast-api.open-meteo.com/v1/forecast"

# Termikvinduet; udenfor er begge versioner alligevel gatet af strålingen.
FIRST_HOUR = 8
LAST_HOUR = 20


def build_url(point: dict, day: date) -> str:
    """Historical-forecast-request for ét punkt og én dag, produktionens felter."""
    return (
        f"{HISTORICAL_URL}"
        f"?latitude={point['lat']}"
        f"&longitude={point['lon']}"
        f"&hourly={','.join(HOURLY_PARAMS)}"
        f"&start_date={day}&end_date={day}"
        f"&timezone={TIMEZONE}"
        f"&wind_speed_unit=kn"
    )


def score_both(point: dict, hourly: dict, index: int, month: int) -> tuple[dict, dict]:
    """(v1-resultat, v2-resultat) for samme time gennem produktionsstien."""
    original = config_module.SCORING_VERSION
    try:
        config_module.SCORING_VERSION = "v1"
        v1 = process_point_hour(point, hourly, index, month=month)
        config_module.SCORING_VERSION = "v2"
        v2 = process_point_hour(point, hourly, index, month=month)
    finally:
        config_module.SCORING_VERSION = original
    return v1, v2


def compare(point: dict, hourly: dict, day: date) -> list[dict]:
    """Print en markdown-række pr. time og returnér rækkerne til opsummering."""
    rows = []
    print(f"| kl | v1 | v2 | diff | SW | dir | low/mid/high | vind | top_m | v2-label |")
    print(f"|---|---|---|---|---|---|---|---|---|---|")
    for i in day_hour_indices(hourly, day):
        hour = int(hourly["time"][i][11:13])
        if not FIRST_HOUR <= hour <= LAST_HOUR:
            continue
        v1, v2 = score_both(point, hourly, i, month=int(hourly["time"][i][5:7]))
        d = v2["data"]
        diff = round(v2["score"] - v1["score"], 1)
        rows.append({"hour": hour, "v1": v1["score"], "v2": v2["score"],
                     "v1_label": v1["label"], "v2_label": v2["label"]})
        clouds = "/".join(
            "-" if d[k] is None else f"{d[k]:.0f}"
            for k in ("cloud_cover_low", "cloud_cover_mid", "cloud_cover_high")
        )
        top = d["thermal_top_m"]
        direct = d["direct_radiation"]
        direct_cell = "-" if direct is None else f"{direct:.0f}"
        print(
            f"| {hour:02d} | {v1['score']:.1f} | {v2['score']:.1f} "
            f"| {diff:+.1f} | {d['shortwave_radiation']:.0f} "
            f"| {direct_cell} "
            f"| {clouds} | {d['wind_speed_kt']:.0f} kt "
            f"| {'-' if top is None else top} | {v2['label']} |"
        )
    return rows


def summarize(rows: list[dict]) -> None:
    if not rows:
        print("\nIngen timer i vinduet.")
        return
    max_v1 = max(r["v1"] for r in rows)
    max_v2 = max(r["v2"] for r in rows)
    hrs_v1 = sum(1 for r in rows if r["v1"] >= 5)
    hrs_v2 = sum(1 for r in rows if r["v2"] >= 5)
    print(f"\nMaks: v1 {max_v1:.1f} / v2 {max_v2:.1f}. "
          f"Timer med score >= 5: v1 {hrs_v1} / v2 {hrs_v2}.")


def main(argv: list[str]) -> None:
    if len(argv) != 2:
        raise SystemExit(__doc__.strip().split("\n")[-2])
    point = resolve_airfield(argv[0])
    day = parse_day(argv[1])
    hourly = fetch_hourly(build_url(point, day))
    if not day_hour_indices(hourly, day):
        raise SystemExit(f"ERROR: svaret dækker ikke {day}")
    print(f"### {point['name']} ({point['id']}), {day}\n")
    rows = compare(point, hourly, day)
    summarize(rows)


if __name__ == "__main__":
    main(sys.argv[1:])
