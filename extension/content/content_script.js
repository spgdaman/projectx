(function () {
  'use strict';

  const hostname = location.hostname.replace(/^www\./, '');
  const config = window.BHK_RETAILER_CONFIG && window.BHK_RETAILER_CONFIG[hostname];
  if (!config) return;

  function onProductPage() {
    return config.productPagePattern.test(location.pathname + location.search);
  }

  function extractText(selector) {
    try {
      const el = document.querySelector(selector);
      return el ? el.textContent.trim() : null;
    } catch {
      return null;
    }
  }

  function extractPrice(selector) {
    try {
      const el = document.querySelector(selector);
      if (!el) return null;
      const num = parseFloat(el.textContent.replace(/[^0-9.]/g, ''));
      return isNaN(num) ? null : num;
    } catch {
      return null;
    }
  }

  // ── Shadow DOM badge ───────────────────────────────────────────────────────

  let badgeHost = null;
  let badgeShadow = null;

  const BADGE_CSS = `
    .bhk-badge {
      position: fixed;
      top: 20px;
      right: 20px;
      z-index: 2147483647;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      font-size: 13px;
      background: #fff;
      border: 1.5px solid #E54416;
      border-radius: 12px;
      box-shadow: 0 4px 16px rgba(0,0,0,0.14);
      padding: 10px 14px;
      max-width: 230px;
      cursor: pointer;
      user-select: none;
      transition: box-shadow 0.15s;
    }
    .bhk-badge:hover { box-shadow: 0 6px 20px rgba(0,0,0,0.2); }
    .bhk-badge-header {
      font-size: 10px;
      font-weight: 700;
      color: #E54416;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      margin-bottom: 4px;
    }
    .bhk-badge-price {
      font-size: 18px;
      font-weight: 700;
      color: #111827;
    }
    .bhk-badge-retailer {
      font-size: 11px;
      color: #6B7280;
      margin-top: 1px;
    }
    .bhk-badge-savings {
      margin-top: 5px;
      font-size: 11px;
      font-weight: 600;
      color: #E54416;
    }
    .bhk-badge-loading {
      font-size: 12px;
      color: #6B7280;
      padding: 2px 0;
    }
    .bhk-badge-close {
      position: absolute;
      top: 6px;
      right: 8px;
      font-size: 16px;
      line-height: 1;
      color: #9CA3AF;
      cursor: pointer;
      background: none;
      border: none;
      padding: 0;
    }
    .bhk-badge-close:hover { color: #6B7280; }
  `;

  function createBadge() {
    if (badgeHost) return;
    badgeHost = document.createElement('div');
    badgeHost.id = 'bhk-price-badge';
    document.body.appendChild(badgeHost);
    badgeShadow = badgeHost.attachShadow({ mode: 'closed' });

    const style = document.createElement('style');
    style.textContent = BADGE_CSS;
    badgeShadow.appendChild(style);

    const badge = document.createElement('div');
    badge.className = 'bhk-badge';
    badge.innerHTML = `
      <button class="bhk-badge-close" title="Dismiss">&times;</button>
      <div class="bhk-badge-header">&#128293; Bargain Hunters</div>
      <div class="bhk-badge-loading">Checking prices&hellip;</div>
    `;
    _attachBadgeListeners(badge);
    badgeShadow.appendChild(badge);
  }

  function _attachBadgeListeners(badge) {
    const closeBtn = badge.querySelector('.bhk-badge-close');
    if (closeBtn) {
      closeBtn.addEventListener('click', function (e) {
        e.stopPropagation();
        removeBadge();
      });
    }
    badge.addEventListener('click', function () {
      try { chrome.runtime.sendMessage({ type: 'OPEN_POPUP' }); } catch { /* ignore */ }
    });
  }

  function updateBadge(cheaperResults, currentPrice) {
    if (!badgeShadow) return;
    const badge = badgeShadow.querySelector('.bhk-badge');
    if (!badge) return;

    const best = cheaperResults[0];
    const saving = currentPrice ? Math.round(currentPrice - best.price) : null;
    const savingHtml = saving && saving > 0
      ? `<div class="bhk-badge-savings">&#127381; Save KES ${saving.toLocaleString()} vs here</div>`
      : '';

    badge.innerHTML = `
      <button class="bhk-badge-close" title="Dismiss">&times;</button>
      <div class="bhk-badge-header">&#128293; Cheaper elsewhere</div>
      <div class="bhk-badge-price">KES ${best.price.toLocaleString()}</div>
      <div class="bhk-badge-retailer">at ${best.retailer}</div>
      ${savingHtml}
    `;
    _attachBadgeListeners(badge);
  }

  function removeBadge() {
    if (badgeHost) {
      badgeHost.remove();
      badgeHost = null;
      badgeShadow = null;
    }
  }

  // ── Main logic ─────────────────────────────────────────────────────────────

  let lastPathname = location.pathname;
  let currentProductName = null;

  async function checkPage() {
    console.log('[BHK] path:', location.pathname, '| product page?', onProductPage());
    if (!onProductPage()) return;

    // Try DOM selector first, fall back to document.title parser
    let productName = extractText(config.productNameSelector);
    // Reject modal/overlay text — real product names are short and don't ask questions
    if (productName && (productName.length > 80 || productName.includes('confirm') || productName.includes('please'))) {
      productName = null;
    }
    if (!productName && config.titleParser) {
      const parsed = config.titleParser(document.title);
      // Only use if it looks like a real product name (not a generic site title)
      if (parsed && parsed.length > 3 && parsed.length < 80) productName = parsed;
    }
    console.log('[BHK] product name found:', productName, '| title:', document.title);
    if (!productName || productName === currentProductName) return;

    currentProductName = productName;
    createBadge();

    const currentPrice = extractPrice(config.priceSelector);
    const data = await window.BHK_fetchComparison(productName);
    console.log('[BHK] API response:', data, '| current price:', currentPrice);

    if (!data || !data.results || data.results.length === 0) return;

    // Only show badge when a DIFFERENT retailer has a cheaper price.
    // If only same-retailer results exist, the user is already at the source.
    const otherRetailers = data.results.filter(function (r) { return r.retailer !== config.name; });
    const cheaperElsewhere = otherRetailers.filter(function (r) {
      return !currentPrice || r.price < currentPrice;
    });

    if (cheaperElsewhere.length === 0) {
      removeBadge();
      return;
    }

    updateBadge(cheaperElsewhere, currentPrice);

    try {
      chrome.runtime.sendMessage({
        type: 'TRACK_EVENT',
        event: 'extension_comparison_shown',
        properties: {
          product_query: productName,
          matched_name: data.matched_name,
          current_retailer: config.name,
          current_price: currentPrice,
          cheaper_count: cheaperElsewhere.length,
          cheapest_retailer: cheaperElsewhere[0].retailer,
          cheapest_price: cheaperElsewhere[0].price,
        },
      });
    } catch { /* ignore */ }
  }

  // Respond to popup requests for product info
  chrome.runtime.onMessage.addListener(function (msg, _sender, sendResponse) {
    if (msg.type === 'GET_PRODUCT_INFO') {
      sendResponse({
        name: extractText(config.productNameSelector),
        price: extractPrice(config.priceSelector),
        retailer: config.name,
      });
    }
    return true;
  });

  // Run on load
  checkPage();

  // Retry at 2 s and 5 s to catch age-gate dismissals and lazy-loaded product titles
  setTimeout(checkPage, 2000);
  setTimeout(checkPage, 5000);

  // Watch direct children of <body> for modal removal (age gates, cookie banners)
  // subtree:false avoids firing on every text/attribute change in the whole page
  let debounceTimer = null;
  new MutationObserver(function () {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(checkPage, 600);
  }).observe(document.body, { childList: true, subtree: false });

  // SPA navigation — watch title element for URL changes
  const titleEl = document.querySelector('title');
  if (titleEl) {
    new MutationObserver(function () {
      if (location.pathname !== lastPathname) {
        lastPathname = location.pathname;
        currentProductName = null;
        removeBadge();
        setTimeout(checkPage, 800);
      }
    }).observe(titleEl, { childList: true });
  }
})();
