"""Camada mobile (PWA) do sistema de Ordens de Serviço.

Este pacote entrega o *mesmo* sistema em formato de aplicativo para celular,
sem duplicar regra de negócio:

* :mod:`appmodules.mobile.middleware` — faz o app responder sob o prefixo ``/m``
  (instalável como PWA), mantendo ``url_for`` e sessão idênticos.
* :mod:`appmodules.mobile.context` — helpers ``render_page`` / ``is_mobile_request``
  usados pelas rotas existentes para escolher o template mobile.
* :mod:`appmodules.mobile.routes` — telas exclusivas do app (manifest, service
  worker, offline, formulário de abertura, menu "Mais").

Nada de lógica de negócio mora aqui: as rotas originais continuam sendo as
únicas responsáveis por falar com o Google Sheets.
"""

from appmodules.mobile.context import (  # noqa: F401
    MOBILE_PREFIX,
    cache_key_by_mode,
    is_mobile_request,
    register_context_processors,
    render_page,
)
from appmodules.mobile.middleware import (  # noqa: F401
    MobilePrefixMiddleware,
    install_mobile_middleware,
)
from appmodules.mobile.routes import mobile_bp  # noqa: F401

__all__ = [
    "MOBILE_PREFIX",
    "cache_key_by_mode",
    "MobilePrefixMiddleware",
    "install_mobile_middleware",
    "is_mobile_request",
    "mobile_bp",
    "register_context_processors",
    "render_page",
]
