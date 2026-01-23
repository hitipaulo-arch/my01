"""Serviço unificado de notificações."""

import os
import logging
import smtplib
import json
import requests
from email.message import EmailMessage
from typing import Optional

logger = logging.getLogger(__name__)


class NotificationService:
    """Gerencia notificações via email e WhatsApp."""
    
    @staticmethod
    def enviar_email(
        numero_pedido: str,
        solicitante: str,
        setor: str,
        prioridade: str,
        descricao: str,
        equipamento: str,
        timestamp: str,
        info_adicional: str = ''
    ) -> bool:
        """Envia notificação por email."""
        
        enabled = os.getenv('NOTIFY_ENABLED', 'false').strip().lower() in ('1', 'true', 'yes', 'on')
        if not enabled:
            return False
        
        to_raw = os.getenv('SMTP_RECIPIENTS', os.getenv('NOTIFY_TO', '')).strip()
        smtp_host = os.getenv('SMTP_HOST', '').strip()
        
        if not to_raw or not smtp_host:
            logger.warning("Email habilitado, mas SMTP_RECIPIENTS ou SMTP_HOST não configurados")
            return False
        
        recipients = [e.strip() for e in to_raw.split(',') if e.strip()]
        if not recipients:
            logger.warning("Email habilitado, mas SMTP_RECIPIENTS está vazio")
            return False
        
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
        smtp_user = os.getenv('SMTP_USER', '').strip()
        smtp_password = os.getenv('SMTP_PASSWORD', '').strip()
        use_tls = os.getenv('SMTP_USE_TLS', 'true').strip().lower() in ('1', 'true', 'yes', 'on')
        use_ssl = os.getenv('SMTP_USE_SSL', 'false').strip().lower() in ('1', 'true', 'yes', 'on')
        
        from_addr = os.getenv('NOTIFY_FROM', smtp_user or 'no-reply@localhost').strip()
        subject = f"[OS] Nova OS aberta #{numero_pedido} - {prioridade}"
        
        body_lines = [
            "Nova Ordem de Serviço aberta no sistema.",
            "",
            f"OS: #{numero_pedido}",
            f"Data/Hora: {timestamp}",
            f"Solicitante: {solicitante}",
            f"Setor: {setor}",
            f"Equipamento/Local: {equipamento}",
            f"Prioridade: {prioridade}",
            "",
            "Descrição:",
            (descricao or "").strip(),
        ]
        if info_adicional and info_adicional.strip():
            body_lines += ["", "Info adicional:", info_adicional.strip()]
        
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = from_addr
        msg['To'] = ', '.join(recipients)
        msg.set_content('\n'.join(body_lines))
        
        timeout = float(os.getenv('SMTP_TIMEOUT_SECONDS', '10'))
        
        try:
            if use_ssl:
                server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=timeout)
            else:
                server = smtplib.SMTP(smtp_host, smtp_port, timeout=timeout)
            
            with server:
                server.ehlo()
                if (not use_ssl) and use_tls:
                    server.starttls()
                    server.ehlo()
                if smtp_user and smtp_password:
                    server.login(smtp_user, smtp_password)
                server.send_message(msg)
            
            logger.info(f"Email enviado para: {', '.join(recipients)} (OS #{numero_pedido})")
            return True
        except Exception as e:
            logger.error(f"Falha ao enviar email (OS #{numero_pedido}): {e}")
            return False
    
    @staticmethod
    def enviar_whatsapp(
        numero_pedido: str,
        solicitante: str,
        setor: str,
        prioridade: str,
        descricao: str,
        equipamento: str,
        timestamp: str,
        info_adicional: str = ''
    ) -> bool:
        """Envia notificação por WhatsApp via Twilio."""
        
        enabled = os.getenv('WHATSAPP_ENABLED', 'false').strip().lower() in ('1', 'true', 'yes', 'on')
        if not enabled:
            return False
        
        account_sid = os.getenv('TWILIO_ACCOUNT_SID', '').strip()
        auth_token = os.getenv('TWILIO_AUTH_TOKEN', '').strip()
        from_number = os.getenv('TWILIO_WHATSAPP_FROM', '').strip()
        to_raw = os.getenv('TWILIO_WHATSAPP_TO', '').strip()
        
        if not all([account_sid, auth_token, from_number, to_raw]):
            logger.warning("WhatsApp habilitado, mas credenciais Twilio não configuradas")
            return False
        
        recipients = [n.strip() for n in to_raw.split(',') if n.strip()]
        if not recipients:
            logger.warning("WhatsApp habilitado, mas TWILIO_WHATSAPP_TO está vazio")
            return False
        
        emoji_priority = {
            'Urgente': '🚨',
            'Alta': '⚠️',
            'Média': '📋',
            'Baixa': '📝'
        }
        emoji = emoji_priority.get(prioridade, '📋')
        
        message_lines = [
            f"{emoji} *Nova OS #{numero_pedido}*",
            f"Prioridade: *{prioridade}*",
            "",
            f"📅 {timestamp}",
            f"👤 {solicitante}",
            f"🏢 {setor}",
            f"🔧 {equipamento}",
            "",
            "📝 Descrição:",
            (descricao or "").strip()[:200] + ("..." if len(descricao or "") > 200 else "")
        ]
        if info_adicional and info_adicional.strip():
            message_lines += ["", "ℹ️ Info adicional:", info_adicional.strip()[:100]]
        
        message_body = '\n'.join(message_lines)
        
        url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
        timeout = float(os.getenv('TWILIO_TIMEOUT_SECONDS', '10'))
        content_sid = os.getenv('TWILIO_CONTENT_SID', '').strip()
        content_vars_json = os.getenv('TWILIO_CONTENT_VARIABLES_JSON', '').strip()
        content_map = os.getenv('TWILIO_CONTENT_MAP', '').strip()
        
        success_count = 0
        for recipient in recipients:
            try:
                payload = {
                    'From': from_number,
                    'To': recipient,
                }
                
                if content_sid:
                    payload['ContentSid'] = content_sid
                    auto_vars = None
                    if not content_vars_json:
                        try:
                            field_values = {
                                'numero_pedido': str(numero_pedido or ''),
                                'timestamp': str(timestamp or ''),
                                'solicitante': str(solicitante or ''),
                                'setor': str(setor or ''),
                                'equipamento': str(equipamento or ''),
                                'prioridade': str(prioridade or ''),
                                'descricao': (str(descricao or '')[:200] + ("..." if len(str(descricao or '')) > 200 else '')),
                                'info': (info_adicional.strip()[:100] if info_adicional and info_adicional.strip() else '')
                            }
                            
                            auto_vars = {}
                            if content_map:
                                pairs = [p.strip() for p in content_map.split(',') if p.strip()]
                                for pair in pairs:
                                    try:
                                        key, field = [x.strip() for x in pair.split('=', 1)]
                                        if key and field and field in field_values:
                                            auto_vars[str(key)] = field_values[field]
                                    except Exception:
                                        continue
                            else:
                                auto_vars = {
                                    "1": field_values['numero_pedido'],
                                    "2": field_values['timestamp'],
                                    "3": field_values['solicitante'],
                                    "4": field_values['setor'],
                                    "5": field_values['equipamento'],
                                    "6": field_values['prioridade'],
                                    "7": field_values['descricao']
                                }
                                if field_values['info']:
                                    auto_vars["8"] = field_values['info']
                            
                            if auto_vars:
                                content_vars_json = json.dumps(auto_vars, ensure_ascii=False)
                        except Exception as e:
                            logger.error(f"Falha ao montar ContentVariables: {e}")
                            content_vars_json = None
                    
                    if content_vars_json:
                        payload['ContentVariables'] = content_vars_json
                    else:
                        payload['Body'] = message_body
                else:
                    payload['Body'] = message_body
                
                response = requests.post(url, auth=(account_sid, auth_token), 
                                       data=payload, timeout=timeout)
                if response.status_code in (200, 201):
                    logger.info(f"WhatsApp enviado para {recipient} (OS #{numero_pedido})")
                    success_count += 1
                else:
                    logger.error(f"Falha WhatsApp para {recipient}: {response.status_code}")
            except Exception as e:
                logger.error(f"Erro ao enviar WhatsApp para {recipient}: {e}")
        
        return success_count > 0
    
    @staticmethod
    def notificar_nova_os(
        numero_pedido: str,
        solicitante: str,
        setor: str,
        prioridade: str,
        descricao: str,
        equipamento: str,
        timestamp: str,
        info_adicional: str = ''
    ) -> dict:
        """Envia todas as notificações para uma nova OS."""
        
        resultados = {
            'email': False,
            'whatsapp': False
        }
        
        try:
            resultados['email'] = NotificationService.enviar_email(
                numero_pedido, solicitante, setor, prioridade, 
                descricao, equipamento, timestamp, info_adicional
            )
        except Exception as e:
            logger.error(f"Erro ao notificar email: {e}")
        
        try:
            resultados['whatsapp'] = NotificationService.enviar_whatsapp(
                numero_pedido, solicitante, setor, prioridade,
                descricao, equipamento, timestamp, info_adicional
            )
        except Exception as e:
            logger.error(f"Erro ao notificar whatsapp: {e}")
        
        return resultados
