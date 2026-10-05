import json, time, requests, pickle, os, sys
sys.path.insert(0,'/home/jens/AI/Flyvevejr')
from termik.locations import AIRFIELDS
from termik.config import HOURLY_PARAMS
S='analyse-data'
P={p['id']:p for p in AIRFIELDS}
pids=['ringsted','kalundborg','goerloese','kongsted','frederikssund','saeby','aarhus','silkeborg','bolhede','kolding','aars','viborg','skive','lolland','herning','holstebro','arnborg','vejle']
out=pickle.load(open(f'{S}/hist_full.pkl','rb')) if os.path.exists(f'{S}/hist_full.pkl') else {}
for pid in pids:
    for a,b in [('2026-05-15','2026-06-22'),('2026-07-10','2026-08-24'),('2026-10-02','2026-10-04')]:
        k=(pid,a)
        if k in out: continue
        while True:
            try:
                r=requests.get('https://historical-forecast-api.open-meteo.com/v1/forecast',params=dict(latitude=P[pid]['lat'],longitude=P[pid]['lon'],hourly=','.join(HOURLY_PARAMS),start_date=a,end_date=b,timezone='Europe/Copenhagen',wind_speed_unit='kn'),timeout=180).json()
            except Exception as e:
                r={'reason':str(e)}
            if 'hourly' in r: break
            print('wait',pid,a,r.get('reason'),flush=True); time.sleep(65)
        out[k]=r['hourly']; pickle.dump(out,open(f'{S}/hist_full.pkl','wb')); print('ok',pid,a,flush=True); time.sleep(8)
print('DONE',flush=True)
