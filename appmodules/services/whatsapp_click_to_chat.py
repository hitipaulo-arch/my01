"""
WhatsApp Click-to-Chat Service
Envia notificações via WhatsApp usando links wa.me (universal, works em qualquer dispositivo)
"""
import os
import webbrowser
import logging
from urllib.parse import quote
from datetime import datetime

logger = logging.getLogger(__name__)


class WhatsAppClickToChatService:
    """
    Serviço universal de notificação WhatsApp via Click-to-Chat links.
    Funciona em Windows, Mac, Linux, Android, iOS sem dependências complexas.
    """

    def __init__(self, phone_to: str = None, delay_seconds: int = 0):
        self.phone_to = phone_to or os.getenv('WHATSAPP_WEB_TO', '5512982200009')
        self.delay_seconds = delay_seconds or int(os.getenv('WHATSAPP_WEB_DELAY_SECONDS', 0))
        self.enabled = os.getenv('WHATSAPP_WEB_ENABLED', 'true').lower() == 'true'

    def gerar_link_chat(self, phone_number: str, message: str) -> str:
        """Gera link wa.me com mensagem pré-preenchida"""
        # Remove tudo exceto dígitos
        number_digits = ''.join(filter(str.isdigit, phone_number))
        
        # Prepara mensagem
        message_encoded = quote(message)
        
        # Gera link wa.me
        link = f"https://wa.me/{number_digits}?text={message_encoded}"
        return link

    def abrir_whatsapp(self, link: str) -> bool:
        """
        Abre WhatsApp com o link wa.me
        Usa os.startfile em Windows, webbrowser.open como fallback
        """
        try:
            if os.name == 'nt':  # Windows
                try:
                    os.startfile(link)
                    logger.info(f"WhatsApp aberto via os.startfile: {link[:50]}...")
                    return True
                except Exception as e:
                    logger.warning(f"os.startfile falhou, tentando webbrowser.open: {e}")
            
            # Fallback universal
            webbrowser.open(link, new=2)
            logger.info(f"WhatsApp aberto via webbrowser: {link[:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao abrir WhatsApp: {e}")
            return False

    def enviar_whatsapp_click_to_chat(self, numero_pedido: str, solicitante: str, 
                                       setor: str, prioridade: str, descricao: str,
                                       equipamento: str, timestamp: str = None,
                                       info_adicional: str = None) -> dict:
        """
        Envia notificação via Click-to-Chat WhatsApp
        Returns: dict com {'success': bool, 'link': str, 'phone': str, 'method': 'click_to_chat'}
        """
        if not self.enabled:
            return {'success': False, 'phone': self.phone_to, 'method': 'click_to_chat', 
                    'link': None, 'message': 'Serviço desabilitado'}

        try:
            if not timestamp:
                timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

            # Formata mensagem com emojis
            message = self._montar_mensagem(numero_pedido, solicitante, setor, 
                                          prioridade, descricao, equipamento,
                                          timestamp, info_adicional)

            # Gera link wa.me
            link = self.gerar_link_chat(self.phone_to, message)

            # Tenta abrir WhatsApp
            browser_opened = self.abrir_whatsapp(link)

            return {
                'success': True,
                'phone': self.phone_to,
                'method': 'click_to_chat',
                'link': link,
                'message': message,
                'browser_opened': browser_opened,
                'timestamp': timestamp
            }

        except Exception as e:
            logger.error(f"Erro ao enviar via Click-to-Chat: {e}", exc_info=True)
            return {
                'success': False,
                'phone': self.phone_to,
                'method': 'click_to_chat',
                'link': None,
                'error': str(e)
            }

    def _montar_mensagem(self, numero_pedido: str, solicitante: str, setor: str,
                        prioridade: str, descricao: str, equipamento: str,
                        timestamp: str, info_adicional: str = None) -> str:
        """Monta mensagem formatada com emojis"""
        # Mapa de prioridades com emojis
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

    def obter_info_dispositivo(self) -> dict:
        """Retorna info do dispositivo/SO"""
        return {
            'os_name': os.name,
            'platform': os.sys.platform if hasattr(os, 'sys') else 'unknown',
            'python_version': os.sys.version if hasattr(os, 'sys') else 'unknown'
        }

    def _normalizar_numero(self, phone: str) -> str:
        """Normaliza número de telefone para formato +55xxx"""
        digits = ''.join(filter(str.isdigit, phone))
        if not digits.startswith('55'):
            return '+55' + digits
        return '+55' + digits
