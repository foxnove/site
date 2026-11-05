"""Private Amadeus monitor with an allowlisted public export."""
import datetime as dt
import hashlib
import json
import math
import os
import smtplib
import time
from email.message import EmailMessage
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parent
BRAZIL = set('SSA GRU CGH VCP GIG SDU BSB CNF PLU REC FOR NAT JPA MCZ AJU BPS IOS VIX CWB POA FLN BEL MAO SLZ THE CGB CGR GYN PMW PVH RBR MCP BVB FEN JDO PNZ NVT IGU JOI XAP UDI UBA RAO SJP LDB MGF'.split())
OFFER_FIELDS = 'id destination departure return price currency airlines airline_names stops connections durations baggage direct domestic_connection international_connection checked_at change_percent historical_low promotion period'.split()

def read_json(path, default):
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else default

def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    tmp.replace(path)

def search_jobs(cfg):
    windows = []
    for start, end in cfg['windows']:
        dates = []
        day, last = dt.date.fromisoformat(start), dt.date.fromisoformat(end)
        while day <= last:
            for length in cfg.get('durations', [14,18,21,24]):
                ret = day + dt.timedelta(days=length)
                if ret <= last:
                    dates.append((day.isoformat(),ret.isoformat()))
            day += dt.timedelta(days=cfg.get('date_step_days',1))
        windows.append(dates)
    jobs = []
    destinations = list(dict.fromkeys(cfg['destinations']+cfg.get('extra_destinations',[])))
    for i in range(max((len(w) for w in windows),default=0)):
        for dest in destinations:
            for dates in windows:
                if i < len(dates):
                    jobs.append((dest,*dates[i]))
    return jobs

def next_batch(jobs,cursor,limit):
    n = min(max(0,limit),len(jobs))
    return ([jobs[(cursor+i)%len(jobs)] for i in range(n)],(cursor+n)%len(jobs)) if jobs else ([],cursor)

def plan_batch(jobs,state,limit):
    """Reserve one slot for rechecking a known opportunity; keep exploring."""
    if not jobs or limit<=0:
        return []
    valid = set(jobs)
    watched = [(x['destination'],x['departure'],x['return']) for _,x in sorted(state.get('watchlist',{}).items())]
    watched = [x for x in watched if x in valid]
    selected = []
    if watched and limit>1:
        selected.append((watched[state.get('watch_cursor',0)%len(watched)],True))
    exploration,_ = next_batch(jobs,state.get('cursor',0),len(jobs))
    for job in exploration:
        if len(selected)>=limit:
            break
        if not any(job==x[0] for x in selected):
            selected.append((job,False))
    return selected

def normalize_offer(raw,job,carriers,now):
    price = float(raw['price']['grandTotal'])
    if raw['price'].get('currency') != 'BRL' or not math.isfinite(price) or price <= 0:
        raise ValueError('Invalid BRL price')
    itineraries = raw['itineraries']
    if len(itineraries)!=2 or any(not i.get('segments') for i in itineraries):
        raise ValueError('Not round trip')
    if itineraries[0]['segments'][0]['departure']['iataCode']!='SSA' or itineraries[-1]['segments'][-1]['arrival']['iataCode']!='SSA':
        raise ValueError('Invalid origin')
    connections = [[s['arrival']['iataCode'] for s in i['segments'][:-1]] for i in itineraries]
    airlines = sorted(set(s['carrierCode'] for i in itineraries for s in i['segments']))
    identity = [job,[[(s.get('carrierCode'),s.get('number'),s['departure'].get('at'),s['departure']['iataCode'],s['arrival']['iataCode']) for s in i['segments']] for i in itineraries]]
    bags = []
    for traveler in raw.get('travelerPricings',[]):
        for fare in traveler.get('fareDetailsBySegment',[]):
            bag = fare.get('includedCheckedBags')
            if bag is not None:
                bags.append({'segment':str(fare.get('segmentId','')),**{k:bag[k] for k in ('quantity','weight','weightUnit') if k in bag}})
    return {'id':hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()[:24],
        'destination':job[0],'departure':job[1],'return':job[2],'price':round(price,2),'currency':'BRL',
        'airlines':airlines,'airline_names':[carriers.get(c,c) for c in airlines],
        'stops':[len(i['segments'])-1 for i in itineraries],'connections':connections,
        'durations':[i.get('duration') for i in itineraries],'baggage':bags,
        'direct':all(len(i['segments'])==1 and not any(s.get('numberOfStops',0) for s in i['segments']) for i in itineraries),
        'domestic_connection':any(c in BRAZIL for leg in connections for c in leg),
        'international_connection':any(c not in BRAZIL for leg in connections for c in leg),
        'checked_at':now,'period':'fev-mar' if job[1][5:7] in ('02','03') else 'jul-ago'}

