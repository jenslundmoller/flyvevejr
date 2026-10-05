import sys; sys.path.insert(0, "/home/jens/AI/Flyvevejr")
import json, pickle, collections
from termik.locations import AIRFIELDS
from termik.fetch_weather import process_point_hour
W='analyse-data'
P={p['id']:p for p in AIRFIELDS}
M={'True':'aarhus','Sæby':'saeby','Viborg':'viborg','Vesthimmerland/Aars':'aars','Arnborg':'arnborg','Christianshede':'silkeborg','Gesten':'kolding','Bolhede':'bolhede','Nørre Felding':'holstebro','Skinderholm':'herning','Skive':'skive'}
B={'staerk':(7.5,10),'god':(6.5,10),'mulig':(4.5,8.5),'svag':(0,6)}
H=pickle.load(open(f'{W}/hist.pkl','rb'))
F=json.load(open(f'{W}/facit.json'))
rows=[]
for f in F:
    pid=M.get(f['field'])
    if not pid or f['label']=='tynd': continue
    h=H[pid]['hourly']; p=dict(P[pid]); st=H[pid]['sst'].get(f['day'])
    if st is not None: p['sea_temp_c']=st
    hrs={}
    for i,t in enumerate(h['time']):
        if t.startswith(f['day']) and 11<=int(t[11:13])<=18:
            r=process_point_hour(p,h,i,month=int(t[5:7]))
            hrs[int(t[11:13])]=dict(s=r['score'],lim=r['data'].get('limited_by'),cc=r['data']['cloud_cover'])
    best=sorted(hrs.values(),key=lambda x:-x['s'])[:3]
    m=sum(x['s'] for x in best)/3
    lo,hi=B[f['label']]; err=max(0,lo-m,m-hi)
    lims=collections.Counter(c for x in hrs.values() for c in (x['lim'] or []))
    rows.append(dict(day=f['day'],field=f['field'],label=f['label'],longest=f['longest'],o60=f['o60'],score=round(m,2),err=round(err,2),lims=dict(lims),cc=[x['cc'] for x in hrs.values()]))
json.dump(rows,open(f'{W}/rows.json','w'),ensure_ascii=False,indent=0)
print(len(rows))
