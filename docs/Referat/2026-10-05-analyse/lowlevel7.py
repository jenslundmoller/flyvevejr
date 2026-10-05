"""Punkt 7: giver icon/dmi-lavniveaufelter information ud over produktionens score?

Metrik: AUC bar mod kort, dels alene, dels inden for produktionens scorebånd
(parvis kun mellem timer i samme bånd). 0.5 = ingen ekstra information.
"""
import json, pickle, sys
sys.path.insert(0, '/home/jens/AI/Flyvevejr')
from termik.locations import AIRFIELDS
from termik.fetch_weather import process_point_hour
from termik.scoring import compute_thermal_top
S = 'analyse-data'
P = {p['id']: p for p in AIRFIELDS}
H = pickle.load(open(f'{S}/hist_full.pkl', 'rb'))
M = pickle.load(open(f'{S}/hist_models.pkl', 'rb'))
def find(pid, day, model=None):
    src = H if model is None else {k[:2]: v for k, v in M.items() if k[2] == model}
    for (p, a), h in src.items():
        if p == pid and h['time'][0][:10] <= day <= h['time'][-1][:10]: return h
R = json.load(open(f'{S}/solar_rows.json'))
BANDS = [(0, 3), (3, 5), (5, 6.5), (6.5, 8), (8, 11)]
def auc(pos, neg):
    if not pos or not neg: return None, 0
    w = sum((p > n) + 0.5 * (p == n) for p in pos for n in neg)
    return w / (len(pos) * len(neg)), len(pos) * len(neg)
def report(name, key, rows, higher_is_better=True):
    rs = [r for r in rows if r.get(key) is not None]
    sgn = 1 if higher_is_better else -1
    a, _ = auc([sgn * r[key] for r in rs if r['soared']], [sgn * r[key] for r in rs if not r['soared']])
    num = den = 0
    for lo, hi in BANDS:
        b = [r for r in rs if lo <= r['score'] < hi]
        x, n = auc([sgn * r[key] for r in b if r['soared']], [sgn * r[key] for r in b if not r['soared']])
        if x is not None: num += x * n; den += n
    print(f"  {name:<44} n={len(rs):>3}  AUC alene {a:.3f}  inden for scorebånd {num/den:.3f}")
def lapse(t_lo, z_lo, t_hi, z_hi):
    if None in (t_lo, z_lo, t_hi, z_hi) or z_hi - z_lo < 50: return None
    return (t_lo - t_hi) / (z_hi - z_lo) * 100
for r in R:
    pt = P[r['pid']]; elev = pt.get('elevation_m', 0)
    h = find(r['pid'], r['day']); i = h['time'].index(f"{r['day']}T{r['hr']:02d}:00")
    res = process_point_hour(dict(pt), h, i, month=int(r['day'][5:7]))
    r['lapse_prod'] = res['data']['lapse_rate']
    r['top_prod'] = res['data']['thermal_top_m']
    ic = find(r['pid'], r['day'], 'icon_seamless'); dm = find(r['pid'], r['day'], 'dmi_seamless')
    j = ic['time'].index(h['time'][i]); k = dm['time'].index(h['time'][i])
    g = lambda d, f, idx: d.get(f, [None] * (idx + 1))[idx]
    t2 = g(ic, 'temperature_2m', j)
    r['icon_lapse_950'] = lapse(t2, elev + 2, g(ic, 'temperature_950hPa', j), g(ic, 'geopotential_height_950hPa', j))
    r['icon_lapse_900'] = lapse(t2, elev + 2, g(ic, 'temperature_900hPa', j), g(ic, 'geopotential_height_900hPa', j))
    # laveste lags-lapse under ~1.5 km: fanger en inversion som 925/850 springer over
    prof = [(elev + 2, t2)] + [(g(ic, f'geopotential_height_{p}hPa', j), g(ic, f'temperature_{p}hPa', j)) for p in (1000, 950, 925, 900, 850)]
    prof = sorted((z, t) for z, t in prof if z is not None and t is not None and z >= elev + 2)
    layers = [lapse(t1, z1, t2_, z2) for (z1, t1), (z2, t2_) in zip(prof, prof[1:]) if z1 < 1500]
    layers = [x for x in layers if x is not None]
    r['icon_min_layer'] = min(layers) if layers else None
    r['icon_shf'] = -g(ic, 'sensible_heat_flux', j) if g(ic, 'sensible_heat_flux', j) is not None else None
    t180i = g(ic, 'temperature_180m', j); t180d = g(dm, 'temperature_180m', k)
    r['icon_sfc_lapse'] = (t2 - t180i) / 1.78 if None not in (t2, t180i) else None
    r['dmi_sfc_lapse'] = (g(dm, 'temperature_2m', k) - t180d) / 1.78 if None not in (g(dm, 'temperature_2m', k), t180d) else None
    lv = {p: g(ic, f'temperature_{p}hPa', j) for p in (950, 925, 900, 850)}
    lz = {p: g(ic, f'geopotential_height_{p}hPa', j) for p in (950, 925, 900, 850)}
    for p in (800, 700, 600):
        lv[p] = h[f'temperature_{p}hPa'][i]; lz[p] = h[f'geopotential_height_{p}hPa'][i]
    tt = compute_thermal_top(surface_temp_c=t2, surface_dewpoint_c=g(ic, 'dewpoint_2m', j),
        surface_pressure_hpa=h['surface_pressure'][i], surface_elevation_m=elev,
        level_temps_c=lv, level_heights_m=lz, shortwave_radiation=h['shortwave_radiation'][i])
    r['top_icon'] = tt['thermal_top_m']
    r['bm925_minus_icon925'] = (h['temperature_925hPa'][i] - lv[925]) if None not in (h['temperature_925hPa'][i], lv[925]) else None
print(f"{len(R)} timer med facit, bar {sum(r['soared'] for r in R)}")
print("\nReference (produktionen i dag):")
report('produktionens score', 'score', R)
report('lapse_rate (produktion)', 'lapse_prod', R)
report('termiktop (produktion)', 'top_prod', R)
report('direkte stråling (best_match)', 'direct', R)
print("\nNye felter:")
report('icon lapse 2 m -> 950 hPa', 'icon_lapse_950', R)
report('icon lapse 2 m -> 900 hPa', 'icon_lapse_900', R)
report('icon laveste lags-lapse under 1.5 km', 'icon_min_layer', R)
report('icon termiktop med 950/925/900/850', 'top_icon', R)
report('icon sensibel varmestrøm (op = +)', 'icon_shf', R)
report('icon lapse 2-180 m', 'icon_sfc_lapse', R)
report('dmi lapse 2-180 m', 'dmi_sfc_lapse', R)
for key, name in [('icon_sfc_lapse', 'icon'), ('dmi_sfc_lapse', 'dmi')]:
    for lo, hi, cap in [(-99, 0.3, 1), (0.3, 0.5, 2)]:
        b = [r for r in R if r.get(key) is not None and lo <= r[key] < hi]
        print(f"  {name} 2-180 m-cap {cap} ville ramme {len(b)} timer, bar {sum(r['soared'] for r in b)}, score i dag median {sorted(r['score'] for r in b)[len(b)//2] if b else '-'}")
d = [r['bm925_minus_icon925'] for r in R if r['bm925_minus_icon925'] is not None]
print(f"\nbest_match 925 minus icon 925: middel {sum(d)/len(d):+.2f} K, |forskel| > 1 K i {sum(abs(x) > 1 for x in d)}/{len(d)} timer")
json.dump(R, open(f'{S}/lowlevel_rows.json', 'w'))
