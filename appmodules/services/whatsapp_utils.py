"""
Funções utilitárias compartilhadas para serviços WhatsApp
"""

def normalizar_numero_whatsapp(phone: str) -> str:
    """
    Normaliza número para formato +55xxxxxxxxxx
    
    Args:
        phone: Número de telefone em qualquer formato
        
    Returns:
        str: Número normalizado com +55 e dígitos
    """
    digits = ''.join(filter(str.isdigit, phone))
    if not digits.startswith('55'):
        return '+55' + digits
    return '+' + digits


def montar_mensagem_os(numero_pedido: str, solicitante: str, setor: str,
                       prioridade: str, descricao: str, equipamento: str,
                       timestamp: str, info_adicional: str = None) -> str:
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
