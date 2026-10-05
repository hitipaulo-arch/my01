"""Ponto de entrada principal da aplicação Flask."""

import logging
import os

from appmodules import create_app
from appmodules.models.usuario import Role
from appmodules.repositories.ferramentas_repository import (
    add_historico_entry,
    get_ferramentas_list,
    get_or_create_ferramentas_worksheet,
    get_or_create_historico_worksheet,
)
from appmodules.routes.ferramentas_routes import (
    atualizar_ferramenta,
    deletar_ferramenta,
    ferramentas,
    historico_ferramentas,
)
from appmodules.routes.webhook_routes import webhook_whatsapp
from appmodules.services.ai_service import (
    build_admin_ai_context as _build_admin_ai_context,
    get_ai_model_candidates as _get_ai_model_candidates,
    get_ai_model_name as _get_ai_model_name,
    get_nvidia_ai_client as _get_nvidia_ai_client,
)
from appmodules.utils.validators import validate_item_form_data, validate_user_payload
from appmodules.utils import admin_required
from config import Config

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None

logging.basicConfig(level=getattr(logging, Config.LOGGING.LEVEL.upper(), logging.INFO), format=Config.LOGGING.FORMAT)
logger = logging.getLogger(__name__)

def get_nvidia_ai_client():
    """Wrapper compatível que permite monkeypatch de app.OpenAI."""
    return _get_nvidia_ai_client(openai_cls=OpenAI)
get_ai_model_candidates = _get_ai_model_candidates
get_ai_model_name = _get_ai_model_name
build_admin_ai_context = _build_admin_ai_context


def _validate_item_form_data(nome_item, codigo_item, quantidade_raw, observacao):
    """Adapter legado que preserva a validação acumulada do monólito."""
    errors = []
    nome_normalizado = str(nome_item or "").strip()
    if not nome_normalizado:
        errors.append("Nome do item é obrigatório.")
    elif len(nome_normalizado) < Config.VALIDATION.MIN_NOME_ITEM_LENGTH:
        errors.append("Nome do item é muito curto.")
    if not codigo_item or not str(codigo_item).strip():
        errors.append("Código do item é obrigatório.")
    if quantidade_raw < 0 or quantidade_raw > Config.VALIDATION.MAX_QUANTIDADE:
        errors.append("Quantidade inválida.")
    if len(observacao or "") > Config.VALIDATION.MAX_OBSERVACAO_LENGTH:
        errors.append("Observação muito longa (máx. 500 caracteres).")
    if errors:
        return False, " ".join(errors)
    return validate_item_form_data(nome_item, codigo_item, quantidade_raw, observacao)


def _validate_user_payload(payload=None, *, username=None, senha=None, role=None):
    """Adapter para o payload JSON e a assinatura de formulário legada."""
    if payload is not None:
        return validate_user_payload(payload)
    errors = []
    if not username or len(str(username).strip()) < Config.VALIDATION.MIN_USERNAME_LENGTH:
        errors.append("Username deve ter no mínimo 3 caracteres.")
    if not senha or len(str(senha)) < Config.VALIDATION.MIN_PASSWORD_LENGTH:
        errors.append("Senha deve ter no mínimo 12 caracteres.")
    if role not in {item.value for item in Role}:
        errors.append("Role inválida.")
    return (False, " ".join(errors)) if errors else (True, "")


app = create_app()
app.config.update({
    "get_nvidia_ai_client": lambda: get_nvidia_ai_client(),
    "get_ai_model_candidates": lambda: [get_ai_model_name(), *[m for m in get_ai_model_candidates() if m != get_ai_model_name()]],
    "get_ai_model_name": lambda: get_ai_model_name(),
    "build_admin_ai_context": lambda: build_admin_ai_context(),
})
app_env = app.config.get("APP_ENV", os.getenv("APP_ENV", "production"))


@app.route("/favicon.ico")
def favicon():
    return "", 204


if __name__ == "__main__":
    app.run(host=os.getenv("HOST", "127.0.0.1"), port=int(os.getenv("PORT", Config.FLASK.PORT)), debug=os.getenv("FLASK_DEBUG", str(Config.FLASK.DEBUG)).lower() in ("true", "1"))
