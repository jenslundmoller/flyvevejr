import json
from collections import defaultdict
F=json.load(open('analyse-data/flights.json'))
for f in F: f['field']=f['field'].split(' EK')[0].split(' (')[0]
by=defaultdict(list)
for f in F: by[(f['day'],f['field'])].append(f)
res=[]
for (d,fl),fs in sorted(by.items()):
    planes=defaultdict(set)
    for f in fs:
        if f['pilots']: planes[f['plane']].add(f['pilots'][0])
    school={p for p,s in planes.items() if len(s)>=3}
    sig=[f for f in fs if f['plane'] not in school and f['mins'] is not None]
    sig.sort(key=lambda f:-f['mins'])
    longest=sig[0]['mins'] if sig else 0
    o60=sum(1 for f in sig if f['mins']>=60); o120=sum(1 for f in sig if f['mins']>=120)
    if o60>=2 and longest>=120: lab='staerk'
    elif longest>=90: lab='god'
    elif longest>=60: lab='mulig'
    elif len(sig)>=2 and longest<45: lab='svag'
    else: lab='tynd'
    res.append(dict(day=d,field=fl,n=len(fs),school=sorted(school),signal_n=len(sig),longest=longest,o60=o60,o120=o120,label=lab,top=[(f['mins'],f['plane'],f['toff'],f['land'],f['launch']) for f in sig[:6]]))
    print(d,fl,'n',len(fs),'school',sorted(school),'sig',len(sig),'o60',o60,'o120',o120,lab)
    for t in res[-1]['top']: print('    ',t)
json.dump(res,open('analyse-data/facit.json','w'),ensure_ascii=False,indent=1)
