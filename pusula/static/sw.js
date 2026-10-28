/* Lezzet Pusulası service worker: ana ekrana eklenebilmek ve bağlantı yokken
   anlamlı bir sayfa göstermek için. Sayfalar her zaman ağdan gelir (veriler güncel kalsın);
   sadece CSS/JS/ikonlar önbelleğe alınır. */
const SURUM = "pusula-v1";
const ON_BELLEK = [
  "/static/css/pusula.css",
  "/static/js/pusula.js",
  "/static/js/harita.js",
  "/static/ikon/ikon-192.png",
  "/cevrimdisi"
];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(SURUM).then((c) => c.addAll(ON_BELLEK)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys()
      .then((adlar) => Promise.all(adlar.filter((a) => a !== SURUM).map((a) => caches.delete(a))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const istek = e.request;
  if (istek.method !== "GET") return;
  const url = new URL(istek.url);
  if (url.origin !== location.origin) return;

  if (istek.mode === "navigate") {
    e.respondWith(fetch(istek).catch(() => caches.match("/cevrimdisi")));
    return;
  }
  if (url.pathname.startsWith("/static/")) {
    e.respondWith(
      caches.match(istek).then((kayitli) => {
        const ag = fetch(istek).then((yanit) => {
          if (yanit.ok) caches.open(SURUM).then((c) => c.put(istek, yanit.clone()));
          return yanit;
        });
        return kayitli || ag;
      })
    );
  }
});
