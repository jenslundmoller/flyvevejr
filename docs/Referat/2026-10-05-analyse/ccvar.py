import json, pickle, sys, inspect, textwrap
sys.path.insert(0,'/home/jens/AI/Flyvevejr')
from datetime import date
from termik.locations import AIRFIELDS
from termik.fetch_weather import process_point_hour
from termik.tools.replay_day import day_hour_indices
import termik.scoring_v2 as v2
S='analyse-data'
P={p['id']:p for p in AIRFIELDS}
H=pickle.load(open(f'{S}/hist_full.pkl','rb'))
def hourly(pid,day):
    for (p,a),h in H.items():
        if p==pid and h['time'][0][:10]<=day<=h['time'][-1][:10]: return h
src=inspect.getsource(v2.apply_dealbreakers_v2)
OLD="    if cloud_cover >= 87:\n        max_score = min(max_score, 2)\n"
assert OLD in src
VARIANTS={'current (cap 2)':OLD,
 'cap 4':"    if cloud_cover >= 87:\n        max_score = min(max_score, 4)\n",
 'cap 5':"    if cloud_cover >= 87:\n        max_score = min(max_score, 5)\n",
 'minus 1.5':"    if cloud_cover >= 87:\n        score = score - 1.5\n",
 'minus 2':"    if cloud_cover >= 87:\n        score = score - 2.0\n",
 'minus 2, cap 5':"    if cloud_cover >= 87:\n        score = score - 2.0\n        max_score = min(max_score, 5)\n"}
fns={}
for n,code in VARIANTS.items():
    ns=dict(vars(v2)); exec(src.replace(OLD,code),ns); fns[n]=ns['apply_dealbreakers_v2']
real=v2.apply_dealbreakers_v2
R=[r for r in json.load(open(f'{S}/caps_rows.json'))]
cache=pickle.load(open(f'{S}/season_cache.pkl','rb')); sst=json.load(open(f'{S}/sst_cells.json'))
D=json.load(open(f'{S}/validate_925.json'))
BAND={'staerk':(7.5,10),'god':(6.5,10),'mulig':(4.5,8.5),'svag':(0,6)}
err=lambda v,l:max(0,BAND[l][0]-v,v-BAND[l][1])
print(f"{'variant':<16}| hours: sep  acc  | calib soared% by score 0-3 / 3-5 / 5-6.5 / 6.5-8 / 8+ | days summer dev/inband  oct dev/inband")
for n,fn in fns.items():
    v2.apply_dealbreakers_v2=fn
    for r in R:
        h=hourly(r['pid'],r['day']); i=h['time'].index(f"{r['day']}T{r['hr']:02d}:00")
        r['v']=process_point_hour(dict(P[r['pid']]),h,i,month=int(r['day'][5:7]))['score']
    s=[r['v'] for r in R if r['soared']]; t=[r['v'] for r in R if r['short']]
    acc=sum((r['v']>=5)==r['soared'] for r in R)/len(R)
    cal=[]
    for lo,hi in [(0,3),(3,5),(5,6.5),(6.5,8),(8,11)]:
        rs=[r for r in R if lo<=r['v']<hi]; cal.append(f"{100*sum(r['soared'] for r in rs)//max(1,len(rs)):>2}%({len(rs):>3})")
    for d in D:
        hh,_=cache[d['point_id']]; dd=date.fromisoformat(d['day']); q=dict(P[d['point_id']])
        x=sst.get(d['point_id'],{}).get(d['day'])
        if x is not None and q.get('sea_cell') is not None: q['sea_temp_c']=x
        sc=sorted((process_point_hour(q,hh,i,month=dd.month)['score'] for i in day_hour_indices(hh,dd) if 11<=int(hh['time'][i][11:13])<=18),reverse=True)
        d['v']=round(sum(sc[:3])/3,1)
    sm=[d for d in D if not d.get('new')]; oc=[d for d in D if d.get('new')]
    f=lambda g:(sum(err(d['v'],d['label']) for d in g), sum(err(d['v'],d['label'])==0 for d in g))
    a,b=f(sm); c,e=f(oc)
    print(f"{n:<16}| {sum(s)/len(s)-sum(t)/len(t):.2f} {acc:.3f} | {' '.join(cal)} | {a:5.1f}/{b}  {c:5.1f}/{e}")
v2.apply_dealbreakers_v2=real
