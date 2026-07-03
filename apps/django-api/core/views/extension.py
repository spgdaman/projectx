import json
import time
import logging
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.conf import settings
from django.utils.text import slugify

import redis as redis_lib
from rapidfuzz import process, fuzz

from core.models import Deal

logger = logging.getLogger(__name__)

MATCH_THRESHOLD = 86
CACHE_TTL = 14400      # 4 hours
RATE_LIMIT = 60
RATE_WINDOW = 60       # seconds


def _get_redis():
    url = getattr(settings, 'REDIS_URL', 'redis://127.0.0.1:6379/1')
    return redis_lib.Redis.from_url(url, decode_responses=True)


def _get_client_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '127.0.0.1')


def _check_rate_limit(ip):
    """Returns True if request is within limit."""
    window_bucket = int(time.time()) // RATE_WINDOW
    key = f'ratelimit:ext:{ip}:{window_bucket}'
    try:
        r = _get_redis()
        count = r.incr(key)
        if count == 1:
            r.expire(key, RATE_WINDOW * 2)
        return count <= RATE_LIMIT
    except Exception:
        return True  # fail open on Redis error


def _cors(response):
    response['Access-Control-Allow-Origin'] = '*'
    return response


@csrf_exempt
@require_http_methods(['POST', 'OPTIONS'])
def extension_compare(request):
    if request.method == 'OPTIONS':
        resp = JsonResponse({})
        resp['Access-Control-Allow-Origin'] = '*'
        resp['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        resp['Access-Control-Allow-Headers'] = 'Content-Type'
        return resp

    ip = _get_client_ip(request)
    if not _check_rate_limit(ip):
        return _cors(JsonResponse({'detail': 'Rate limit exceeded.'}, status=429))

    try:
        body = json.loads(request.body)
        q = str(body.get('q', '')).strip()
    except (json.JSONDecodeError, AttributeError):
        return _cors(JsonResponse({'detail': 'Invalid JSON.'}, status=400))

    if not q:
        return _cors(JsonResponse({'detail': 'q is required.'}, status=400))

    cache_key = f'ext_compare:{slugify(q)}'

    try:
        r = _get_redis()
        cached = r.get(cache_key)
        if cached:
            resp = JsonResponse(json.loads(cached))
            resp['X-Cache'] = 'HIT'
            return _cors(resp)
    except Exception:
        pass

    deals_qs = (
        Deal.objects
        .select_related('product', 'retailer')
        .only(
            'current_price', 'link', 'scraped_at',
            'product__name', 'product__url',
            'retailer__name',
        )
    )

    candidates = [(deal.product.name, deal) for deal in deals_qs]

    empty_data = {
        'matched_name': None, 'match_score': 0, 'results': [],
        'cheapest_retailer': None, 'savings': 0, 'savings_pct': 0,
    }

    if not candidates:
        return _cors(JsonResponse(empty_data))

    names = [c[0] for c in candidates]
    matches = process.extract(
        q, names,
        scorer=fuzz.token_sort_ratio,
        score_cutoff=MATCH_THRESHOLD,
        limit=None,
    )

    if not matches:
        try:
            _get_redis().setex(cache_key, CACHE_TTL, json.dumps(empty_data))
        except Exception:
            pass
        return _cors(JsonResponse(empty_data))

    best_match = max(matches, key=lambda m: m[1])
    matched_name = best_match[0]
    top_score = round(float(best_match[1]), 1)

    # Lowest price per retailer wins when multiple rows match
    by_retailer: dict[str, dict] = {}
    for _product_name, _score, idx in matches:
        deal = candidates[idx][1]
        retailer = deal.retailer.name
        price = float(deal.current_price)
        if retailer not in by_retailer or price < by_retailer[retailer]['price']:
            by_retailer[retailer] = {
                'retailer': retailer,
                'price': price,
                'currency': 'KES',
                'url': deal.link or deal.product.url or '',
                'in_stock': True,
                'last_updated': deal.scraped_at.isoformat(),
            }

    results = sorted(by_retailer.values(), key=lambda x: x['price'])

    savings = 0.0
    savings_pct = 0.0
    if len(results) > 1:
        cheapest_price = results[0]['price']
        priciest_price = results[-1]['price']
        savings = round(priciest_price - cheapest_price, 2)
        if priciest_price > 0:
            savings_pct = round((savings / priciest_price) * 100, 1)

    data = {
        'matched_name': matched_name,
        'match_score': top_score,
        'results': results,
        'cheapest_retailer': results[0]['retailer'] if results else None,
        'savings': savings,
        'savings_pct': savings_pct,
    }

    try:
        _get_redis().setex(cache_key, CACHE_TTL, json.dumps(data))
    except Exception:
        pass

    return _cors(JsonResponse(data))