def analyze(offers,state,cfg,now):
    history = state.setdefault('history',[])
    sent = state.setdefault('alerts',{})
    observations = state.setdefault('observations',{})
    enriched, alerts, minima = [], [], {}
    for offer in offers:
        item = dict(offer)
        period = item.get('period','fev-mar' if item['departure'][5:7] in ('02','03') else 'jul-ago')
        previous = observations.get(item['id'])
        baseline = previous['price'] if previous else None
        item['change_percent'] = round((item['price']/baseline-1)*100,2) if baseline else None
        item['historical_low'] = min(item['price'],previous['low']) if previous else item['price']
        item['promotion'] = item['price']<=cfg['max_brl'] or (item['change_percent'] is not None and item['change_percent']<=-cfg.get('drop_percent',10))
        last = sent.get(item['id'])
        if item['promotion'] and (not last or item['price']<=last['price']*(1-cfg.get('drop_percent',10)/100)):
            alerts.append(item)
        enriched.append(item)
        key = item['destination'],period
        minima[key] = min(minima.get(key,math.inf),item['price'])
        observations[item['id']] = {'price':item['price'],'low':item['historical_low'],'at':now}
    for (dest,period),price in minima.items():
        history.append({'at':now,'destination':dest,'period':period,'price':price})
    state['history'] = history[-10000:]
    return enriched,alerts

def mark_sent(alerts,state,now):
    for item in alerts:
        state.setdefault('alerts',{})[item['id']] = {'price':item['price'],'at':now}

def public_snapshot(run,history):
    fields = 'status environment updated_at last_attempt_at last_success_at requests successful_queries queries_total errors quota scheduler email_status coverage max_brl'.split()
    result = {k:run[k] for k in fields if k in run}
    result['schema_version'] = 2
    result['offers'] = [{k:o[k] for k in OFFER_FIELDS if k in o} for o in run.get('offers',[])] if run.get('status')!='test' else []
    result['history'] = [{k:h[k] for k in ('at','destination','period','price')} for h in history]
    return result

class ApiError(Exception):
    pass

class Amadeus:
    def __init__(self,state,budget,test=False,session=None):
        self.state,self.budget = state,budget
        self.host = 'https://test.api.amadeus.com' if test else 'https://api.amadeus.com'
        self.session,self.token,self.requests = session or requests.Session(),None,0

    def request(self,method,path,**kwargs):
        for attempt in range(3):
            if self.state['usage']['requests']>=self.budget:
                raise ApiError('monthly_budget_reached')
            self.state['usage']['requests']+=1
            self.requests+=1
            try:
                response = self.session.request(method,self.host+path,timeout=(10,40),**kwargs)
            except requests.RequestException:
                if attempt==2:
                    raise ApiError('network_unavailable') from None
                time.sleep(2**attempt)
                continue
            if response.status_code==429 or response.status_code>=500:
                if attempt==2:
                    raise ApiError('http_'+str(response.status_code))
                try:
                    delay = min(60,max(1,float(response.headers.get('Retry-After',2**attempt))))
                except ValueError:
                    delay = 2**attempt
                time.sleep(delay)
                continue
            if not response.ok:
                raise ApiError('http_'+str(response.status_code))
            try:
                data = response.json()
            except ValueError:
                raise ApiError('invalid_json') from None
            if not isinstance(data,dict):
                raise ApiError('invalid_json_structure')
            return data
        raise ApiError('network_unavailable')

    def authenticate(self):
        data = self.request('POST','/v1/security/oauth2/token',data={'grant_type':'client_credentials','client_id':os.environ['AMADEUS_CLIENT_ID'],'client_secret':os.environ['AMADEUS_CLIENT_SECRET']})
        self.token = data.get('access_token')
        if not self.token:
            raise ApiError('invalid_oauth_response')

    def search(self,job,non_stop=False):
        params = {'originLocationCode':'SSA','destinationLocationCode':job[0],'departureDate':job[1],'returnDate':job[2],'adults':1,'currencyCode':'BRL','max':20}
        if non_stop:
            params['nonStop'] = 'true'
        try:
            return self.request('GET','/v2/shopping/flight-offers',params=params,headers={'Authorization':'Bearer '+self.token})
        except ApiError as error:
            if str(error)!='http_401':
                raise
            self.authenticate()
            return self.request('GET','/v2/shopping/flight-offers',params=params,headers={'Authorization':'Bearer '+self.token})

