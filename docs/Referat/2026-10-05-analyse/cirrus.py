import json, pickle, sys
from collections import defaultdict
sys.path.insert(0,'/home/jens/AI/Flyvevejr')
from datetime import date
from termik.locations import AIRFIELDS
from termik.fetch_weather import process_point_hour
from termik.scoring_v2 import radiation_season_factor
S='analyse-data'
P={p['id']:p for p in AIRFIELDS}
M={'Arnborg':'arnborg','Christianshede':'silkeborg','Gesten':'kolding','Gørløse':'goerloese','Kalundborg':'kalundborg','Kongsted':'kongsted','Sæby':'saeby','Slaglille':'ringsted','True':'aarhus','Vesthimmerland/Aars':'aars','Viborg':'viborg','Bolhede':'bolhede','Frederikssund':'frederikssund','Skive':'skive','Maribo':'lolland','Nørre Felding':'holstebro','Skinderholm':'herning'}
H=pickle.load(open(f'{S}/hist_full.pkl','rb'))
def hourly(pid,day):
    for (p,a),h in H.items():
        if p==pid and h['time'][0][:10]<=day<=h['time'][-1][:10]: return h
F=json.load(open(f'{S}/flights.json'))
by=defaultdict(list)
for f in F:
    fl=f['field'].split(' EK')[0].split(' (')[0]
    if fl in M: by[(f['day'],M[fl])].append(f)
def mins(t): h,m=t.split(':'); return int(h)*60+int(m)
rows=[]
for (day,pid),fs in sorted(by.items()):
    planes=defaultdict(set)
    for f in fs:
        if f['pilots']: planes[f['plane']].add(f['pilots'][0])
    school={p for p,s in planes.items() if len(s)>=3}
    sig=[f for f in fs if f['plane'] not in school and f['mins'] and f['toff']]
    h=hourly(pid,day)
    if not h or not sig: continue
    idx={int(t[11:13]):i for i,t in enumerate(h['time']) if t.startswith(day)}
    for hr in range(11,18):
        i=idx[hr]; hi=h['cloud_cover_high']
        trail=[hi[j] for j in range(i-3,i+1) if hi[j] is not None]
        shield = hi[i] is not None and hi[i]>=50 and max(trail)>=85
        lo,hi_=hr*60,hr*60+60
        over=[f for f in sig if mins(f['toff'])<hi_ and mins(f['toff'])+f['mins']>lo]
        if not over: continue
        soared=any(f['mins']>=60 for f in over); short=all(f['mins']<30 for f in over)
        sw=h['shortwave_radiation'][i]; dr=h['direct_radiation'][i]
        d=date.fromisoformat(day); scale=radiation_season_factor(P[pid]['lat'],d.timetuple().tm_yday)
        res=process_point_hour(dict(P[pid]),h,i,month=d.month)
        rows.append(dict(day=day,pid=pid,hr=hr,shield=shield,high=hi[i],high_max=max(trail),sw=sw,direct=dr,dfrac=dr/sw if sw else 0,direct_rel=dr/scale,soared=soared,short=short,score=res['score'],n=len(over),longest=max(f['mins'] for f in over)))
json.dump(rows,open(f'{S}/cirrus_rows.json','w'))
sh=[r for r in rows if r['shield']]
print('active hours',len(rows),' shield hours',len(sh),' soared',sum(r['soared'] for r in sh),' short',sum(r['short'] for r in sh))
print('\nSHIELD HOURS (sorted by direct radiation, season-scaled):')
for r in sorted(sh,key=lambda r:r['direct_rel']):
    tag='SOARED' if r['soared'] else ('short ' if r['short'] else 'mixed ')
    print(f"{r['day']} {r['pid']:<13}{r['hr']:>3}h {tag} longest {r['longest']:>4}m n{r['n']:>2} | high {r['high']:>3}/{r['high_max']:>3}  SW {r['sw']:>4.0f} direct {r['direct']:>4.0f} (rel {r['direct_rel']:>4.0f}) frac {r['dfrac']:.2f}  score {r['score']}")
