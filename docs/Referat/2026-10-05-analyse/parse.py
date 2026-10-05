import re, html, json, sys
def clean(s): return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',s))).strip()
out=[]
import glob
for day in sorted(f[16:26] for f in glob.glob('analyse-data/sl_*.html')):
    h=open(f'analyse-data/sl_{day}.html').read()
    parts=re.split(r'<h2>',h)[1:]
    for p in parts:
        name=clean(p[:p.find('</h2>')])
        tb=p.find('<tbody>');te=p.find('</tbody>')
        if tb<0: continue
        for row in re.findall(r'<tr>(.*?)</tr>',p[tb:te],re.S):
            tds=re.findall(r'<td[^>]*>(.*?)</td>',row,re.S)
            c=[clean(t) for t in tds]
            if len(c)<6: continue
            dur=c[1]; plane=re.search(r'hidden-xs">([^<]*)<',tds[2]); plane=plane.group(1).strip() if plane else c[2]
            pil=html.unescape(re.sub(r'<[^>]+>','',tds[3]))
            pil=re.sub(r'\(paid by.*?\)','',pil); club=re.search(r'\[(.*?)\]',pil); pil=re.sub(r'\[.*?\]','',pil)
            pilots=[re.sub(r'\s+',' ',x).strip() for x in pil.split('/') if x.strip()]
            times=[x for x in c if re.fullmatch(r'\d{1,2}:\d{2}',x)]
            m=re.fullmatch(r'(\d+):(\d+)',dur)
            mins=int(m.group(1))*60+int(m.group(2)) if m else None
            launch=None
            for x in c[4:6]:
                if x in ('A','S','W','E','B'): launch=x
            out.append(dict(day=day,field=name,mins=mins,plane=plane,pilots=pilots,launch=launch,toff=times[1] if len(times)>1 else None,land=times[2] if len(times)>2 else None,raw=c[:8]))
json.dump(out,open('analyse-data/flights.json','w'),ensure_ascii=False,indent=0)
from collections import Counter
for d in ['2026-10-03','2026-10-04']:
    print(d, Counter(f['field'] for f in out if f['day']==d).most_common())
