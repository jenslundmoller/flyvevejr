import json, pickle, time, requests
from datetime import date
from termik.locations import AIRFIELDS, SEA_POINTS
from termik.tools.replay_day import day_hour_indices
from termik.fetch_weather import process_point_hour
S='analyse-data'
P={p['id']:p for p in AIRFIELDS}
cache=pickle.load(open(f'{S}/season_cache.pkl','rb'))
R=json.load(open(f'{S}/sst_scores.json'))
cellsst={}
for pid in sorted({r['point_id'] for r in R}):
    c=P[pid].get('sea_cell')
    if c is None or c in cellsst: continue
    la,lo=SEA_POINTS['cells'][c]
    h=requests.get('https://marine-api.open-meteo.com/v1/marine',params=dict(latitude=la,longitude=lo,hourly='sea_surface_temperature',start_date='2026-07-06',end_date='2026-10-04',timezone='Europe/Copenhagen'),timeout=60).json()['hourly']
    cellsst[c]={t[:10]:v for t,v in zip(h['time'],h['sea_surface_temperature']) if t[11:13]=='13'}; time.sleep(1.5)
BAND={'staerk':(7.5,10),'god':(6.5,10),'mulig':(4.5,8.5),'svag':(0,6)}
err=lambda v,l:max(0,BAND[l][0]-v,v-BAND[l][1])
for r in R:
    hourly,_=cache[r['point_id']]; d=date.fromisoformat(r['day']); pt=dict(P[r['point_id']])
    for tag in ('final','final_clim'):
        q=dict(pt)
        if tag=='final' and pt.get('sea_cell') is not None:
            v=cellsst[pt['sea_cell']].get(r['day'])
            if v is not None: q['sea_temp_c']=v
        sc=sorted((process_point_hour(q,hourly,i,month=d.month)['score'] for i in day_hour_indices(hourly,d) if 11<=int(hourly['time'][i][11:13])<=18),reverse=True)
        r[tag]=round(sum(sc[:3])/3,1)
for grp,fl in [('summer',lambda r:not r.get('new')),('oct',lambda r:r.get('new'))]:
    rs=[r for r in R if fl(r)]
    for tag,name in (('base','before fixes'),('table','fix 1-3 (live)'),('final','+ measured SST'),('final_clim','+ climatology only')):
        e=[err(r[tag if tag!='base' else 'base_top3'],r['label']) for r in rs]
        key=tag if tag!='base' else 'base_top3'
        g=[r[key] for r in rs if r['label']!='svag']; w=[r[key] for r in rs if r['label']=='svag']
        print(f"{grp:<7}{name:<19} in-band {sum(x==0 for x in e):>2}/{len(rs)} dev {sum(e):5.1f} worst {max(e):.1f} sep {sum(g)/len(g)-sum(w)/len(w):.2f}")
print()
for r in R:
    if abs(r['final']-r['table'])>=0.4:
        print(r['day'],f"{r['plads']:<20}{r['label']:<7}{r['signal_longest']:>4}m  live {r['table']:>4} -> measured {r['final']:>4}   (before fixes {r['base_top3']})")
json.dump(R,open(f'{S}/validate_sst.json','w'),ensure_ascii=False)
