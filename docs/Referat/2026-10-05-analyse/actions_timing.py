"""Punkt 13: timing af Open-Meteo-kaldene i update-forecast-loggene.

Hent loggene først (fra repo-roden):
  mkdir -p analyse-data/logs
  for id in $(gh run list --workflow update-forecast.yml --limit 200 \
      --created ">=2026-10-01" --json databaseId,status \
      -q '.[]|select(.status=="completed")|.databaseId'); do
    gh run view $id --log > analyse-data/logs/$id.log; done
  python3 actions_timing.py analyse-data/logs

"Batch n/27 ok in X s" er inkl. genforsøg og backoff; scriptet trækker de
fejlede forsøg og ventetiden fra, så kun det vellykkede forsøg tælles.
Kørsler fra før loglinjerne fik varighed (1/10 morgen) springes over.
"""
import collections
import glob
import re
import sys
from datetime import datetime


def ts(line):
    return datetime.fromisoformat(re.search(r"(\d{4}-\d\d-\d\dT[\d:.]+)Z", line)[1][:26]).timestamp()


def attempts(path):
    """[(start, end, ok, attempt_no)] for alle kald i én kørsel (ekskl. redningsrunden)."""
    lines = [l for l in open(path, encoding="utf-8", errors="ignore")
             if ("Batch" in l and "sweep" not in l) or "API request failed after" in l]
    if not any(" ok in " in l for l in lines):
        return None
    run, pend, k = [], 0.0, 0
    for l in lines:
        t = ts(l)
        m = re.search(r"failed after ([\d.]+)s.*retrying in (\d+)s", l)
        if m:
            run.append((t - float(m[1]), t, False, k))
            pend += float(m[1]) + int(m[2])
            k += 1
            continue
        m = re.search(r"ok in ([\d.]+)s", l)
        if m:
            d = float(m[1]) - pend
            run.append((t - d, t, True, k))
        pend, k = 0.0, 0
    return run


def pct(x, p):
    x = sorted(x)
    return x[min(len(x) - 1, int(p * len(x)))]


runs = [r for r in (attempts(f) for f in sorted(glob.glob(sys.argv[1] + "/*.log"))) if r]
ok = [e - s for r in runs for s, e, o, _ in r if o]
bad = [e - s for r in runs for s, e, o, _ in r if not o]
print(f"{len(runs)} kørsler, {len(ok)} vellykkede og {len(bad)} fejlede forsøg")
print(f"vellykket: p50 {pct(ok, .5):.1f} p90 {pct(ok, .9):.1f} p99 {pct(ok, .99):.1f} max {max(ok):.1f} s")
print(f"fejlet:    p50 {pct(bad, .5):.1f} p90 {pct(bad, .9):.1f} max {max(bad):.1f} s, "
      f"{sum(30 <= v < 30.5 for v in bad)} på 30.0-30.5 s")
for lo, hi in [(0, 1), (1, 2), (2, 10), (10, 25), (25, 60)]:
    print(f"  vellykket {lo}-{hi} s: {sum(lo <= v < hi for v in ok)}")

per_try = collections.defaultdict(lambda: [0, 0])
for r in runs:
    for _, _, o, k in r:
        per_try[k][0] += 1
        per_try[k][1] += not o
print("fejlrate pr. forsøg:", {k + 1: f"{f}/{n} = {f / n:.0%}" for k, (n, f) in sorted(per_try.items())})

gap = collections.defaultdict(lambda: [0, 0])
for r in runs:
    for i, (s, _, o, _) in enumerate(r):
        prev = [x for x in r[:i] if x[2]]
        if prev:
            b = min(int((s - prev[-1][0]) // 5) * 5, 200)
            gap[b][0] += 1
            gap[b][1] += not o
print("tid siden forrige vellykkede kald startede -> fejlrate (kun spande med n >= 20):")
for b, (n, f) in sorted(gap.items()):
    if n >= 20:
        label = f"{b}-{b + 5} s" if b < 200 else ">= 200 s"
        print(f"  {label}: n={n} fejl={f / n:.0%}")
