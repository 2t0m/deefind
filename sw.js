// Service Worker minimal pour PWA
const CACHE_NAME = 'deezer-search-v1';

self.addEventListener('install', (event) => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(clients.claim());
});

self.addEventListener('fetch', (event) => {
  // Laisser passer toutes les requêtes sans mise en cache
  event.respondWith(fetch(event.request));
});
