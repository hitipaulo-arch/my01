"""
WhatsApp Web Service usando pywhatkit
Envia mensagens via WhatsApp Web automático (requer WhatsApp Web logado)
"""
import os
import logging
from datetime import datetime
import time

try:
    import pywhatkit as kit
except ImportError:
    kit = None

logger = logging.getLogger(__name__)


class WhatsAppWebNotificationService:
    """
    Serviço de notificação WhatsApp Web automatizado com pywhatkit
    Requer WhatsApp Web logado em +5512991635552
    """

    def __init__(self, phone_from: str = None, phone_to: str = None, delay_seconds: int = None):
        self.phone_from = phone_from or os.getenv('WHATSAPP_FROM', '+5512991635552')
        self.phone_to = phone_to or os.getenv('WHATSAPP_WEB_TO', '5512982200009')
        self.delay_seconds = delay_seconds or int(os.getenv('WHATSAPP_WEB_DELAY_SECONDS', '35'))
        self.enabled = os.getenv('WHATSAPP_WEB_ENABLED', 'true').lower() == 'true'

        if not kit:
            logger.warning("pywhatkit não instalado - WhatsApp Web service desabilitado")
            self.enabled = False

    def enviar_whatsapp_web(self, numero_pedido: str, solicitante: str, setor: str,
                           prioridade: str, descricao: str, equipamento: str,
                           timestamp: str = None, info_adicional: str = None) -> dict:
        """
        Envia mensagem via WhatsApp Web automático
        Returns: dict com resultado do envio
        """
        if not self.enabled:
            return {
                'success': False,
                'phone': self.phone_to,
                'method': 'whatsapp_web',
                'message': 'Serviço desabilitado ou pywhatkit não disponível'
            }

        try:
            if not timestamp:
                timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

            # Monta mensagem
            message = self._montar_mensagem(numero_pedido, solicitante, setor,
                                           prioridade, descricao, equipamento,
                                           timestamp, info_adicional)

            # Normaliza número
            phone_normalized = self._normalizar_numero(self.phone_to)

            # Envia via pywhatkit (síncrono)
            logger.info(f"Enviando via WhatsApp Web para {phone_normalized}...")
            
            # sendwhatmsg_instantly abre navegador e envia imediatamente
            kit.sendwhatmsg_instantly(phone_normalized, message, wait_time=2, tab_close=False)

            logger.info(f"✅ Mensagem enviada via WhatsApp Web para {phone_normalized}")
            return {
                'success': True,
                'phone': phone_normalized,
                'method': 'whatsapp_web',
                'message': message,
                'timestamp': timestamp
            }

        except Exception as e:
            logger.error(f"Erro ao enviar via WhatsApp Web: {e}", exc_info=True)
            return {
                'success': False,
                'phone': self.phone_to,
                'method': 'whatsapp_web',
                'error': str(e)
            }

    def _montar_mensagem(self, numero_pedido: str, solicitante: str, setor: str,
                        prioridade: str, descricao: str, equipamento: str,
                        timestamp: str, info_adicional: str = None) -> str:
        """Monta mensagem formatada com prioridade"""
        emoji_priority = {
            'urgente': '🚨',
            'alta': '⚠️',
            'média': '📋',
            'baixa': '📝'
        }
        emoji = emoji_priority.get(prioridade.lower(), '📋')

        message = (
            f"{emoji} *NOVA OS #{numero_pedido}*\n"
            f"📅 *Data/Hora:* {timestamp}\n"
            f"👤 *Solicitante:* {solicitante}\n"
            f"🏢 *Setor:* {setor}\n"
            f"🔧 *Equipamento:* {equipamento}\n"
            f"⚡ *Prioridade:* *{prioridade.upper()}*\n\n"
            f"📝 *Descrição:*\n{descricao}"
        )

        if info_adicional:
            message += f"\n\nℹ️ *Info:* {info_adicional}"

        return message

    def _normalizar_numero(self, phone: str) -> str:
        """Normaliza número para formato +55xxxxxxxxxx"""
        digits = ''.join(filter(str.isdigit, phone))
        if not digits.startswith('55'):
            return '+55' + digits
        return '+55' + digits