def send_alerts(alerts,state,now):
    pending = state.setdefault('pending_alerts',{})
    for item in alerts:
        pending[item['id']] = item
    cutoff = (dt.datetime.now(dt.timezone.utc)-dt.timedelta(hours=24)).isoformat()
    pending = {key:item for key,item in pending.items() if item.get('checked_at',now)>=cutoff}
    state['pending_alerts'] = pending
    if not all(os.getenv(k) for k in ('SMTP_USER','SMTP_APP_PASSWORD','ALERT_TO')):
        return 'not_configured'
    alerts = list(pending.values())
    if not alerts:
        return 'no_new_promotions'
    msg = EmailMessage()
    msg['Subject'] = 'Radar Europa 2027 — novas promoções'
    msg['From'],msg['To'] = os.environ['SMTP_USER'],os.environ['ALERT_TO']
    lines = []
    for x in alerts:
        lines.append(f"SSA → {x['destination']} | R$ {x['price']:.2f} por pessoa, ida e volta\n{x['departure']} → {x['return']} | {', '.join(x.get('airline_names',[]))}\nEscalas ida/volta: {x.get('stops')} | Conexões: {x.get('connections')}\nVariação: {x.get('change_percent')}% | Mínimo histórico: R$ {x['historical_low']:.2f}\n")
    msg.set_content('\n'.join(lines)+'\nTarifas sujeitas a alteração e reconfirmação. A API não fornece link de compra.\nhttps://foxnove.github.io/youtube/radar-europa-2027/')
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com',465,timeout=30) as smtp:
            smtp.login(os.environ['SMTP_USER'],os.environ['SMTP_APP_PASSWORD'])
            smtp.send_message(msg)
    except (OSError,smtplib.SMTPException):
        return 'send_failed'
    mark_sent(alerts,state,now)
    state['pending_alerts'] = {}
    return 'sent'

