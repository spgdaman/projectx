// Loaded as non-module content script — exposes window global for content_script.js.
// Background service worker calls the API directly without this file.
const BHK_API_BASE = 'https://www.bargainhunters.co.ke/api/v1';

window.BHK_fetchComparison = async function (productName) {
  try {
    const res = await fetch(`${BHK_API_BASE}/extension/compare/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ q: productName }),
    });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
};
