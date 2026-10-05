import sys; sys.path.insert(0, "/home/jens/AI/Flyvevejr")
import json, pickle, collections
import termik.scoring_v2 as s2
from termik.locations import AIRFIELDS
from termik.fetch_weather import process_point_hour
W='analyse-data'
P={p['id']:p for p in AIRFIELDS}
H=pickle.load(open(f'{W}/hist.pkl','rb')); HO=pickle.load(open(f'{W}/hist_oct.pkl','rb'))
M={'True':'aarhus','Sæby':'saeby','Viborg':'viborg','Vesthimmerland/Aars':'aars','Arnborg':'arnborg','Christianshede':'silkeborg','Gesten':'kolding','Bolhede':'bolhede','Nørre Felding':'holstebro','Skinderholm':'herning','Skive':'skive',
   'Gørløse':'goerloese','Frederikssund':'frederikssund','Kalundborg':'kalundborg','Kongsted':'kongsted','Slaglille':'ringsted','Maribo':'lolland'}
SJ={'goerloese','frederikssund','kalundborg','kongsted','ringsted','lolland'}
B={'staerk':(7.5,10),'god':(6.5,10),'mulig':(4.5,8.5),'svag':(0,6)}
cases=[]
for f in json.load(open(f'{W}/facit.json')):
    if f['field'] in M and f['label']!='tynd': cases.append((f['day'],M[f['field']],f['label'],H))
for l in open('/home/jens/AI/Flyvevejr/docs/Referat/2026-10-05-startlist-weekend.jsonl'):
    r=json.loads(l)
    if r['label']!='tynd' and r['plads']!='Hammer': cases.append((r['day'],r['point_id'],r['label'],HO))
orig=s2.effective_lapse_v2
CTX={}
def make(clamp=None, upper_min=None):
    def eff(l850, ml, depth):
        if upper_min is not None and CTX['up'] is not None and CTX['up']<upper_min: return l850
        if clamp is not None and ml is not None: ml=min(ml,clamp)
        return orig(l850, ml, depth)
    return eff
V={'A current':orig,'B no fix3':make(upper_min=99),'C clamp 1.0':make(clamp=1.0),'D upper>=0':make(upper_min=0.0),'D2 upper>=0.2':make(upper_min=0.2),'E clamp+upper>=0':make(clamp=1.0,upper_min=0.0)}
res=collections.defaultdict(list)
for day,pid,lab,HH in cases:
    h=HH[pid]['hourly']; p=dict(P[pid]); st=HH[pid]['sst'].get(day)
    if st is not None: p['sea_temp_c']=st
    idx=[i for i,t in enumerate(h['time']) if t.startswith(day) and 11<=int(t[11:13])<=18]
    for name,fn in V.items():
        s2.effective_lapse_v2=fn
        sc=[]
        for i in idx:
            e=p.get('elevation_m',0)
            T9,T8,z9,z8=(h[k][i] for k in ('temperature_925hPa','temperature_850hPa','geopotential_height_925hPa','geopotential_height_850hPa'))
            CTX['up']=(T9-T8)/((z8-z9)/100) if None not in (T9,T8,z9,z8) else None
            sc.append(process_point_hour(p,h,i,month=int(h['time'][i][5:7]))['score'])
        m=sum(sorted(sc)[-3:])/3; lo,hi=B[lab]
        res[name].append(dict(day=day,pid=pid,label=lab,score=m,err=max(0,lo-m,m-hi),grp='okt' if day>='2026-10' else ('sj' if pid in SJ else 'jy')))
s2.effective_lapse_v2=orig
json.dump(res,open(f'{W}/variants.json','w'))
def summ(rs):
    fl=[r['score'] for r in rs if r['label']!='svag']; wk=[r['score'] for r in rs if r['label']=='svag']
    by=collections.defaultdict(list)
    for r in rs: by[r['day']].append(r)
    wd=[]
    for d,x in by.items():
        a=[r['score'] for r in x if r['label']!='svag']; b=[r['score'] for r in x if r['label']=='svag']
        if a and b: wd.append(sum(a)/len(a)-sum(b)/len(b))
    return f"{sum(r['err']==0 for r in rs):3}/{len(rs):3} dev {sum(r['err'] for r in rs):5.1f} sep {sum(fl)/len(fl)-sum(wk)/len(wk):4.2f} wday {sum(wd)/len(wd):4.2f}"
for name,rs in res.items():
    print(f"{name:18}", '| all', summ(rs), '| jy', summ([r for r in rs if r['grp']=='jy']), '| sj', summ([r for r in rs if r['grp']=='sj']), '| okt', summ([r for r in rs if r['grp']=='okt']))
