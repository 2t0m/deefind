const STATIC_CACHE = 'deefind-static-v2';
const RUNTIME_CACHE = 'deefind-runtime-v2';
const API_CACHE = 'deefind-api-v2';

const PRECACHE_ASSETS = [
  '/',
  '/index.html',
  '/styles.css',
  '/app.js',
  '/manifest.json'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then((cache) => cache.addAll(PRECACHE_ASSETS)).catch(() => null)
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(
      keys
        .filter((key) => ![STATIC_CACHE, RUNTIME_CACHE, API_CACHE].includes(key))
        .map((key) => caches.delete(key))
    );
    await clients.claim();
  })());
});

function staleWhileRevalidate(request, cacheName) {
  return caches.open(cacheName).then(async (cache) => {
    const cached = await cache.match(request);
    const networkPromise = fetch(request)
      .then((response) => {
        if (response && response.ok) {
          cache.put(request, response.clone());
        }
        return response;
      })
      .catch(() => cached);
    return cached || networkPromise;
  });
}

function networkFirst(request, cacheName) {
  return caches.open(cacheName).then(async (cache) => {
    try {
      const fresh = await fetch(request);
      if (fresh && fresh.ok) {
        cache.put(request, fresh.clone());
      }
      return fresh;
    } catch (_) {
      const cached = await cache.match(request);
      if (cached) {
        return cached;
      }
      throw _;
    }
  });
}

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') {
    return;
  }

  const requestUrl = new URL(event.request.url);
  const isSameOrigin = requestUrl.origin === self.location.origin;

  if (isSameOrigin && requestUrl.pathname.startsWith('/search')) {
    event.respondWith(networkFirst(event.request, API_CACHE));
    return;
  }

  if (isSameOrigin && requestUrl.pathname.startsWith('/album_tracks')) {
    event.respondWith(networkFirst(event.request, API_CACHE));
    return;
  }

  if (isSameOrigin && requestUrl.pathname.startsWith('/playlist_tracks')) {
    event.respondWith(networkFirst(event.request, API_CACHE));
    return;
  }

  if (isSameOrigin) {
    event.respondWith(staleWhileRevalidate(event.request, RUNTIME_CACHE));
  }
});
