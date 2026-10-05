"""Formatação dos campos do app de produção.

Mantém as **mesmas regras** de máscara usadas no sistema de OS (código no
formato ``##-##-#####`` e MTC com até 4 dígitos), mas dentro do próprio app: o
app de produção não importa nada do sistema de OS, nem o contrário. Assim os
dois podem ser copiados, publicados e reiniciados de forma independente.

Sobre o código com letras: se o valor tiver letras, ele é preservado como veio —
extrair apenas dígitos apagaria informação de códigos alfanuméricos.
"""

from __future__ import annotations


def format_codigo_code(valor: str) -> str:
    """Normaliza o código do item para ``##-##-#####``.

    * vazio → vazio;
    * com letras → devolvido como veio (evita perda de informação);
    * só dígitos/símbolos → extrai os dígitos e insere os hífens.
    """

    bruto = str(valor or "").strip()
    if not bruto:
        return ""
    if any(caractere.isalpha() for caractere in bruto):
        return bruto

    digitos = "".join(caractere for caractere in bruto if caractere.isdigit())
    if not digitos:
        return bruto
    if len(digitos) <= 2:
        return digitos
    if len(digitos) <= 4:
        return f"{digitos[:2]}-{digitos[2:]}"
    return f"{digitos[:2]}-{digitos[2:4]}-{digitos[4:9]}"


def format_mtc_code(valor: str) -> str:
    """Normaliza o número MTC para até 4 dígitos."""

    digitos = "".join(caractere for caractere in str(valor or "") if caractere.isdigit())
    return digitos[:4] if digitos else ""


def formatar_data(valor: str) -> str:
    """Formata o prazo como ``dd/mm/aaaa`` a partir de dígitos digitados."""

    digitos = "".join(c for c in str(valor or "") if c.isdigit())[:8]
    if len(digitos) <= 2:
        return digitos
    if len(digitos) <= 4:
        return f"{digitos[:2]}/{digitos[2:]}"
    return f"{digitos[:2]}/{digitos[2:4]}/{digitos[4:]}"
