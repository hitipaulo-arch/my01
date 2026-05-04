"""
WhatsApp Web Service usando pywhatkit
Envia mensagens via WhatsApp Web automático (requer WhatsApp Web logado)
"""
import os
import logging
from datetime import datetime
from .whatsapp_utils import normalizar_numero_whatsapp, montar_mensagem_os

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
        # Phone numbers MUST come from environment variables, no defaults
        self.phone_from = phone_from or os.getenv('WHATSAPP_FROM')
        self.phone_to = phone_to or os.getenv('WHATSAPP_WEB_TO')
        self.delay_seconds = delay_seconds or int(os.getenv('WHATSAPP_WEB_DELAY_SECONDS', '35'))
        
        if not self.phone_from or not self.phone_to:
            logger.warning(
                "WHATSAPP_FROM ou WHATSAPP_WEB_TO não configurados. "
                "WhatsApp Web service será desabilitado."
            )
            self.enabled = False
            return
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
            message = montar_mensagem_os(numero_pedido, solicitante, setor,
                                        prioridade, descricao, equipamento,
                                        timestamp, info_adicional)

            # Normaliza número
            phone_normalized = normalizar_numero_whatsapp(self.phone_to)

            # Envia via pywhatkit (síncrono)
            logger.info(f"Enviando via WhatsApp Web para {phone_normalized}...")
            
            # wait_time increased to 15 seconds for reliable auto-sending
            # pywhatkit needs time to: open browser, load WhatsApp, navigate to chat, type, and send
            kit.sendwhatmsg_instantly(
                phone_normalized, 
                message, 
                wait_time=15,       # 15 segundos para processamento completo
                tab_close=False     # Mantém a aba aberta para confirmação visual
            )

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

    def enviar_mensagem_direta(self, phone_to: str, message: str) -> dict:
        """Envia uma mensagem direta para um número específico via WhatsApp Web (com envio automático)."""
        if not self.enabled:
            return {
                'success': False,
                'phone': phone_to,
                'method': 'whatsapp_web',
                'message': 'Serviço desabilitado ou pywhatkit não disponível'
            }

        try:
            phone_normalized = normalizar_numero_whatsapp(phone_to)
            logger.info(f"Enviando mensagem automaticamente via WhatsApp Web para {phone_normalized}...")
            
            # wait_time increased to 15 seconds for reliable auto-sending
            # pywhatkit needs time to: open browser, load WhatsApp, navigate to chat, type, and send
            kit.sendwhatmsg_instantly(
                phone_normalized, 
                message, 
                wait_time=15,      # 15 segundos para processamento completo
                tab_close=False     # Mantém a aba aberta para confirmação visual
            )
            logger.info(f"✅ Mensagem enviada AUTOMATICAMENTE via WhatsApp Web para {phone_normalized}")
            return {
                'success': True,
                'phone': phone_normalized,
                'method': 'whatsapp_web',
                'message': message,
                'auto_sent': True
            }
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem automaticamente via WhatsApp Web: {e}", exc_info=True)
            return {
                'success': False,
                'phone': phone_to,
                'method': 'whatsapp_web',
                'error': str(e)
            }


