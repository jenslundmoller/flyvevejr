import sys; sys.path.insert(0, "/home/jens/AI/Flyvevejr")
import json, time, requests, pickle, os
from termik.locations import AIRFIELDS, SEA_POINTS
from termik.config import HOURLY_PARAMS, MARINE_API_URL
W='analyse-data'
P={p['id']:p for p in AIRFIELDS}
def get(url,params):
    while True:
        try:
            r=requests.get(url,params=params,timeout=180).json()
            if 'hourly' in r: return r['hourly']
            print('wait',r.get('reason'),flush=True)
        except Exception as e: print('err',e,flush=True)
        time.sleep(65)
def pull(fname,pids,a,b):
    f=f'{W}/{fname}'
    out=pickle.load(open(f,'rb')) if os.path.exists(f) else {}
    for pid in pids:
        if pid in out: continue
        p=P[pid]
        h=get('https://historical-forecast-api.open-meteo.com/v1/forecast',dict(latitude=p['lat'],longitude=p['lon'],hourly=','.join(HOURLY_PARAMS),start_date=a,end_date=b,timezone='Europe/Copenhagen',wind_speed_unit='kn'))
        sst={}
        if p.get('sea_cell') is not None:
            lat,lon=SEA_POINTS['cells'][p['sea_cell']]
            m=get(MARINE_API_URL,dict(latitude=lat,longitude=lon,hourly='sea_surface_temperature',start_date=a,end_date=b,timezone='Europe/Copenhagen'))
            sst={t[:10]:v for t,v in zip(m['time'],m['sea_surface_temperature']) if t[11:13]=='13'}
        out[pid]=dict(hourly=h,sst=sst); pickle.dump(out,open(f,'wb')); print('ok',fname,pid,flush=True); time.sleep(8)
pull('hist.pkl',['goerloese','frederikssund','kalundborg','kongsted','ringsted','lolland'],'2026-07-03','2026-09-27')
oct_ids=sorted({json.loads(l)['point_id'] for l in open('/home/jens/AI/Flyvevejr/docs/Referat/2026-10-05-startlist-weekend.jsonl')})
pull('hist_oct.pkl',oct_ids,'2026-10-02','2026-10-04')
print('DONE')
