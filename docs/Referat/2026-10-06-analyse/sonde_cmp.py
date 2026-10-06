import sys; sys.path.insert(0, "/home/jens/AI/Flyvevejr")
import json, pickle, math, statistics as st
from termik.scoring import _bolton_lcl_temp_k
S='analyse-data'
SO=json.load(open(f'{S}/sondes.json')); M=pickle.load(open(f'{S}/schleswig.pkl','rb'))
mi={t:i for i,t in enumerate(M['time'])}
def lcl_agl(t,td): return (t+273.15-_bolton_lcl_temp_k(t+273.15,td+273.15))/0.0098
def es(t): return 6.112*math.exp(17.67*t/(t+243.5))
def td_from_e(e): l=math.log(e/6.112); return 243.5*l/(17.67-l)
rows=[]
for d,lv in sorted(SO.items()):
    if len(lv)<20: continue
    z0=lv[0][1]; p0,_,T0,Td0=lv[0][:4]
    ml=[l for l in lv if l[1]-z0<=500]
    th=st.mean(l[6] for l in ml); w=st.mean(l[5] for l in ml)
    ml_lcl=None
    for p,z,T,Td,rh,mr,tha in lv:
        tp=th*(p/1000)**0.2857-273.15; e=w*p/(622+w)
        if tp<=td_from_e(e): ml_lcl=z-z0; break
    sat=next((z-z0 for p,z,T,Td,rh,mr,tha in lv if z-z0>150 and rh>=95 and z-z0<3500),None)
    i=mi.get(f'{d}T12:00')
    if i is None: continue
    mt,mtd=M['temperature_2m'][i],M['dewpoint_2m'][i]
    rows.append(dict(day=d,sT=T0,sTd=Td0,mT=mt,mTd=mtd,s_lcl=lcl_agl(T0,Td0),ml_lcl=ml_lcl,sat=sat,m_lcl=lcl_agl(mt,mtd),cc=M['cloud_cover'][i]))
json.dump(rows,open(f'{S}/sonde_rows.json','w'))
def grp(name,rs):
    if not rs: return
    f=lambda k: st.median(k(r) for r in rs if None not in (k.__defaults__ or ()))
    print(f"{name:10} n={len(rs):3} T2 model-sonde {st.median(r['mT']-r['sT'] for r in rs):+.1f}  Td2 model-sonde {st.median(r['mTd']-r['sTd'] for r in rs):+.1f} | LCL: model {st.median(r['m_lcl'] for r in rs):4.0f} sonde-surface {st.median(r['s_lcl'] for r in rs):4.0f} sonde-mixedlayer {st.median(r['ml_lcl'] for r in rs if r['ml_lcl']):4.0f} sonde-saturated {st.median(r['sat'] for r in rs if r['sat']):4.0f} | model-mixedlayer {st.median(r['m_lcl']-r['ml_lcl'] for r in rs if r['ml_lcl']):+4.0f}")
for m in ['05','06','07','08','09','10']: grp('month '+m,[r for r in rows if r['day'][5:7]==m])
grp('Jun-Aug',[r for r in rows if r['day'][5:7] in('06','07','08')]); grp('Sep-Oct',[r for r in rows if r['day'][5:7] in('09','10')])
