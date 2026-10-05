"""Application factory do sistema de OS.

Este módulo existe **separado** de ``appmodules/__init__.py`` de propósito: o
pacote ``appmodules`` é importado também pelo app de produção independente
(``appmodules.producao_web``), que não deve arrastar as dependências do sistema
de OS — em especial ``config.py``, que exige ``SECRET_KEY`` definida.

Por isso ``appmodules/__init__.py`` só expõe ``create_app`` sob demanda
(``__getattr__``); quem importa o pacote não carrega Flask, serviços nem
configuração.
"""

import logging
import os

from flask import Flask, jsonify, render_template, request

try:
	from dotenv import load_dotenv

	load_dotenv()
except ImportError:  # pragma: no cover
	pass

from appmodules.extensions import cache, csrf, limiter
from appmodules.integracao import (
	register_context_processors as register_producao_app_context,
)
from appmodules.mobile import (
	install_mobile_middleware,
	mobile_bp,
	render_page,
)
from appmodules.mobile import (
	register_context_processors as register_mobile_context,
)
from appmodules.repositories import CentraisRepository, ProducaoRepository
from appmodules.routes.auth_routes import auth_bp
from appmodules.routes.admin_routes import admin_bp
from appmodules.routes.centrais_routes import centrais_bp
from appmodules.routes.os_routes import os_bp
from appmodules.routes.producao_routes import producao_bp
from appmodules.routes.compras_routes import compras_bp
from appmodules.routes.ferramentas_routes import ferramentas_bp
from appmodules.routes.webhook_routes import webhook_bp
from appmodules.services import NotificationService, SheetsService, UserService
from appmodules.services.whatsapp_webhook_service import WhatsAppWebhookService
from config import Config

logger = logging.getLogger(__name__)



def _load_dotenv() -> None:
	"""Carrega .env quando python-dotenv estiver disponível."""
	return None


def _build_services():
	"""Cria os serviços da aplicação, preservando indisponibilidade do Sheets."""
	creds_file = os.path.join(
		os.path.dirname(os.path.dirname(__file__)), "credentials.json"
	)
	try:
		sheets_service = SheetsService(
			creds_file,
			Config.SHEETS.SHEET_ID,
			Config.SHEETS.SHEET_TAB,
			Config.SHEETS.SHEET_HORARIO_TAB,
			Config.SHEETS.SHEET_USUARIOS_TAB,
			Config.SHEETS.SHEET_PRODUCAO_TAB,
		)
		user_service = UserService(sheets_service)
		centrais_repository = CentraisRepository(sheets_service)
		logger.info("Serviços inicializados com sucesso")
	except (RuntimeError, OSError, ValueError, TypeError):
		logger.exception("Erro ao inicializar serviços")
		sheets_service = None
		user_service = None
		centrais_repository = None

	return sheets_service, user_service, centrais_repository


def _configure_error_handlers(app: Flask) -> None:
	@app.errorhandler(404)
	def page_not_found(error):
		logger.warning("Página não encontrada: %s", request.url)
		return render_page("erro.html", mensagem="Página não encontrada."), 404

	@app.errorhandler(500)
	def internal_server_error(error):
		logger.exception("Erro interno do servidor")
		return render_page("erro.html", mensagem="Erro interno do servidor."), 500

	@app.errorhandler(Exception)
	def handle_exception(error):
		if hasattr(error, "code"):
			return error

		logger.exception("Erro não tratado")
		return render_page("erro.html", mensagem="Ocorreu um erro inesperado."), 500


