"""
Formatadores centralizados para códigos e dados de produção.

Este módulo contém funções de formatação reutilizáveis extraídas do app.py
para evitar duplicação de código e facilitar testes.
"""

import re
from typing import Any, Dict


def format_codigo_code(value: str) -> str:
    """
    Formata código do item: remove espaços, converte para maiúsculas,
    mantém apenas alfanuméricos e hífens.

    Args:
        value: Código bruto do formulário

    Returns:
        Código formatado
    """
    if not value:
        return ""
    # Remove espaços e converte para maiúsculas
    formatted = value.strip().upper()
    # Mantém apenas alfanuméricos e hífens
    formatted = re.sub(r"[^A-Z0-9\-]", "", formatted)
    return formatted


def format_mtc_code(value: str) -> str:
    """
    Formata código MTC: remove espaços, converte para maiúsculas,
    mantém apenas alfanuméricos.

    Args:
        value: Código MTC bruto do formulário

    Returns:
        Código MTC formatado
    """
    if not value:
        return ""
    # Remove espaços e converte para maiúsculas
    formatted = value.strip().upper()
    # Mantém apenas alfanuméricos
    formatted = re.sub(r"[^A-Z0-9]", "", formatted)
    return formatted


def append_producao_info(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Adiciona informações computadas ao item de produção.

    Args:
        item: Dicionário com dados do item

    Returns:
        Item enriquecido com campos adicionais
    """
    if not isinstance(item, dict):
        return item

    # Cria cópia para não mutar o original
    enriched = item.copy()

    # Calcula status de produção baseado em quantidade vs meta
    try:
        quantidade = int(enriched.get("Quantidade", 0) or 0)
        meta = int(enriched.get("Meta de produção", 0) or 0)
        if meta > 0:
            percentual = (quantidade / meta) * 100
            enriched["Percentual Produção"] = round(percentual, 1)
            if percentual >= 100:
                enriched["Status Produção"] = "Concluído"
            elif percentual > 0:
                enriched["Status Produção"] = "Em andamento"
            else:
                enriched["Status Produção"] = "Não iniciado"
        else:
            enriched["Percentual Produção"] = 0
            enriched["Status Produção"] = "Sem meta"
    except (ValueError, TypeError):
        enriched["Percentual Produção"] = 0
        enriched["Status Produção"] = "Inválido"

    # Formata data se existir
    carimbo = enriched.get("Carimbo de data/hora", "")
    if carimbo:
        enriched["Data Formatada"] = carimbo

    return enriched


# Compatibilidade com imports legados de app.py
_format_codigo_code = format_codigo_code
_format_mtc_code = format_mtc_code
_append_producao_info = append_producao_info