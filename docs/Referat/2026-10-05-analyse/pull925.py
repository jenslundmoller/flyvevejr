import json, time, requests, pickle, os
S='analyse-data'
import sys; sys.path.insert(0,'/home/jens/AI/Flyvevejr')
from termik.locations import AIRFIELDS
P={p['id']:p for p in AIRFIELDS}
D=json.load(open('/home/jens/AI/Flyvevejr/docs/Referat/2026-08-25-paalandsvind-pooled.json'))
pids=sorted({r['point_id'] for r in D})
out=pickle.load(open(f'{S}/h925.pkl','rb')) if os.path.exists(f'{S}/h925.pkl') else {}
VARS='temperature_2m,temperature_925hPa,temperature_850hPa,geopotential_height_925hPa,wind_speed_10m,wind_direction_10m'
for pid in pids:
    for (a,b) in [('2024-05-01','2024-09-30'),('2025-05-01','2025-09-30'),('2026-05-01','2026-10-04')]:
        k=(pid,a[:4])
        if k in out: continue
        while True:
            r=requests.get('https://historical-forecast-api.open-meteo.com/v1/forecast',params=dict(latitude=P[pid]['lat'],longitude=P[pid]['lon'],hourly=VARS,start_date=a,end_date=b,timezone='Europe/Copenhagen',wind_speed_unit='kn'),timeout=180).json()
            if 'hourly' in r: break
            print('wait',pid,a,r.get('reason'),flush=True); time.sleep(65)
        out[k]=r['hourly']; pickle.dump(out,open(f'{S}/h925.pkl','wb')); print('ok',pid,a,flush=True); time.sleep(6)
print('DONE')
