import os,json,time,datetime as dt,requests
from pathlib import Path
ROOT=Path(__file__).parent
cfg=json.loads((ROOT/"config.json").read_text())
client=os.environ.get("AMADEUS_CLIENT_ID")
secret=os.environ.get("AMADEUS_CLIENT_SECRET")
if not client or not secret: raise SystemExit("Credenciais Amadeus ausentes: nenhuma tarifa foi consultada.")
host="https://test.api.amadeus.com" if os.getenv("AMADEUS_TEST")=="true" else "https://api.amadeus.com"
r=requests.post(host+"/v1/security/oauth2/token",data={"grant_type":"client_credentials","client_id":client,"client_secret":secret},timeout=30)
r.raise_for_status()
token=r.json()["access_token"]
out=[];errors=[]
for destination in cfg["destinations"]:
 for start,end in cfg["windows"]:
  date=dt.date.fromisoformat(start);last=dt.date.fromisoformat(end)
  while date+dt.timedelta(days=14)<=last:
   ret=date+dt.timedelta(days=14)
   params={"originLocationCode":"SSA","destinationLocationCode":destination,"departureDate":date.isoformat(),"returnDate":ret.isoformat(),"adults":1,"currencyCode":"BRL","max":3}
   try:
    response=requests.get(host+"/v2/shopping/flight-offers",params=params,headers={"Authorization":"Bearer "+token},timeout=35)
    response.raise_for_status()
    for offer in response.json().get("data",[]):
     out.append({"destination":destination,"departure":date.isoformat(),"return":ret.isoformat(),"price":float(offer["price"]["grandTotal"]),"stops":[len(i["segments"])-1 for i in offer["itineraries"]],"airlines":offer.get("validatingAirlineCodes",[])})
   except requests.RequestException as e: errors.append(str(e)[:200])
   date+=dt.timedelta(days=14)
   time.sleep(.25)
out.sort(key=lambda x:x["price"])
path=ROOT/"docs/data.json"
path.write_text(json.dumps({"updated_at":dt.datetime.now(dt.timezone.utc).isoformat(),"offers":out[:200],"errors":errors[:20]},indent=2))
print("Ofertas:",len(out),"Erros:",len(errors))
if out and os.getenv("SMTP_USER") and os.getenv("SMTP_APP_PASSWORD"):
 import smtplib
 from email.message import EmailMessage
 alerts=[x for x in out if x["price"]<=cfg["max_brl"]]
 if alerts:
  msg=EmailMessage();msg["Subject"]="Radar Europa 2027 — tarifas abaixo do limite";msg["From"]=os.environ["SMTP_USER"];msg["To"]="diego.fox001@gmail.com"
  msg.set_content("\\n".join(f'{x["destination"]} R$ {x["price"]:.2f} | {x["departure"]} → {x["return"]}' for x in alerts[:20]))
  with smtplib.SMTP_SSL("smtp.gmail.com",465,timeout=30) as smtp:
   smtp.login(os.environ["SMTP_USER"],os.environ["SMTP_APP_PASSWORD"]);smtp.send_message(msg)
