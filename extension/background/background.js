// Manifest V3 service worker — PostHog analytics proxy.
// Loaded as an ES module ("type": "module" in manifest.json).

const POSTHOG_ENDPOINT = 'https://eu.i.posthog.com/capture/';
const POSTHOG_TOKEN = 'phc_tLy92jvRyNfwupRskkh5TASRyLbab2RkJGhbNH2ywZAV';

async function trackPostHog(event, properties = {}) {
  try {
    const stored = await chrome.storage.local.get(['bhk_distinct_id']);
    let distinctId = stored.bhk_distinct_id;
    if (!distinctId) {
      distinctId = crypto.randomUUID();
      await chrome.storage.local.set({ bhk_distinct_id: distinctId });
    }
    await fetch(POSTHOG_ENDPOINT, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        api_key: POSTHOG_TOKEN,
        event,
        distinct_id: distinctId,
        properties: {
          ...properties,
          $lib: 'bhk-extension',
          $lib_version: chrome.runtime.getManifest().version,
        },
      }),
    });
  } catch {
    // fail silently — analytics must never break the extension
  }
}

chrome.runtime.onMessage.addListener((msg, _sender, _sendResponse) => {
  if (msg.type === 'TRACK_EVENT') {
    trackPostHog(msg.event, msg.properties ?? {});
  }
  // Content script badge was clicked — open the popup
  if (msg.type === 'OPEN_POPUP') {
    chrome.action.openPopup().catch(() => {});
  }
  return false;
});

chrome.runtime.onInstalled.addListener((details) => {
  const version = chrome.runtime.getManifest().version;
  if (details.reason === 'install') {
    trackPostHog('extension_installed', { version });
  } else if (details.reason === 'update') {
    trackPostHog('extension_updated', { version, previous_version: details.previousVersion });
  }
});