def create_app(config_object=None):
	"""Cria uma instância Flask configurada para produção ou testes."""
	_load_dotenv()
	logging.basicConfig(
		level=getattr(logging, Config.LOGGING.LEVEL.upper(), logging.INFO),
		format=Config.LOGGING.FORMAT,
	)

	app = Flask(
		__name__,
		template_folder="../templates",
		static_folder="../static",
	)
	app.config.from_object(config_object or Config.FLASK)
	app.config.from_object(Config.CACHE)
	app.config.from_object(Config.PRODUCAO_APP)
	if isinstance(config_object, dict):
		app.config.update(config_object)

	csrf.init_app(app)
	cache.init_app(app)

	app_env = os.getenv("APP_ENV", os.getenv("FLASK_ENV", "production"))
	app.config["APP_ENV"] = app_env

	if limiter is not None:
		try:
			limiter.init_app(app)
			app.config["limiter"] = limiter
			logger.info("Flask-Limiter inicializado")
		except (RuntimeError, ValueError, TypeError) as exc:  # pragma: no cover
			app.config["limiter"] = None
			logger.warning("Falha ao iniciar Flask-Limiter: %s", exc)
	else:
		app.config["limiter"] = None
		logger.warning(
			"Flask-Limiter não disponível. Instale 'Flask-Limiter' para habilitar rate limiting."
		)

	sheets_service, user_service, centrais_repository = _build_services()
	app.config.update(
		{
			"sheets_service": sheets_service,
			"user_service": user_service,
			"centrais_repository": centrais_repository,
			"producao_repository": ProducaoRepository(sheets_service) if sheets_service else None,
			"notification_service": NotificationService,
			"webhook_service": WhatsAppWebhookService(sheets_service=sheets_service),
		}
	)

	@app.before_request
	def check_services_availability():
		# O shell do app mobile (manifest, service worker e tela offline) precisa
		# continuar acessível mesmo com o Sheets fora do ar — assim o PWA instala e
		# mostra o aviso de indisponibilidade em vez de falhar silenciosamente.
		recursos_pwa = {
			"mobile.manifest",
			"mobile.service_worker",
			"mobile.offline",
			"mobile.instalar",
		}
		if request.endpoint and (
			request.endpoint.startswith("static")
			or request.endpoint == "favicon"
			or request.endpoint in recursos_pwa
		):
			return None

		if app.config.get("sheets_service") is None:
			logger.warning(
				"Serviço indisponível ao acessar endpoint: %s",
				request.endpoint or request.path,
			)
			if (
				request.path.startswith("/api/")
				or request.is_json
				or request.headers.get("X-Requested-With") == "XMLHttpRequest"
			):
				return jsonify(
					{"erro": "Serviço temporariamente indisponível", "status": 503}
				), 503
			return (
				render_template(
					"erro.html", mensagem="Serviço temporariamente indisponível"
				),
				503,
			)

	webhook_enabled = os.getenv("WHATSAPP_WEBHOOK_ENABLED", "false").lower() == "true"
	webhook_token = os.getenv("WHATSAPP_WEBHOOK_TOKEN", "").strip()
	webhook_secret = os.getenv("WHATSAPP_WEBHOOK_SECRET", "").strip()
	if webhook_enabled and webhook_token and not webhook_secret:
		if app_env == "production":
			logger.critical(
				"FALHA CRÍTICA DE SEGURANÇA: WHATSAPP_WEBHOOK_SECRET não configurado em PRODUÇÃO."
			)
			raise RuntimeError(
				"WHATSAPP_WEBHOOK_SECRET é obrigatório em produção quando webhook está habilitado."
			)
		logger.warning(
			"AVISO DE SEGURANÇA: WHATSAPP_WEBHOOK_SECRET não configurado (ambiente não-produção)."
		)
	elif webhook_enabled and not webhook_token:
		logger.warning(
			"Webhook WhatsApp habilitado mas WHATSAPP_WEBHOOK_TOKEN não configurado."
		)
	elif webhook_enabled and webhook_secret:
		logger.info("Webhook WhatsApp configurado com secret válido")

	app.register_blueprint(auth_bp)
	app.register_blueprint(admin_bp)
	app.register_blueprint(os_bp)
	app.register_blueprint(centrais_bp)
	app.register_blueprint(producao_bp)
	app.register_blueprint(compras_bp)
	app.register_blueprint(ferramentas_bp)
	app.register_blueprint(webhook_bp)
	app.register_blueprint(mobile_bp)

	# App mobile (PWA): prefixo /m + helpers de contexto usados pelos templates.
	# As rotas continuam exatamente as mesmas — só o template muda no modo app.
	install_mobile_middleware(app)
	register_mobile_context(app)

	# Atalho para o app dedicado de produção (por setor) em todas as telas.
	# É só um link: o app de produção tem login, sessão e planilha próprios.
	register_producao_app_context(app)

	configured_limiter = app.config.get("limiter")
	if configured_limiter:
		try:
			app.view_functions["auth.login"] = configured_limiter.limit("5/minute")(
				app.view_functions["auth.login"]
			)
			app.view_functions["auth.cadastro"] = configured_limiter.limit("3/minute")(
				app.view_functions["auth.cadastro"]
			)
		except KeyError:
			logger.warning("Não foi possível aplicar rate limit em rotas de auth.")
		try:
			app.view_functions["webhook.webhook_whatsapp"] = configured_limiter.limit("10/minute")(
				app.view_functions["webhook.webhook_whatsapp"]
			)
		except KeyError:
			logger.warning("Não foi possível aplicar rate limit ao webhook WhatsApp.")

	_configure_error_handlers(app)
	return app
