import json
from unittest.mock import patch, MagicMock
from django.test import TestCase, RequestFactory
from django.utils import timezone

from core.views.extension import extension_compare, CACHE_TTL


class ExtensionCompareViewTest(TestCase):

    def setUp(self):
        self.factory = RequestFactory()

    def _post(self, body, ip='1.2.3.4'):
        req = self.factory.post(
            '/api/v1/extension/compare/',
            data=json.dumps(body),
            content_type='application/json',
        )
        req.META['REMOTE_ADDR'] = ip
        return req

    def _mock_deal(self, name='Milo 200g', retailer='Naivas', price=120.0,
                   link='https://naivas.online/milo'):
        deal = MagicMock()
        deal.product.name = name
        deal.product.url = link
        deal.retailer.name = retailer
        deal.current_price = price
        deal.link = link
        deal.scraped_at = timezone.now()
        return deal

    # ── Test 1: match found returns comparison results ────────────────────────

    @patch('core.views.extension._get_redis')
    @patch('core.views.extension.Deal')
    def test_compare_returns_results_when_match_found(self, MockDeal, mock_get_redis):
        mock_redis = MagicMock()
        mock_redis.get.return_value = None
        mock_redis.incr.return_value = 1
        mock_get_redis.return_value = mock_redis

        MockDeal.objects.select_related.return_value.only.return_value = [
            self._mock_deal('Milo 200g', 'Naivas', 120.0),
            self._mock_deal('Milo 200g', 'Carrefour', 135.0),
        ]

        resp = extension_compare(self._post({'q': 'Milo 200g'}))

        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertEqual(data['matched_name'], 'Milo 200g')
        self.assertEqual(len(data['results']), 2)
        self.assertEqual(data['cheapest_retailer'], 'Naivas')
        self.assertEqual(data['savings'], 15.0)
        self.assertGreater(data['savings_pct'], 0)
        self.assertEqual(resp['Access-Control-Allow-Origin'], '*')

    # ── Test 2: no match returns empty results ────────────────────────────────

    @patch('core.views.extension._get_redis')
    @patch('core.views.extension.Deal')
    def test_compare_no_match_returns_empty_results(self, MockDeal, mock_get_redis):
        mock_redis = MagicMock()
        mock_redis.get.return_value = None
        mock_redis.incr.return_value = 1
        mock_get_redis.return_value = mock_redis

        # DB has a product completely unrelated to the query
        MockDeal.objects.select_related.return_value.only.return_value = [
            self._mock_deal('Sony PlayStation 5 Console', 'Naivas', 65000.0),
        ]

        resp = extension_compare(self._post({'q': 'Milo Chocolate Drink 200g'}))

        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertIsNone(data['matched_name'])
        self.assertEqual(data['results'], [])
        self.assertIsNone(data['cheapest_retailer'])

    # ── Test 3: 61st request from same IP gets 429 ───────────────────────────

    @patch('core.views.extension._get_redis')
    def test_compare_rate_limited_at_61_requests(self, mock_get_redis):
        mock_redis = MagicMock()
        mock_redis.incr.return_value = 61   # over RATE_LIMIT=60
        mock_get_redis.return_value = mock_redis

        resp = extension_compare(self._post({'q': 'Milo'}, ip='10.0.0.1'))

        self.assertEqual(resp.status_code, 429)
        data = json.loads(resp.content)
        self.assertIn('detail', data)

    # ── Test 4: result is cached in Redis on first call ───────────────────────

    @patch('core.views.extension._get_redis')
    @patch('core.views.extension.Deal')
    def test_compare_caches_response_in_redis(self, MockDeal, mock_get_redis):
        mock_redis = MagicMock()
        mock_redis.get.return_value = None
        mock_redis.incr.return_value = 1
        mock_get_redis.return_value = mock_redis

        MockDeal.objects.select_related.return_value.only.return_value = [
            self._mock_deal(),
        ]

        extension_compare(self._post({'q': 'Milo 200g'}))

        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args[0]
        cache_key, ttl, payload = call_args
        self.assertTrue(cache_key.startswith('ext_compare:'))
        self.assertEqual(ttl, CACHE_TTL)
        cached_data = json.loads(payload)
        self.assertIn('results', cached_data)
        self.assertIn('matched_name', cached_data)
