"""Helpers padronizados para tratamento de erros em rotas."""

import logging
import os
from flask import render_template

logger = logging.getLogger(__name__)


def _is_production() -> bool:
    """Detecta se o ambiente atual é de produção."""
    # Default 'production' alinhado com o app.py (app_env)
    app_env = os.environ.get("APP_ENV", os.environ.get("FLASK_ENV", "production")).lower()
    return app_env in ("production", "prod")


def render_service_unavailable(template_name: str = "erro.html"):
    """Renderiza resposta 503 quando um serviço essencial está indisponível.

    Args:
        template_name: Nome do template a ser renderizado.

    Returns:
        Tuple (response, status_code) pronta para retornar de uma rota Flask.
    """
    logger.warning("Serviço essencial indisponível ao renderizar %s", template_name)
    return render_template(
        template_name,
        mensagem="Serviço temporariamente indisponível. Tente novamente em instantes.",
        tipo_mensagem="warning",
    ), 503


def render_route_error(
    exception: Exception,
    template_name: str = "erro.html",
    user_message: str | None = None,
    extra_context: dict | None = None,
):
    """Renderiza resposta 500 padronizada para erros em rotas.

    Em produção, oculta detalhes técnicos. Em desenvolvimento, inclui a mensagem
    da exceção para facilitar o debug.

    Args:
        exception: Exceção capturada.
        template_name: Nome do template a ser renderizado.
        user_message: Mensagem amigável opcional para exibir ao usuário.
        extra_context: Variáveis adicionais a serem passadas ao template
            (ex.: listas vazias, métricas zeradas). Não sobrescreve
            ``mensagem``/``tipo_mensagem`` definidas pelo helper.

    Returns:
        Tuple (response, status_code) pronta para retornar de uma rota Flask.
    """
    logger.error("Erro ao processar rota: %s", exception, exc_info=True)

    if _is_production() and user_message is None:
        user_message = "Ocorreu um erro ao processar sua solicitação. Tente novamente."

    context = {
        "mensagem": user_message or str(exception),
        "tipo_mensagem": "danger",
    }
    if extra_context:
        for key, value in extra_context.items():
            context.setdefault(key, value)
    return render_template(template_name, **context), 500
