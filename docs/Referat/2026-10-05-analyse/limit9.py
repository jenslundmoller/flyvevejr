"""Punkt 9: hvilket loft sætter scoren, time for time, med nuværende kode."""
import json, pickle, sys
from collections import Counter, defaultdict
sys.path.insert(0, '/home/jens/AI/Flyvevejr')
from termik.locations import AIRFIELDS
from termik.fetch_weather import process_point_hour
import termik.scoring_v2 as v2
from termik.config import *
S = sys.argv[1] if len(sys.argv) > 1 else "analyse-data"
P = {p['id']: p for p in AIRFIELDS}
H = pickle.load(open(f'{S}/hist_full.pkl', 'rb'))
def hourly(pid, day):
    for (p, a), h in H.items():
        if p == pid and h['time'][0][:10] <= day <= h['time'][-1][:10]: return h
cap = {}; comp = {}
real = v2.apply_dealbreakers_v2
def spy(score, lapse_rate, cloud_cover, precipitation, wind_kt, wind_gusts_kt, temp, **k):
    cap['a'] = dict(raw=score, lapse=lapse_rate, cc=cloud_cover, precip=precipitation, wind=wind_kt, gust=wind_gusts_kt, temp=temp, **k)
    return real(score, lapse_rate, cloud_cover, precipitation, wind_kt, wind_gusts_kt, temp, **k)
v2.apply_dealbreakers_v2 = spy
for name, key in [('score_lapse_rate','lapse_rate'),('score_solar_v2','solar'),('score_spread','spread'),('score_wind_v2','wind'),('score_gusts','gusts'),('score_temperature','temperature'),('score_precipitation','precipitation')]:
    f = getattr(v2, name)
    def w(*a, _f=f, _k=key, **k):
        r = _f(*a, **k); comp[_k] = r; return r
    setattr(v2, name, w)

def caps_for(a):
    """Alle lofter der rammer timen, i samme rækkefølge som apply_dealbreakers_v2."""
    c = []; sc = a.get('radiation_scale', 1.0)
    if a.get('shortwave_radiation') is not None:
        eff = v2.effective_radiation_v2(a['shortwave_radiation'], a.get('trailing_radiation'), cloud_cover=a['cc'], trailing_cloud_cover=a.get('trailing_cloud_cover'), temp_850hpa_trend=a.get('temp_850hpa_trend', 0), radiation_scale=sc)
        g = [cv for t, cv in RADIATION_GATE if eff < t * sc]
        if g: c.append(('radiation', min(g)))
    if a.get('boundary_layer_height') is not None and a['boundary_layer_height'] < SHALLOW_BOUNDARY_LAYER_M: c.append(('shallow_bl', SHALLOW_BOUNDARY_LAYER_MAX_SCORE))
    L = a['lapse']
    if L < 0.5: c.append(('stable', 1))
    elif L < 0.65: c.append(('stable', 3))
    elif L < 0.70: c.append(('stable', 5))
    sl = a.get('surface_lapse_rate')
    if sl is not None and sl < 0.3: c.append(('surface_stable', 1))
    elif sl is not None and sl < 0.5: c.append(('surface_stable', 2))
    if a['cc'] >= OVERCAST_COVER: c.append(('overcast', OVERCAST_MAX_SCORE))
    hi = a.get('cloud_cover_high')
    if hi is not None and hi >= CIRRUS_SHIELD_PRESENT_MIN and max([hi] + list(a.get('trailing_cirrus') or [])) >= CIRRUS_SHIELD_THRESHOLD: c.append(('cirrus', CIRRUS_SHIELD_MAX_SCORE))
    if (a.get('cloud_cover_mid') or 0) >= MID_LEVEL_DECK_THRESHOLD: c.append(('mid_cloud', MID_LEVEL_DECK_MAX_SCORE))
    if a['precip'] > 0: c.append(('rain', 1))
    ew = a['wind'] + a['gust'] / 2; wc = []
    if a['wind'] > 35: wc.append(2)
    if a['gust'] >= 35: wc.append(1)
    elif a['gust'] >= 30: wc.append(2)
    if ew > 35: wc.append(1)
    elif ew > 30: wc.append(2)
    elif ew > 25: wc.append(4)
    if wc: c.append(('wind', min(wc)))
    if a['temp'] < 5: c.append(('cold', 3))
    if a['cape'] > 1500: c.append(('cape', 5))
    elif a['cape'] > 1000: c.append(('cape', 7))
    if a.get('thermal_top_cap') is not None: c.append(('low_top', a['thermal_top_cap']))
    return c

R = json.load(open(f'{S}/cirrus_rows2.json'))
out = []
for r in R:
    h = hourly(r['pid'], r['day'])
    if h is None: continue
    i = [k for k, t in enumerate(h['time']) if t == f"{r['day']}T{r['hr']:02d}:00"][0]
    res = process_point_hour(dict(P[r['pid']]), h, i, month=int(r['day'][5:7]))
    a = cap['a']; c = caps_for(a); final = res['score']
    pen = a['raw'] - (OVERCAST_PENALTY if a['cc'] >= OVERCAST_COVER else 0)
    m = min([v for _, v in c], default=10)
    binding = [n for n, v in c if v == m] if m < pen and final < 10 else []
    weak = max(WEIGHTS_V2, key=lambda k: WEIGHTS_V2[k] * (10 - comp[k]))
    out.append(dict(r, final=final, raw=round(a['raw'], 2), caps=c, binding=binding, weakest=weak,
                    seabreeze=res['data'].get('seabreeze_penalty') if 'data' in res else None))
json.dump(out, open(f'{S}/limit_rows.json', 'w'))
lab = [r for r in out if r['soared'] or r['short']]
print(f"{len(out)} timer kl. 11-17 ({len(lab)} med facit)")
nb = [r for r in out if r['binding']]
print(f"loft binder: {len(nb)}/{len(out)} = {len(nb)/len(out):.0%}; flere lofter på samme værdi: {sum(len(r['binding'])>1 for r in nb)}")
cnt = Counter(' + '.join(r['binding']) for r in nb)
print("\nbindende loft -> timer, heraf bar / kort")
for k, n in cnt.most_common():
    s = sum(r['soared'] for r in nb if ' + '.join(r['binding']) == k); t = sum(r['short'] for r in nb if ' + '.join(r['binding']) == k)
    print(f"  {k:<28} {n:>4}   {s:>3} / {t}")
fr = [r for r in out if not r['binding']]
print("\nintet loft: svageste vægtede komponent -> timer (score-median)")
for k, n in Counter(r['weakest'] for r in fr).most_common():
    sc = sorted(r['final'] for r in fr if r['weakest'] == k)
    print(f"  {k:<14} {n:>4}  median {sc[len(sc)//2]}")
print("\nkun timer med score < 6.5:")
low = [r for r in out if r['final'] < 6.5]
print(f"  {len(low)} timer; loft binder i {sum(bool(r['binding']) for r in low)}")
for k, n in Counter((' + '.join(r['binding']) or 'intet loft: ' + r['weakest']) for r in low).most_common(12): print(f"    {k:<36} {n}")
