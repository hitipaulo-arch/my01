"""Middleware que expõe o sistema como aplicativo instalável em ``/m``.

A ideia é simples e não invasiva: quando a requisição chega em ``/m/...``, o
prefixo é movido para ``SCRIPT_NAME`` antes de o Flask rotear. Resultado:

* as rotas existentes continuam idênticas (``/gerenciar``, ``/producao``, ...);
* todos os ``url_for`` passam a gerar ``/m/...`` automaticamente, mantendo o
  usuário dentro do app;
* sessão, CSRF e cookies continuam valendo para os dois modos.
"""

from __future__ import annotations

import logging

from appmodules.mobile.context import MOBILE_PREFIX

logger = logging.getLogger(__name__)


class MobilePrefixMiddleware:
    """Remove o prefixo ``/m`` e sinaliza o modo aplicativo via WSGI environ."""

    def __init__(self, wsgi_app, prefix: str = MOBILE_PREFIX):
        self.wsgi_app = wsgi_app
        self.prefix = "/" + prefix.strip("/")

    def __call__(self, environ, start_response):
        path = environ.get("PATH_INFO", "") or "/"

        if path == self.prefix or path.startswith(self.prefix + "/"):
            rest = path[len(self.prefix) :] or "/"
            environ["PATH_INFO"] = rest
            environ["MOBILE_APP"] = "1"
            environ["MOBILE_PREFIX_STRIPPED"] = self.prefix

            # Mantém o prefixo visível para url_for/redirects e para o sw.js.
            script_name = environ.get("SCRIPT_NAME", "") or ""
            environ["SCRIPT_NAME"] = f"{script_name}{self.prefix}"

            # Alguns servidores (e proxies) leem essas chaves em vez de PATH_INFO.
            for key in ("RAW_URI", "REQUEST_URI"):
                raw_uri = environ.get(key)
                if not raw_uri:
                    continue
                if raw_uri == self.prefix or raw_uri.startswith(self.prefix + "/"):
                    stripped = raw_uri[len(self.prefix) :] or "/"
                    environ[key] = stripped if stripped.startswith("/") else "/" + stripped

        return self.wsgi_app(environ, start_response)


def install_mobile_middleware(app) -> None:
    """Envolve a aplicação Flask com o middleware do app mobile."""

    app.wsgi_app = MobilePrefixMiddleware(app.wsgi_app)
    logger.info("App mobile habilitado em '%s/'", MOBILE_PREFIX)
