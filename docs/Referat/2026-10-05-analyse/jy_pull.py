import sys; sys.path.insert(0, "/home/jens/AI/Flyvevejr")
import json, time, requests, pickle, os
from termik.locations import AIRFIELDS, SEA_POINTS
from termik.config import HOURLY_PARAMS, MARINE_API_URL
W='analyse-data'
P={p['id']:p for p in AIRFIELDS}
pids=['silkeborg','kolding','aarhus','viborg','arnborg','saeby','bolhede','aars','skive','herning','holstebro']
f=f'{W}/hist.pkl'
out=pickle.load(open(f,'rb')) if os.path.exists(f) else {}
def get(url,params):
    while True:
        try:
            r=requests.get(url,params=params,timeout=180).json()
            if 'hourly' in r: return r['hourly']
            print('wait',r.get('reason'),flush=True)
        except Exception as e: print('err',e,flush=True)
        time.sleep(65)
for pid in pids:
    if pid in out: continue
    p=P[pid]
    h=get('https://historical-forecast-api.open-meteo.com/v1/forecast',dict(latitude=p['lat'],longitude=p['lon'],hourly=','.join(HOURLY_PARAMS),start_date='2026-07-03',end_date='2026-09-27',timezone='Europe/Copenhagen',wind_speed_unit='kn'))
    sst={}
    if p.get('sea_cell') is not None:
        lat,lon=SEA_POINTS['cells'][p['sea_cell']]
        m=get(MARINE_API_URL,dict(latitude=lat,longitude=lon,hourly='sea_surface_temperature',start_date='2026-07-03',end_date='2026-09-27',timezone='Europe/Copenhagen'))
        sst={t[:10]:v for t,v in zip(m['time'],m['sea_surface_temperature']) if t[11:13]=='13'}
    out[pid]=dict(hourly=h,sst=sst); pickle.dump(out,open(f,'wb')); print('ok',pid,len(sst),flush=True); time.sleep(8)
print('DONE')
