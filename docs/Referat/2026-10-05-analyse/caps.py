import json, pickle, sys
from collections import Counter, defaultdict
sys.path.insert(0,'/home/jens/AI/Flyvevejr')
from termik.locations import AIRFIELDS
from termik.fetch_weather import process_point_hour
import termik.scoring_v2 as v2
from termik.config import *
S='analyse-data'
P={p['id']:p for p in AIRFIELDS}
H=pickle.load(open(f'{S}/hist_full.pkl','rb'))
def hourly(pid,day):
    for (p,a),h in H.items():
        if p==pid and h['time'][0][:10]<=day<=h['time'][-1][:10]: return h
cap={}
real=v2.apply_dealbreakers_v2
def spy(score,lapse_rate,cloud_cover,precipitation,wind_kt,wind_gusts_kt,temp,**k):
    cap['args']=dict(raw=score,lapse=lapse_rate,cc=cloud_cover,precip=precipitation,wind=wind_kt,gust=wind_gusts_kt,temp=temp,**k)
    return real(score,lapse_rate,cloud_cover,precipitation,wind_kt,wind_gusts_kt,temp,**k)
v2.apply_dealbreakers_v2=spy
def caps_for(a):
    c=[]; sc=a.get('radiation_scale',1.0)
    if a.get('shortwave_radiation') is not None:
        eff=v2.effective_radiation_v2(a['shortwave_radiation'],a.get('trailing_radiation'),cloud_cover=a['cc'],trailing_cloud_cover=a.get('trailing_cloud_cover'),temp_850hpa_trend=a.get('temp_850hpa_trend',0),radiation_scale=sc)
        for t,cv in RADIATION_GATE:
            if eff<t*sc: c.append((f'radiation<{t}',cv))
    if a.get('boundary_layer_height') is not None and a['boundary_layer_height']<SHALLOW_BOUNDARY_LAYER_M: c.append(('BL<900',SHALLOW_BOUNDARY_LAYER_MAX_SCORE))
    L=a['lapse']
    if L<0.5: c.append(('lapse<0.50',1))
    elif L<0.65: c.append(('lapse<0.65',3))
    elif L<0.70: c.append(('lapse<0.70',5))
    if a['cc']>=87: c.append(('cloud>=87',2))
    hi=a.get('cloud_cover_high')
    if hi is not None and hi>=CIRRUS_SHIELD_PRESENT_MIN and max([hi]+list(a.get('trailing_cirrus') or []))>=CIRRUS_SHIELD_THRESHOLD: c.append(('cirrus shield',3))
    if (a.get('cloud_cover_mid') or 0)>=MID_LEVEL_DECK_THRESHOLD: c.append(('mid deck',2))
    if a['precip']>0: c.append(('precip',1))
    ew=a['wind']+a['gust']/2
    if a['gust']>=30 or ew>25 or a['wind']>35: c.append(('wind/gust',4 if ew<=30 and a['gust']<30 else 2))
    if a['temp']<5: c.append(('temp<5',3))
    if a.get('thermal_top_cap') is not None: c.append(('low base',a['thermal_top_cap']))
    return c
R=json.load(open(f'{S}/cirrus_rows2.json'))
out=[]
for r in R:
    if not (r['soared'] or r['short']): continue
    h=hourly(r['pid'],r['day']); i=[k for k,t in enumerate(h['time']) if t==f"{r['day']}T{r['hr']:02d}:00"][0]
    res=process_point_hour(dict(P[r['pid']]),h,i,month=int(r['day'][5:7]))
    a=cap['args']; c=caps_for(a); final=res['score']
    binding=[n for n,v in c if v<=final+0.05 and v<a['raw']] if final< a['raw']-0.05 else []
    out.append(dict(r,raw=round(a['raw'],1),final=final,caps=[n for n,v in c],binding=binding))
json.dump(out,open(f'{S}/caps_rows.json','w'),ensure_ascii=False)
low=[r for r in out if not r['shield'] and r['final']<3.05]
print('non-shield hours score<=3:',len(low),' soared',sum(r['soared'] for r in low))
cnt=defaultdict(lambda:[0,0])
for r in low:
    key=' + '.join(sorted(r['binding'])) or 'no cap (raw score low)'
    cnt[key][0 if r['soared'] else 1]+=1
print('\nbinding cap(s) -> soared / short')
for k,(s,t) in sorted(cnt.items(),key=lambda x:-sum(x[1])): print(f'  {k:<45} {s:>3} / {t:<3} ({100*s//(s+t)}% soared)')
# each cap individually across ALL labeled hours where it binds
print('\nevery cap, all hours where it binds (incl. shield):')
c2=defaultdict(lambda:[0,0])
for r in out:
    for b in r['binding']: c2[b][0 if r['soared'] else 1]+=1
for k,(s,t) in sorted(c2.items(),key=lambda x:-sum(x[1])): print(f'  {k:<20} {s:>3} / {t:<3} ({100*s//(s+t)}% soared)')
print('\nbaseline: all hours',sum(r['soared'] for r in out),'/',len(out))
