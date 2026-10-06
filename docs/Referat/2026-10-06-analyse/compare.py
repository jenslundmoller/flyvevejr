import sys; sys.path.insert(0, "/home/jens/AI/Flyvevejr")
import sqlite3, pickle, json, math, collections
from datetime import datetime
from zoneinfo import ZoneInfo
from termik.locations import AIRFIELDS
from termik.fetch_weather import process_point_hour
S='analyse-data'
TZ=ZoneInfo('Europe/Copenhagen'); R_KM=20
WX=pickle.load(open(f'{S}/wx.pkl','rb'))
P=[p for p in AIRFIELDS if p['id'] in WX]
def km(a,b,c,d):
    x=math.radians(d-b)*math.cos(math.radians((a+c)/2)); y=math.radians(c-a); return 6371*math.hypot(x,y)
c=sqlite3.connect(f'file:{S}/fr_prod.db?mode=ro',uri=True)
groups=collections.defaultdict(list)
for fid,st,et,sa,ea,lat,lon,climb in c.execute('select flight_id,start_ts,end_ts,start_alt,end_alt,lat,lon,avg_climb_ms from thermals'):
    best=min(P,key=lambda p:km(lat,lon,p['lat'],p['lon']))
    if km(lat,lon,best['lat'],best['lon'])>R_KM: continue
    t=datetime.fromtimestamp(et,TZ)
    if not 10<=t.hour<=18: continue
    groups[(best['id'],t.strftime('%Y-%m-%d'),t.hour)].append((ea,fid,climb,ea-sa))
idx={pid:{t:i for i,t in enumerate(WX[pid]['time'])} for pid in WX}
PP={p['id']:p for p in P}
rows=[]
for (pid,d,h),th in groups.items():
    if len(th)<3 or len({x[1] for x in th})<2: continue
    i=idx[pid].get(f'{d}T{h:02d}:00')
    if i is None: continue
    r=process_point_hour(PP[pid],WX[pid],i,month=int(d[5:7])); dd=r['data']
    alts=sorted(x[0] for x in th)
    p90=alts[min(len(alts)-1,int(round(0.9*(len(alts)-1))))]
    base=[v for v in (dd['lcl_m'],dd['ti_zero_m']) if v is not None]
    rows.append(dict(pid=pid,day=d,hour=h,n=len(th),nf=len({x[1] for x in th}),obs_p90=p90,obs_max=alts[-1],obs_med=alts[len(alts)//2],
        climb=sum(x[2] for x in th)/len(th),elev=PP[pid].get('elevation_m',0),
        top=dd['thermal_top_m'],lcl=dd['lcl_m'],ti=dd['ti_zero_m'],base=min(base) if base else None,lim=dd['thermal_top_limited_by'],
        score=r['score'],bl=dd['boundary_layer_height'],cc=dd['cloud_cover'],sw=dd['shortwave_radiation']))
json.dump(rows,open(f'{S}/rows.json','w'))
print(len(rows),'site-hours', len({(r['pid'],r['day']) for r in rows}),'site-days', len({r['day'] for r in rows}),'days')
