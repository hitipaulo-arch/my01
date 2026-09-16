"""Contexto compartilhado das telas mobile (menu, modo app e renderização).

O app mobile é o **mesmo** sistema Flask: as rotas continuam idênticas e apenas
o template muda quando a requisição vem do prefixo ``/m``. Assim nenhuma regra
de negócio é reescrita — somente a apresentação.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from flask import current_app, render_template, request, session

logger = logging.getLogger(__name__)

#: Prefixo público do aplicativo (barra final implícita: ``/m/``).
MOBILE_PREFIX = "/m"

#: Template usado quando a tela mobile ainda não existe (evita 500/preview quebrado).
MOBILE_FALLBACK_TEMPLATE = "mobile/erro.html"


# ──────────────────────────────────────────────────────────────────────────────
# Detecção de modo app
# ──────────────────────────────────────────────────────────────────────────────
def is_mobile_request() -> bool:
    """Informa se a requisição atual está no modo aplicativo (``/m``).

    O middleware (:class:`~appmodules.mobile.middleware.MobilePrefixMiddleware`)
    marca o *environ* e move o prefixo para ``SCRIPT_NAME`` — com isso todos os
    ``url_for`` continuam apontando para dentro do app.
    """

    try:
        if request.environ.get("MOBILE_APP") == "1":
            return True
        return bool(request.script_root) and request.script_root.rstrip("/").endswith(
            MOBILE_PREFIX
        )
    except RuntimeError:  # pragma: no cover - fora de contexto de requisição
        return False


def cache_key_by_mode(base: str = "view"):
    """Cria um ``key_prefix`` de cache que separa app mobile e versão web.

    O middleware do app move ``/m`` para ``SCRIPT_NAME``, então ``request.path``
    é idêntico nos dois modos (``/relatorios``, por exemplo). Sem esta separação,
    o Flask-Caching devolveria o HTML da versão web para quem está no app (e
    vice-versa). O prefixo inclui o modo antes do caminho, mantendo o
    comportamento padrão de cache por rota.

    Uso::

        @cache.cached(timeout=300, key_prefix=cache_key_by_mode("view/relatorios"))
    """

    def _key() -> str:
        try:
            modo = "app" if is_mobile_request() else "web"
            return f"{base}/{modo}{request.path}"
        except RuntimeError:  # pragma: no cover - fora de contexto de requisição
            return f"{base}/web"

    return _key


def _template_exists(template_name: str) -> bool:
    """Verifica se o template existe no loader do Jinja atual."""

    try:
        current_app.jinja_env.get_template(template_name)
        return True
    except Exception:
        return False


def render_page(template_name: str, **context: Any):
    """Renderiza ``templates/mobile/<template_name>`` quando no modo app.

    Mantém a assinatura idêntica a ``flask.render_template``, o que permite
    trocar as chamadas nas rotas existentes sem tocar em nenhuma regra de
    negócio. Se o template mobile não existir, cai no template desktop.
    """

    if is_mobile_request():
        mobile_template = template_name
        if not mobile_template.startswith("mobile/"):
            mobile_template = f"mobile/{template_name}"

        if _template_exists(mobile_template):
            return render_template(mobile_template, **context)
        logger.warning(
            "Template mobile '%s' não encontrado; usando versão desktop.", mobile_template
        )

    return render_template(template_name, **context)


# ──────────────────────────────────────────────────────────────────────────────
# Menu do aplicativo (mesmos itens/permissoes do _top_nav.html)
# ──────────────────────────────────────────────────────────────────────────────
ADMIN = "admin"
OPERADOR = "operador"
VISUALIZADOR = "visualizador"
PUBLICO = "publico"

ROLES_LOGADOS = (ADMIN, OPERADOR, VISUALIZADOR)
ROLES_NAO_ADMIN = (OPERADOR, VISUALIZADOR)

#: Cada item: (chave, rótulo, emoji, endpoint, perfis)
APP_MENU: List[Dict[str, Any]] = [
    {
        "key": "nova_os",
        "label": "Nova OS",
        "icon": "📝",
        "endpoint": "mobile.nova_os",
        "roles": ROLES_LOGADOS + (PUBLICO,),
        "hint": "Abrir chamado",
    },
    {
        "key": "os_abertas",
        "label": "OS Abertas",
        "icon": "🟢",
        "endpoint": "os.os_abertas",
        "roles": ROLES_LOGADOS + (PUBLICO,),
        "hint": "Chamados em andamento",
    },
    {
        "key": "consultar",
        "label": "Consultar OS",
        "icon": "🔍",
        "endpoint": "os.consultar_pedido",
        "roles": ROLES_LOGADOS + (PUBLICO,),
        "hint": "Status pelo número do pedido",
    },
    {
        "key": "upload",
        "label": "Enviar Arquivo",
        "icon": "📎",
        "endpoint": "os.upload_documento",
        "roles": ROLES_LOGADOS + (PUBLICO,),
        "hint": "Anexar documento de apoio",
    },
    {
        "key": "gerenciar",
        "label": "Gerenciar OS",
        "icon": "📋",
        "endpoint": "os.gerenciar",
        "roles": (ADMIN,),
        "hint": "Editar e finalizar chamados",
    },
    {
        "key": "centrais",
        "label": "Centrais",
        "icon": "📡",
        "endpoint": "centrais.centrais",
        "roles": (ADMIN,),
        "hint": "Portas, status e programação",
    },
    {
        "key": "ferramentas",
        "label": "Ferramentas",
        "icon": "🔧",
        "endpoint": "ferramentas",
        "roles": (ADMIN,),
        "hint": "Controle e histórico",
    },
    {
        "key": "producao",
        "label": "Produção",
        "icon": "🏭",
        "endpoint": "producao",
        "roles": ROLES_LOGADOS,
        "hint": "Cadastrar e atualizar itens",
    },
    {
        "key": "producao_abertas",
        "label": "OPs Abertas",
        "icon": "📦",
        "endpoint": "producao_abertas",
        "roles": (ADMIN,),
        "hint": "Itens fora de concluído/bloqueado",
    },
    {
        "key": "dashboard",
        "label": "Dashboard",
        "icon": "📊",
        "endpoint": "dashboard_producao",
        "roles": ROLES_LOGADOS,
        "hint": "Indicadores de produção",
    },
    {
        "key": "itens",
        "label": "Itens / Compras",
        "icon": "🧰",
        "endpoint": "itens",
        "roles": ROLES_LOGADOS,
        "hint": "Alerta de reposição de estoque",
    },
    {
        "key": "relatorios",
        "label": "Relatórios",
        "icon": "📈",
        "endpoint": "relatorios",
        "roles": (ADMIN,),
        "hint": "Auditoria e indicadores",
    },
    {
        "key": "tempo",
        "label": "Tempo por Funcionário",
        "icon": "⏱️",
        "endpoint": "tempo_por_funcionario",
        "roles": (ADMIN,),
        "hint": "Horas trabalhadas por OS",
    },
    {
        "key": "usuarios",
        "label": "Usuários",
        "icon": "👥",
        "endpoint": "usuarios_admin",
        "roles": (ADMIN,),
        "hint": "Criar, alterar papel e remover",
    },
    {
        "key": "ia",
        "label": "IA Admin",
        "icon": "🤖",
        "endpoint": "admin_ia",
        "roles": (ADMIN,),
        "hint": "Resumo e perguntas sobre a operação",
    },
    {
        "key": "login",
        "label": "Entrar",
        "icon": "🔐",
        "endpoint": "auth.login",
        "roles": (PUBLICO,),
        "hint": "Acesso da equipe",
    },
    {
        "key": "cadastro",
        "label": "Cadastrar usuário",
        "icon": "🧾",
        "endpoint": "auth.cadastro",
        "roles": (PUBLICO,),
        "hint": "Criar nova conta",
    },
]

#: Abas fixas na barra inferior.
APP_TABS: List[Dict[str, Any]] = [
    {
        "key": "inicio",
        "label": "Início",
        "icon": "🏠",
        "endpoint": "os.homepage",
        "roles": ROLES_LOGADOS + (PUBLICO,),
    },
    {
        "key": "nova_os",
        "label": "Nova OS",
        "icon": "📝",
        "endpoint": "mobile.nova_os",
        "roles": ROLES_LOGADOS + (PUBLICO,),
    },
    {
        "key": "os_abertas",
        "label": "OS Abertas",
        "icon": "🟢",
        "endpoint": "os.os_abertas",
        "roles": ROLES_LOGADOS + (PUBLICO,),
    },
    {
        "key": "producao",
        "label": "Produção",
        "icon": "🏭",
        "endpoint": "producao",
        "roles": ROLES_LOGADOS,
    },
    {
        "key": "mais",
        "label": "Mais",
        "icon": "☰",
        "endpoint": "mobile.mais",
        "roles": ROLES_LOGADOS + (PUBLICO,),
    },
]


def current_role_key() -> str:
    """Normaliza a role da sessão para uma das chaves usadas no menu."""

    role = str(session.get("role", "") or "").strip().lower()
    if "admin" in role:
        return ADMIN
    if "operador" in role:
        return OPERADOR
    if "visualizador" in role:
        return VISUALIZADOR
    return PUBLICO


def session_user() -> Optional[str]:
    """Nome do usuário logado (ou ``None`` para acesso público)."""

    return session.get("usuario")


def role_label(role_key: Optional[str] = None) -> str:
    """Rótulo amigável do perfil (mesmos termos do topo da versão web)."""

    role_key = role_key or current_role_key()
    return {
        ADMIN: "Admin",
        OPERADOR: "Operador",
        VISUALIZADOR: "Visualizador",
        PUBLICO: "Acesso Público",
    }.get(role_key, "Acesso Público")


def role_badge_class(role_key: Optional[str] = None) -> str:
    """Classe Bootstrap do badge de perfil."""

    role_key = role_key or current_role_key()
    return {
        ADMIN: "bg-danger",
        OPERADOR: "bg-warning text-dark",
        VISUALIZADOR: "bg-info text-dark",
        PUBLICO: "bg-secondary",
    }.get(role_key, "bg-secondary")


def _build_items(items: List[Dict[str, Any]], role_key: str) -> List[Dict[str, Any]]:
    """Filtra os itens permitidos e resolve as URLs (mantendo o prefixo /m)."""

    from flask import url_for

    permitidos: List[Dict[str, Any]] = []
    for item in items:
        if role_key not in item["roles"]:
            continue
        try:
            url = url_for(item["endpoint"])
        except Exception:  # pragma: no cover - endpoint ausente em versão antiga
            logger.warning("Endpoint '%s' não encontrado para o menu mobile.", item["endpoint"])
            continue
        permitidos.append({**item, "url": url})
    return permitidos


def mobile_menu() -> Dict[str, Any]:
    """Monta o contexto de navegação do app (abas + menu completo)."""

    role_key = current_role_key()
    usuario = session_user()
    tabs = _build_items(APP_TABS, role_key)
    itens = _build_items(APP_MENU, role_key)

    logout_url = None
    if usuario:
        try:
            from flask import url_for

            logout_url = url_for("auth.logout")
        except Exception:  # pragma: no cover
            logout_url = None

    return {
        "is_mobile_app": is_mobile_request(),
        "role_key": role_key,
        "role_label": role_label(role_key),
        "role_badge_class": role_badge_class(role_key),
        "usuario": usuario,
        "tabs": tabs,
        "modulos": itens,
        "logout_url": logout_url,
    }


def register_context_processors(app) -> None:
    """Disponibiliza helpers do app mobile em todos os templates."""

    @app.context_processor
    def _inject_mobile_context() -> Dict[str, Any]:
        return {
            "mobile": mobile_menu(),
            "mobile_prefix": MOBILE_PREFIX,
            "is_mobile_app": is_mobile_request(),
            "desktop_url": _desktop_url(),
        }


def _desktop_url() -> str:
    """URL equivalente fora do modo app (para o botão "Versão web")."""

    try:
        query = request.query_string.decode("utf-8")
        path = request.path or "/"
        return f"{path}?{query}" if query else path
    except RuntimeError:  # pragma: no cover
        return "/"
