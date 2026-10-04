/*
 * The installed app's service worker. It does one thing: when a page
 * navigation fails because the device is offline, it answers with
 * `/offline.html` instead of the browser's own error page.
 *
 * It caches nothing else on purpose. Pages, API responses and the session all
 * come from the network exactly as they do without it, so a deploy can never
 * be hidden behind a stale copy. Bump CACHE when `offline.html` changes.
 */
const CACHE = "osce-offline-v1";
const OFFLINE_URL = "/offline.html";

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE).then((cache) => cache.add(new Request(OFFLINE_URL, { cache: "reload" }))),
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      const keys = await caches.keys();
      await Promise.all(keys.filter((key) => key !== CACHE).map((key) => caches.delete(key)));
      // Lets the navigation request start while the worker boots, so having a
      // worker does not slow a launch down.
      if (self.registration.navigationPreload) await self.registration.navigationPreload.enable();
      await self.clients.claim();
    })(),
  );
});

self.addEventListener("fetch", (event) => {
  if (event.request.mode !== "navigate") return;
  event.respondWith(
    (async () => {
      try {
        return (await event.preloadResponse) || (await fetch(event.request));
      } catch {
        const cache = await caches.open(CACHE);
        return (await cache.match(OFFLINE_URL)) || Response.error();
      }
    })(),
  );
});
