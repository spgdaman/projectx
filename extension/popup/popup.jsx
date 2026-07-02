import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';

const API_BASE = 'https://www.bargainhunters.co.ke/api/v1';

// ── Spinner ───────────────────────────────────────────────────────────────────
function Spinner() {
  return (
    <div style={{ textAlign: 'center', padding: '28px 0' }}>
      <div style={{
        width: 32, height: 32, border: '3px solid #FDEBD0',
        borderTopColor: '#E54416', borderRadius: '50%',
        margin: '0 auto 10px',
        animation: 'spin 0.8s linear infinite',
      }} />
      <p style={{ fontSize: 13, color: '#6B7280' }}>Checking prices&hellip;</p>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

// ── Results ───────────────────────────────────────────────────────────────────
function ResultsView({ data, productName }) {
  const sorted = [...data.results].sort((a, b) => a.price - b.price);
  return (
    <div>
      <div style={{ background: '#E54416', padding: '12px 16px' }}>
        <div style={{ fontSize: 10, fontWeight: 700, color: 'rgba(255,255,255,0.8)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Best price for
        </div>
        <div style={{ fontSize: 13, fontWeight: 600, color: '#fff', marginTop: 2, lineHeight: 1.3, wordBreak: 'break-word' }}>
          {data.matched_name || productName}
        </div>
      </div>

      <div style={{ padding: '4px 0', background: '#fff' }}>
        {sorted.map((r, i) => (
          <a
            key={r.retailer}
            href={r.url}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: '10px 16px', textDecoration: 'none', color: 'inherit',
              background: i === 0 ? '#FFF9F1' : '#fff',
              borderBottom: i < sorted.length - 1 ? '1px solid #E5E7EB' : 'none',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              {i === 0 && (
                <span style={{
                  background: '#E54416', color: '#fff', fontSize: 9, fontWeight: 700,
                  padding: '2px 5px', borderRadius: 4, letterSpacing: '0.04em', flexShrink: 0,
                }}>
                  BEST
                </span>
              )}
              <span style={{ fontSize: 13, fontWeight: i === 0 ? 600 : 400 }}>{r.retailer}</span>
            </div>
            <span style={{ fontSize: 14, fontWeight: 700, color: i === 0 ? '#E54416' : '#111827', flexShrink: 0, marginLeft: 8 }}>
              KES {r.price.toLocaleString()}
            </span>
          </a>
        ))}
      </div>

      {data.savings > 0 && (
        <div style={{
          margin: '8px 12px', padding: '8px 12px',
          background: '#FDEBD0', borderRadius: 8, fontSize: 12, color: '#C73D0F', fontWeight: 600,
        }}>
          Save KES {data.savings.toLocaleString()} ({data.savings_pct}%) vs most expensive
        </div>
      )}

      <div style={{ padding: '8px 12px 12px' }}>
        <a
          href="https://www.bargainhunters.co.ke/deals"
          target="_blank"
          rel="noopener noreferrer"
          style={{
            display: 'block', textAlign: 'center', background: '#E54416',
            color: '#fff', fontSize: 12, fontWeight: 700, padding: '8px',
            borderRadius: 8, textDecoration: 'none',
          }}
        >
          Browse all deals &rarr;
        </a>
      </div>
    </div>
  );
}

// ── No match ──────────────────────────────────────────────────────────────────
function NoMatchView({ productName }) {
  return (
    <div style={{ padding: '24px 20px', textAlign: 'center' }}>
      <div style={{ fontSize: 30, marginBottom: 10 }}>&#128269;</div>
      <div style={{ fontSize: 13, fontWeight: 600, color: '#111827', marginBottom: 6 }}>
        No match found
      </div>
      <div style={{ fontSize: 12, color: '#6B7280', lineHeight: 1.5 }}>
        &ldquo;{productName}&rdquo; isn&rsquo;t tracked yet.
      </div>
      <a
        href="https://www.bargainhunters.co.ke/deals"
        target="_blank"
        rel="noopener noreferrer"
        style={{
          display: 'inline-block', marginTop: 14, fontSize: 12,
          color: '#E54416', fontWeight: 600, textDecoration: 'none',
        }}
      >
        Browse all deals &rarr;
      </a>
    </div>
  );
}

// ── Error ─────────────────────────────────────────────────────────────────────
function ErrorView({ onRetry }) {
  return (
    <div style={{ padding: '24px 20px', textAlign: 'center' }}>
      <div style={{ fontSize: 30, marginBottom: 10 }}>&#9888;&#65039;</div>
      <div style={{ fontSize: 13, fontWeight: 600, color: '#111827', marginBottom: 6 }}>
        Connection error
      </div>
      <div style={{ fontSize: 12, color: '#6B7280', marginBottom: 14 }}>
        Could not reach Bargain Hunters servers.
      </div>
      <button
        onClick={onRetry}
        style={{
          background: '#E54416', color: '#fff', border: 'none',
          borderRadius: 8, padding: '8px 20px', fontSize: 12,
          fontWeight: 700, cursor: 'pointer',
        }}
      >
        Retry
      </button>
    </div>
  );
}

// ── Idle (not on a product page) ──────────────────────────────────────────────
function IdleView() {
  return (
    <div style={{ padding: '24px 20px', textAlign: 'center' }}>
      <div style={{ fontSize: 30, marginBottom: 10 }}>&#128722;</div>
      <div style={{ fontSize: 13, fontWeight: 600, color: '#111827', marginBottom: 6 }}>
        Bargain Hunters Kenya
      </div>
      <div style={{ fontSize: 12, color: '#6B7280', lineHeight: 1.6 }}>
        Visit a product page on Naivas, Carrefour, Chandarana, or FoodPlus to compare prices instantly.
      </div>
    </div>
  );
}

// ── Header ────────────────────────────────────────────────────────────────────
function Header() {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 8,
      padding: '10px 14px', borderBottom: '1px solid #E5E7EB', background: '#fff',
    }}>
      <span style={{ fontSize: 18 }}>&#128293;</span>
      <span style={{ fontSize: 13, fontWeight: 700, color: '#E54416' }}>Bargain Hunters</span>
      <span style={{ marginLeft: 'auto', fontSize: 10, color: '#9CA3AF', fontWeight: 600 }}>KENYA</span>
    </div>
  );
}

// ── App root ──────────────────────────────────────────────────────────────────
function App() {
  // States: loading | results | no_match | error | idle
  const [state, setState] = useState('loading');
  const [data, setData] = useState(null);
  const [productName, setProductName] = useState('');

  async function run() {
    setState('loading');
    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (!tab?.id) { setState('idle'); return; }

      let info = null;
      try {
        info = await chrome.tabs.sendMessage(tab.id, { type: 'GET_PRODUCT_INFO' });
      } catch {
        setState('idle');
        return;
      }

      if (!info?.name) { setState('idle'); return; }
      setProductName(info.name);

      const res = await fetch(`${API_BASE}/extension/compare/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ q: info.name }),
      });

      if (!res.ok) { setState('error'); return; }

      const json = await res.json();
      if (!json.results || json.results.length === 0) {
        setState('no_match');
      } else {
        setData(json);
        setState('results');
        chrome.runtime.sendMessage({
          type: 'TRACK_EVENT',
          event: 'popup_comparison_shown',
          properties: {
            product_query: info.name,
            matched_name: json.matched_name,
            result_count: json.results.length,
            cheapest_retailer: json.cheapest_retailer,
          },
        });
      }
    } catch {
      setState('error');
    }
  }

  useEffect(() => { run(); }, []);

  return (
    <div>
      <Header />
      {state === 'loading'  && <Spinner />}
      {state === 'results'  && <ResultsView data={data} productName={productName} />}
      {state === 'no_match' && <NoMatchView productName={productName} />}
      {state === 'error'    && <ErrorView onRetry={run} />}
      {state === 'idle'     && <IdleView />}
    </div>
  );
}

createRoot(document.getElementById('root')).render(<App />);
