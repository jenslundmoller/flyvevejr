import json, pickle, sys
sys.path.insert(0,'/home/jens/AI/Flyvevejr')
from termik.locations import AIRFIELDS
S='analyse-data'
P={p['id']:p for p in AIRFIELDS}
H=pickle.load(open(f'{S}/h925.pkl','rb')); sst=json.load(open(f'{S}/sst_cells.json'))
D=json.load(open('/home/jens/AI/Flyvevejr/docs/Referat/2026-08-25-paalandsvind-pooled.json'))
lab=lambda r: 'staerk' if r['signal_over60']>=2 and r['signal_longest']>=120 else 'god' if r['signal_longest']>=90 else 'mulig' if r['signal_longest']>=60 else 'svag' if r['signal_n']>=2 and r['signal_longest']<45 else 'tynd'
def window(pid,day):
    h=H.get((pid,day[:4]))
    if not h: return None
    idx=[i for i,t in enumerate(h['time']) if t.startswith(day) and 12<=int(t[11:13])<=16]
    def m(k):
        v=[h[k][i] for i in idx if h[k][i] is not None]; return sum(v)/len(v) if v else None
    return dict(t2=m('temperature_2m'),t850=m('temperature_850hPa'),t925=m('temperature_925hPa'),z925=m('geopotential_height_925hPa'))
rows=[]
for r in D:
    if lab(r)=='tynd': continue
    w=window(r['point_id'],r['day']); s=sst[r['point_id']].get(r['day'])
    if not w or s is None or None in w.values(): continue
    rows.append(dict(r,sst=s,A=s-w['t850'],B=(s-w['t925'])/(w['z925']/100),bar=r['signal_longest']>=60,**w))
on_all=[r for r in rows if r['onshore_hours']>=4 and r['mean_wind_kt']>=8]
on26=[r for r in on_all if r['v2_max']>=6.5]
def f(x): return f"{sum(r['bar'] for r in x)}/{len(x)}"
for name,on in (('26-day study sample',on26),('all 48 active onshore',on_all)):
    print(f'== {name}: n={len(on)}  (misclassified = stable&flew + convective&died)')
    def rep(label,stable):
        st=[r for r in on if stable(r)]; cv=[r for r in on if not stable(r)]
        mis=sum(r['bar'] for r in st)+sum(not r['bar'] for r in cv)
        print(f"  {label:<34} stable flew {f(st):>6}   convective flew {f(cv):>6}   misclassified {mis}")
    rep('A<7 (current, measured SST)',lambda r:r['A']<7)
    for b in (0.7,0.8,0.9,1.0):
        rep(f'B<{b} only',lambda r,b=b:r['B']<b)
    for b in (0.7,0.8,0.9,1.0):
        rep(f'A<7 AND B<{b} (both stable)',lambda r,b=b:r['A']<7 and r['B']<b)
print()
for r in sorted(on_all,key=lambda r:r['A']):
    if r['A']<9: print(r['day'],f"{r['plads']:<20}",'bar' if r['bar'] else '---',f"{r['signal_longest']:>4}m  A {r['A']:5.1f}  B {r['B']:5.2f}  sst {r['sst']} t925 {r['t925']:.1f} t850 {r['t850']:.1f}  v2max {r['v2_max']}")
json.dump(rows,open(f'{S}/rows925.json','w'),ensure_ascii=False)
