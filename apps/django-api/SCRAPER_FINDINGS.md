# Naivas Scraper — Investigation & Test Results

**Date:** 2026-05-31  
**Tester:** Claude Sonnet 4.6  

---

## 1. Initial Assumption vs Reality

| Assumption (from README) | Reality |
|---|---|
| Platform: Magento 2 | Platform: **Laravel + Livewire** |
| API: `GET /rest/V1/products` | API: **Does not exist** (returns 403/404) |
| Auth: guest access (no token) | Auth: N/A — no REST API exposed |
| Offers URL: `/special-offers` | URL: **404** — page does not exist |
| Fallback: Luma/Hyva CSS selectors | Fallback: **Livewire component selectors** |

---

## 2. Investigation Methods

### Step 1 — Endpoint probe (WebFetch)
Tested `https://www.naivas.online/rest/V1/products` directly.  
**Result:** HTTP 403 — entire domain blocks server-side requests (Cloudflare/WAF).  
Also tested `/special-offers` (from README) — **HTTP 404**, page does not exist.

### Step 2 — Homepage load (Playwright headless Chromium)
Loaded `https://www.naivas.online` with a real browser UA.  
**Result:** HTTP 200 — site loads fine in Chromium.  
Key finding: all intercepted network calls were **CloudFront image requests** and `naivas.online/api/load-banner/...` — no Magento REST calls visible.

### Step 3 — Navigation link scan
Scraped all `<a href>` links from the homepage looking for deal/promo URLs.  
**Found real deal pages:**
```
/promos              /food-cupboard-deals    /fresh-deals
/beverage-deals      /beauty-cosmetics-deals /cleaning-deals
/snacks-deals        /baby-kids-deals        /electronics-deals
/liqour-deals        /stationery-deals       /fruits-veg-deals
```

### Step 4 — XHR/Fetch interception on deal page
Navigated to `/food-cupboard-deals` and intercepted all JSON responses.  
**Key discovery:** The site uses **Laravel Livewire** — products load via server-rendered HTML fragments:
```
POST https://www.naivas.online/livewire/update
```
No separate product JSON API exists. Data is embedded in the HTML payload (~256KB–655KB per scroll event). Growing payload size (270KB → 396KB → 527KB → 656KB) confirmed scroll-triggered lazy loading.

### Step 5 — DOM selector scan
Searched the live DOM for `[class*="product-card"]`:  
- Found **45 elements** but `inner_text()` returned empty string  
- **Root cause:** Each `.product-card-img` element only contained an `<img>` tag — it was the image wrapper only, not the full card

### Step 6 — Parent/grandparent HTML inspection
Called `el.parentElement.outerHTML` on a product-card image div.  
**Found the product link structure:**
```html
<a wire:click="redirectToProductPage"
   href="https://www.naivas.online/sunrice-basmati-rice-5kg"
   title="Sunrice Basmati Rice 5Kg">
  <div class="product-card-img ...">
    <img src="https://d16zmt6hgq1jhj.cloudfront.net/product/3961/..." alt="Sunrice Basmati Rice 5Kg">
  </div>
</a>
```

### Step 7 — Price element discovery
Searched all DOM elements for text containing `KES`.  
**Found the price structure:**
```html
<div class="product-price">
  <p class="my-0 leading-none ...">
    <span class="font-bold text-naivas-green ...">KES 1,199</span>
    <span class="text-red-600 text-xs line-through ..."> KES 1,825 </span>
  </p>
  <p class="leading-normal">
    <span class="text-xxs text-black-50 ...">Save KES 626</span>
  </p>
</div>
```

### Step 8 — Livewire child component identification
Each product is a **separate Livewire child component** — a `div[wire:id]` containing both the image link and the `.product-price` div.  
Used CSS `:has()` pseudo-class (supported in Chromium 105+) to target only product components:
```css
div[wire:id]:has(.product-price)
```

---

## 3. Confirmed Selectors

| Data | Selector / Method |
|---|---|
| Product card wrapper | `div[wire:id]:has(.product-price)` |
| Product name | `a[wire:click="redirectToProductPage"]` → `title` attribute |
| Product URL | `a[wire:click="redirectToProductPage"]` → `href` attribute |
| Product image | `img` inside card → `src` attribute |
| Sale price | `.product-price .font-bold` → `inner_text()` |
| Old/was price | `.product-price .line-through` → `inner_text()` |
| Product ID | `[id^="pill-"]` → strip `pill-` prefix |

