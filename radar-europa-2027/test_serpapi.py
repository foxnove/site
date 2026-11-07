import datetime as dt
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
try:
    import serpapi_scan as serp
except ImportError:
    serp = None

class SerpTests(unittest.TestCase):
    def test_free_search_request_has_roundtrip_brl_and_no_extra_lookup(self):
        calls=[]
        class Session:
            def get(self,url,**kwargs):
                calls.append((url,kwargs))
                class Response:
                    status_code=200
                    def json(self):return {'search_metadata':{'status':'Success'},'best_flights':[]}
                return Response()
        with patch.dict(os.environ,{'SERPAPI_API_KEY':'test-only'}):
            data=serp.SerpApi(session=Session()).search(('LIS','2027-02-20','2027-03-06'))
        self.assertEqual(len(calls),1)
        params=calls[0][1]['params']
        self.assertEqual((params['engine'],params['type'],params['departure_id'],params['currency']),('google_flights',1,'SSA','BRL'))
        self.assertEqual(params['return_date'],'2027-03-06')
        self.assertNotIn('departure_token',params)
        self.assertFalse(params.get('no_cache',False))

    def test_quota_and_cooldown_block_without_searching(self):
        now=dt.datetime(2026,11,5,12,tzinfo=dt.timezone.utc)
        cfg={'daily_request_budget':6,'monthly_request_budget':180}
        for usage,expected in [({'month':'2026-11','requests':180},'monthly_budget_reached'),
          ({'month':'2026-11','requests':5,'day':'2026-11-05','daily_requests':6},'daily_budget_reached'),
          ({'month':'2026-11','requests':1,'last_search_at':'2026-11-05T11:00:00+00:00'},'cooldown')]:
            self.assertEqual(serp.budget_block(usage,cfg,now),expected)

    def test_unknown_return_is_never_invented_or_labelled_direct(self):
        raw={'type':'Round trip','price':4300,'total_duration':500,'flights':[
          {'departure_airport':{'id':'SSA','time':'2027-02-20 23:00'},'arrival_airport':{'id':'LIS','time':'2027-02-21 10:00'},'airline':'TAP','flight_number':'TP 28'}]}
        item=serp.normalize(raw,('LIS','2027-02-20','2027-03-06'),'now','https://www.google.com/travel/flights?hl=pt')
        self.assertEqual(item['price'],4300)
        self.assertEqual(item['stops'],[0,None])
        self.assertTrue(item['outbound_direct'])
        self.assertIsNone(item['direct'])
        self.assertFalse(item['return_details_available'])
        self.assertNotIn('departure_token',item)

    def test_paid_plan_and_exhausted_free_pool_are_blocked(self):
        for account in [{'plan_monthly_price':10,'plan_searches_left':10,'this_month_usage':0},
                        {'plan_monthly_price':0,'plan_searches_left':0,'this_month_usage':0}]:
            with self.assertRaises(serp.ApiError):
                serp.validate_account(account,180)

    def test_successful_scan_persists_only_normalized_public_data(self):
        raw={'type':'Round trip','price':4300,'total_duration':500,'departure_token':'private-token','flights':[
          {'departure_airport':{'id':'SSA','time':'2027-02-20 23:00'},'arrival_airport':{'id':'LIS','time':'2027-02-21 10:00'},'airline':'TAP','flight_number':'TP 28'}]}
        calls=[]
        class Session:
            def get(self,url,**kwargs):
                calls.append(url)
                class Response:
                    status_code=200
                    def json(self):
                        if url.endswith('account.json'):
                            return {'plan_monthly_price':0,'plan_searches_left':250,'this_month_usage':0,'searches_per_month':250}
                        return {'search_metadata':{'status':'Success','google_flights_url':'https://www.google.com/travel/flights'},'best_flights':[raw]}
                return Response()
        with tempfile.TemporaryDirectory() as directory,patch.dict(os.environ,{'SERPAPI_API_KEY':'test-only'},clear=True),patch.object(serp.requests,'Session',Session):
            root=Path(directory)
            (root/'config.json').write_text(json.dumps({'origin':'SSA','max_brl':4500,'windows':[['2027-02-20','2027-03-31'],['2027-07-21','2027-08-13']],'destinations':['LIS'],'monthly_request_budget':180,'daily_request_budget':6}))
            self.assertEqual(serp.main(root),0)
            text=(root/'docs/data.json').read_text(encoding='utf-8');data=json.loads(text)
            self.assertEqual(data['status'],'ok')
            self.assertEqual(len(data['offers']),1)
            self.assertEqual(data['quota']['used'],1)
            self.assertEqual(data['provider'],'serpapi')
            self.assertNotIn('private-token',text)
            self.assertNotIn('test-only',text)
            self.assertEqual(serp.main(root),0)
            self.assertEqual(len(calls),2,'second run must not make even an account request during cooldown')

if __name__=='__main__':unittest.main()
