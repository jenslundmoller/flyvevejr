import sys; sys.path.insert(0, "/home/jens/AI/Flyvevejr")
import json, re, time, requests, os
S='analyse-data'
days=sorted({r['day'] for r in json.load(open(f'{S}/rows.json'))})
f=f'{S}/sondes.json'
out=json.load(open(f)) if os.path.exists(f) else {}
for d in days:
    if d in out: continue
    for a in range(3):
        try:
            t=requests.get('https://weather.uwyo.edu/wsgi/sounding',params={'datetime':f'{d} 12:00:00','id':'10035','type':'TEXT:LIST','src':'UNKNOWN'},timeout=60).text; break
        except Exception as e: print('err',d,e); time.sleep(10)
    txt=re.sub(r'<[^>]+>','',t)
    lv=[]
    for line in txt.splitlines():
        p=line.split()
        if len(p)>=9 and re.fullmatch(r'\d{3,4}\.\d',p[0]) and re.fullmatch(r'\d+',p[1]):
            try: lv.append([float(p[0]),float(p[1]),float(p[2]),float(p[3]),float(p[4]),float(p[5]),float(p[8])])
            except ValueError: pass
    out[d]=lv; print(d,len(lv),flush=True)
    json.dump(out,open(f,'w')); time.sleep(2)
