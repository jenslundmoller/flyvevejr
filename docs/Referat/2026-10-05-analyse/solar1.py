"""Punkt 1: læser score_solar en god dags egne cumulus som dæmpning?"""
import json, pickle, sys
sys.path.insert(0, '/home/jens/AI/Flyvevejr')
from termik.locations import AIRFIELDS
from termik.fetch_weather import process_point_hour
import termik.scoring_v2 as v2
from termik.config import WEIGHTS_V2
S = 'analyse-data'
P = {p['id']: p for p in AIRFIELDS}
H = pickle.load(open(f'{S}/hist_full.pkl', 'rb'))
def hourly(pid, day):
    for (p, a), h in H.items():
        if p == pid and h['time'][0][:10] <= day <= h['time'][-1][:10]: return h
comp = {}
f = v2.score_solar_v2
def w(*a, **k):
    r = f(*a, **k); comp['solar'] = r; comp['args'] = (a, k); return r
v2.score_solar_v2 = w
R = json.load(open(f'{S}/limit_rows.json'))
rows = []
for r in R:
    if not (r['soared'] or r['short']): continue
    h = hourly(r['pid'], r['day']); i = h['time'].index(f"{r['day']}T{r['hr']:02d}:00")
    res = process_point_hour(dict(P[r['pid']]), h, i, month=int(r['day'][5:7]))
    g = lambda k: h[k][i]
    rows.append(dict(pid=r['pid'], day=r['day'], hr=r['hr'], soared=r['soared'], score=res['score'], solar=comp['solar'],
        low=g('cloud_cover_low'), mid=g('cloud_cover_mid'), high=g('cloud_cover_high'), tot=g('cloud_cover'),
        direct=g('direct_radiation'), sw=g('shortwave_radiation'), binding=r['binding'],
        scale=comp['args'][1].get('radiation_scale', 1.0)))
json.dump(rows, open(f'{S}/solar_rows.json', 'w'))
def table(title, rs, key, bins):
    print(f"\n{title}  (n={len(rs)})")
    print(f"  {'bin':<10} {'n':>4} {'bar':>5} {'solar':>6} {'score':>6} {'direct':>7} {'cap binds':>9}")
    for lo, hi in bins:
        b = [x for x in rs if x[key] is not None and lo <= x[key] < hi]
        if not b: continue
        m = lambda k: sum(x[k] for x in b) / len(b)
        print(f"  {lo:>3}-{hi:<5} {len(b):>4} {100*sum(x['soared'] for x in b)/len(b):>4.0f}% {m('solar'):>6.1f} {m('score'):>6.1f} {m('direct'):>7.0f} {sum(bool(x['binding']) for x in b):>9}")
print(f"alle timer med facit: {len(rows)}, bar {100*sum(x['soared'] for x in rows)/len(rows):.0f}%")
cu = [x for x in rows if (x['mid'] or 0) < 30 and (x['high'] or 0) < 50]
table("Cumulus-regime (mid < 30, høj < 50), efter lav sky %", cu, 'low', [(0,10),(10,25),(25,40),(40,55),(55,70),(70,85),(85,101)])
table("Cumulus-regime, efter direkte stråling W/m²", cu, 'direct', [(0,150),(150,250),(250,350),(350,450),(450,550),(550,700),(700,1200)])
nocap = [x for x in cu if not x['binding']]
table("Cumulus-regime uden bindende loft, efter lav sky %", nocap, 'low', [(0,10),(10,25),(25,40),(40,55),(55,70),(70,85),(85,101)])
