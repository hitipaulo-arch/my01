"""
Validadores centralizados para formulários e payloads.

Fonte única de validação usada por app.py. As implementações vivas
originalmente em app.py foram movidas para cá; app.py apenas importa.
"""

from typing import Tuple, Any

from config import Config
from appmodules.models.usuario import Role


def parse_int_field(value: Any, default: int = 0) -> int:
    """
    Converte um valor para inteiro com fallback seguro.

    Aceita valores no formato brasileiro (ex.: "1.500" ou "1,5")
    removendo separadores de milhar antes da conversão.

    Args:
        value: Valor a ser convertido (string, int, float, None, etc.)
        default: Valor padrão caso a conversão falhe

    Returns:
        Inteiro convertido ou valor padrão
    """
    try:
        texto = str(value or "").strip().replace(".", "").replace(",", ".")
        if not texto:
            return default
        return int(float(texto))
    except (ValueError, TypeError):
        return default


def validate_item_form_data(
    nome_item: str,
    codigo_item: str,
    quantidade_raw: int,
    observacao: str,
    *,
    allow_empty_codigo: bool = False,
) -> Tuple[bool, str]:
    """
    Valida dados do formulário de item de produção/compra.

    Acumula TODOS os erros encontrados em uma única mensagem.

    Args:
        nome_item: Nome do item (obrigatório)
        codigo_item: Código do item (obrigatório, salvo allow_empty_codigo)
        quantidade_raw: Quantidade já convertida para int
        observacao: Observação opcional
        allow_empty_codigo: permite código vazio (usado em fluxos especiais)

    Returns:
        Tupla (valido: bool, mensagem: str)
    """
    val_cfg = Config.VALIDATION
    errors = []

    nome_limpo = str(nome_item or "").strip()
    codigo_limpo = str(codigo_item or "").strip()
    observacao_limpa = str(observacao or "").strip()

    if len(nome_limpo) < val_cfg.MIN_NOME_ITEM_LENGTH:
        errors.append(
            f"Nome do item deve ter pelo menos {val_cfg.MIN_NOME_ITEM_LENGTH} caracteres."
        )
    if len(nome_limpo) > val_cfg.MAX_NOME_ITEM_LENGTH:
        errors.append(
            f"Nome do item deve ter no máximo {val_cfg.MAX_NOME_ITEM_LENGTH} caracteres."
        )
    if not allow_empty_codigo and not codigo_limpo:
        errors.append("Código do item é obrigatório.")
    if len(observacao_limpa) > val_cfg.MAX_OBSERVACAO_LENGTH:
        errors.append(
            f"Observação deve ter no máximo {val_cfg.MAX_OBSERVACAO_LENGTH} caracteres."
        )
    if quantidade_raw < 0:
        errors.append("Quantidade não pode ser negativa.")
    if quantidade_raw > val_cfg.MAX_QUANTIDADE:
        errors.append(
            f"Quantidade deve ser menor ou igual a {val_cfg.MAX_QUANTIDADE}."
        )

    if errors:
        return False, " ".join(errors)
    return True, ""


def validate_user_payload(username: str, senha: str, role: str) -> Tuple[bool, str]:
    """
    Valida os dados de criação de usuário (username/senha/role).

    Args:
        username: Nome de usuário
        senha: Senha
        role: Papel (admin, operador, visualizador...)

    Returns:
        Tupla (valido: bool, mensagem: str)
    """
    val_cfg = Config.VALIDATION
    errors = []

    username_limpo = str(username or "").strip()
    senha_limpa = str(senha or "").strip()
    role_limpo = str(role or "").strip().lower()

    if len(username_limpo) < val_cfg.MIN_USERNAME_LENGTH:
        errors.append(
            f"Username deve ter pelo menos {val_cfg.MIN_USERNAME_LENGTH} caracteres."
        )
    if len(senha_limpa) < val_cfg.MIN_PASSWORD_LENGTH:
        errors.append(
            f"Senha deve ter pelo menos {val_cfg.MIN_PASSWORD_LENGTH} caracteres."
        )

    roles_validos = {r.value for r in Role}
    if role_limpo not in roles_validos:
        errors.append("Role inválida.")

    if errors:
        return False, " ".join(errors)
    return True, ""


# Compatibilidade com imports legados de app.py
_parse_int_field = parse_int_field
_validate_item_form_data = validate_item_form_data
_validate_user_payload = validate_user_payload
