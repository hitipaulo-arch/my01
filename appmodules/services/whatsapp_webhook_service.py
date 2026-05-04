"""
WhatsApp Webhook Service - Receber e processar mensagens
Integração para receber mensagens do WhatsApp e processar comandos
"""
import os
import logging
import json
import re
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class WhatsAppWebhookService:
    """
    Serviço para receber e processar mensagens WhatsApp.
    Suporta parsing de comandos e validação de remetente.
    """

    # Comandos suportados
    COMANDOS = {
        'status': r'status\s+(\S+)',  # status OS-123
        'concluir': r'(?:concluir|concluído|done|finalizar)\s+(\S+)',  # concluir OS-123
        'chegada': r'(?:cheguei|chegada|arrived)\s+(\S+)',  # cheguei OS-123
        'pausa': r'(?:pausa|pause)\s+(\S+)',  # pausa OS-123
        'retomar': r'(?:retomar|resume)\s+(\S+)',  # retomar OS-123
        'ajuda': r'(?:ajuda|help|\?)',  # ajuda / help
    }

    def __init__(self, sheets_service=None, whatsapp_phone: str = None):
        """
        Inicializa o serviço de webhook.
        
        Args:
            sheets_service: Serviço do Google Sheets para atualizar dados
            whatsapp_phone: Número de WhatsApp autorizado para receber (formato 55XXXXXXXXXXX)
        """
        self.sheets_service = sheets_service
        self.whatsapp_phone = whatsapp_phone or os.getenv('WHATSAPP_WEBHOOK_FROM')
        
        # Validar token obrigatório - não usar padrão inseguro
        self.webhook_token = os.getenv('WHATSAPP_WEBHOOK_TOKEN', '').strip()
        
        if not self.webhook_token:
            logger.warning(
                "⚠️  WHATSAPP_WEBHOOK_TOKEN não configurado. "
                "Webhook WhatsApp será DESABILITADO por questões de segurança. "
                "Gere um token seguro: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
            )
        
        self.enabled = (
            os.getenv('WHATSAPP_WEBHOOK_ENABLED', 'false').lower() == 'true'
            and bool(self.webhook_token)
        )

    def validar_token(self, token: str) -> bool:
        """Valida token do webhook para segurança"""
        return token == self.webhook_token and self.enabled

    def extrair_numero_whatsapp(self, telefone: str) -> str:
        """Extrai apenas dígitos do número de WhatsApp"""
        return ''.join(filter(str.isdigit, telefone))

    def validar_remetente(self, telefone_remetente: str) -> bool:
        """Valida se o remetente é autorizado"""
        if not self.whatsapp_phone:
            logger.warning("WHATSAPP_WEBHOOK_FROM não configurado, permitindo todos os remetentes")
            return True

        remetente_digitos = self.extrair_numero_whatsapp(telefone_remetente)
        phone_digitos = self.extrair_numero_whatsapp(self.whatsapp_phone)
        
        autorizado = remetente_digitos == phone_digitos
        
        if not autorizado:
            logger.warning(f"Remetente não autorizado: {remetente_digitos}")
        
        return autorizado

    def extrair_comando(self, mensagem: str) -> Optional[Dict[str, Any]]:
        """
        Extrai comando e parâmetros da mensagem.
        
        Returns:
            Dict com {'tipo': str, 'numero_os': str} ou None se não encontrar
        """
        mensagem = mensagem.strip().lower()
        
        for tipo_comando, padrao in self.COMANDOS.items():
            match = re.search(padrao, mensagem)
            if match:
                if tipo_comando == 'ajuda':
                    return {'tipo': 'ajuda', 'numero_os': None}
                
                numero_os = match.group(1).upper() if match.groups() else None
                return {
                    'tipo': tipo_comando,
                    'numero_os': numero_os
                }
        
        return None

    def processar_mensagem(self, dados: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processa uma mensagem WhatsApp recebida.
        
        Args:
            dados: Dict com 'from', 'text', 'timestamp'
        
        Returns:
            Dict com resultado do processamento
        """
        resultado = {
            'sucesso': False,
            'tipo': None,
            'numero_os': None,
            'resposta': 'Erro ao processar mensagem'
        }
        
        try:
            telefone = dados.get('from', '')
            texto = dados.get('text', '').strip()
            
            # Validar remetente
            if not self.validar_remetente(telefone):
                resultado['resposta'] = '❌ Você não está autorizado a enviar comandos'
                return resultado
            
            # Extrair comando
            comando = self.extrair_comando(texto)
            
            if not comando:
                resultado['resposta'] = (
                    '❓ Comando não reconhecido. Envie:\n'
                    '  • status OS-123\n'
                    '  • cheguei OS-123\n'
                    '  • concluído OS-123\n'
                    '  • pausa OS-123\n'
                    '  • ajuda'
                )
                return resultado
            
            resultado['tipo'] = comando['tipo']
            resultado['numero_os'] = comando['numero_os']
            resultado['sucesso'] = True
            
            # Montar resposta conforme tipo de comando
            if comando['tipo'] == 'ajuda':
                resultado['resposta'] = (
                    '📋 Comandos disponíveis:\n'
                    '  • status OS-123 → Ver status da OS\n'
                    '  • cheguei OS-123 → Notificar chegada\n'
                    '  • concluído OS-123 → Finalizar OS\n'
                    '  • pausa OS-123 → Pausar OS\n'
                    '  • retomar OS-123 → Retomar OS\n'
                    '  • ajuda → Mostrar esta mensagem'
                )
            else:
                os_num = comando.get('numero_os', '???')
                respostas = {
                    'status': f'✅ Verificando status de {os_num}...',
                    'concluir': f'✅ Marcando {os_num} como concluída...',
                    'chegada': f'✅ Registrando chegada em {os_num}...',
                    'pausa': f'⏸️  Pausando {os_num}...',
                    'retomar': f'▶️  Retomando {os_num}...',
                }
                resultado['resposta'] = respostas.get(comando['tipo'], '✅ Comando processado')
        
        except Exception as e:
            logger.error(f"Erro ao processar mensagem webhook: {e}")
            resultado['resposta'] = f'❌ Erro: {str(e)}'
        
        return resultado
