"""
Aplicação Flask Refatorada - Gestão de Ordens de Serviço

Ponto de entrada principal da aplicação.
"""

import os
import logging
import json
import pandas as pd
import hmac
import hashlib
from pathlib import Path

# Carrega variáveis do .env, se disponível
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass  # python-dotenv não instalado, usando variáveis de ambiente do sistema

from flask import (
    Flask,
    render_template,
    jsonify,
    request,
    redirect,
    url_for,
    flash,
    session,
    current_app,
)
from flask_wtf.csrf import CSRFProtect
from flask_caching import Cache


# Configuração de logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Imports dos serviços
from appmodules.services import SheetsService, NotificationService, UserService
from appmodules.services.whatsapp_webhook_service import WhatsAppWebhookService
from appmodules.routes.auth_routes import auth_bp
from appmodules.routes.os_routes import os_bp
from appmodules.routes.centrais_routes import centrais_bp
from centrais_repository import CentraisRepository
from report_logic import gerar_dados_relatorio
from appmodules.utils import login_required, admin_required, render_route_error
from config import Config
from appmodules.models.usuario import Role

# Inicializa serviços globais
CREDS_FILE = Path(__file__).parent / "credentials.json"

try:
    sheets_service = SheetsService(
        str(CREDS_FILE),
        Config.SHEETS.SHEET_ID,
        Config.SHEETS.SHEET_TAB,
        Config.SHEETS.SHEET_HORARIO_TAB,
        Config.SHEETS.SHEET_USUARIOS_TAB,
        Config.SHEETS.SHEET_PRODUCAO_TAB,
    )
    user_service = UserService(sheets_service)
    centrais_repository = CentraisRepository(sheets_service)
    logger.info("Serviços inicializados com sucesso")
except Exception as e:
    logger.error(f"Erro ao inicializar serviços: {e}")
    sheets_service = None
    user_service = None
    centrais_repository = None

# Flask App
app = Flask(__name__)
app.config.from_object(Config.FLASK)
app.config.from_object(Config.CACHE)

app_env = os.getenv("APP_ENV", os.getenv("FLASK_ENV", "production"))

csrf = CSRFProtect(app)
cache = Cache(app)

# Inicializa rate limiter (opcional)
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address

    limiter = Limiter(key_func=get_remote_address, app=app)
    app.config["limiter"] = limiter
    logger.info("Flask-Limiter inicializado")
except Exception:
    limiter = None
    logger.warning(
        "Flask-Limiter não disponível. Instale 'Flask-Limiter' para habilitar rate limiting."
    )

# Torna serviços disponíveis globalmente
app.config["sheets_service"] = sheets_service
app.config["user_service"] = user_service
app.config["centrais_repository"] = centrais_repository
app.config["notification_service"] = NotificationService

# Inicializa serviço de webhook WhatsApp
webhook_service = WhatsAppWebhookService(sheets_service=sheets_service)
app.config["webhook_service"] = webhook_service

# Validação estrita de segurança para webhook em produção
# Verifica se webhook está habilitado (token configurado + enabled=true)
webhook_enabled = os.getenv("WHATSAPP_WEBHOOK_ENABLED", "false").lower() == "true"
webhook_token = os.getenv("WHATSAPP_WEBHOOK_TOKEN", "").strip()
webhook_secret = os.getenv("WHATSAPP_WEBHOOK_SECRET", "").strip()

if webhook_enabled and webhook_token:
    if not webhook_secret:
        if app_env == "production":
            logger.critical(
                "FALHA CRÍTICA DE SEGURANÇA: WHATSAPP_WEBHOOK_SECRET não configurado em PRODUÇÃO. "
                "A aplicação não iniciará para evitar exposição do endpoint."
            )
            raise RuntimeError(
                "WHATSAPP_WEBHOOK_SECRET é obrigatório em produção quando webhook está habilitado. "
                "Configure a variável de ambiente antes de iniciar."
            )
        else:
            logger.warning(
                "AVISO DE SEGURANÇA: WHATSAPP_WEBHOOK_SECRET não configurado (ambiente não-produção). "
                "O webhook funcionará mas NÃO deve ser usado em produção sem esta configuração."
            )
    else:
        logger.info("Webhook WhatsApp configurado com secret válido")
elif webhook_enabled and not webhook_token:
    logger.warning(
        "Webhook WhatsApp habilitado mas WHATSAPP_WEBHOOK_TOKEN não configurado. "
        "Webhook será desabilitado por segurança."
    )

# Registra blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(os_bp)
app.register_blueprint(centrais_bp)

# Aplica rate limiting em rotas críticas de blueprints (DEPOIS do registro)
limiter = app.config.get("limiter")
if limiter:
    try:
        # Protege a rota de login contra força bruta
        app.view_functions["auth.login"] = limiter.limit("5/minute")(
            app.view_functions["auth.login"]
        )
        # Protege a rota de cadastro contra brute-force de criação de contas
        app.view_functions["auth.cadastro"] = limiter.limit("3/minute")(
            app.view_functions["auth.cadastro"]
        )
    except KeyError:
        logger.warning("Não foi possível aplicar rate limit em rotas de auth.")

# ════════════════════════════════════════════════════════════════════════════════
# ROTAS DE WEBHOOK (WhatsApp)
# ════════════════════════════════════════════════════════════════════════════════


