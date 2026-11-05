import importlib.util
import unittest
import os
import json
import tempfile
from unittest.mock import patch
from pathlib import Path

spec = importlib.util.spec_from_file_location('radar', Path(__file__).with_name('radar.py'))
radar = importlib.util.module_from_spec(spec)
if spec.loader and Path(spec.origin).exists():
    spec.loader.exec_module(radar)


class RadarTests(unittest.TestCase):
    def test_batch_rechecks_known_opportunities_while_exploring_dates(self):
        jobs=[('LIS','2027-02-20','2027-03-06'),('MAD','2027-07-01','2027-07-15')]
        state={'cursor':1,'watchlist':{'LIS|fev-mar':{'destination':'LIS','departure':'2027-02-20','return':'2027-03-06','price':5000}}}
        batch=radar.plan_batch(jobs,state,2)
        self.assertEqual(batch,[((('LIS','2027-02-20','2027-03-06')),True),((('MAD','2027-07-01','2027-07-15')),False)])

    def test_different_itineraries_do_not_create_false_price_drops(self):
        state = {'history':[], 'alerts':{}}
        cfg = {'max_brl':4500,'drop_percent':10}
        first = {'id':'a','destination':'LIS','departure':'2027-02-20','return':'2027-03-06','price':6000}
        radar.analyze([first],state,cfg,'first')
        other = dict(first,id='b',price=5000,return_date='unused')
        other['return'] = '2027-03-10'
        enriched,alerts = radar.analyze([other],state,cfg,'second')
        self.assertIsNone(enriched[0]['change_percent'])
        self.assertEqual(alerts,[])

    def test_non_object_api_response_is_a_safe_api_error(self):
        class Session:
            def request(self,*args,**kwargs):
                class Response:
                    status_code=200
                    ok=True
                    def json(self): return []
                return Response()
        api = radar.Amadeus({'usage':{'requests':0}},400,session=Session())
        with self.assertRaisesRegex(radar.ApiError,'invalid_json_structure'):
            api.request('GET','/v2/shopping/flight-offers')
        self.assertEqual(api.state['usage']['requests'],1)

    def test_all_new_promotions_are_sent_and_marked(self):
        messages=[]
        class SMTP:
            def __init__(self,*args,**kwargs): pass
            def __enter__(self): return self
            def __exit__(self,*args): pass
            def login(self,*args): pass
            def send_message(self,message): messages.append(message)
        alerts=[{'id':str(i),'destination':'LIS','price':4000,'departure':'2027-02-20','return':'2027-03-06','historical_low':4000} for i in range(25)]
        state={}
        with patch.dict(os.environ,{'SMTP_USER':'test@example.invalid','SMTP_APP_PASSWORD':'fake-test-only','ALERT_TO':'test@example.invalid'}),patch.object(radar.smtplib,'SMTP_SSL',SMTP):
            self.assertEqual(radar.send_alerts(alerts,state,'now'),'sent')
        self.assertEqual(len(state['alerts']),25)
        self.assertEqual(messages[0].get_content().count('SSA → LIS'),25)

    def test_search_explicitly_can_prioritize_nonstop_flights(self):
        class Session:
            def request(self,method,url,**kwargs):
                if kwargs['params'].get('nonStop') != 'true':
                    raise AssertionError('Direct search must ask Amadeus for nonStop flights')
                if kwargs['params']['currencyCode'] != 'BRL' or kwargs['params']['originLocationCode'] != 'SSA':
                    raise AssertionError('Wrong currency or origin')
                class Response:
                    status_code=200
                    ok=True
                    def json(self): return {'data':[]}
                return Response()
        api = radar.Amadeus({'usage':{'requests':0}},400,session=Session())
        api.token='test-token-only'
        self.assertEqual(api.search(('LIS','2027-02-20','2027-03-06'),non_stop=True),{'data':[]})

    def test_missing_credentials_preserves_last_success_and_returns_failure(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {}, clear=True):
            root = Path(directory)
            (root/'docs').mkdir()
            (root/'config.json').write_text(json.dumps({'origin':'SSA','max_brl':4500}))
            (root/'docs/data.json').write_text(json.dumps({'offers':[], 'last_success_at':'2026-11-01T12:00:00Z','updated_at':'2026-11-01T12:00:00Z'}))
            self.assertEqual(radar.main(root), 2)
            result = json.loads((root/'docs/data.json').read_text())
            self.assertEqual(result['status'], 'credentials_missing')
            self.assertEqual(result['last_success_at'], '2026-11-01T12:00:00Z')
            self.assertEqual(result['requests'], 0)

    def test_test_mode_cannot_overwrite_production_snapshot(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'AMADEUS_ENV':'test'}, clear=True):
            root = Path(directory)
            (root/'docs').mkdir()
            (root/'config.json').write_text(json.dumps({'origin':'SSA','max_brl':4500}))
            original = '{"offers":[],"status":"ok"}'
            (root/'docs/data.json').write_text(original)
            self.assertEqual(radar.main(root), 2)
            self.assertEqual((root/'docs/data.json').read_text(), original)
            self.assertEqual(json.loads((root/'private/test-output.json').read_text())['offers'], [])

    def test_budget_prevents_even_oauth_when_exhausted(self):
        api = radar.Amadeus({'usage':{'requests':400}}, 400)
        with self.assertRaisesRegex(radar.ApiError, 'monthly_budget_reached'):
            api.request('POST','/v1/security/oauth2/token')
        self.assertEqual(api.requests, 0)

    def test_http_429_retries_are_bounded_and_count_toward_budget(self):
        class Session:
            def request(self,*args,**kwargs):
                class Response:
                    status_code=429
                    headers={'Retry-After':'1'}
                return Response()
        api = radar.Amadeus({'usage':{'requests':0}},400,session=Session())
        with patch.object(radar.time,'sleep'), self.assertRaisesRegex(radar.ApiError,'http_429'):
            api.request('GET','/v2/shopping/flight-offers')
        self.assertEqual(api.requests,3)
        self.assertEqual(api.state['usage']['requests'],3)

    def test_round_trip_normalization_and_domestic_connection(self):
        offer = {'id': '1', 'price': {'grandTotal': '4300.50', 'currency': 'BRL'},
                 'validatingAirlineCodes': ['TP'], 'itineraries': [
                     {'duration': 'PT14H', 'segments': [
                         {'departure': {'iataCode': 'SSA'}, 'arrival': {'iataCode': 'GRU'}, 'carrierCode': 'TP'},
                         {'departure': {'iataCode': 'GRU'}, 'arrival': {'iataCode': 'LIS'}, 'carrierCode': 'TP'}]},
                     {'duration': 'PT9H', 'segments': [
                         {'departure': {'iataCode': 'LIS'}, 'arrival': {'iataCode': 'SSA'}, 'carrierCode': 'TP'}]}]}
        item = radar.normalize_offer(offer, ('LIS', '2027-02-20', '2027-03-06'), {'TP': 'TAP'}, 'now')
        self.assertEqual(item['price'], 4300.50)
        self.assertEqual(item['stops'], [1, 0])
        self.assertEqual(item['connections'], [['GRU'], []])
        self.assertFalse(item['direct'])
        self.assertTrue(item['domestic_connection'])
        self.assertEqual(item['airline_names'], ['TAP'])

    def test_non_brl_and_invalid_price_are_rejected(self):
        for price in [{'currency': 'USD', 'grandTotal': '10'}, {'currency': 'BRL', 'grandTotal': 'NaN'}]:
            with self.assertRaises(ValueError):
                radar.normalize_offer({'price': price}, ('LIS', '2027-02-20', '2027-03-06'), {}, 'now')

    def test_windows_and_rotation_cover_all_dates_without_exceeding_limit(self):
        cfg = {'destinations': ['LIS'], 'extra_destinations': [], 'windows': [['2027-02-20','2027-03-31']], 'durations': [14, 24]}
        jobs = radar.search_jobs(cfg)
        self.assertIn(('LIS','2027-03-17','2027-03-31'), jobs)
        batch, cursor = radar.next_batch(jobs, 0, 3)
        self.assertEqual(len(batch), 3)
        self.assertEqual(cursor, 3)
        self.assertTrue(all(x[2] <= '2027-03-31' for x in jobs))

    def test_alerts_deduplicate_and_compare_history(self):
        state = {'history': [], 'alerts': {}}
        offer = {'id':'flight', 'destination':'LIS', 'departure':'2027-02-20', 'return':'2027-03-06', 'price':4400}
        enriched, alerts = radar.analyze([offer], state, {'max_brl':4500,'drop_percent':10}, '2026-11-05T00:00:00+00:00')
        self.assertEqual(len(alerts), 1)
        radar.mark_sent(alerts, state, 'now')
        self.assertEqual(radar.analyze([offer], state, {'max_brl':4500,'drop_percent':10}, 'later')[1], [])
        offer = dict(offer, price=3900)
        enriched, alerts = radar.analyze([offer], state, {'max_brl':4500,'drop_percent':10}, 'later')
        self.assertEqual(len(alerts), 1)
        self.assertAlmostEqual(enriched[0]['change_percent'], -11.36, places=2)

    def test_public_snapshot_never_exports_secrets_or_test_offers(self):
        snapshot = radar.public_snapshot({'status':'test','offers':[{'price':1}], 'alerts':{'private':'secret'}, 'email':'private@example.org'}, [])
        self.assertEqual(snapshot['offers'], [])
        self.assertNotIn('email', snapshot)
        self.assertNotIn('alerts', snapshot)


if __name__ == '__main__':
    unittest.main()
