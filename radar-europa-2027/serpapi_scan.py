"""One economical Google Flights search per run; no return/booking lookups."""
import datetime as dt
import hashlib
import json
import math
import os
from urllib.parse import urlparse
import requests
from radar import ROOT, BRAZIL, ApiError, read_json, write_json, search_jobs, next_batch, plan_batch, analyze, send_alerts, public_snapshot

def budget_block(usage,cfg,now):
    month=now.strftime('%Y-%m')
    day=now.astimezone(dt.timezone(dt.timedelta(hours=-3))).date().isoformat()
    if usage.get('month')==month and usage.get('requests',0)>=min(180,cfg.get('monthly_request_budget',180)):
        return 'monthly_budget_reached'
    if usage.get('day')==day and usage.get('daily_requests',0)>=min(6,cfg.get('daily_request_budget',6)):
        return 'daily_budget_reached'
    last=usage.get('last_search_at')
    if last and (now-dt.datetime.fromisoformat(last)).total_seconds()<21600:
        return 'cooldown'
    return None

def validate_account(account,limit):
    try:
        if float(account['plan_monthly_price'])!=0:
            raise ApiError('free_plan_required')
        remaining=int(account['plan_searches_left'])
        used=int(account['this_month_usage'])
        if remaining<=0 or used>=min(180,limit):
            raise ApiError('account_quota_exhausted')
    except (KeyError,ValueError,TypeError):
        raise ApiError('account_quota_unverified') from None

class SerpApi:
    def __init__(self,session=None):
        self.session=session or requests.Session()

    def get(self,path,params):
        try:
            response=self.session.get('https://serpapi.com/'+path,params={**params,'api_key':os.environ['SERPAPI_API_KEY']},timeout=(10,90))
        except requests.RequestException:
            raise ApiError('network_unavailable') from None
        if response.status_code!=200:
            raise ApiError('http_'+str(response.status_code))
        try:
            data=response.json()
        except ValueError:
            raise ApiError('invalid_json') from None
        if not isinstance(data,dict):
            raise ApiError('invalid_json_structure')
        if data.get('error'):
            raise ApiError('serpapi_error')
        return data

    def account(self):
        # The Account API is free and does not consume search credits.
        return self.get('account.json',{})

    def search(self,job):
        data=self.get('search.json',{'engine':'google_flights','departure_id':'SSA','arrival_id':job[0],
            'outbound_date':job[1],'return_date':job[2],'type':1,'currency':'BRL','adults':1,
            'hl':'pt','gl':'br','sort_by':2})
        if data.get('search_metadata',{}).get('status')!='Success':
            raise ApiError('search_not_completed')
        return data

def safe_url(value):
    if not isinstance(value,str):return None
    parsed=urlparse(value)
    if parsed.scheme=='https' and parsed.netloc in ('www.google.com','google.com') and parsed.path.startswith('/travel/flights') and not any(x in parsed.query.lower() for x in ('api_key','access_token','serpapi')):
        return value
    return None

def normalize(raw,job,now,source_url=None):
    price=float(raw['price'])
    if not math.isfinite(price) or price<=0 or raw.get('type')!='Round trip':
        raise ValueError('Invalid round-trip price')
    flights=raw['flights']
    if not flights or flights[0]['departure_airport']['id']!='SSA' or flights[-1]['arrival_airport']['id']!=job[0]:
        raise ValueError('Invalid route')
    if not flights[0]['departure_airport'].get('time','').startswith(job[1]):
        raise ValueError('Invalid date')
    connections=[flight['arrival_airport']['id'] for flight in flights[:-1]]
    identity=['serpapi',job,[(f.get('flight_number'),f['departure_airport'],f['arrival_airport'],f.get('travel_class')) for f in flights]]
    outbound_direct=len(flights)==1 and not raw.get('layovers')
    domestic=any(c in BRAZIL for c in connections)
    minutes=int(raw.get('total_duration',0))
    if minutes<=0:raise ValueError('Invalid duration')
    result={'id':hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()[:24],
        'destination':job[0],'departure':job[1],'return':job[2],'price':round(price,2),'currency':'BRL',
        'airlines':[],'airline_names':sorted(set(f.get('airline','Não informada') for f in flights)),
        'stops':[len(flights)-1,None],'connections':[connections,None],
        'durations':[f'PT{minutes//60}H{minutes%60}M',None],'baggage':[],
        'direct':None,'domestic_connection':True if domestic else None,'international_connection':None,
        'outbound_direct':outbound_direct,'outbound_domestic_connection':domestic,
        'return_details_available':False,'checked_at':now,'period':'fev-mar' if job[1][5:7] in ('02','03') else 'jul-ago'}
    if safe_url(source_url):result['source_url']=safe_url(source_url)
    return result