@app.route("/webhook/whatsapp", methods=["GET", "POST"])
def webhook_whatsapp():
    """
    Webhook para receber mensagens do WhatsApp.
    GET: Validação do webhook pelo provedor
    POST: Receber mensagens
    """
    webhook_service = current_app.config.get("webhook_service")

    if not webhook_service:
        logger.error("Webhook service não inicializado")
        return jsonify({"erro": "Serviço indisponível"}), 503

    if not webhook_service.enabled:
        logger.warning("Webhook WhatsApp desabilitado")
        return jsonify({"erro": "Webhook desabilitado"}), 403

    # Validação GET (handshake do provedor)
    if request.method == "GET":
        token = request.args.get("hub.verify_token", "")
        desafio = request.args.get("hub.challenge", "")

        if webhook_service.validar_token(token):
            logger.info("Webhook validado com sucesso")
            return desafio, 200
        else:
            logger.warning(f"Token de webhook inválido: {token[:20]}...")
            return jsonify({"erro": "Token inválido"}), 403

    # Processar POST (mensagem recebida)
    if request.method == "POST":
        try:
            # Limita tamanho do payload para evitar DoS por body muito grande
            max_bytes = int(
                os.getenv("WHATSAPP_MAX_PAYLOAD_BYTES", 1024 * 1024)
            )  # 1MB por padrão
            content_length = request.content_length or 0
            if content_length and content_length > max_bytes:
                logger.warning(
                    f"Payload do webhook excede limite ({content_length} > {max_bytes})"
                )
                return jsonify({"erro": "Payload muito grande"}), 413

            # Validação HMAC/assinatura (obrigatória para segurança)
            webhook_secret = os.getenv("WHATSAPP_WEBHOOK_SECRET", "").strip()
            sig_hdr = request.headers.get(
                "X-Hub-Signature-256"
            ) or request.headers.get("X-Hub-Signature")
            raw = request.get_data() or b""
            if not sig_hdr:
                logger.warning("Assinatura de webhook ausente (X-Hub-Signature-256)")
                return jsonify({"erro": "Assinatura ausente"}), 403

            # aceita formatos como 'sha256=<hex>' ou apenas o hex
            sig = sig_hdr.split("=", 1)[1] if sig_hdr.startswith("sha256=") else sig_hdr

            computed = hmac.new(
                webhook_secret.encode(), raw, hashlib.sha256
            ).hexdigest()
            if not hmac.compare_digest(computed, sig):
                logger.warning("Assinatura de webhook inválida")
                return jsonify({"erro": "Assinatura inválida"}), 403

            # Parse JSON (após validação de assinatura)
            dados = request.get_json(silent=True) or {}

            # Extrair dados da mensagem
            mensagens = (
                dados.get("entry", [{}])[0]
                .get("changes", [{}])[0]
                .get("value", {})
                .get("messages", [])
            )

            if not mensagens:
                logger.debug("Webhook recebido sem mensagens (pode ser status update)")
                return jsonify({"OK": True}), 200

            mensagem = mensagens[0]
            tipo = mensagem.get("type", "unknown")

            # Processar apenas mensagens de texto
            if tipo != "text":
                logger.info(f"Tipo de mensagem ignorado: {tipo}")
                return jsonify({"OK": True}), 200

            # Extrair dados
            remetente = mensagem.get("from", "")
            texto = mensagem.get("text", {}).get("body", "")
            timestamp_unix = int(mensagem.get("timestamp", 0) or 0)

            # Converter timestamp
            from datetime import datetime as dt

            timestamp = (
                dt.fromtimestamp(timestamp_unix).isoformat()
                if timestamp_unix
                else dt.now().isoformat()
            )

            logger.info(f"Mensagem WhatsApp recebida de {remetente}: {texto[:50]}")

            # Processar mensagem
            resultado = webhook_service.processar_mensagem(
                {"from": remetente, "text": texto, "timestamp": timestamp}
            )

            # Log do resultado
            if resultado.get("sucesso"):
                logger.info(
                    f"Comando processado: {resultado.get('tipo')} - {resultado.get('numero_os', 'N/A')}"
                )
            else:
                logger.warning(f"Erro ao processar: {resultado.get('erro')}")

            # TODO: Aqui você pode enviar resposta automática via WhatsApp API
            # exemplo: NotificationService.enviar_resposta_whatsapp(remetente, resultado['resposta'])

            return jsonify({"OK": True, "resultado": resultado}), 200

        except Exception as e:
            logger.error(f"Erro ao processar webhook: {e}", exc_info=True)
            if app_env == "production":
                return jsonify({"erro": "Erro interno no servidor"}), 500
            return jsonify({"erro": str(e)}), 500

    # Registra limitador ao endpoint caso exista (usa view_functions para evitar warnings de lint)
    try:
        if limiter and "webhook_whatsapp" in app.view_functions:
            app.view_functions["webhook_whatsapp"] = limiter.limit("10/minute")(
                app.view_functions["webhook_whatsapp"]
            )
    except Exception:
        pass


# ════════════════════════════════════════════════════════════════════════════════
# ROTAS DE ADMINISTRAÇÃO
# ════════════════════════════════════════════════════════════════════════════════


@app.route("/usuarios", methods=["GET", "POST"])
@admin_required
def usuarios_admin():
    """Admin UI para gerenciar usuários."""

    user_service = current_app.config.get("user_service")
    mensagem = None
    tipo_mensagem = "success"

    if request.method == "POST":
        if not user_service:
            mensagem = "Serviço de usuários não disponível."
            tipo_mensagem = "danger"
        else:
            acao = request.form.get("acao")
            username = request.form.get("username", "").strip()

            if not username:
                mensagem = "Username é obrigatório."
                tipo_mensagem = "danger"
            else:
                if acao == "delete":
                    if user_service.deletar_usuario(username):
                        mensagem = f"Usuário {username} removido com sucesso."
                    else:
                        mensagem = f"Erro ao remover usuário {username}."
                        tipo_mensagem = "danger"
                else:
                    senha = request.form.get("senha", "").strip()
                    role = request.form.get("role", Role.ADMIN.value).strip().lower()
                    valido, mensagem_validacao = _validate_user_payload(
                        username=username,
                        senha=senha,
                        role=role,
                    )

                    if not valido:
                        mensagem = mensagem_validacao
                        tipo_mensagem = "danger"
                    else:
                        if user_service.criar_usuario(username, senha, role):
                            mensagem = f"Usuário {username} criado com sucesso."
                        else:
                            erro_detalhe = getattr(user_service, "last_error", None)
                            if erro_detalhe and "protected" in erro_detalhe.lower():
                                mensagem = (
                                    f"Erro ao criar usuário {username}: a aba de usuários está protegida no Google Sheets. "
                                    "Remova a proteção ou conceda permissão de edição à service account."
                                )
                            elif erro_detalhe:
                                mensagem = (
                                    f"Erro ao criar usuário {username}: {erro_detalhe}"
                                )
                            else:
                                mensagem = f"Erro ao criar usuário {username}."
                            tipo_mensagem = "danger"

    usuarios = user_service.get_todos_usuarios() if user_service else []
    usuarios_dict = {u.username: u.to_dict() for u in usuarios}

    return render_template(
        "usuarios.html",
        usuarios=usuarios_dict,
        mensagem=mensagem,
        tipo_mensagem=tipo_mensagem,
    )


