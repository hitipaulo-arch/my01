"""
Funções utilitárias compartilhadas para serviços WhatsApp
"""
import re


def normalizar_numero_whatsapp(phone: str) -> str:
    """
    Normaliza número para formato +55xxxxxxxxxx

    Args:
        phone: Número de telefone em qualquer formato

    Returns:
        str: Número normalizado com +55 e dígitos
    """
    digits = "".join(filter(str.isdigit, phone))
    if not digits.startswith("55"):
        return "+55" + digits
    return "+" + digits


def _mascarar_pii(texto: str) -> str:
    """Mascarar PII (números de telefone, nomes) em texto para logging seguro."""
    if not texto:
        return ""
    # Mascarar números de telefone (padrões com 8 a 13 dígitos)
    # Ex: (12) 99123-4567 -> (12) 9****-**67
    texto = re.sub(
        r"(\d{2,4})[ \-.]?(\d{1,5})[ \-.]?(\d{4})", r"\1****\3", texto
    )
    # Mascarar sequências de 4+ dígitos que não foram pegas
    texto = re.sub(r"\d{4,}", "****", texto)

    return texto


def montar_mensagem_os(
    numero_pedido: str,
    solicitante: str,
    setor: str,
    prioridade: str,
    descricao: str,
    equipamento: str,
    timestamp: str,
    info_adicional: str = None,
) -> str:
    """
    Monta mensagem formatada com emojis para notificação de OS

    Args:
        numero_pedido: Número da OS
        solicitante: Nome de quem solicitou
        setor: Setor responsável
        prioridade: Nível de prioridade (urgente/alta/média/baixa)
        descricao: Descrição do problema
        equipamento: Equipamento afetado
        timestamp: Data/hora da OS
        info_adicional: Informações adicionais opcionais

    Returns:
        str: Mensagem formatada com emojis
    """
    emoji_priority = {"urgente": "🚨", "alta": "⚠️", "média": "📋", "baixa": "📝"}
    emoji = emoji_priority.get(prioridade.lower(), "📋")

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
