const CACHE_NAME = 'spotitool-v2-offline';
const OFFLINE_URL = '/offline.html'; // We need a route for this actually, or serve static file
// Since Flask serves templates, we should probably serve a static HTML or cache the rendered page.
// Let's assume /offline is a route or we serve static/offline.html if we move it there.
// Flask templates are not static. The user created templates/offline.html. 
// We must expose a route /offline or move it to static. 
// Easier: Create a route in app.py for /offline and cache that.

const ASSETS_TO_CACHE = [
    '/',
    '/offline',
    '/static/manifest.json',
    '/static/img/spotitool_logo.png'
];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll(ASSETS_TO_CACHE);
        })
    );
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((keyList) => {
            return Promise.all(keyList.map((key) => {
                if (key !== CACHE_NAME) {
                    return caches.delete(key);
                }
            }));
        })
    );
    self.clients.claim();
});

self.addEventListener('fetch', (event) => {
    if (event.request.mode === 'navigate') {
        event.respondWith(
            fetch(event.request)
                .catch(() => {
                    return caches.match(OFFLINE_URL);
                })
        );
    } else {
        event.respondWith(
            fetch(event.request)
                .catch(() => caches.match(event.request))
        );
    }
});