@app.route("/relatorios")
@app.route("/auditoria")
@admin_required
@cache.cached(timeout=300) # Cache por 5 minutos
def relatorios():
    """
    Página de relatórios.
    A lógica de processamento de dados foi movida para 'appmodules/logic/report_logic.py'.
    """
    try:
        sheets_service = current_app.config.get("sheets_service")
        dados_relatorio = gerar_dados_relatorio(sheets_service)
        return render_template("relatorios.html", **dados_relatorio)
    except Exception as e:
        logger.error(f"Erro ao carregar relatórios: {e}")
        return render_template(
            "erro.html", mensagem=f"Erro ao carregar relatórios: {e}"
        ), 500


@app.route("/tempo-por-funcionario")
@admin_required
def tempo_por_funcionario():
    """Página com tempo de trabalho por funcionário."""
    return render_template(
        "tempo_por_funcionario.html", dados=[], chart_data={}, total_registros=0
    )


# ════════════════════════════════════════════════════════════════════════════════
# ERROR HANDLERS
# ════════════════════════════════════════════════════════════════════════════════


@app.errorhandler(404)
def page_not_found(e):
    """Handler para páginas não encontradas."""
    logger.warning(f"Página não encontrada: {request.url}")
    return render_template("erro.html", mensagem="Página não encontrada."), 404


@app.errorhandler(500)
def internal_server_error(e):
    """Handler para erros internos."""
    logger.error(f"Erro interno: {e}", exc_info=True)
    return render_template("erro.html", mensagem="Erro interno do servidor."), 500


@app.errorhandler(Exception)
def handle_exception(e):
    """Handler genérico para exceções."""
    if hasattr(e, "code"):
        return e

    logger.error(f"Erro não tratado: {e}", exc_info=True)
    return render_template("erro.html", mensagem="Ocorreu um erro inesperado."), 500


def _parse_int_field(value, default=0):
    """Converte valores numéricos vindos de formulário em inteiro seguro."""
    try:
        texto = str(value or "").strip().replace(".", "").replace(",", ".")
        if not texto:
            return default
        return int(float(texto))
    except Exception:
        return default


def _format_codigo_code(value):
    """Normaliza o código do item para o formato ##-##-#####.

    Alterações recentes mostraram que códigos alfanuméricos eram perdidos
    porque a função removia tudo que não fosse dígito. Para evitar perda de
    dados, mantemos o valor original quando ele contém letras. Apenas
    normalizamos (extraímos dígitos e inserimos hífens) quando o valor contém
    apenas dígitos ou símbolos. A função é idempotente para formatos já
    compatíveis.
    """
    raw = str(value or "").strip()
    if not raw:
        return ""

    # Se tiver letras, não alteramos para evitar perda de informação
    if any(ch.isalpha() for ch in raw):
        return raw

    # Extrai apenas dígitos e formata
    digits = "".join(ch for ch in raw if ch.isdigit())
    if not digits:
        return raw
    if len(digits) <= 2:
        return digits
    if len(digits) <= 4:
        return f"{digits[:2]}-{digits[2:]}"
    return f"{digits[:2]}-{digits[2:4]}-{digits[4:9]}"


def _format_mtc_code(value):
    """Normaliza o número MTC para o formato #### (4 dígitos)."""
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    return digits[:4] if digits else ""


def _append_producao_info(existing_info: str, nova_info: str) -> str:
    """Concatena informações adicionais com histórico simples."""
    existing_info = str(existing_info or "").strip()
    nova_info = str(nova_info or "").strip()
    if not nova_info:
        return existing_info

    timestamp = pd.Timestamp.now().strftime("%d/%m/%Y %H:%M:%S")
    extra = f"[{timestamp}] {nova_info}"
    if existing_info:
        return existing_info + "\n" + extra
    return extra


def _validate_item_form_data(
    nome_item: str,
    codigo_item: str,
    quantidade_raw: int,
    observacao: str,
    *,
    allow_empty_codigo: bool = False,
) -> tuple[bool, str]:
    """Valida os dados de um item de produção/cadastro de compra."""
    val_cfg = Config.VALIDATION
    errors = []

    nome_limpo = str(nome_item or "").strip()
    codigo_limpo = str(codigo_item or "").strip()
    observacao_limpa = str(observacao or "").strip()

    if len(nome_limpo) < val_cfg.MIN_NOME_ITEM_LENGTH:
        errors.append(
            f"Nome do item deve ter pelo menos {val_cfg.MIN_NOME_ITEM_LENGTH} caracteres."
        )
    if len(nome_limpo) > val_cfg.MAX_NOME_ITEM_LENGTH:
        errors.append(
            f"Nome do item deve ter no máximo {val_cfg.MAX_NOME_ITEM_LENGTH} caracteres."
        )
    if not allow_empty_codigo and not codigo_limpo:
        errors.append("Código do item é obrigatório.")
    if len(observacao_limpa) > val_cfg.MAX_OBSERVACAO_LENGTH:
        errors.append(
            f"Observação deve ter no máximo {val_cfg.MAX_OBSERVACAO_LENGTH} caracteres."
        )
    if quantidade_raw < 0:
        errors.append("Quantidade não pode ser negativa.")
    if quantidade_raw > val_cfg.MAX_QUANTIDADE:
        errors.append(
            f"Quantidade deve ser menor ou igual a {val_cfg.MAX_QUANTIDADE}."
        )

    if errors:
        return False, " ".join(errors)
    return True, ""


def _validate_user_payload(username: str, senha: str, role: str) -> tuple[bool, str]:
    """Valida os dados de criação de usuário."""
    val_cfg = Config.VALIDATION
    errors = []

    username_limpo = str(username or "").strip()
    senha_limpa = str(senha or "").strip()
    role_limpo = str(role or "").strip().lower()

    if len(username_limpo) < val_cfg.MIN_USERNAME_LENGTH:
        errors.append(
            f"Username deve ter pelo menos {val_cfg.MIN_USERNAME_LENGTH} caracteres."
        )
    if len(senha_limpa) < val_cfg.MIN_PASSWORD_LENGTH:
        errors.append(
            f"Senha deve ter pelo menos {val_cfg.MIN_PASSWORD_LENGTH} caracteres."
        )

    roles_validos = {r.value for r in Role}
    if role_limpo not in roles_validos:
        errors.append("Role inválida.")

    if errors:
        return False, " ".join(errors)
    return True, ""


