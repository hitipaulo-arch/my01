"""
WhatsApp Web Service usando pywhatkit
Envia mensagens via WhatsApp Web automático (requer WhatsApp Web logado)
"""

import os
import logging
from datetime import datetime
from .whatsapp_utils import (
    normalizar_numero_whatsapp,
    montar_mensagem_os,
    _mascarar_pii,
)

try:
    import pywhatkit as kit
except Exception as _import_error:  # pragma: no cover - depende do ambiente
    # Além de ImportError, o pywhatkit (via pyautogui/mouseinfo) levanta
    # KeyError/DisplayConnectionError em servidores sem X11/DISPLAY — como
    # Render, Docker e CI. Nesses casos o envio automático fica desabilitado.
    import logging as _logging

    _logging.getLogger(__name__).warning(
        "pywhatkit indisponível neste ambiente (%s). "
        "Envio automático via WhatsApp Web desabilitado.",
        _import_error,
    )
    kit = None

logger = logging.getLogger(__name__)


class WhatsAppWebNotificationService:
    """
    Serviço de notificação WhatsApp Web automatizado com pywhatkit.
    Requer WHATSAPP_FROM/WHATSAPP_WEB_TO configurados e WhatsApp Web logado
    no navegador da máquina que executa o app (controlado por
    WHATSAPP_WEB_ENABLED).
    """

    def __init__(
        self, phone_from: str = None, phone_to: str = None, delay_seconds: int = None
    ):
        # Phone numbers MUST come from environment variables, no defaults
        self.phone_from = phone_from or os.getenv("WHATSAPP_FROM")
        self.phone_to = phone_to or os.getenv("WHATSAPP_WEB_TO")
        self.delay_seconds = delay_seconds or int(
            os.getenv("WHATSAPP_WEB_DELAY_SECONDS", "15")
        )

        if not self.phone_from or not self.phone_to:
            logger.warning(
                "WHATSAPP_FROM ou WHATSAPP_WEB_TO não configurados. "
                "WhatsApp Web service será desabilitado."
            )
            self.enabled = False
            return  # Early exit
        self.enabled = os.getenv("WHATSAPP_WEB_ENABLED", "false").lower() == "true"

        if not kit:
            logger.warning(
                "pywhatkit não instalado - WhatsApp Web service desabilitado"
            )
            self.enabled = False

    def _send_message(self, phone_number: str, message: str) -> dict:
        """
        Método privado para encapsular o envio da mensagem via pywhatkit.
        """
        try:
            phone_normalized = normalizar_numero_whatsapp(phone_number)
            logger.info(
                f"Enviando mensagem via WhatsApp Web para {phone_normalized} (aguarde {self.delay_seconds}s)..."
            )

            # pywhatkit precisa de tempo para: abrir navegador, carregar WhatsApp,
            # navegar para o chat, digitar e enviar.
            kit.sendwhatmsg_instantly(
                phone_normalized,
                message,
                wait_time=self.delay_seconds,
                tab_close=False,  # Mantém a aba aberta para confirmação visual
            )

            logger.info(f"✅ Mensagem enviada via WhatsApp Web para {phone_normalized}")
            return {
                "success": True,
                "phone": phone_normalized,
                "method": "whatsapp_web",
                "message": _mascarar_pii(message),
            }
        except Exception as e:
            logger.error(
                f"Erro ao enviar mensagem via WhatsApp Web para {phone_number}: {e}",
                exc_info=True,
            )
            return {
                "success": False,
                "phone": phone_number,
                "method": "whatsapp_web",
                "error": str(e),
            }

    def enviar_whatsapp_web(
        self,
        numero_pedido: str,
        solicitante: str,
        setor: str,
        prioridade: str,
        descricao: str,
        equipamento: str,
        timestamp: str = None,
        info_adicional: str = None,
    ) -> dict:
        """
        Envia mensagem via WhatsApp Web automático
        Returns: dict com resultado do envio
        """
        if not self.enabled:
            return {
                "success": False,
                "phone": self.phone_to,
                "method": "whatsapp_web",
                "message": "Serviço desabilitado ou pywhatkit não disponível",
            }

        if not timestamp:
            timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        try:
            message = montar_mensagem_os(numero_pedido, solicitante, setor, prioridade, descricao, equipamento, timestamp, info_adicional)
            result = self._send_message(self.phone_to, message)
            result["timestamp"] = timestamp
            return result
        except Exception as e:
            logger.error(f"Erro ao enviar via WhatsApp Web: {e}", exc_info=True)
            return {
                "success": False,
                "phone": self.phone_to,
                "method": "whatsapp_web",
                "error": str(e),
            }

    def enviar_mensagem_direta(self, phone_to: str, message: str) -> dict:
        """Envia uma mensagem direta para um número específico via WhatsApp Web (com envio automático)."""
        if not self.enabled:
            return {
                "success": False,
                "phone": phone_to,
                "method": "whatsapp_web",
                "message": "Serviço desabilitado ou pywhatkit não disponível",
            }

        result = self._send_message(phone_to, message)
        result["auto_sent"] = result.get("success", False)
        return result
