import sys; sys.path.insert(0, "/home/jens/AI/Flyvevejr")
import time, requests, pickle, os
from termik.locations import AIRFIELDS
from termik.config import HOURLY_PARAMS
f='analyse-data/wx.pkl'
out=pickle.load(open(f,'rb')) if os.path.exists(f) else {}
for p in AIRFIELDS:
    if p['id'] in out or p['id'].startswith('arnborg_') or p['id']=='eskebjerg_polyt': continue
    while True:
        try:
            r=requests.get('https://historical-forecast-api.open-meteo.com/v1/forecast',params=dict(latitude=p['lat'],longitude=p['lon'],hourly=','.join(HOURLY_PARAMS),start_date='2026-05-18',end_date='2026-10-04',timezone='Europe/Copenhagen',wind_speed_unit='kn'),timeout=240).json()
            if 'hourly' in r: break
            print('wait',r.get('reason'),flush=True)
        except Exception as e: print('err',e,flush=True)
        time.sleep(65)
    out[p['id']]=r['hourly']; pickle.dump(out,open(f,'wb')); print('ok',p['id'],flush=True); time.sleep(8)
print('DONE',len(out))