def _get_current_user_role():
    """Retorna a role do usuário logado, se disponível."""
    username = session.get("usuario")
    if not username:
        return None

    user_service = current_app.config.get("user_service")
    if not user_service:
        return session.get("role")

    user_data = user_service.get_usuario(username)
    if user_data:
        return user_data.role
    else:
        # Se o usuário da sessão não existe mais no serviço, invalida a sessão.
        logger.warning(f"Usuário '{username}' da sessão não encontrado. Invalidando sessão.")
        session.clear()
        return None

    return session.get("role")


@app.route("/producao", methods=["GET", "POST"])
@login_required
def producao():
    """Página de cadastro e acompanhamento de produção."""
    sheets_service = current_app.config.get("sheets_service")
    if not sheets_service:
        return render_template(
            "producao.html",
            itens=[],
            mensagem="Serviço de planilhas indisponível",
            read_only=True,
            tipo_mensagem="danger",
        ), 503

    user_role = _get_current_user_role()
    read_only = user_role != Role.ADMIN.value

    if request.method == "POST":
        if read_only:
            flash("Operadores têm acesso somente visualização nesta página.", "warning")
            return redirect(url_for("producao"))

        try:
            nome_item = request.form.get("nome_item", "").strip()
            codigo_item = _format_codigo_code(request.form.get("codigo_item", "").strip())
            quantidade_produzida = _parse_int_field(
                request.form.get("quantidade_produzida", 0), 0
            )
            observacao = request.form.get("observacao", "").strip()
            valido, mensagem = _validate_item_form_data(
                nome_item=nome_item,
                codigo_item=codigo_item,
                quantidade_raw=quantidade_produzida,
                observacao=observacao,
            )
            if not valido:
                flash(mensagem, "danger")
                return redirect(url_for("producao"))

            dados = [
                pd.Timestamp.now().strftime("%d/%m/%Y %H:%M:%S"),
                nome_item,
                codigo_item,
                _format_mtc_code(request.form.get("mtc_projeto", "")),
                str(quantidade_produzida),
                str(_parse_int_field(request.form.get("meta_producao", 0), 0)),
                request.form.get("status", "Em andamento").strip() or "Em andamento",
                observacao,
                request.form.get("responsavel", "").strip(),
                request.form.get("informacoes_adicionais", "").strip(),
                "produção",
            ]

            if not dados[1] or not dados[2]:
                flash("Nome do item e código são obrigatórios.", "danger")
                return redirect(url_for("producao"))

            item_id = str(int(pd.Timestamp.now().timestamp() * 1000))
            row_data = [str(item_id)] + dados

            if not sheets_service.add_producao(row_data):
                flash("Erro ao salvar item de produção.", "danger")
                return redirect(url_for("producao"))

            flash("Item de produção cadastrado com sucesso!", "success")
            return redirect(url_for("producao"))
        except Exception as e:
            logger.error(f"Erro ao cadastrar produção: {e}", exc_info=True)
            if app_env == "production":
                flash("Erro ao cadastrar item.", "danger")
            else:
                flash(f"Erro ao cadastrar item: {e}", "danger")
            return redirect(url_for("producao"))

    try:
        itens = sheets_service.get_all_producao(use_cache=True)
        itens_ordenados = sorted(
            itens, key=lambda item: item.get("row_id", 0), reverse=True
        )
        return render_template(
            "producao.html", itens=itens_ordenados, read_only=read_only
        )
    except Exception as e:
        logger.error(f"Erro ao carregar produção: {e}", exc_info=True)
        return render_template(
            "erro.html", mensagem=f"Erro ao processar dados: {e}"
        ), 500


