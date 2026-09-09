"""
Formatadores centralizados para códigos e dados de produção.

Fonte única de formatação usada por app.py. As implementações vivas
originalmente em app.py foram movidas para cá; app.py apenas importa.
"""

from datetime import datetime


def format_codigo_code(value: str) -> str:
    """
    Normaliza o código do item para o formato ##-##-#####.

    Alterações recentes mostraram que códigos alfanuméricos eram perdidos
    porque a função removia tudo que não fosse dígito. Para evitar perda de
    dados, mantemos o valor original quando ele contém letras. Apenas
    normalizamos (extraímos dígitos e inserimos hífens) quando o valor contém
    apenas dígitos ou símbolos. A função é idempotente para formatos já
    compatíveis.

    Args:
        value: Código bruto do formulário

    Returns:
        Código formatado
    """
    raw = str(value or "").strip()
    if not raw:
        return ""

    # Se tiver letras, não alteramos para evitar perda de informação
    if any(ch.isalpha() for ch in raw):
        return raw

    # Extrai apenas dígitos e formata
    digits = "".join(ch for ch in raw if ch.isdigit())
    if not digits:
        return raw
    if len(digits) <= 2:
        return digits
    if len(digits) <= 4:
        return f"{digits[:2]}-{digits[2:]}"
    return f"{digits[:2]}-{digits[2:4]}-{digits[4:9]}"


def format_mtc_code(value: str) -> str:
    """
    Normaliza o número MTC para o formato #### (até 4 dígitos).

    Args:
        value: Código MTC bruto do formulário

    Returns:
        Código MTC formatado
    """
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    return digits[:4] if digits else ""


def append_producao_info(existing_info: str, nova_info: str) -> str:
    """
    Concatena informações adicionais com histórico simples.

    Cada nova anotação é prefixada com um timestamp entre colchetes e
    adicionada em uma nova linha, preservando o histórico anterior.

    Args:
        existing_info: Informações já registradas
        nova_info: Nova anotação a acrescentar

    Returns:
        Texto combinado com histórico
    """
    existing_info = str(existing_info or "").strip()
    nova_info = str(nova_info or "").strip()
    if not nova_info:
        return existing_info

    timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    extra = f"[{timestamp}] {nova_info}"
    if existing_info:
        return existing_info + "\n" + extra
    return extra


# Compatibilidade com imports legados de app.py
_format_codigo_code = format_codigo_code
_format_mtc_code = format_mtc_code
_append_producao_info = append_producao_info
