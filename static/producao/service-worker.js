/* ==========================================================================
   Service worker do app de produção (PWA)
   --------------------------------------------------------------------------
   Estratégias:
     • navegação (HTML): rede primeiro; sem rede, mostra a tela /offline;
     • estáticos do app: cache primeiro com revalidação em background;
     • CDNs versionadas: cache-first.
   As respostas com dados de produção (OPs e status) NUNCA entram no cache: o
   chão de fábrica precisa ver o status real, não o de ontem.

   IMPORTANTE: ao alterar app.css, app.js, unified.css ou os ícones, incremente
   CACHE_VERSION — senão o celular pode rodar a versão antiga do arquivo até a
   segunda visita.
   ========================================================================== */

const CACHE_VERSION = "producao-v1";
const OFFLINE_URL = "/offline";

const PRECACHE_URLS = [
    OFFLINE_URL,
    "/instalar",
    "/static/unified.css",
    "/static/producao/app.css",
    "/static/producao/app.js",
    "/static/producao/icons/icon-192.png",
    "/static/producao/icons/icon-512.png",
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
            .then((chaves) =>
                Promise.all(chaves.filter((chave) => chave !== CACHE_VERSION).map((chave) => caches.delete(chave)))
            )
            .then(() => self.clients.claim())
    );
});

self.addEventListener("fetch", (event) => {
    const request = event.request;

    if (request.method !== "GET") return;

    const url = new URL(request.url);

    // Navegação: rede primeiro, tela offline como rede de segurança.
    if (request.mode === "navigate") {
        event.respondWith(
            fetch(request).catch(() =>
                caches.match(OFFLINE_URL).then((resposta) => resposta || Response.error())
            )
        );
        return;
    }

    // CDNs versionadas (Bootstrap): cache-first.
    if (url.origin !== self.location.origin) {
        event.respondWith(
            caches.match(request).then(
                (cacheado) =>
                    cacheado ||
                    fetch(request).then((resposta) => {
                        const copia = resposta.clone();
                        caches.open(CACHE_VERSION).then((cache) => cache.put(request, copia));
                        return resposta;
                    })
            )
        );
        return;
    }

    // Estáticos do app: cache primeiro com revalidação.
    if (url.pathname.startsWith("/static/")) {
        event.respondWith(
            caches.match(request).then((cacheado) => {
                const rede = fetch(request)
                    .then((resposta) => {
                        const copia = resposta.clone();
                        caches.open(CACHE_VERSION).then((cache) => cache.put(request, copia));
                        return resposta;
                    })
                    .catch(() => cacheado || Response.error());
                return cacheado || rede;
            })
        );
    }
});
