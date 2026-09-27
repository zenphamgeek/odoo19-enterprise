"use strict";

const CACHE = "pos-react-cold-start-v1";
const NAVIGATION_CACHE = "pos-react-navigation-v1";
const OWNER_KEY = new URL("__navigation_owner__", self.registration.scope).href;
const STATIC = [
    "/pos_react/static/src/app.css",
    "/pos_react/static/lib/react/react.production.min.js",
    "/pos_react/static/lib/react/react-dom.production.min.js",
    "/pos_react/static/src/plugin_registry.js",
    "/pos_react/static/src/restaurant_adapter.js",
    "/pos_react/static/src/offline_store.js",
    "/pos_react/static/src/metadata_graph.js",
    "/pos_react/static/src/tax_engine.js",
    "/pos_react/static/src/pricelist_engine.js",
    "/pos_react/static/src/realtime.js",
    "/pos_react/static/src/app.js",
];

self.addEventListener("install", (event) => {
    event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(STATIC)));
});

self.addEventListener("activate", (event) => {
    event.waitUntil(caches.keys().then((keys) => Promise.all(
        keys.filter((key) => key.startsWith("pos-react-cold-start-") && key !== CACHE).map((key) => caches.delete(key))
    )).then(() => self.clients.claim()));
});

self.addEventListener("message", (event) => {
    if (event.data?.type !== "CACHE_NAVIGATION" || event.data.url !== event.source.url) return;
    const url = new URL(event.data.url);
    const assets = Array.isArray(event.data.assets) ? event.data.assets.map((asset) => new URL(asset, url)) : [];
    const owner = event.data.owner;
    if (typeof owner !== "string" || !/^[^:]+:\d+$/.test(owner) || url.origin !== self.location.origin || !/^\/pos\/react\/\d+$/.test(url.pathname) || assets.some((asset) => asset.origin !== url.origin || !asset.pathname.includes("/static/"))) return;
    event.waitUntil(caches.open(NAVIGATION_CACHE).then(async (cache) => {
        const current = await cache.match(OWNER_KEY);
        if (current && await current.text() !== owner) await cache.keys().then((keys) => Promise.all(keys.map((key) => cache.delete(key))));
        const response = await fetch(url.href, { credentials: "include" });
        if (!response.ok || response.type !== "basic") return;
        await Promise.all([cache.put(OWNER_KEY, new Response(owner)), cache.put(`${url.href}#owner=${encodeURIComponent(owner)}`, response)]);
        await caches.open(CACHE).then((staticCache) => Promise.all(assets.map((asset) => staticCache.add(asset.href))));
    }));
});

self.addEventListener("fetch", (event) => {
    const { request } = event;
    if (request.method !== "GET") return;
    if (request.mode === "navigate") {
        event.respondWith(fetch(request).catch(async () => {
            const cache = await caches.open(NAVIGATION_CACHE);
            const current = await cache.match(OWNER_KEY);
            if (!current) return Response.error();
            return await cache.match(`${request.url}#owner=${encodeURIComponent(await current.text())}`) || Response.error();
        }));
    } else if (new URL(request.url).origin === self.location.origin && new URL(request.url).pathname.includes("/static/")) {
        event.respondWith(caches.match(request).then((cached) => cached || fetch(request)));
    }
});
