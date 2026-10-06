import sys; sys.path.insert(0, "/home/jens/AI/Flyvevejr")
# Varianter af Hcrit-fradraget mod observeret top (90 %-fraktil af end_alt),
# uden de sjællandske timer der stopper ved et luftrumsloft. Kræver rows.json
# fra compare.py.
import json, statistics as st
from datetime import date
from termik.scoring_v2 import radiation_season_factor
from termik.locations import AIRFIELDS

LAT = {p['id']: p['lat'] for p in AIRFIELDS}
SJ = {'goerloese', 'frederikssund', 'kalundborg', 'kongsted', 'ringsted', 'toelloese', 'lolland'}
R = json.load(open('analyse-data/rows.json'))
R = [r for r in R if r['lim'] != 'inversion' and r['base']]


def capped(r):
    """Sjællandske timer hvor fraktilen ligger ved loftet ~750 m eller ~1400 m."""
    return r['pid'] in SJ and (700 <= r['obs_p90'] <= 820 or 1380 <= r['obs_p90'] <= 1520)


def margin(sw, full=200, none=500, thr=600):
    if sw is None or sw <= 0:
        return none
    return full if sw >= thr else none + (sw / thr) * (full - none)


def top(r, fn):
    raw = r['base']; agl = raw - r['elev']; m = fn(r)
    if agl > 0:
        m = min(m, agl / 2)
    return max(0, raw - m)


season = lambda r: radiation_season_factor(LAT[r['pid']], date.fromisoformat(r['day']).timetuple().tm_yday)
VARIANTS = {
    'nuvaerende 200-500 @600': lambda r: margin(r['sw']),
    'saeson 100-300': lambda r: margin(r['sw'], 100, 300, 600 * season(r)),
    'fast 100': lambda r: 100,
    'fast 150': lambda r: 150,
    'intet': lambda r: 0,
}
free = [r for r in R if not capped(r)]
GROUPS = {
    'Jylland+Fyn': [r for r in R if r['pid'] not in SJ],
    'alle uden loft': free,
    'maj-aug': [r for r in free if r['day'][5:7] in ('05', '06', '07', '08')],
    'sep-okt': [r for r in free if r['day'][5:7] in ('09', '10')],
}
cap = [r for r in R if capped(r)]
for name, fn in VARIANTS.items():
    out = []
    for g, rs in GROUPS.items():
        d = [top(r, fn) - r['obs_p90'] for r in rs]
        out.append(f"{g} {st.median(d):+4.0f}/{st.mean(abs(x) for x in d):3.0f}")
    below = sum(top(r, fn) < r['obs_p90'] - 50 for r in cap) / len(cap)
    print(f"{name:24}", ' | '.join(out), f"| loft-timer under loftet: {below:.0%}")
