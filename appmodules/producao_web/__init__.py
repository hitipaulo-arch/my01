"""App de produção — controle por setor (aplicação independente).

Este pacote monta uma aplicação Flask **separada** do sistema de OS:

* entra em execução pelo arquivo ``producao_app.py`` (ex.: ``python producao_app.py``
  ou ``gunicorn producao_app:app``), normalmente em outra porta;
* tem login próprio (por setor, com PIN) e sessão própria;
* guarda os dados em uma planilha Google dedicada, configurada em
  ``PRODUCAO_SPREADSHEET_ID`` (ou em arquivo local, no modo de desenvolvimento);
* é instalável no celular como app (PWA), pensado para o chão de fábrica.

Nada aqui é importado pelo sistema de OS: derrubar ou reiniciar um não afeta o
outro.
"""

from __future__ import annotations

import logging
from typing import Any

from flask import Flask, render_template
from flask_wtf.csrf import CSRFProtect

from appmodules.producao_web import setores as fluxo
from appmodules.producao_web.config import ProducaoConfig
from appmodules.producao_web.routes import producao_bp
from appmodules.producao_web.storage import criar_storage

logger = logging.getLogger(__name__)

APP_NOME = "Controle de Produção"
APP_SUBTITULO = "Ordens de produção por setor"
VERSAO = "1.0.0"

csrf = CSRFProtect()


def _configurar_logging(debug: bool = False) -> None:
    if logging.getLogger().handlers:
        return
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def create_app(configuracao: dict[str, Any] | None = None) -> Flask:
    """Cria a aplicação do app de produção."""

    config = ProducaoConfig.carregar()
    if configuracao:
        config.update(configuracao)
    return _montar_app(config)


def _montar_app(config: dict[str, Any]) -> Flask:
    """Monta a aplicação Flask a partir de uma configuração já pronta."""

    _configurar_logging(bool(config.get("DEBUG")))

    # A pasta de templates é a do projeto: os nomes usados nas rotas já vêm
    # prefixados (``producao/login.html``), o que evita ambiguidade com o
    # sistema de OS, que tem templates de mesmo nome.
    app = Flask(
        __name__,
        template_folder="../../templates",
        static_folder="../../static",
    )
    app.config.update(config)
    app.config.update(
        {
            "APP_NOME": APP_NOME,
            "APP_SUBTITULO": APP_SUBTITULO,
            "APP_VERSAO": VERSAO,
        }
    )

    csrf.init_app(app)
    app.config["producao_storage"] = criar_storage(app.config)

    app.register_blueprint(producao_bp)

    _registrar_filtros(app)
    _registrar_erros(app)

    @app.context_processor
    def _globais():
        return {
            "app_nome": APP_NOME,
            "app_subtitulo": APP_SUBTITULO,
            "app_versao": VERSAO,
            "fluxo_setores": fluxo.SETORES,
        }

    logger.info(
        "App de produção pronto (armazenamento: %s) em http://0.0.0.0:%s",
        app.config["producao_storage"].nome,
        app.config.get("PORT"),
    )
    return app


def criar_para_testes(configuracao: dict[str, Any] | None = None) -> Flask:
    """Cria o app para os testes, sem exigir configuração de ambiente.

    Diferente de :func:`create_app`, não passa por ``ProducaoConfig.carregar``:
    os testes fornecem exatamente o que querem usar (banco local temporário,
    PIN de gestão fixo, sem Google Sheets).
    """

    config = {
        "SECRET_KEY": "teste",
        "STORAGE": "local",
        "ADMIN_PIN": "",
        "PORT": 5001,
        "DEBUG": False,
        "SPREADSHEET_ID": "",
        "CREDENCIAIS": "credentials.json",
        "ESCOPOS": [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive.file",
        ],
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
        "SESSION_COOKIE_SECURE": False,
        "WTF_CSRF_ENABLED": True,
        "WTF_CSRF_TIME_LIMIT": None,
        "PERMANENT_SESSION_LIFETIME": 3600,
        "TESTING": True,
    }
    config.update(configuracao or {})
    return _montar_app(config)


def _registrar_filtros(app: Flask) -> None:
    @app.template_filter("classe_status")
    def classe_status(status: str) -> str:
        """Classe CSS do selo de status do setor."""

        mapa = {
            fluxo.NAO_INICIADO: "st-pendente",
            fluxo.EM_ANDAMENTO: "st-andamento",
            fluxo.CONCLUIDO: "st-concluido",
            fluxo.OP_AGUARDANDO: "st-pendente",
            fluxo.OP_EM_ANDAMENTO: "st-andamento",
            fluxo.OP_CONCLUIDA: "st-concluido",
        }
        return mapa.get(str(status or "").strip(), "st-pendente")

    @app.template_filter("icone_status")
    def icone_status(status: str) -> str:
        mapa = {
            fluxo.NAO_INICIADO: "○",
            fluxo.EM_ANDAMENTO: "◐",
            fluxo.CONCLUIDO: "●",
        }
        return mapa.get(str(status or "").strip(), "○")

    @app.template_filter("data_curta")
    def data_curta(valor: str) -> str:
        """Mostra só a data quando a hora não importa (prazo)."""

        texto = str(valor or "").strip()
        return texto.split(" ")[0] if texto else ""

    @app.template_filter("hora_curta")
    def hora_curta(valor: str) -> str:
        """Mostra ``dd/mm HH:MM`` para os carimbos de setor."""

        texto = str(valor or "").strip()
        if not texto:
            return ""
        partes = texto.split(" ")
        if len(partes) >= 2:
            return f"{partes[0][:5]} {partes[1][:5]}"
        return texto


def _registrar_erros(app: Flask) -> None:
    from appmodules.producao_web import auth

    @app.errorhandler(404)
    def _nao_encontrado(_erro):
        return (
            render_template(
                "producao/erro.html",
                mensagem="Página não encontrada no app de produção.",
                usuario=auth.usuario_atual(),
                e_gestao=auth.e_gestao(),
                setor_usuario=auth.setor_do_usuario(),
                setores=fluxo.SETORES,
                status_setor=fluxo.STATUS_SETOR,
                abas=[],
            ),
            404,
        )

    @app.errorhandler(500)
    def _erro_interno(erro):
        logger.error("Erro interno no app de produção: %s", erro, exc_info=True)
        return (
            render_template(
                "producao/erro.html",
                mensagem="Erro interno no app de produção. Tente novamente.",
                usuario=auth.usuario_atual(),
                e_gestao=auth.e_gestao(),
                setor_usuario=auth.setor_do_usuario(),
                setores=fluxo.SETORES,
                status_setor=fluxo.STATUS_SETOR,
                abas=[],
            ),
            500,
        )
