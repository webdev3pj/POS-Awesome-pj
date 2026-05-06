const SEARCH_VERSION = new URL(self.location.href).searchParams.get("v") || "dev";
const CACHE_PREFIX = "posawesome-posapp-shell";
const CACHE_NAME = `${CACHE_PREFIX}:${SEARCH_VERSION}`;
const POS_PATH = "/app/posapp";

function sameOrigin(url) {
  return url.origin === self.location.origin;
}

function isPosShell(url) {
  return sameOrigin(url) && (url.pathname === POS_PATH || url.pathname === `${POS_PATH}/`);
}

function isStaticAsset(url) {
  return (
    sameOrigin(url) &&
    (url.pathname.startsWith("/assets/") ||
      url.pathname.startsWith("/files/") ||
      /\.(?:js|css|png|jpg|jpeg|gif|svg|webp|ico|woff|woff2|ttf|map)$/i.test(url.pathname))
  );
}

function isBusinessApi(url) {
  return (
    sameOrigin(url) &&
    (url.pathname.startsWith("/api/") ||
      url.pathname.startsWith("/socket.io/") ||
      url.pathname.startsWith("/desk") ||
      (url.pathname.startsWith("/app/") && !isPosShell(url)))
  );
}

async function cachePut(request, response) {
  if (!response || !response.ok) return response;
  const cache = await caches.open(CACHE_NAME);
  await cache.put(request, response.clone());
  return response;
}

async function networkFirst(request) {
  try {
    const response = await fetch(request);
    return await cachePut(request, response);
  } catch (error) {
    const cached = await caches.match(request);
    if (cached) return cached;
    throw error;
  }
}

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then((cache) => cache.addAll([POS_PATH]).catch(() => undefined))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((key) => key.startsWith(CACHE_PREFIX) && key !== CACHE_NAME)
            .map((key) => caches.delete(key))
        )
      )
      .then(() => self.clients.claim())
  );
});

self.addEventListener("message", (event) => {
  const data = event.data || {};
  if (data.type !== "POSAPP_PRECACHE_URLS" || !Array.isArray(data.urls)) return;
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      const urls = data.urls
        .map((raw) => {
          try {
            return new URL(raw, self.location.origin);
          } catch (error) {
            return null;
          }
        })
        .filter((url) => url && (isPosShell(url) || isStaticAsset(url)))
        .map((url) => url.href);
      return Promise.all(urls.map((url) => cache.add(url).catch(() => undefined)));
    })
  );
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return;

  const url = new URL(event.request.url);
  if (!sameOrigin(url)) return;
  if (isBusinessApi(url)) return;

  if (isPosShell(url) || isStaticAsset(url)) {
    event.respondWith(networkFirst(event.request));
  }
});
