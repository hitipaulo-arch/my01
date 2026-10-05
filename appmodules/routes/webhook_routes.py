"""Webhook HTTP do WhatsApp."""

import hashlib
import hmac
import logging
import os
from datetime import datetime, timezone

from flask import Blueprint, current_app, jsonify, request

webhook_bp = Blueprint("webhook", __name__)
logger = logging.getLogger(__name__)


@webhook_bp.route("/webhook/whatsapp", methods=["GET", "POST"])
def webhook_whatsapp():
    """Valida e processa o webhook do WhatsApp."""
    service = current_app.config.get("webhook_service")
    if not service:
        return jsonify({"erro": "Serviço indisponível"}), 503
    if not service.enabled:
        return jsonify({"erro": "Webhook desabilitado"}), 403
    if request.method == "GET":
        if service.validar_token(request.args.get("hub.verify_token", "")):
            return request.args.get("hub.challenge", ""), 200
        return jsonify({"erro": "Token inválido"}), 403
    try:
        max_bytes = int(os.getenv("WHATSAPP_MAX_PAYLOAD_BYTES", 1024 * 1024))
        content_length = request.content_length or 0
        if content_length and content_length > max_bytes:
            return jsonify({"erro": "Payload muito grande"}), 413
        raw = request.get_data() or b""
        signature = request.headers.get("X-Hub-Signature-256") or request.headers.get("X-Hub-Signature")
        if not signature:
            return jsonify({"erro": "Assinatura ausente"}), 403
        received = signature.split("=", 1)[1] if signature.startswith("sha256=") else signature
        expected = hmac.new(os.getenv("WHATSAPP_WEBHOOK_SECRET", "").strip().encode(), raw, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, received):
            return jsonify({"erro": "Assinatura inválida"}), 403
        data = request.get_json(silent=True) or {}
        messages = data.get("entry", [{}])[0].get("changes", [{}])[0].get("value", {}).get("messages", [])
        if not messages or messages[0].get("type", "unknown") != "text":
            return jsonify({"OK": True}), 200
        message = messages[0]
        timestamp_unix = int(message.get("timestamp", 0) or 0)
        timestamp = datetime.fromtimestamp(timestamp_unix, tz=timezone.utc).isoformat() if timestamp_unix else datetime.now(timezone.utc).isoformat()
        resultado = service.processar_mensagem({"from": message.get("from", ""), "text": message.get("text", {}).get("body", ""), "timestamp": timestamp})
        return jsonify({"OK": True, "resultado": resultado}), 200
    except Exception as exc:
        logger.error("Erro ao processar webhook: %s", exc, exc_info=True)
        if current_app.config.get("APP_ENV", os.getenv("APP_ENV", "production")) == "production":
            return jsonify({"erro": "Erro interno no servidor"}), 500
        return jsonify({"erro": str(exc)}), 500


__all__ = ["webhook_bp", "webhook_whatsapp"]