def main(root=ROOT):
    cfg=read_json(root/'config.json',{})
    if cfg.get('origin')!='SSA':raise ValueError('Origin must be SSA')
    current=dt.datetime.now(dt.timezone.utc)
    now=current.isoformat()
    state_path=root/'private/state.json'
    state=read_json(state_path,{})
    usage=state.setdefault('serpapi_usage',{})
    old=read_json(root/'docs/data.json',{'offers':[],'history':[]})
    run={'provider':'serpapi','status':'credentials_missing','environment':'production',
        'updated_at':old.get('updated_at'),'last_success_at':old.get('last_success_at'),'last_attempt_at':now,
        'offers':old.get('offers',[]),'errors':[],'requests':0,'successful_queries':0,
        'scheduler':{'status':'active' if os.getenv('RADAR_SCHEDULE_ENABLED')=='true' else 'not_confirmed','interval_hours':6},
        'email_status':'ready' if all(os.getenv(k) for k in ('SMTP_USER','SMTP_APP_PASSWORD','ALERT_TO')) else 'not_configured','max_brl':cfg['max_brl']}
    block=budget_block(usage,cfg,current)
    if block:
        run['status']='cooldown' if block=='cooldown' else 'quota_exhausted'
        run['errors']=[{'code':block}] if block!='cooldown' else []
    elif os.getenv('SERPAPI_API_KEY'):
        try:
            api=SerpApi()
            account=api.account()
            validate_account(account,cfg.get('monthly_request_budget',180))
            prioritized=cfg.get('prioritized_destinations',['LIS','MAD','CDG','FCO','MXP'])
            scan_cfg={**cfg,'destinations':list(dict.fromkeys(prioritized+cfg['destinations']))}
            jobs=[job for job in search_jobs(scan_cfg) if job[1]>now[:10]]
            if not jobs:raise ApiError('no_future_dates')
            # Balance both travel seasons. One paid query per execution keeps
            # the free monthly budget intact; consecutive runs alternate seasons.
            periods={'fev-mar':[], 'jul-ago':[]}
            for candidate in jobs:
                season='fev-mar' if candidate[1][5:7] in ('02','03') else 'jul-ago'
                periods[season].append(candidate)
            if not all(periods.values()):
                raise ApiError('missing_travel_window')
            target='fev-mar' if state.get('queries_total',0)%2==0 else 'jul-ago'
            season_jobs=periods[target]
            season_cursors=state.setdefault('season_cursors',{})
            season_index=int(season_cursors.get(target,0))%len(season_jobs)
            job=season_jobs[season_index]
            is_watch=False
            if usage.get('month')!=now[:7]:
                usage['month'],usage['requests']=now[:7],0
            day=current.astimezone(dt.timezone(dt.timedelta(hours=-3))).date().isoformat()
            if usage.get('day')!=day:usage['day'],usage['daily_requests']=day,0
            usage['requests']+=1;usage['daily_requests']+=1;usage['last_search_at']=now
            # Reserve quota before the search; even a timeout cannot lose the counter.
            write_json(state_path,state)
            run['requests']=1
            data=api.search(job)
            found=[]
            for name in ('best_flights','other_flights'):
                rows=data.get(name,[])
                if not isinstance(rows,list):raise ApiError('invalid_offers_response')
                for raw in rows:
                    try:found.append(normalize(raw,job,now,data.get('search_metadata',{}).get('google_flights_url')))
                    except (ValueError,KeyError,TypeError,IndexError,AttributeError):run['errors'].append({'code':'invalid_offer'})
            found=list({x['id']:x for x in found}.values())
            enriched,alerts=analyze(found,state,cfg,now)
            season_cursors[target]=(season_index+1)%len(season_jobs)
            watchlist=state.setdefault('watchlist',{})
            for item in found:
                key=item['destination']+'|'+item['period']
                if key not in watchlist or item['price']<watchlist[key]['price']:
                    watchlist[key]={k:item[k] for k in ('destination','departure','return','price')}
            cutoff=(current-dt.timedelta(hours=24)).isoformat()
            retained=[o for o in old.get('offers',[]) if o.get('checked_at','')>=cutoff and (o['destination'],o['departure'],o['return'])!=job]
            run['offers']=sorted({o['id']:o for o in retained+enriched}.values(),key=lambda o:o['price'])[:500]
            run['status']='partial' if run['errors'] else 'ok'
            run['updated_at']=run['last_success_at']=now
            run['successful_queries']=1
            run['coverage']={'mode':'alternating_travel_seasons','combinations':len(jobs),'queries_this_run':1,'durations':cfg.get('durations',[]),'return_details':'not_requested_to_save_credits'}
            state['queries_total']=state.get('queries_total',0)+1
            run['email_status']=send_alerts(alerts,state,now)
        except ApiError as error:
            run['status']='quota_exhausted' if str(error) in ('monthly_budget_reached','account_quota_exhausted') else 'error'
            run['errors']=[{'code':str(error)}]
        except (ValueError,KeyError,TypeError,AttributeError,IndexError):
            run['status']='error';run['errors']=[{'code':'invalid_offers_response'}]
    else:run['errors']=[{'code':'credentials_missing'}]
    run['quota']={'month':usage.get('month',now[:7]),'used':usage.get('requests',0),'limit':min(180,cfg.get('monthly_request_budget',180)),
        'daily_used':usage.get('daily_requests',0),'daily_limit':min(6,cfg.get('daily_request_budget',6))}
    run['queries_total']=state.get('queries_total',0)
    write_json(state_path,state)
    write_json(root/'docs/data.json',public_snapshot(run,state.get('history',old.get('history',[]))))
    print(json.dumps({'status':run['status'],'offers':len(run['offers']),'searches_this_run':run['requests'],'monthly_search_attempts':run['quota']['used']}))
    return 0 if run['status'] in ('ok','partial','cooldown','quota_exhausted') else 2

if __name__=='__main__':raise SystemExit(main())