@app.route("/producao/atualizar/<int:row_id>", methods=["POST"])
@admin_required
def atualizar_producao(row_id):
    """Atualiza um item de produção existente."""
    sheets_service = current_app.config.get("sheets_service")
    if not sheets_service:
        return jsonify({"success": False, "message": "Serviço indisponível"}), 503

    try:
        original = sheets_service.get_producao_by_row_id(row_id) or {}
        if not original:
            return jsonify({"success": False, "message": "Item não encontrado."}), 404

        nome_item = request.form.get("nome_item", original.get("Nome do item", "")).strip()
        codigo_item = _format_codigo_code(
            request.form.get("codigo_item", original.get("Código", "")).strip()
        )
        quantidade_produzida = _parse_int_field(
            request.form.get(
                "quantidade_produzida", original.get("Quantidade produzida", 0)
            ),
            0,
        )
        observacao = request.form.get("observacao", original.get("Observação", "")).strip()
        valido, mensagem = _validate_item_form_data(
            nome_item=nome_item,
            codigo_item=codigo_item,
            quantidade_raw=quantidade_produzida,
            observacao=observacao,
        )
        if not valido:
            return jsonify({"success": False, "message": mensagem}), 400

        row_data = [
            str(original.get("ID", "") or original.get("id", "") or row_id),
            str(original.get("Carimbo de data/hora", "")).strip(),
            nome_item,
            codigo_item,
            _format_mtc_code(
                request.form.get(
                    "mtc_projeto", original.get("Número do projeto MTC", "")
                )
            ),
            str(quantidade_produzida),
            str(
                _parse_int_field(
                    request.form.get(
                        "meta_producao", original.get("Meta de produção", 0)
                    ),
                    0,
                )
            ),
            request.form.get("status", original.get("Status", "Em andamento")).strip()
            or "Em andamento",
            observacao,
            request.form.get("responsavel", original.get("Responsável", "")).strip(),
            _append_producao_info(
                original.get("Informações adicionais", ""),
                request.form.get("nova_informacao", ""),
            ),
            str(original.get("Origem", "produção")).strip() or "produção",
        ]

        if not row_data[2] or not row_data[3]:
            return jsonify(
                {"success": False, "message": "Nome do item e código são obrigatórios."}
            ), 400

        if not sheets_service.update_producao(row_id, row_data):
            return jsonify(
                {"success": False, "message": "Não foi possível atualizar o item."}
            ), 500

        return jsonify(
            {"success": True, "message": "Item atualizado com sucesso!"}
        ), 200
    except Exception as e:
        logger.error(f"Erro ao atualizar produção: {e}", exc_info=True)
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/producao/dados")
@admin_required
@cache.cached(timeout=30) # Cache por 30 segundos para dados "quase" em tempo real
def producao_dados():
    """Retorna os dados agregados da produção para atualização em tempo real."""
    sheets_service = current_app.config.get("sheets_service")
    if not sheets_service:
        return jsonify({"success": False, "message": "Serviço indisponível"}), 503

    try:
        itens_brutos = sheets_service.get_all_producao(use_cache=False, force_refresh=True)

        # Filtra para não incluir itens cancelados no dashboard
        status_cancelado = {"cancelado", "cancelada"}
        itens = [
            item for item in itens_brutos
            if str(item.get("Status", "")).strip().lower() not in status_cancelado
        ]

        summary = {
            "total_itens": len(itens),
            "total_produzido": 0,
            "total_meta": 0,
            "total_faltante": 0,
            "percentual_global": 0,
        }

        barras = []
        status_counts = {"Concluído": 0, "Em andamento": 0, "Pendente": 0}
        responsavel_counts = {}

        def _status_bucket(valor):
            texto = str(valor or "").strip().lower()
            if texto in ("concluído", "concluido", "finalizado", "finalizada"):
                return "Concluído"
            if texto in ("em andamento", "andamento"):
                return "Em andamento"
            return "Pendente"

        for item in itens:
            produzido = _parse_int_field(item.get("Quantidade produzida", 0), 0)
            meta = _parse_int_field(item.get("Meta de produção", 0), 0)
            restante = max(meta - produzido, 0)

            summary["total_produzido"] += produzido
            summary["total_meta"] += meta
            barras.append(
                {
                    "nome": item.get("Nome do item", ""),
                    "produzido": produzido,
                    "restante": restante,
                    "meta": meta,
                    "status": item.get("Status", ""),
                    "percentual": round((produzido / meta) * 100, 1) if meta else 0,
                }
            )
            status_counts[_status_bucket(item.get("Status", ""))] += 1
            responsavel = str(item.get("Responsável", "")).strip() or "Não atribuído"
            responsavel_counts[responsavel] = (
                responsavel_counts.get(responsavel, 0) + 1
            )

        summary["total_faltante"] = max(
            summary["total_meta"] - summary["total_produzido"], 0
        )
        summary["percentual_global"] = (
            round((summary["total_produzido"] / summary["total_meta"]) * 100, 1)
            if summary["total_meta"]
            else 0
        )

        # Ordena os itens por status mais comum (segundo status_counts), depois por nome
        status_order = [
            k for k, v in sorted(status_counts.items(), key=lambda kv: -kv[1])
        ]
        status_rank = {s: i for i, s in enumerate(status_order)}
        barras = sorted(
            barras,
            key=lambda item: (
                status_rank.get(item.get("status", ""), len(status_rank)),
                item.get("nome", "") or "",
            ),
        )

        return jsonify(
            {
                "success": True,
                "summary": summary,
                "items": barras,
                "status_counts": status_counts,
                "responsavel_counts": responsavel_counts,
            }
        ), 200
    except Exception as e:
        logger.error(f"Erro ao gerar dados de produção: {e}", exc_info=True)
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/producao-abertas")
@login_required
def producao_abertas():
    """Página que mostra as OPs de produção que não estão concluídas ou bloqueadas."""
    sheets_service = current_app.config.get("sheets_service")
    if not sheets_service:
        return render_template(
            "producao_abertas.html",
            itens=[],
            mensagem="Serviço de planilhas indisponível",
            tipo_mensagem="danger",
        ), 503

    try:
        itens = sheets_service.get_all_producao(use_cache=True)

        # Filtra itens que não estão concluídos ou bloqueados
        status_excluidos = {"concluído", "concluido", "bloqueado", "bloqueada", "cancelado", "cancelada"}
        itens_abertos = [
            item
            for item in itens
            if str(item.get("Status", "")).strip().lower() not in status_excluidos
        ]

        # Calcula estatísticas
        total_itens = len(itens)
        total_ops_abertas = len(itens_abertos)
        itens_bloqueados = sum(
            1
            for item in itens
            if str(item.get("Status", "")).strip().lower() in {"bloqueado", "bloqueada"}
        )
        itens_concluidos = sum(
            1
            for item in itens
            if str(item.get("Status", "")).strip().lower() in {"concluído", "concluido"}
        )
        taxa_conclusao = round((itens_concluidos / total_itens * 100), 1) if total_itens > 0 else 0

        # Ordena os itens restantes
        itens_ordenados = sorted(
            itens_abertos, key=lambda item: item.get("row_id", 0), reverse=True
        )

        return render_template(
            "producao_abertas.html",
            itens=itens_ordenados,
            total_ops_abertas=total_ops_abertas,
            itens_bloqueados=itens_bloqueados,
            taxa_conclusao=taxa_conclusao,
        )
    except Exception as e:
        return render_route_error(
            e,
            user_message="Erro ao carregar dados de produção em aberto.",
        )


@app.route("/dashboard-producao")
@login_required
def dashboard_producao():
    """Exibe o painel visual de produção."""
    sheets_service = current_app.config.get("sheets_service")
    if not sheets_service:
        return render_template(
            "dashboard_producao.html", mensagem_erro="Serviço indisponível"
        ), 503

    return render_template("dashboard_producao.html")


