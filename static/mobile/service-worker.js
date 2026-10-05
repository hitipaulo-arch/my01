/* ==========================================================================
   Service worker do app (PWA) — Gestão OS
   --------------------------------------------------------------------------
   Estratégias:
     • navegação (HTML): rede primeiro; se falhar, mostra a tela offline;
     • assets estáticos do app: cache primeiro com revalidação em background;
     • CDNs (Bootstrap, Bootstrap Icons, Chart.js): cache-first (os arquivos são
       versionados por URL).
   Nada de dados do Google Sheets é armazenado: as respostas dinâmicas passam
   direto pela rede para não exibir informação desatualizada.

   IMPORTANTE: ao alterar app.js, mobile.css, unified.css ou os ícones do app,
   incremente CACHE_VERSION abaixo. Os assets usam cache primeiro com
   revalidação em background, então sem o incremento o celular pode rodar uma
   versão antiga do JS até a segunda visita.
   ========================================================================== */

const CACHE_VERSION = "gestao-os-v2";
const SCOPE = self.registration.scope; // https://host/m/
const OFFLINE_URL = new URL("offline", SCOPE).toString();

const PRECACHE_URLS = [
    OFFLINE_URL,
    new URL("instalar", SCOPE).toString(),
    "/static/unified.css",
    "/static/mobile/mobile.css",
    "/static/mobile/app.js",
    "/static/mobile/icons/icon-192.png",
    "/static/mobile/icons/icon-512.png",
];

self.addEventListener("install", (event) => {
    event.waitUntil(
        caches
            .open(CACHE_VERSION)
            .then((cache) =>
                Promise.all(
                    PRECACHE_URLS.map((url) =>
                        cache.add(new Request(url, { cache: "reload" })).catch(() => null)
                    )
                )
            )
            .then(() => self.skipWaiting())
    );
});

self.addEventListener("activate", (event) => {
    event.waitUntil(
        caches
            .keys()
            .then((keys) => Promise.all(keys.filter((key) => key !== CACHE_VERSION).map((key) => caches.delete(key))))
            .then(() => self.clients.claim())
    );
});

function isCdnRequest(url) {
    return /cdn\.jsdelivr\.net|cdnjs\.cloudflare\.com|unpkg\.com/.test(url.hostname);
}

function isStaticRequest(url) {
    return url.pathname.startsWith("/static/") || url.pathname.includes("/static/mobile/");
}

self.addEventListener("fetch", (event) => {
    const request = event.request;

    if (request.method !== "GET") {
        return; // POST/PUT continuam direto para o servidor (CSRF intacto).
    }

    const url = new URL(request.url);

    // Navegação: rede primeiro, offline em caso de falha.
    if (request.mode === "navigate") {
        event.respondWith(
            fetch(request).catch(() =>
                caches.match(OFFLINE_URL).then((response) => response || caches.match(OFFLINE_URL))
            )
        );
        return;
    }

    // Assets do próprio app: cache primeiro (rápido), atualiza em background.
    if (isStaticRequest(url)) {
        event.respondWith(
            caches.match(request).then((cached) => {
                const network = fetch(request)
                    .then((response) => {
                        if (response && response.status === 200) {
                            const copy = response.clone();
                            caches.open(CACHE_VERSION).then((cache) => cache.put(request, copy));
                        }
                        return response;
                    })
                    .catch(() => cached);
                return cached || network;
            })
        );
        return;
    }

    // CDNs versionadas: cache-first.
    if (isCdnRequest(url)) {
        event.respondWith(
            caches.match(request).then(
                (cached) =>
                    cached ||
                    fetch(request)
                        .then((response) => {
                            const copy = response.clone();
                            caches.open(CACHE_VERSION).then((cache) => cache.put(request, copy));
                            return response;
                        })
                        .catch(() => cached)
            )
        );
    }
});
