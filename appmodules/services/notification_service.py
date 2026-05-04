"""Serviço unificado de notificações."""

import os
import logging
import smtplib
import json
import requests
import re
from concurrent.futures import ThreadPoolExecutor
from email.message import EmailMessage
from typing import Optional

from appmodules.services.whatsapp_click_to_chat import WhatsAppClickToChatService
from appmodules.services.whatsapp_web_service import WhatsAppWebNotificationService

logger = logging.getLogger(__name__)


class NotificationService:
    """Gerencia notificações via email e WhatsApp."""

    _executor = ThreadPoolExecutor(max_workers=int(os.getenv('NOTIFICATION_MAX_WORKERS', '4')))

    @staticmethod
    def _run_async(task_name: str, target, *args, **kwargs) -> bool:
        """Executa uma tarefa em background para não bloquear a resposta HTTP."""
        async_enabled = os.getenv('NOTIFICATION_ASYNC_ENABLED', 'true').strip().lower() in ('1', 'true', 'yes', 'on')

        if not async_enabled:
            try:
                target(*args, **kwargs)
                return True
            except Exception as e:
                logger.error("Erro ao executar tarefa síncrona %s: %s", task_name, e)
                return False

        def _runner():
            try:
                target(*args, **kwargs)
            except Exception as e:
                logger.error("Erro em tarefa assíncrona %s: %s", task_name, e)

        try:
            NotificationService._executor.submit(_runner)
            return True
        except Exception as e:
            logger.error("Falha ao enfileirar tarefa assíncrona %s: %s", task_name, e)
            return False

    @staticmethod
    def _normalizar_destino_whatsapp(numero: str) -> Optional[str]:
        """Normaliza número para formato com DDI 55 para uso em integrações WhatsApp."""
        if not numero:
            return None

        raw = str(numero).strip()
        if raw.lower().startswith('whatsapp:'):
            sufixo = raw.split(':', 1)[1].strip()
            digitos = re.sub(r'\D', '', sufixo)
            if len(digitos) < 10:
                return None
            if not digitos.startswith('55'):
                digitos = f"55{digitos}"
            return digitos

        digitos = re.sub(r'\D', '', raw)
        if len(digitos) < 10:
            return None
        if not digitos.startswith('55'):
            digitos = f"55{digitos}"

        return digitos
    
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
            'whatsapp_web': False,
            'whatsapp_click_to_chat': False
        }
        
        try:
            resultados['email'] = NotificationService.enviar_email(
                numero_pedido, solicitante, setor, prioridade, 
                descricao, equipamento, timestamp, info_adicional
            )
        except Exception as e:
            logger.error(f"Erro ao notificar email: {e}")
        

        # WhatsApp Web Automático
        try:
            service_web = WhatsAppWebNotificationService()
            result_web = service_web.enviar_whatsapp_web(
                numero_pedido, solicitante, setor, prioridade,
                descricao, equipamento, timestamp, info_adicional
            )
            resultados['whatsapp_web'] = result_web.get('success', False)
        except Exception as e:
            logger.error(f"Erro ao notificar whatsapp (Web): {e}")
        
        # WhatsApp Click-to-Chat (Universal)
        try:
            service_chat = WhatsAppClickToChatService()
            result_chat = service_chat.enviar_whatsapp_click_to_chat(
                numero_pedido, solicitante, setor, prioridade,
                descricao, equipamento, timestamp, info_adicional
            )
            resultados['whatsapp_click_to_chat'] = result_chat.get('success', False)
        except Exception as e:
            logger.error(f"Erro ao notificar whatsapp (Click-to-Chat): {e}")
        
        return resultados

    @staticmethod
    def enqueue_notificar_nova_os(
        numero_pedido: str,
        solicitante: str,
        setor: str,
        prioridade: str,
        descricao: str,
        equipamento: str,
        timestamp: str,
        info_adicional: str = ''
    ) -> bool:
        """Agenda envio de notificações de nova OS sem bloquear a requisição."""
        return NotificationService._run_async(
            'notificar_nova_os',
            NotificationService.notificar_nova_os,
            numero_pedido,
            solicitante,
            setor,
            prioridade,
            descricao,
            equipamento,
            timestamp,
            info_adicional,
        )

    @staticmethod
    def notificar_finalizacao_os(
        numero_pedido: str,
        solicitante: str,
        whatsapp_solicitante: str,
        servico_realizado: str = '',
        status_os: str = 'Finalizada'
    ) -> bool:
        """Envia WhatsApp para o solicitante quando a OS é finalizada usando WhatsApp Web no PC."""
        enabled = os.getenv('WHATSAPP_WEB_ENABLED', 'true').strip().lower() in ('1', 'true', 'yes', 'on')
        if not enabled:
            logger.warning("Notificação de finalização desativada: WHATSAPP_WEB_ENABLED=false (OS #%s)", numero_pedido)
            return False

        to_number = NotificationService._normalizar_destino_whatsapp(whatsapp_solicitante)
        if not to_number:
            logger.warning("Número de WhatsApp do solicitante inválido para OS #%s", numero_pedido)
            return False

        mensagem = f"Sua OS #{numero_pedido} já está terminada, agradecemos seu contato!!"
        logger.info("Iniciando notificação de finalização da OS #%s para %s", numero_pedido, to_number)

        try:
            service_web = WhatsAppWebNotificationService(phone_to=to_number)
            result_web = service_web.enviar_mensagem_direta(phone_to=to_number, message=mensagem)
            if result_web.get('success', False):
                logger.info("WhatsApp de finalização enviado via WhatsApp Web para %s (OS #%s)", to_number, numero_pedido)
                return True

            logger.warning(
                "Falha no envio direto via WhatsApp Web (OS #%s, destino=%s): %s",
                numero_pedido,
                to_number,
                result_web.get('error') or result_web.get('message') or 'erro não informado'
            )

            service_chat = WhatsAppClickToChatService(phone_to=to_number)
            result_chat = service_chat.gerar_link_chat(to_number, mensagem)
            opened = service_chat.abrir_whatsapp(result_chat)
            if opened:
                logger.info("Fallback click-to-chat aberto para %s (OS #%s, link=%s)", to_number, numero_pedido, result_chat)
                return True

            logger.error(
                "Falha no envio de finalização via WhatsApp Web e fallback click-to-chat (OS #%s, destino=%s)",
                numero_pedido,
                to_number
            )
            return False
        except Exception as e:
            logger.error("Erro ao enviar WhatsApp de finalização (OS #%s): %s", numero_pedido, e)
            return False

    @staticmethod
    def enqueue_notificar_finalizacao_os(
        numero_pedido: str,
        solicitante: str,
        whatsapp_solicitante: str,
        servico_realizado: str = '',
        status_os: str = 'Finalizada'
    ) -> bool:
        """Agenda notificação de finalização sem bloquear a atualização da OS."""
        return NotificationService._run_async(
            'notificar_finalizacao_os',
            NotificationService.notificar_finalizacao_os,
            numero_pedido,
            solicitante,
            whatsapp_solicitante,
            servico_realizado,
            status_os,
        )
