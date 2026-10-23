/* FilmiSet service worker.
   - data/*.json   -> stale-while-revalidate  (fresh catalogue, instant when offline)
   - navigations   -> network-first           (a new deploy shows up immediately)
   - posters/*     -> cache-first             (they never change)
   Bump CACHE whenever the shell changes. */
const CACHE = 'filmiset-v2-2026-10-23';
const SHELL = ['./', './index.html', './manifest.webmanifest', './icon.svg'];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE)
      .then(c => c.addAll(SHELL))
      .then(() => self.skipWaiting())
      .catch(() => self.skipWaiting())
  );
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;

  let url;
  try { url = new URL(req.url); } catch (_) { return; }
  if (url.origin !== self.location.origin) return;      // fonts / CDNs: plain network

  const path = url.pathname;

  /* 1. catalogue JSON — works both at /  and at /filmiset/ */
  if (path.includes('/data/') && path.endsWith('.json')) {
    e.respondWith(
      caches.open(CACHE).then(cache =>
        cache.match(req).then(hit => {
          const net = fetch(req)
            .then(res => { if (res && res.ok) cache.put(req, res.clone()); return res; })
            .catch(() => hit);
          return hit || net;                             // instant from cache, refresh behind
        })
      )
    );
    return;
  }

  /* 2. the page itself — always try the network first so updates land */
  const isHTML = req.mode === 'navigate' || (req.headers.get('accept') || '').includes('text/html');
  if (isHTML) {
    e.respondWith(
      fetch(req)
        .then(res => {
          const copy = res.clone();
          caches.open(CACHE).then(c => c.put('./index.html', copy)).catch(() => {});
          return res;
        })
        .catch(() => caches.match('./index.html').then(r => r || caches.match('./')))
    );
    return;
  }

  /* 3. posters — immutable, cache-first */
  if (path.includes('/posters/')) {
    e.respondWith(
      caches.match(req).then(hit => hit || fetch(req).then(res => {
        if (res && res.ok) {
          const copy = res.clone();
          caches.open(CACHE).then(c => c.put(req, copy)).catch(() => {});
        }
        return res;
      }))
    );
    return;
  }

  /* 4. everything else — network, fall back to cache */
  e.respondWith(fetch(req).catch(() => caches.match(req)));
});
