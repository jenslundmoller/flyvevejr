"""Kørselsplanen for forecast-workflowet (besluttet 2026-10-05).

Hver 3. time, ingen kørsler mellem 20 og 05 UTC (ingen kigger om natten),
men en frisk prognose om morgenen. Læses med regex, ikke yaml, så testen
ikke kræver en pakke runneren ellers ikke har.
"""

import re
from pathlib import Path

WORKFLOWS = Path(__file__).resolve().parents[2] / ".github" / "workflows"


def cron_lines(name):
    return re.findall(r"-\s*cron:\s*'([^']+)'", (WORKFLOWS / name).read_text(encoding="utf-8"))


def expand(field, lo, hi):
    out = set()
    for part in field.split(","):
        step = 1
        if "/" in part:
            part, step = part.split("/")
            step = int(step)
        if part == "*":
            a, b = lo, hi
        elif "-" in part:
            a, b = map(int, part.split("-"))
        else:
            a = b = int(part)
        out |= set(range(a, b + 1, step))
    return out


NIGHT = set(range(20, 24)) | set(range(0, 5))


def run_hours(name):
    hours = set()
    for line in cron_lines(name):
        hours |= expand(line.split()[1], 0, 23)
    return hours


def test_forecast_runs_every_third_hour_during_the_day():
    assert run_hours("update-forecast.yml") == {5, 8, 11, 14, 17}


def test_no_forecast_runs_at_night():
    assert not run_hours("update-forecast.yml") & NIGHT


def test_first_run_is_early_morning():
    assert min(run_hours("update-forecast.yml")) == 5


def test_fallback_watches_while_runs_can_be_queued():
    # Sidste kørsel startes ~17:15-17:45; vagthunden skal nå at se den stå
    # 15 min i kø, og den skal ikke køre om natten.
    hours = run_hours("forecast-fallback.yml")
    assert {5, 17, 18} <= hours
    assert not hours & NIGHT
