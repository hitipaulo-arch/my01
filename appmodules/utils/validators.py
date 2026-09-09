"""
Validadores centralizados para formulários e payloads.

Este módulo contém funções de validação reutilizáveis extraídas do app.py
para evitar duplicação de código e facilitar testes.
"""

from typing import Tuple, Any, Dict
from appmodules.models.usuario import Role


def parse_int_field(value: Any, default: int = 0) -> int:
    """
    Converte um valor para inteiro com fallback seguro.

    Args:
        value: Valor a ser convertido (string, int, float, None, etc.)
        default: Valor padrão caso a conversão falhe

    Returns:
        Inteiro convertido ou valor padrão
    """
    try:
        if value is None or value == "":
            return default
        return int(float(str(value).strip()))
    except (ValueError, TypeError):
        return default


def validate_item_form_data(
    nome_item: str,
    codigo_item: str,
    quantidade_raw: int,
    observacao: str,
) -> Tuple[bool, str]:
    """
    Valida dados do formulário de item de produção.

    Args:
        nome_item: Nome do item (obrigatório)
        codigo_item: Código do item (obrigatório)
        quantidade_raw: Quantidade já convertida para int
        observacao: Observação opcional

    Returns:
        Tupla (valido: bool, mensagem: str)
    """
    if not nome_item or not nome_item.strip():
        return False, "Nome do item é obrigatório."

    if not codigo_item or not codigo_item.strip():
        return False, "Código do item é obrigatório."

    if quantidade_raw < 0:
        return False, "Quantidade não pode ser negativa."

    if len(observacao) > 500:
        return False, "Observação muito longa (máx. 500 caracteres)."

    return True, ""


def validate_user_payload(payload: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Valida payload de criação/atualização de usuário.

    Args:
        payload: Dicionário com dados do usuário

    Returns:
        Tupla (valido: bool, mensagem: str)
    """
    if not isinstance(payload, dict):
        return False, "Payload deve ser um objeto JSON."

    required_fields = ["username", "email", "role"]
    for field in required_fields:
        if field not in payload or not payload[field]:
            return False, f"Campo obrigatório ausente: {field}"

    # Validar role
    valid_roles = [role.value for role in Role]
    if payload.get("role") not in valid_roles:
        return False, (
            f"Role inválida. Valores permitidos: {', '.join(valid_roles)}"
        )

    # Validar email básico
    email = payload.get("email", "")
    if "@" not in email or "." not in email.split("@")[-1]:
        return False, "Formato de email inválido."

    return True, ""


# Compatibilidade com imports legados de app.py
_parse_int_field = parse_int_field
_validate_item_form_data = validate_item_form_data
_validate_user_payload = validate_user_payload