@app.route("/itens", methods=["GET", "POST"])
@app.route("/compras", methods=["GET", "POST"])
@login_required
def itens():
    """Exibe e cadastra itens com alerta automático de compra."""
    sheets_service = current_app.config.get("sheets_service")
    if not sheets_service:
        return render_template("compras.html", itens=[], read_only=True), 503

    user_role = _get_current_user_role()
    read_only = user_role != Role.ADMIN.value

    # Constantes de validação (centralizadas em config.py)
    val_cfg = Config.VALIDATION
    min_nome = val_cfg.MIN_NOME_ITEM_LENGTH
    max_nome = val_cfg.MAX_NOME_ITEM_LENGTH
    max_obs = val_cfg.MAX_OBSERVACAO_LENGTH
    max_qtd = val_cfg.MAX_QUANTIDADE
    threshold_default = val_cfg.ITEM_ALERT_THRESHOLD_DEFAULT
    thresholds_especificos = val_cfg.ITEM_ALERT_THRESHOLDS or {}

    def _threshold_para_item(nome_item: str) -> int:
        """Retorna o limite de alerta para um item (case-insensitive)."""
        if not thresholds_especificos:
            return threshold_default
        chave = (nome_item or "").strip().lower()
        return int(thresholds_especificos.get(chave, threshold_default))

    try:
        if request.method == "POST":
            if read_only:
                flash(
                    "Operadores têm acesso somente visualização nesta página.",
                    "warning",
                )
                return redirect(url_for("itens"))

            nome_item = request.form.get("nome_item", "").strip()
            codigo_item = _format_codigo_code(
                request.form.get("codigo_item", "").strip()
            )
            mtc_projeto = _format_mtc_code(request.form.get("mtc_projeto", ""))
            quantidade_raw = _parse_int_field(request.form.get("quantidade", 0), 0)
            observacao = request.form.get("observacao", "").strip()

            # --- Validações de comprimento ---
            if len(nome_item) < min_nome:
                flash(
                    f"O nome do item deve ter pelo menos {min_nome} caracteres.",
                    "danger",
                )
                return redirect(url_for("itens"))
            if len(nome_item) > max_nome:
                flash(
                    f"O nome do item deve ter no máximo {max_nome} caracteres.",
                    "danger",
                )
                return redirect(url_for("itens"))
            if len(observacao) > max_obs:
                flash(
                    f"A observação deve ter no máximo {max_obs} caracteres.",
                    "danger",
                )
                return redirect(url_for("itens"))

            # --- Validação de quantidade ---
            if quantidade_raw < 0:
                flash("A quantidade não pode ser negativa.", "danger")
                return redirect(url_for("itens"))
            if quantidade_raw > max_qtd:
                flash(
                    f"A quantidade não pode ser maior que {max_qtd:,}.".replace(
                        ",", "."
                    ),
                    "danger",
                )
                return redirect(url_for("itens"))

            if not nome_item or not codigo_item:
                flash("Nome do item e código são obrigatórios.", "danger")
                return redirect(url_for("itens"))

            # --- Detecção de duplicidade por código ---
            try:
                existentes = sheets_service.get_all_producao(use_cache=True)
                for existente in existentes:
                    if (
                        str(existente.get("Origem", "")).strip().lower() != "item"
                    ):
                        continue
                    codigo_existente = _format_codigo_code(
                        str(existente.get("Código", "")).strip()
                    )
                    if codigo_existente and codigo_existente == codigo_item:
                        flash(
                            f"Já existe um item cadastrado com o código {codigo_item}.",
                            "warning",
                        )
                        return redirect(url_for("itens"))
            except Exception as dup_err:
                logger.warning(
                    f"Não foi possível verificar duplicidade de itens: {dup_err}"
                )

            row_data = [
                str(int(pd.Timestamp.now().timestamp() * 1000)),
                pd.Timestamp.now().strftime("%d/%m/%Y %H:%M:%S"),
                nome_item,
                codigo_item,
                mtc_projeto,
                str(quantidade_raw),
                "0",
                "Em andamento",
                observacao,
                "",
                "",
                "item",
            ]

            if not sheets_service.add_producao(row_data):
                flash("Não foi possível adicionar o item.", "danger")
                return redirect(url_for("itens"))

            flash("Item adicionado com sucesso!", "success")
            return redirect(url_for("itens"))

        sheets_service.marcar_origem_padrao_producao("produção")
        itens = sheets_service.get_all_producao(use_cache=True)
        itens_alerta = []
        itens_normais = []

        # Evita processar listas maiores do que o necessário para a página de compras.
        for item in itens:
            origem = str(item.get("Origem", "")).strip().lower()
            if origem != "item":
                continue
            # Recupera a quantidade tentando várias possíveis colunas para
            # manter compatibilidade com planilhas antigas/variações.
            quantidade = _parse_int_field(
                item.get(
                    "Quantidade produzida",
                    item.get(
                        "Quantidade",
                        item.get(
                            "Quantidade Item", item.get("Quantidade produzida ", 0)
                        ),
                    ),
                ),
                0,
            )
            nome_item_atual = str(item.get("Nome do item", "")).strip()
            threshold_item = _threshold_para_item(nome_item_atual)
            status_compra = (
                "precisa solicitar comprar"
                if quantidade <= threshold_item
                else "não precisa solicitar comprar"
            )
            item_compra = {
                "nome_item": nome_item_atual,
                "codigo_item": item.get("Código", ""),
                "mtc_projeto": _format_mtc_code(item.get("Número do projeto MTC", "")),
                "quantidade": quantidade,
                "status_compra": status_compra,
                "row_id": item.get("row_id"),
                "threshold": threshold_item,
            }

            if quantidade <= threshold_item:
                itens_alerta.append(item_compra)
            else:
                itens_normais.append(item_compra)

        itens_alerta = sorted(itens_alerta, key=lambda item: item.get("quantidade", 0))
        itens_normais = sorted(
            itens_normais, key=lambda item: item.get("quantidade", 0), reverse=True
        )

        # Estatísticas para os cards
        total_itens = len(itens_alerta) + len(itens_normais)
        total_alerta = len(itens_alerta)
        total_normais = len(itens_normais)
        total_estoque = sum(i.get("quantidade", 0) for i in (itens_alerta + itens_normais))

        return render_template(
            "compras.html",
            itens_alerta=itens_alerta,
            itens_normais=itens_normais,
            read_only=read_only,
            stats={
                "total_itens": total_itens,
                "total_alerta": total_alerta,
                "total_normais": total_normais,
                "total_estoque": total_estoque,
                "threshold_default": threshold_default,
            },
        )
    except Exception as e:
        logger.error(f"Erro ao carregar compras: {e}", exc_info=True)
        return render_template(
            "erro.html", mensagem=f"Erro ao processar dados: {e}"
        ), 500


