"""Punkt 1: varianter af score_solar_v2, time- og dagsvalidering (mønster: ccvar.py)."""
import json, pickle, sys
sys.path.insert(0, '/home/jens/AI/Flyvevejr')
from datetime import date
from termik.locations import AIRFIELDS
from termik.fetch_weather import process_point_hour
from termik.tools.replay_day import day_hour_indices
import termik.scoring_v2 as v2
S = 'analyse-data'
P = {p['id']: p for p in AIRFIELDS}
H = pickle.load(open(f'{S}/hist_full.pkl', 'rb'))
def hourly(pid, day):
    for (p, a), h in H.items():
        if p == pid and h['time'][0][:10] <= day <= h['time'][-1][:10]: return h
real = v2.score_solar_v2
def make(allow=40, cloud_w=0.4, low_w=1.0):
    def solar(cloud_cover, shortwave_radiation, cloud_cover_low=None, cloud_cover_mid=None,
              cloud_cover_high=None, direct_radiation=None, radiation_scale=1.0):
        if cloud_cover_low is None or cloud_cover_mid is None or cloud_cover_high is None:
            eff = cloud_cover
        else:
            eff = min(100.0, max(0.0, cloud_cover_low - allow) * low_w + cloud_cover_mid * 0.7 + cloud_cover_high * 0.5)
        cf = max(0.0, (100 - eff) / 100)
        rf = min(direct_radiation / (600 * radiation_scale), 1.0) if direct_radiation is not None else min(shortwave_radiation / (800 * radiation_scale), 1.0)
        return (cf * cloud_w + rf * (1 - cloud_w)) * 10
    return solar
VARIANTS = {
    'nu (allow 40)': real,
    'kopi af nu': make(),
    'allow 60': make(allow=60),
    'allow 80': make(allow=80),
    'lav sky tæller ikke': make(low_w=0.0),
    'kun direkte sol': make(cloud_w=0.0),
    'lav sky halv vægt': make(low_w=0.5),
}
only = sys.argv[1:] or list(VARIANTS)
R = [r for r in json.load(open(f'{S}/limit_rows.json')) if r['soared'] or r['short']]
cache = pickle.load(open(f'{S}/season_cache.pkl', 'rb')); sst = json.load(open(f'{S}/sst_cells.json'))
D = json.load(open(f'{S}/validate_925.json'))
BAND = {'staerk': (7.5, 10), 'god': (6.5, 10), 'mulig': (4.5, 8.5), 'svag': (0, 6)}
err = lambda v, l: max(0, BAND[l][0] - v, v - BAND[l][1])
print(f"{'variant':<20}| timer: sep   acc  | bar pr. score 0-3 / 3-5 / 5-6.5 / 6.5-8 / 8+                | dage sommer afv/i bånd sep | okt afv/i bånd sep")
out = {}
for n in only:
    v2.score_solar_v2 = VARIANTS[n]
    for r in R:
        h = hourly(r['pid'], r['day']); i = h['time'].index(f"{r['day']}T{r['hr']:02d}:00")
        r['v'] = process_point_hour(dict(P[r['pid']]), h, i, month=int(r['day'][5:7]))['score']
    s = [r['v'] for r in R if r['soared']]; t = [r['v'] for r in R if r['short']]
    acc = sum((r['v'] >= 5) == r['soared'] for r in R) / len(R)
    cal = []
    for lo, hi in [(0, 3), (3, 5), (5, 6.5), (6.5, 8), (8, 11)]:
        rs = [r for r in R if lo <= r['v'] < hi]; cal.append(f"{100*sum(r['soared'] for r in rs)//max(1,len(rs)):>2}%({len(rs):>3})")
    for d in D:
        hh, _ = cache[d['point_id']]; dd = date.fromisoformat(d['day']); q = dict(P[d['point_id']])
        x = sst.get(d['point_id'], {}).get(d['day'])
        if x is not None and q.get('sea_cell') is not None: q['sea_temp_c'] = x
        sc = sorted((process_point_hour(q, hh, i, month=dd.month)['score'] for i in day_hour_indices(hh, dd) if 11 <= int(hh['time'][i][11:13]) <= 18), reverse=True)
        d['v'] = round(sum(sc[:3]) / 3, 1)
    def f(g):
        good = [d['v'] for d in g if d['label'] != 'svag']; weak = [d['v'] for d in g if d['label'] == 'svag']
        sep = sum(good)/len(good) - sum(weak)/len(weak) if good and weak else float('nan')
        return sum(err(d['v'], d['label']) for d in g), sum(err(d['v'], d['label']) == 0 for d in g), len(g), sep
    a, b, nb, sa = f([d for d in D if not d.get('new')]); c, e, ne, se = f([d for d in D if d.get('new')])
    print(f"{n:<20}| {sum(s)/len(s)-sum(t)/len(t):.2f} {acc:.3f} | {' '.join(cal)} | {a:5.1f} {b}/{nb} {sa:.2f} | {c:5.1f} {e}/{ne} {se:.2f}", flush=True)
    out[n] = {'hours': {f"{r['pid']}|{r['day']}|{r['hr']}": r['v'] for r in R}, 'days': {f"{d['point_id']}|{d['day']}": d['v'] for d in D}}
v2.score_solar_v2 = real
json.dump(out, open(f'{S}/solarvar.json', 'w'))
