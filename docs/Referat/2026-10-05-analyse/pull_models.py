"""Punkt 7: lavniveau-felter fra icon_seamless og dmi_seamless for startlist-dagene."""
import time, requests, pickle, os, sys
sys.path.insert(0, '/home/jens/AI/Flyvevejr')
from termik.locations import AIRFIELDS
S = 'analyse-data'
P = {p['id']: p for p in AIRFIELDS}
H = pickle.load(open(f'{S}/hist_full.pkl', 'rb'))
FIELDS = {
    'icon_seamless': 'temperature_2m,dewpoint_2m,temperature_1000hPa,temperature_950hPa,temperature_925hPa,temperature_900hPa,temperature_850hPa,'
                     'geopotential_height_1000hPa,geopotential_height_950hPa,geopotential_height_925hPa,geopotential_height_900hPa,geopotential_height_850hPa,'
                     'temperature_180m,sensible_heat_flux,shortwave_radiation,direct_radiation',
    'dmi_seamless': 'temperature_2m,temperature_180m,boundary_layer_height',
}
f = f'{S}/hist_models.pkl'
out = pickle.load(open(f, 'rb')) if os.path.exists(f) else {}
ends = {k: h['time'][-1][:10] for k, h in H.items()}
for (pid, a), b in sorted(ends.items()):
    for model, fields in FIELDS.items():
        k = (pid, a, model)
        if k in out: continue
        while True:
            try:
                r = requests.get('https://historical-forecast-api.open-meteo.com/v1/forecast', params=dict(
                    latitude=P[pid]['lat'], longitude=P[pid]['lon'], hourly=fields, models=model,
                    start_date=a, end_date=b, timezone='Europe/Copenhagen'), timeout=180).json()
            except Exception as e:
                r = {'reason': str(e)}
            if 'hourly' in r: break
            print('wait', pid, a, model, r.get('reason'), flush=True); time.sleep(65)
        out[k] = r['hourly']; pickle.dump(out, open(f, 'wb')); print('ok', pid, a, model, flush=True); time.sleep(8)
print('DONE', flush=True)