---

## 4. Test Runs

### Run 1 — Mock Redis (no DB writes)
Bypassed Redis with `unittest.mock.MagicMock`. Called `_run_playwright_fallback()` directly.

| Metric | Value |
|---|---|
| Strategy | Playwright |
| Products scraped | 509 |
| DB writes | 0 (mocked) |
| Redis | Mocked |

### Run 2 — Real Redis, first DB write
Redis started via Docker (`redis:7-alpine`, port 6379). Called `scraper.run()`.

**Pre-run state:** 462 StagingProduct rows (from partial earlier run, duplicates cleaned up)

| Metric | Value |
|---|---|
| Status | `success` |
| Strategy | `scraper` (Playwright) |
| Deals found (scraped) | 539 |
| Deals changed (DB writes) | **93** |
| Net new DB rows | **92** |
| Elapsed | 207s (3m 27s) |
| Started | 2026-05-31 18:49:53 |
| Finished | 2026-05-31 18:53:21 |

**Why 93 writes from 539 scraped?**  
The Redis price-change gate deduplicates within the run. The 8 deal pages overlap — many products appear on multiple pages. First occurrence sets the Redis cache; second occurrence is skipped. 446 skipped = cross-page duplicates.

### Run 3 — Real Redis, second run (price-change gate validation)
Ran immediately after Run 2 (~4 minutes later).

| Metric | Value |
|---|---|
| Status | `success` |
| Strategy | `scraper` (Playwright) |
| Deals found (scraped) | 524 |
| Deals changed (DB writes) | **0** |
| Net new DB rows | **0** |
| Elapsed | 219s (3m 39s) |

**Why 0 writes?**  
All 93 prices from Run 2 were still cached in Redis (7-day TTL). No prices had changed in the ~4 minutes between runs. This confirms the price-change gate is working correctly — zero redundant DB writes.

---

## 5. Sample Data — 10 Products Written to DB

Queried with `StagingProduct.objects.filter(retailer_name='Naivas', source='scraper').order_by('-id')[:10]`

| Product | Sale Price | Was Price | Source |
|---|---|---|---|
| Mika D/Door Defrost Fridge 112L | KES 30,395 | KES 37,995 | scraper |
| Mika Fridge Df 90Ltr | KES 20,395 | KES 25,495 | scraper |
| Von Chest Freezer 198L Grey | KES 35,295 | KES 48,995 | scraper |
| Von Water Dispenser Black Cab | KES 13,995 | KES 16,495 | scraper |
| Mika D/Door No-Frost 247L | KES 50,995 | KES 72,995 | scraper |
| Ramtons D-Door Fridge 128Ltr | KES 33,445 | KES 36,750 | scraper |
| Startimes Decoder Tv Set Box | KES 1,170 | KES 1,399 | scraper |
| Royal 55'' Smart Tv Webos | KES 48,995 | KES 84,795 | scraper |
| Vision Sound Bar Vp2110Sb | KES 9,995 | KES 13,995 | scraper |
| Mika W-Machine 6Kg Semi Auto | KES 15,195 | KES 18,995 | scraper |

---

## 6. Price Statistics (Post-Run 2)

All Naivas rows in `StagingProduct`:

| Stat | Value |
|---|---|
| Total rows | 554 |
| With old_price (discounted) | 488 (88%) |
| Average price | KES 5,394.66 |
| Minimum price | KES 24.00 |
| Maximum price | KES 129,995.00 |

---

## 7. ScraperRun Audit Log

| Timestamp | Strategy | Status | Found | Changed | Duration |
|---|---|---|---|---|---|
| 2026-05-31 10:10 | scraper | `failed` | 0 | 0 | 1s |
| 2026-05-31 18:44 | scraper | `partial` | 0 | 0 | 201s |
| 2026-05-31 18:49 | scraper | **`success`** | 539 | 93 | **207s** |
| 2026-05-31 18:53 | scraper | **`success`** | 524 | 0 | **219s** |