@app.route("/itens/<int:row_id>/editar", methods=["GET", "POST"])
@login_required
def editar_item(row_id: int):
    """Edita um item de produção."""
    sheets_service = current_app.config.get("sheets_service")
    if not sheets_service:
        flash("Serviço de planilhas indisponível.", "danger")
        return redirect(url_for("itens"))

    item = sheets_service.get_producao_by_row_id(row_id)
    if not item:
        flash("Item não encontrado.", "danger")
        return redirect(url_for("itens"))

    if request.method == "POST":
        try:
            nome_item = str(request.form.get("nome_item", "")).strip()
            codigo_item = _format_codigo_code(
                str(request.form.get("codigo_item", "")).strip()
            )
            mtc_projeto = _format_mtc_code(
                str(request.form.get("mtc_projeto", "")).strip()
            )
            quantidade_raw = _parse_int_field(
                request.form.get("quantidade", "0"), 0
            )
            observacao = str(request.form.get("observacao", "")).strip()

            valido, mensagem = _validate_item_form_data(
                nome_item=nome_item,
                codigo_item=codigo_item,
                quantidade_raw=quantidade_raw,
                observacao=observacao,
            )
            if not valido:
                flash(mensagem, "danger")
                return redirect(url_for("editar_item", row_id=row_id))

            quantidade = quantidade_raw

            row_data = [
                item.get("ID", ""),
                item.get("Carimbo de data/hora", ""),
                nome_item,
                codigo_item,
                mtc_projeto,
                str(quantidade),
                item.get("Meta de produção", "0"),
                item.get("Status", "Em andamento"),
                observacao,
                item.get("Responsável", ""),
                item.get("Informações adicionais", ""),
                item.get("Origem", "item"),
            ]

            if not sheets_service.update_producao(row_id, row_data):
                flash("Não foi possível atualizar o item.", "danger")
                return redirect(url_for("editar_item", row_id=row_id))

            flash("Item atualizado com sucesso!", "success")
            return redirect(url_for("itens"))
        except Exception as e:
            logger.error(f"Erro ao editar item: {e}", exc_info=True)
            flash(f"Erro ao editar item: {e}", "danger")
            return redirect(url_for("editar_item", row_id=row_id))

    return render_template("editar_item.html", item=item, row_id=row_id)


@app.route("/itens/<int:row_id>/excluir", methods=["POST"])
@app.route("/itens/<int:row_id>/deletar", methods=["POST"])
@login_required
def excluir_item(row_id: int):
    """Exclui um item de produção."""
    sheets_service = current_app.config.get("sheets_service")
    if not sheets_service:
        flash("Serviço de planilhas indisponível.", "danger")
        return redirect(url_for("itens"))

    try:
        if not sheets_service.delete_producao(row_id):
            flash("Não foi possível excluir o item.", "danger")
            return redirect(url_for("itens"))

        flash("Item excluído com sucesso!", "success")
    except Exception as e:
        logger.error(f"Erro ao excluir item: {e}", exc_info=True)
        flash(f"Erro ao excluir item: {e}", "danger")

    return redirect(url_for("itens"))


@app.route("/ferramentas", methods=["GET", "POST"])
@admin_required
def ferramentas():
    """Página de controle de ferramentas."""
    sheets_service = current_app.config.get("sheets_service")
    if not sheets_service:
        return render_template(
            "ferramentas.html",
            ferramentas=[],
            mensagem="Serviço de planilhas indisponível",
            tipo_mensagem="danger",
        ), 503

    if request.method == "POST":
        try:
            dados = [
                request.form.get("nome", ""),
                request.form.get("patrocinio", ""),
                pd.Timestamp.now().strftime("%d/%m/%Y"),
                request.form.get("ultima_manutencao", ""),
                request.form.get("status", "Disponível"),
                request.form.get("observacao", ""),
                request.form.get("responsavel", ""),
            ]
            worksheet = get_or_create_ferramentas_worksheet(sheets_service)
            worksheet.append_row(dados)
            usuario_atual = session.get("usuario", "desconhecido")
            detalhes_hist = f"Patrocínio: {dados[1]}, Responsável: {dados[6]}, Status: {dados[4]}, Obs: {dados[5]}"
            add_historico_entry(
                sheets_service, dados[0], "Cadastro", usuario_atual, detalhes_hist
            )
            flash("Ferramenta cadastrada com sucesso!", "success")
            return redirect(url_for("ferramentas"))
        except Exception as e:
            logger.error(f"Erro ao adicionar ferramenta: {e}", exc_info=True)
            flash(f"Erro ao adicionar ferramenta: {e}", "danger")
            return redirect(url_for("ferramentas"))

    mensagem = None
    tipo_mensagem = None
    if "_flashes" in session:
        flashes = session.get("_flashes", [])
        if flashes:
            tipo_mensagem, mensagem = flashes[0]

    return render_template(
        "ferramentas.html",
        ferramentas=get_ferramentas_list(sheets_service),
        mensagem=mensagem,
        tipo_mensagem=tipo_mensagem,
    )


def get_or_create_ferramentas_worksheet(sheets_service):
    """Obtém ou cria a worksheet de ferramentas."""
    try:
        spreadsheet = sheets_service.client.open_by_key(sheets_service.sheet_id)
        try:
            worksheet = spreadsheet.worksheet(Config.SHEETS.SHEET_FERRAMENTAS_TAB)
            headers = worksheet.row_values(1)
            if "Responsável" not in headers:
                worksheet.update("G1", [["Responsável"]])
        except Exception:
            worksheet = spreadsheet.add_worksheet(
                title=Config.SHEETS.SHEET_FERRAMENTAS_TAB, rows=500, cols=10
            )
            worksheet.append_row(
                [
                    "Nome",
                    "Patrocínio",
                    "Data de Cadastro",
                    "Última Manutenção",
                    "Status",
                    "Observação",
                    "Responsável",
                ]
            )
            logger.info(f"Aba '{Config.SHEETS.SHEET_FERRAMENTAS_TAB}' criada")
        return worksheet
    except Exception as e:
        logger.error(f"Erro ao obter/criar worksheet de ferramentas: {e}")
        raise


def get_ferramentas_list(sheets_service):
    """Obtém lista de ferramentas."""
    try:
        worksheet = get_or_create_ferramentas_worksheet(sheets_service)
        dados = worksheet.get_all_records()
        return dados if dados else []
    except Exception as e:
        logger.warning(f"Erro ao obter ferramentas: {e}")
        return []


def get_or_create_historico_worksheet(sheets_service):
    """Obtém ou cria a worksheet de histórico de ferramentas."""
    try:
        spreadsheet = sheets_service.client.open_by_key(sheets_service.sheet_id)
        try:
            worksheet = spreadsheet.worksheet(Config.SHEETS.SHEET_HISTORICO_FERRAMENTAS_TAB)
        except Exception:
            worksheet = spreadsheet.add_worksheet(
                title=Config.SHEETS.SHEET_HISTORICO_FERRAMENTAS_TAB, rows=1000, cols=5
            )
            worksheet.append_row(
                ["Ferramenta", "Evento", "Data/Hora", "Usuário", "Detalhes"]
            )
            logger.info(f"Aba '{Config.SHEETS.SHEET_HISTORICO_FERRAMENTAS_TAB}' criada")
        return worksheet
    except Exception as e:
        logger.error(f"Erro ao obter/criar worksheet de histórico: {e}")
        raise


