import json, requests, time
S='analyse-data'
sp=json.load(open(f'{S}/seapoints.json'))
need=['saeby','aarhus','aars','kolding','kalundborg','kongsted','ringsted','goerloese','frederikssund','silkeborg','bolhede','lolland','herning','holstebro','skive','viborg','arnborg']
out={}
for pid in need:
    p=sp[pid]
    r=requests.get('https://marine-api.open-meteo.com/v1/marine',params=dict(latitude=p['lat'],longitude=p['lon'],hourly='sea_surface_temperature',start_date='2024-05-01',end_date='2026-10-04',timezone='Europe/Copenhagen'),timeout=120).json()
    h=r['hourly']; out[pid]={t[:10]:v for t,v in zip(h['time'],h['sea_surface_temperature']) if t[11:13]=='13'}
    print(pid, len(out[pid]), sum(v is None for v in out[pid].values())); time.sleep(2)
json.dump(out,open(f'{S}/sst_hist.json','w'))