def main(root=ROOT):
    cfg = read_json(root/'config.json',{})
    if cfg.get('origin')!='SSA':
        raise ValueError('Origin must be SSA')
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    test = os.getenv('AMADEUS_ENV','production')=='test'
    state_path = root/('private/test-state.json' if test else 'private/state.json')
    state = read_json(state_path,{})
    if state.get('usage',{}).get('month')!=now[:7]:
        state['usage'] = {'month':now[:7],'requests':0}
    old = read_json(root/'docs/data.json',{'offers':[],'history':[]})
    run = {'status':'credentials_missing','environment':'test' if test else 'production','updated_at':old.get('updated_at'),
        'last_success_at':old.get('last_success_at'),'last_attempt_at':now,'offers':old.get('offers',[]),'errors':[],
        'requests':0,'successful_queries':0,'scheduler':{'status':'requires_default_branch_workflow','interval_hours':6},
        'email_status':'ready' if all(os.getenv(k) for k in ('SMTP_USER','SMTP_APP_PASSWORD','ALERT_TO')) else 'not_configured','max_brl':cfg['max_brl']}
    api = Amadeus(state,cfg.get('monthly_request_budget',400),test)
    if all(os.getenv(k) for k in ('AMADEUS_CLIENT_ID','AMADEUS_CLIENT_SECRET')):
        found,completed = [],[]
        try:
            api.authenticate()
            jobs = [j for j in search_jobs(cfg) if j[1]>now[:10]]
            batch = plan_batch(jobs,state,cfg.get('max_queries_per_run',2))
            run['coverage'] = {'mode':'rotating_sample_and_watchlist','combinations':len(jobs),'queries_this_run':len(batch),'durations':cfg.get('durations',[]),'watch_queries':sum(int(w) for _,w in batch)}
            run['coverage']['direct_searches'] = 0
            for index,(job,watched) in enumerate(batch):
                try:
                    nonstop = not watched and (state.get('queries_total',0)+index)%3==0
                    data = api.search(job,non_stop=nonstop)
                    run['coverage']['direct_searches'] += int(nonstop)
                    if not isinstance(data.get('data'),list):
                        raise ApiError('invalid_offers_response')
                    for raw in data['data']:
                        try:
                            dictionaries = data.get('dictionaries',{})
                            carriers = dictionaries.get('carriers',{}) if isinstance(dictionaries,dict) else {}
                            found.append(normalize_offer(raw,job,carriers if isinstance(carriers,dict) else {},now))
                        except (ValueError,KeyError,TypeError,IndexError,AttributeError,OverflowError):
                            run['errors'].append({'code':'invalid_offer','destination':job[0]})
                    completed.append(job)
                    run['successful_queries']+=1
                except ApiError as error:
                    run['errors'].append({'code':str(error),'destination':job[0]})
                    if str(error) in ('monthly_budget_reached','http_401','http_403','http_429'):
                        break
                if watched:
                    state['watch_cursor'] = state.get('watch_cursor',0)+1
                else:
                    state['cursor'] = (jobs.index(job)+1)%len(jobs)
                time.sleep(.2)
            enriched,alerts = analyze(found,state,cfg,now)
            watchlist = state.setdefault('watchlist',{})
            for item in found:
                key = item['destination']+'|'+item['period']
                if key not in watchlist or item['price']<watchlist[key]['price']:
                    watchlist[key] = {k:item[k] for k in ('destination','departure','return','price')}
            cutoff = (dt.datetime.now(dt.timezone.utc)-dt.timedelta(hours=cfg.get('offer_ttl_hours',24))).isoformat()
            retained = [o for o in old.get('offers',[]) if o.get('checked_at','')>=cutoff and (o['destination'],o['departure'],o['return']) not in completed]
            merged = {o['id']:o for o in retained+enriched}
            if run['successful_queries']:
                run['offers'] = sorted(merged.values(),key=lambda x:x['price'])[:500]
                run['updated_at'] = run['last_success_at'] = now
            run['status'] = 'partial' if run['errors'] and run['successful_queries'] else 'ok' if run['successful_queries'] else 'error'
            if not test:
                run['email_status'] = send_alerts(alerts,state,now)
        except ApiError as error:
            run['status'] = 'quota_exhausted' if str(error)=='monthly_budget_reached' else 'error'
            run['errors'].append({'code':str(error)})
    else:
        run['errors'].append({'code':'credentials_missing'})
    run['requests'] = api.requests
    run['quota'] = {'month':now[:7],'used':state['usage']['requests'],'limit':api.budget}
    run['queries_total'] = state.get('queries_total',0)+run['successful_queries']
    state['queries_total'] = run['queries_total']
    if test:
        run['status'] = 'test'
    write_json(state_path,state)
    write_json(root/('private/test-output.json' if test else 'docs/data.json'),public_snapshot(run,state.get('history',old.get('history',[]))))
    print(json.dumps({'status':run['status'],'offers':len(run['offers']) if not test else 0,'requests':api.requests,'successful_queries':run['successful_queries']}))
    return 0 if run['status'] in ('ok','partial') else 2

if __name__=='__main__':
    raise SystemExit(main())
