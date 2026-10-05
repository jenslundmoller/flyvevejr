#!/usr/bin/env python3
"""Find forecast runs the self-hosted runner never picked up.

Forecast-kørslerne går på en selvhostet runner derhjemme, fordi Open-Meteo
drosler GitHub-runnerne (Referat 2026-09-02, opfølgning 5/10). Er maskinen
slukket, venter jobbet i køen i op til et døgn, og kortet viser en gammel
prognose. .github/workflows/forecast-fallback.yml kører dette hver halve
time på en GitHub-hostet runner: kørsler der har stået i kø i mindst
MAX_QUEUED_MINUTES, aflyses og erstattes af én kørsel på ubuntu-latest.

En online runner samler et job op på sekunder, så et kvarter i kø betyder
at den er nede. Reservekørsler (titel med "ubuntu-latest") aflyses aldrig:
GitHubs egen kø kan være langsom, og at aflyse reserven ville efterlade et
hul uden nogen kørsel.

Brug: gh run list --workflow update-forecast.yml \\
        --json databaseId,status,createdAt,displayTitle \\
      | python -m termik.tools.forecast_watchdog
Skriver id'erne på de hængende kørsler, ét pr. linje.
"""

import json
import sys
from datetime import datetime, timezone

MAX_QUEUED_MINUTES = 15
QUEUED_STATES = {"queued", "waiting", "pending", "requested"}
FALLBACK_MARK = "ubuntu-latest"


def stuck_runs(runs, now):
    stuck = []
    for r in runs:
        if r["status"] not in QUEUED_STATES or FALLBACK_MARK in r.get("displayTitle", ""):
            continue
        created = datetime.fromisoformat(r["createdAt"].replace("Z", "+00:00"))
        if (now - created).total_seconds() >= MAX_QUEUED_MINUTES * 60:
            stuck.append(r["databaseId"])
    return stuck


def main(stdin=sys.stdin, now=None):
    now = now or datetime.now(timezone.utc)
    for run_id in stuck_runs(json.load(stdin), now):
        print(run_id)


if __name__ == "__main__":
    main()
