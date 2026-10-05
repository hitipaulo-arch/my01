"""Integração do sistema de OS com o app dedicado de produção.

Esta é a ponte mais **fina** possível: o sistema de OS apenas exibe o endereço
do app de produção (no menu, nas telas antigas de produção e no menu do app
mobile). Nada é importado do outro lado, nenhuma regra de negócio é
compartilhada e nenhum dado é copiado — os dois continuam independentes, com
sessão, login e banco separados.

Como o endereço é resolvido, nesta ordem:

1. ``PRODUCAO_APP_URL`` — endereço completo do app (ex.:
   ``https://producao.minhaempresa.com``). É o que se usa em produção;
2. se ela não existir, o endereço é deduzido do próprio acesso:

   * ``http://127.0.0.1:5000`` (ou ``localhost``) → ``…:PRODUCAO_APP_PORT``;
   * publicações onde o host começa com a porta (ex.: ``5000-abc.e2b.app``) →
     troca o prefixo pela porta do app, mantendo o domínio (e assumindo HTTPS,
     que é como essas publicações são acessadas);
   * qualquer outro domínio → acrescenta ``:PRODUCAO_APP_PORT``.

Para esconder o atalho (por exemplo enquanto o app não estiver publicado),
basta ``PRODUCAO_APP_INTEGRADO=0``.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from flask import current_app, request

logger = logging.getLogger(__name__)

#: Porta padrão do app de produção (a mesma usada em producao_app.py).
PORTA_PADRAO = 5001

#: Textos usados nos atalhos e cartões das telas.
ROTULO = "Produção por Setor"
DESCRICAO = (
    "O app novo acompanha cada ordem de produção pelos setores "
    "(Corte, Corte Painel, CNC, Policorte, Vidros, Portas, Pass-through, Dobra, "
    "Montagem Primária, Solda, Acabamento, Silicone e Limpeza e Embalagem), "
    "com PIN por setor e data/hora de cada etapa."
)


def _booleano(valor: Optional[str], padrao: bool = True) -> bool:
    if valor is None or not str(valor).strip():
        return padrao
    return str(valor).strip().lower() in ("1", "true", "sim", "yes", "on")


def ativo() -> bool:
    """Diz se o atalho para o app de produção deve aparecer."""

    return _booleano(current_app.config.get("PRODUCAO_APP_INTEGRADO"), True)


def porta() -> int:
    try:
        return int(str(current_app.config.get("PRODUCAO_APP_PORT") or PORTA_PADRAO))
    except (TypeError, ValueError):
        return PORTA_PADRAO


def _esquema(requisicao) -> str:
    """Esquema real do acesso, respeitando proxies (X-Forwarded-Proto)."""

    encaminhado = (requisicao.headers.get("X-Forwarded-Proto") or "").split(",")[0].strip()
    return encaminhado or requisicao.scheme or "http"


def _subdominio_com_porta(nome: str) -> Optional[str]:
    """Devolve o resto do host quando ele começa com a porta (``5000-abc.ex``).

    É o padrão de publicações temporárias (``5000-abc.exemplo.com``), em que
    cada porta vira um subdomínio. Nesses casos o acesso é sempre por HTTPS.
    """

    prefixo, separador, resto = nome.partition("-")
    if separador and prefixo.isdigit() and resto:
        return resto
    return None


def url_derivada() -> Optional[str]:
    """Deduz o endereço do app de produção a partir do acesso atual."""

    try:
        host = request.host or ""
    except RuntimeError:  # fora de contexto de requisição
        return None
    if not host:
        return None

    nome = host.partition(":")[0]
    esquema = _esquema(request)
    destino = porta()

    resto = _subdominio_com_porta(nome)
    if resto:
        # Publicações que põem a porta no subdomínio: troca só o número,
        # mantendo domínio e sufixo.
        if esquema == "http" and not request.headers.get("X-Forwarded-Proto"):
            # Publicação é acessada por HTTPS na prática; evita gerar um link
            # http:// a partir de uma página https://.
            esquema = "https"
        return f"{esquema}://{destino}-{resto}"

    # Domínio/ip comum: o app costuma estar na mesma máquina, em outra porta.
    return f"{esquema}://{nome}:{destino}"


def url() -> Optional[str]:
    """Endereço do app de produção (configurado ou deduzido)."""

    configurada = str(current_app.config.get("PRODUCAO_APP_URL") or "").strip()
    if configurada:
        return configurada.rstrip("/")
    if not ativo():
        return None
    return url_derivada()


def dados() -> Dict[str, Any]:
    """Pacote pronto para os templates (``producao_app``)."""

    mostrar = ativo()
    endereco = url() if mostrar else None
    return {
        "mostrar": bool(mostrar and endereco),
        "url": endereco,
        "rotulo": ROTULO,
        "descricao": DESCRICAO,
        "porta": porta(),
        "configurado": bool(str(current_app.config.get("PRODUCAO_APP_URL") or "").strip()),
    }


def register_context_processors(app) -> None:
    """Deixa ``producao_app`` disponível em todos os templates do sistema."""

    @app.context_processor
    def _injetar_app_producao() -> Dict[str, Any]:
        return {"producao_app": dados()}

    logger.debug("Integração com o app de produção registrada (porta %s).", PORTA_PADRAO)
