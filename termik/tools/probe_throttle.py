#!/usr/bin/env python3
"""Measure how long Open-Meteo throttles a GitHub runner after a success.

Produktionsloggene 1-5/10 (overdragelsen 2026-10-05, punkt 13) viste, at et
kald 5 s efter et vellykket kald hænger i 50 % af tilfældene og 50-55 s efter
i 61 %, mens det efter 110 s kun hænger i 2 %. Lokalt hænger intet. Loggene
kan ikke skelne mellem to forklaringer, fordi retry-rytmen altid kobler dem:

  (a) API'et holder igen i et vindue på 60-110 s efter et vellykket kald.
  (b) Det afgørende er pausen efter et hængt kald (15 s: 62 %, 30 s: 7 %).

Proben kører derfor to slags forsøg i blandet rækkefølge, med en pause på
RESET_SECONDS mellem dem, så hvert forsøg starter fra rolig tilstand:

  gap N    Et vellykket kald, og et nyt kald N s efter at det første startede.
  hang30   Et vellykket kald, et nyt efter HANG30_FIRST_GAP s (hænger typisk),
           og hængte det, et tredje 30 s efter at det hængte kald gav op. Under
           (a) fejler det tredje kald (~65 s efter succesen), under (b) lykkes det.

Kaldene er produktionens rigtige batch-URL'er med samme 30 s-timeout.

Brug: python -m termik.tools.probe_throttle [reps]
Køres fra .github/workflows/probe-throttle.yml; lokalt måler den ingenting.
"""

import json
import random
import sys
import time

import requests

GAPS = [20, 40, 60, 80, 100]
REQUEST_TIMEOUT = 30
RESET_SECONDS = 150
HANG30_FIRST_GAP = 5
FIRST_CALL_RETRY_PAUSE = 120
FIRST_CALL_MAX_ATTEMPTS = 3


def plan_trials(gaps, reps, seed=None):
    """Every gap plus the hang30 arm, reps times each, in seeded random order."""
    plan = [g for g in gaps for _ in range(reps)] + ["hang30"] * reps
    random.Random(seed).shuffle(plan)
    return plan


def http_fetch(url):
    """True if the call returned 200 within the timeout, False otherwise."""
    try:
        return requests.get(url, timeout=REQUEST_TIMEOUT).status_code == 200
    except requests.exceptions.RequestException:
        return False


def _wait_until(clock, target):
    remaining = target - clock.monotonic()
    if remaining > 0:
        clock.sleep(remaining)


def run_trial(arm, fetch, urls, clock):
    """Run one trial and return a result row. ok is None if nothing was measured."""
    url = iter(urls * 10)
    result = {"arm": arm, "ok": None, "first_call_attempts": 0}

    # Første kald skal lykkes, ellers er der ingen succes at måle afstanden fra.
    for attempt in range(FIRST_CALL_MAX_ATTEMPTS):
        if attempt:
            clock.sleep(FIRST_CALL_RETRY_PAUSE)
        result["first_call_attempts"] = attempt + 1
        first_start = clock.monotonic()
        if fetch(next(url)):
            break
    else:
        return result

    if arm == "hang30":
        _wait_until(clock, first_start + HANG30_FIRST_GAP)
        hung = not fetch(next(url))
        result["hung"] = hung
        if not hung:
            return result
        clock.sleep(30)
    else:
        _wait_until(clock, first_start + arm)

    start = clock.monotonic()
    result["since_success_s"] = start - first_start
    result["ok"] = fetch(next(url))
    result["duration_s"] = round(clock.monotonic() - start, 1)
    return result


def run_probe(plan, fetch, urls, clock, log=print):
    results = []
    for i, arm in enumerate(plan):
        if i:
            clock.sleep(RESET_SECONDS)
        row = run_trial(arm, fetch, urls, clock)
        log("PROBE " + json.dumps(row))
        results.append(row)
    return results


def summarize(rows):
    """{arm: (measured, failed)}, counting only trials that measured something."""
    out = {}
    for row in rows:
        if row["ok"] is None:
            continue
        n, failed = out.get(str(row["arm"]), (0, 0))
        out[str(row["arm"])] = (n + 1, failed + (not row["ok"]))
    return out


def main():
    from termik.fetch_weather import ALL_POINTS, build_api_url

    reps = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    urls = [build_api_url(ALL_POINTS[i:i + 10]) for i in range(0, len(ALL_POINTS), 10)]
    plan = plan_trials(GAPS, reps)
    print(f"Plan ({len(plan)} trials): {plan}", flush=True)
    rows = run_probe(plan, http_fetch, urls, time, log=lambda s: print(s, flush=True))
    for arm, (n, failed) in sorted(summarize(rows).items()):
        print(f"SUMMARY arm={arm} measured={n} failed={failed}")


if __name__ == "__main__":
    main()
