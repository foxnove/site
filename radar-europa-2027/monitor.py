import os,json,datetime as dt,requests
from pathlib import Path
base=Path(__file__).parent
cfg=json.loads((base/"config.json").read_text())
url=os.getenv("FLIGHT_API_URL")
if not url: raise SystemExit("FLIGHT_API_URL não configurada; nenhuma consulta realizada.")
token=os.getenv("FLIGHT_API_TOKEN")
if not token: raise SystemExit("FLIGHT_API_TOKEN não configurado.")
offers=[]
for dest in cfg["destinations"]:
 for start,end in cfg["windows"]:
  d=dt.date.fromisoformat(start)
  while d<=dt.date.fromisoformat(end):
   ret=d+dt.timedelta(days=14)
   if ret<=dt.date.fromisoformat(end):
    r=requests.get(url,params={"origin":"SSA","destination":dest,"departure":d.isoformat(),"return":ret.isoformat()},headers={"Authorization":"Bearer "+token},timeout=25)
    r.raise_for_status()
    for item in r.json().get("offers",[]):
     offers.append({"destination":dest,"departure":d.isoformat(),"return":ret.isoformat(),"price":float(item["price"])})
   d+=dt.timedelta(days=7)
offers.sort(key=lambda x:x["price"])
(base/"docs/data.json").write_text(json.dumps({"updated_at":dt.datetime.now(dt.timezone.utc).isoformat(),"offers":offers[:100]},indent=2))
print("Ofertas verificadas:",len(offers))