def add_historico_entry(sheets_service, nome_ferramenta, evento, usuario, detalhes=""):
    """Adiciona uma entrada no histórico de ferramentas."""
    try:
        worksheet = get_or_create_historico_worksheet(sheets_service)
        data_hora = pd.Timestamp.now().strftime("%d/%m/%Y %H:%M:%S")
        worksheet.append_row([nome_ferramenta, evento, data_hora, usuario, detalhes])
    except Exception as e:
        logger.warning(f"Erro ao adicionar histórico: {e}")


@app.route("/ferramentas/atualizar/<int:row_id>", methods=["POST"])
@admin_required
def atualizar_ferramenta(row_id):
    """Atualiza uma ferramenta."""
    sheets_service = current_app.config.get("sheets_service")
    if not sheets_service:
        return jsonify({"success": False, "message": "Serviço indisponível"}), 503

    try:
        worksheet = get_or_create_ferramentas_worksheet(sheets_service)
        row_num = row_id + 2  # +2 pelo cabeçalho
        dados_atuais = worksheet.row_values(row_num)
        nome_ferramenta = dados_atuais[0] if dados_atuais else "Desconhecida"
        novo_responsavel = request.form.get("responsavel", "")
        nova_manutencao = request.form.get("ultima_manutencao", "")
        novo_status = request.form.get("status", "")
        nova_observacao = request.form.get("observacao", "")
        old_manutencao = dados_atuais[3] if len(dados_atuais) > 3 else ""
        old_status = dados_atuais[4] if len(dados_atuais) > 4 else ""
        old_observacao = dados_atuais[5] if len(dados_atuais) > 5 else ""
        old_responsavel = dados_atuais[6] if len(dados_atuais) > 6 else ""
        worksheet.update(
            f"D{row_num}:G{row_num}",
            [[nova_manutencao, novo_status, nova_observacao, novo_responsavel]],
        )
        changes = []
        if novo_responsavel != old_responsavel:
            changes.append(
                f"Responsável: {old_responsavel or '-'} → {novo_responsavel or '-'}"
            )
        if nova_manutencao != old_manutencao:
            changes.append(
                f"Manutenção: {old_manutencao or '-'} → {nova_manutencao or '-'}"
            )
        if novo_status != old_status:
            changes.append(f"Status: {old_status or '-'} → {novo_status or '-'}")
        if nova_observacao != old_observacao:
            changes.append(f"Obs: {old_observacao or '-'} → {nova_observacao or '-'}")
        detalhes_hist = ", ".join(changes) if changes else "Sem alterações"
        usuario_atual = session.get("usuario", "desconhecido")
        add_historico_entry(
            sheets_service, nome_ferramenta, "Edição", usuario_atual, detalhes_hist
        )
        return jsonify({"success": True, "message": "Ferramenta atualizada!"})
    except Exception as e:
        logger.error(f"Erro ao atualizar ferramenta: {e}", exc_info=True)
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/ferramentas/deletar/<int:row_id>", methods=["POST"])
@admin_required
def deletar_ferramenta(row_id):
    """Deleta uma ferramenta."""
    sheets_service = current_app.config.get("sheets_service")
    if not sheets_service:
        return jsonify({"success": False, "message": "Serviço indisponível"}), 503

    try:
        worksheet = get_or_create_ferramentas_worksheet(sheets_service)
        row_num = row_id + 2
        dados_atuais = worksheet.row_values(row_num)
        nome_ferramenta = dados_atuais[0] if dados_atuais else "Desconhecida"
        usuario_atual = session.get("usuario", "desconhecido")
        worksheet.delete_rows(row_num)
        add_historico_entry(
            sheets_service,
            nome_ferramenta,
            "Exclusão",
            usuario_atual,
            "Ferramenta excluída",
        )
        return jsonify({"success": True, "message": "Ferramenta deletada!"})
    except Exception as e:
        logger.error(f"Erro ao deletar ferramenta: {e}", exc_info=True)
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/ferramentas/historico")
@admin_required
def historico_ferramentas():
    """Retorna histórico de uma ferramenta em JSON."""
    sheets_service = current_app.config.get("sheets_service")
    if not sheets_service:
        return jsonify({"success": False, "historico": []})
    nome = request.args.get("nome", "")
    try:
        worksheet = get_or_create_historico_worksheet(sheets_service)
        todos = worksheet.get_all_records()
        if nome:
            filtrado = [
                r for r in todos if r.get("Ferramenta", "").lower() == nome.lower()
            ]
        else:
            filtrado = todos
        filtrado = list(reversed(filtrado))
        return jsonify({"success": True, "historico": filtrado})
    except Exception as e:
        logger.error(f"Erro ao obter histórico: {e}")
        return jsonify({"success": False, "historico": [], "error": str(e)})


@app.route("/favicon.ico")
def favicon():
    """Favicon vazio para evitar erro 404."""
    return "", 204


# ════════════════════════════════════════════════════════════════════════════════
# PONTO DE ENTRADA
# ════════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Configurações para o servidor de desenvolvimento Flask.
    # Prioriza variáveis de ambiente, mas com padrões seguros.
    port = int(os.getenv("PORT", Config.FLASK.PORT))
    debug_mode = os.getenv("FLASK_DEBUG", str(Config.FLASK.DEBUG)).lower() in ("true", "1")
    
    # Padrão para '127.0.0.1' (localhost) que é mais seguro para desenvolvimento.
    # Use a variável de ambiente HOST=0.0.0.0 para permitir acesso de outras máquinas na rede.
    host = os.getenv("HOST", "127.0.0.1")
    
    # Adiciona um aviso de segurança se o modo debug estiver ativo em um ambiente de "produção"
    if debug_mode and app_env == "production":
        logger.warning(
            "ALERTA DE SEGURANÇA: O modo DEBUG está ativo em um ambiente de produção. "
            "Desative o modo debug em produção definindo FLASK_DEBUG=false."
        )

    logger.info(f"Iniciando servidor em http://{host}:{port}/ (Debug: {debug_mode}, Env: {app_env})")
    app.run(host=host, port=port, debug=debug_mode)
