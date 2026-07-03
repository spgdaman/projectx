// Retailer-specific selectors and URL pattern matchers.
// Loaded as a non-module content script before content_script.js — sets window global.
// Selectors need re-verification if retailer sites update their DOM structure.
window.BHK_RETAILER_CONFIG = {
  'naivas.online': {
    name: 'Naivas',
    // Livewire/Laravel site — slug URLs like /dola-all-purpose-flour-2kg
    productPagePattern: /^\/[a-z0-9][a-z0-9-]+-[a-z0-9][a-z0-9-]*$/i,
    productNameSelector: 'h1, h2.product-name, [class*="product-title"], [class*="product-name"]',
    // Parse product name from page title: "Jogoo Maize Meal 2Kg | Naivas Online" → "Jogoo Maize Meal 2Kg"
    titleParser: function (title) {
      return title.split(/[|\-–]/)[0].trim();
    },
    priceSelector: '.product-price .font-bold, .font-bold[class*="price"], .price',
  },
  'carrefour.ke': {
    name: 'Carrefour',
    productPagePattern: /\/p\/[A-Z0-9]+\//i,
    productNameSelector: 'h1[data-testid="title"], h1.css-1i6r2gn, h1[class*="title"], h1',
    titleParser: function (title) { return title.split(/[|\-–]/)[0].trim(); },
    priceSelector: '[data-testid="special-price"], [data-testid="price"], [class*="price"]',
  },
  'chandarana.co.ke': {
    name: 'Chandarana',
    productPagePattern: /\/product\/|\/shop\/[^/]+\/[^/]+/,
    productNameSelector: 'h1.product_title, .woocommerce-page h1, h1',
    titleParser: function (title) { return title.split(/[|\-–]/)[0].trim(); },
    priceSelector: '.woocommerce-Price-amount.amount bdi, .price ins .woocommerce-Price-amount bdi, .price .woocommerce-Price-amount bdi',
  },
  'foodplus.co.ke': {
    name: 'FoodPlus',
    productPagePattern: /\/product\/|\/shop\/[^/]+\/[^/]+/,
    productNameSelector: 'h1.product_title, .product-title h1, h1',
    titleParser: function (title) { return title.split(/[|\-–]/)[0].trim(); },
    priceSelector: '.woocommerce-Price-amount bdi, .price .amount',
  },
};
