// Retailer-specific selectors and URL pattern matchers.
// Loaded as a non-module content script before content_script.js — sets window global.
// Selectors need re-verification if retailer sites update their DOM structure.
window.BHK_RETAILER_CONFIG = {
  'naivas.online': {
    name: 'Naivas',
    // Naivas uses plain slug URLs like /dola-all-purpose-flour-2kg — match any
    // single-level path with at least one hyphen; selector gating filters non-product pages.
    productPagePattern: /^\/[a-z0-9][a-z0-9-]+-[a-z0-9][a-z0-9-]*$/i,
    productNameSelector: [
      '.page-title .base',
      '.page-title-wrapper h1',
      '[data-ui-id="page-title-wrapper"] h1',
      '.product-info-main h1',
      'h1[itemprop="name"]',
      'h1.page-title',
      '.product-name h1',
    ].join(', '),
    priceSelector: [
      '[data-price-type="finalPrice"] .price',
      '.price-box .price',
      '.special-price .price',
      '.price',
    ].join(', '),
  },
  'carrefour.ke': {
    name: 'Carrefour',
    productPagePattern: /\/p\/[A-Z0-9]+\//i,
    productNameSelector: 'h1[data-testid="title"], h1.css-1i6r2gn, h1[class*="title"]',
    priceSelector: '[data-testid="special-price"] .price, [data-testid="price"] .price, [class*="price"]',
  },
  'chandarana.co.ke': {
    name: 'Chandarana',
    productPagePattern: /\/product\/|\/shop\/[^/]+\/[^/]+/,
    productNameSelector: 'h1.product_title, .woocommerce-page h1',
    priceSelector: '.woocommerce-Price-amount.amount bdi, .price ins .woocommerce-Price-amount bdi, .price .woocommerce-Price-amount bdi',
  },
  'foodplus.co.ke': {
    name: 'FoodPlus',
    productPagePattern: /\/product\/|\/shop\/[^/]+\/[^/]+/,
    productNameSelector: 'h1.product_title, .product-title h1',
    priceSelector: '.woocommerce-Price-amount bdi, .price .amount',
  },
};
