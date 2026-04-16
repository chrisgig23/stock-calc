const CACHE_NAME = 'wealthtrack-v1';

// Static assets to pre-cache on install
const PRECACHE_URLS = [
  '/static/styles.css',
  '/static/images/icon-192.png',
  '/static/images/icon-512.png',
  '/static/images/wealthtrack_icon.png',
  'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css',
];

// ── Install: pre-cache static shell ─────────────────────────────────────────
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      return Promise.allSettled(
        PRECACHE_URLS.map(url =>
          cache.add(url).catch(() => { /* ignore individual failures */ })
        )
      );
    }).then(() => self.skipWaiting())
  );
});

// ── Activate: remove old caches ──────────────────────────────────────────────
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))
      )
    ).then(() => self.clients.claim())
  );
});

// ── Fetch: strategy by request type ─────────────────────────────────────────
self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);

  // Only handle same-origin requests and known CDN assets
  const isSameOrigin = url.origin === self.location.origin;
  const isCDN = url.hostname.includes('cdnjs.cloudflare.com') ||
                url.hostname.includes('fonts.googleapis.com') ||
                url.hostname.includes('fonts.gstatic.com');

  if (!isSameOrigin && !isCDN) return;

  // Static assets — cache-first, fall back to network
  if (request.url.includes('/static/')) {
    event.respondWith(
      caches.match(request).then(cached => {
        if (cached) return cached;
        return fetch(request).then(response => {
          if (response.ok) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then(cache => cache.put(request, clone));
          }
          return response;
        });
      })
    );
    return;
  }

  // CDN assets — cache-first
  if (isCDN) {
    event.respondWith(
      caches.match(request).then(cached => cached || fetch(request))
    );
    return;
  }

  // HTML navigation — network-first, fall back to cache, then offline page
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request)
        .then(response => {
          // Cache successful page responses for offline fallback
          if (response.ok) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then(cache => cache.put(request, clone));
          }
          return response;
        })
        .catch(() => {
          return caches.match(request).then(cached => {
            if (cached) return cached;
            // Generic offline fallback
            return new Response(offlinePage(), {
              headers: { 'Content-Type': 'text/html' }
            });
          });
        })
    );
    return;
  }
});

function offlinePage() {
  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>WealthTrack — Offline</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Inter', sans-serif;
      background: #0F172A;
      color: #F1F5F9;
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      padding: 24px;
      text-align: center;
    }
    .card {
      background: #1E293B;
      border-radius: 16px;
      padding: 40px 32px;
      max-width: 360px;
      width: 100%;
    }
    .icon { font-size: 2.5rem; margin-bottom: 16px; }
    h1 { font-size: 1.25rem; font-weight: 700; margin-bottom: 10px; }
    p { font-size: 0.9rem; color: #94A3B8; line-height: 1.6; margin-bottom: 24px; }
    button {
      background: #6366F1;
      color: white;
      border: none;
      border-radius: 8px;
      padding: 12px 24px;
      font-size: 0.9rem;
      font-weight: 600;
      cursor: pointer;
      width: 100%;
    }
  </style>
</head>
<body>
  <div class="card">
    <div class="icon">📡</div>
    <h1>You're offline</h1>
    <p>WealthTrack needs a connection to load your portfolio data. Check your network and try again.</p>
    <button onclick="window.location.reload()">Try again</button>
  </div>
</body>
</html>`;
}
