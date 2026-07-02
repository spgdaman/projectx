# Bargain Hunters Kenya — Chrome Extension

## Overview

A Manifest V3 Chrome extension that overlays a price-comparison badge on product pages across Naivas, Carrefour, Chandarana, and FoodPlus. The popup shows a sortable price table for the current product across all retailers, powered by the `POST /api/v1/extension/compare/` endpoint.

---

## Directory structure

```
extension/
├── manifest.json                 # MV3 manifest
├── package.json                  # Vite dev build
├── vite.config.js                # Builds popup.jsx → popup/popup.js
├── .gitignore                    # Excludes node_modules, built popup.js
├── icons/                        # 16×16, 48×48, 128×128 PNG icons (add before publishing)
├── background/
│   └── background.js             # Service worker — PostHog analytics proxy
├── content/
│   ├── content_script.js         # Badge injection, product extraction, SPA nav
│   └── badge.css                 # Shadow host reset; actual styles injected inline
├── popup/
│   ├── popup.html                # Extension popup shell
│   ├── popup.jsx                 # React popup — 4 states (loading/results/no_match/error)
│   └── popup.js                  # Built by Vite (gitignored — run npm run build)
└── utils/
    ├── retailer_config.js        # Per-retailer URL patterns & CSS selectors
    └── api_client.js             # window.BHK_fetchComparison() for content script
```

---

## Backend endpoint

```
POST /api/v1/extension/compare/
Content-Type: application/json
Authorization: none (anonymous)

Body: { "q": "product name string" }

Response 200:
{
  "matched_name": "Milo Chocolate Malt Drink 200g",
  "match_score": 95.2,
  "results": [
    { "retailer": "Naivas", "price": 120.0, "currency": "KES",
      "url": "https://...", "in_stock": true, "last_updated": "2026-06-19T08:00:00" }
  ],
  "cheapest_retailer": "Naivas",
  "savings": 15.0,
  "savings_pct": 11.1
}

Response 429: { "detail": "Rate limit exceeded." }   (>60 req/min per IP)
Response 400: { "detail": "q is required." }
```

Matching uses `rapidfuzz.fuzz.token_sort_ratio` with a threshold of 82. Results are cached in Redis for 4 hours (`ext_compare:<slugified-query>`). Rate limiting uses a Redis counter per IP per 60-second window.

---

## Installation (developer / unpacked)

1. **Build the popup:**
   ```bash
   cd extension
   npm install
   npm run build
   ```
   This outputs `extension/popup/popup.js`.

2. **Add icons** — place `icon16.png`, `icon48.png`, `icon128.png` in `extension/icons/`. Brand colour `#E54416` recommended.

3. **Load in Chrome:**
   - Open `chrome://extensions`
   - Enable **Developer mode**
   - Click **Load unpacked** → select the `extension/` directory

---

## Retailer selectors

Selectors are in `extension/utils/retailer_config.js`. They need to be verified against each retailer's live DOM — they may drift as sites update.

| Retailer | Domain | Notes |
|---|---|---|
| Naivas | naivas.online | Magento-based; `.page-title .base` for product name |
| Carrefour | www.carrefour.ke | React SPA; `h1[data-testid="title"]` |
| Chandarana | chandarana.co.ke | WooCommerce; `h1.product_title` |
| FoodPlus | foodplus.co.ke | WooCommerce; `h1.product_title` |

---

## Analytics

PostHog EU Cloud (`eu.i.posthog.com`). Events fired from `background.js`:

| Event | When |
|---|---|
| `extension_installed` | First install |
| `extension_updated` | Extension update |
| `extension_comparison_shown` | Badge displayed after successful API match |
| `popup_comparison_shown` | User opens popup and results load |

A persistent `distinct_id` UUID is stored in `chrome.storage.local`.

---

## Publishing checklist

- [ ] Add real PNG icons in `extension/icons/`
- [ ] Verify CSS selectors on live retailer sites
- [ ] Run `npm run build` in `extension/`
- [ ] Test as unpacked extension across all 4 retailer domains
- [ ] Create Chrome Web Store developer account
- [ ] Upload as zip of `extension/` directory (excluding `node_modules`, `*.jsx`)