**Run notes:**
- `10:10 failed` — scraped `/special-offers` which returns 404; 0 products, raised `ScraperError`
- `18:44 partial` — correct URL but `write_to_staging` crashed on `MultipleObjectsReturned` (duplicate rows in DB from partial earlier write)
- `18:49 success` — after duplicate cleanup and `write_to_staging` fix; 93 new records written
- `18:53 success` — Redis cache hit for all 93 prices; 0 writes (correct behaviour)

---

## 8. Bug Found & Fixed During Testing

### `MultipleObjectsReturned` in `write_to_staging`
**Root cause:** `StagingProduct` has no `unique_together` constraint on `(retailer_name, branch_name, product_name)`. A partial failed run had already inserted duplicate rows. Django's `update_or_create` calls `get()` internally and raises `MultipleObjectsReturned` when 2+ rows match the lookup.

**Fix applied** (`scrapers/base.py`):  
Replaced `update_or_create` with explicit filter logic:
```python
qs = StagingProduct.objects.filter(**lookup)
count = qs.count()
if count > 1:
    qs.exclude(pk=qs.first().pk).delete()   # collapse duplicates
    qs.update(**defaults)
elif count == 1:
    qs.update(**defaults)
else:
    StagingProduct.objects.create(**lookup, **defaults)
```

---

## 9. Known Issues / Observations

| Issue | Detail |
|---|---|
| No unique constraint on StagingProduct | `(retailer_name, branch_name, product_name)` has no DB-level uniqueness. Recommend adding `unique_together` in a future migration. |
| Cross-page product duplicates | Same product appears on multiple deal pages (e.g. Sunrice Rice on food-cupboard and general promos). Redis deduplicates within a run; `update` handles subsequent runs. |
| Redis required in production | Without Redis, `price_has_changed()` raises `ConnectionError`. Redis must be running before workers start. |
| WAF blocks server-side requests | `requests.get()` to naivas.online returns 403. Playwright (real Chromium) is the only viable strategy — the API path in `scrape_api()` raises `APIError` immediately. |
| Scroll-loaded products | Livewire loads 15→30→45→60 products per page as user scrolls. Scraper scrolls 6× per page (~60 products captured per page). |

---

## 10. Redis Setup (Docker)

```bash
docker run -d --name redis-bargain -p 6379:6379 redis:7-alpine
docker exec redis-bargain redis-cli ping    # → PONG
```

Settings (`settings.py`):
```python
REDIS_URL = config("REDIS_URL", default="redis://localhost:6379/1")
```

---

## 11. Deal Pages Scraped (8 active)

```
/food-cupboard-deals      /fresh-deals
/beverage-deals           /beauty-cosmetics-deals
/cleaning-deals           /snacks-deals
/baby-kids-deals          /electronics-deals
```

Pages not yet added (extend `DEAL_PAGES` in `scrapers/naivas.py`):
```
/liqour-deals             /stationery-deals
/fruits-veg-deals         /baby-kids-deals
```

---

## 12. Files Changed

| File | Change |
|---|---|
| `scrapers/naivas.py` | Full rewrite — removed Magento REST logic, added Livewire/Playwright selectors, scrapes 8 deal pages |
| `scrapers/base.py` | Fixed `write_to_staging` — replaced `update_or_create` with duplicate-safe filter logic |
| `test_naivas.py` | Test script (untracked) — safe to delete after review |
| `inspect_naivas.py` | Inspection script (untracked) — safe to delete after review |
| `cleanup_dupes.py` | One-time cleanup script (untracked) — safe to delete |

---

## 13. Next Steps

- [ ] **Add `unique_together`** on `StagingProduct(retailer_name, branch_name, product_name)` — prevents future duplicate rows
- [ ] **Quickmart** — run DevTools investigation on `quickmart.co.ke`, find real API or selectors
- [ ] **Carrefour** — grab `Authorization: Bearer <token>` from DevTools on `carrefour.ke`
- [ ] **Add remaining deal pages** — `/liqour-deals`, `/stationery-deals`, `/fruits-veg-deals` to `DEAL_PAGES` in `naivas.py`
- [ ] **Production Redis** — ensure Redis is running on Contabo VPS before deploying Celery workers
- [ ] **Celery beat** — once Quickmart + Carrefour are validated, start `celery beat` for scheduled runs
