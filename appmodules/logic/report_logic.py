"""
Módulo de Lógica de Negócio para Geração de Relatórios.

Este módulo encapsula a complexidade de processar dados brutos das planilhas
e transformá-los em informações prontas para serem exibidas nos relatórios.

Refatorado para remover a dependência de pandas, usando apenas a
biblioteca padrão do Python.
"""

import logging
from collections import Counter, defaultdict
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def _first_col(rows, *candidatos):
    """Encontra a primeira coluna existente nos dados a partir de
    uma lista de candidatos."""
    if not rows:
        return None
    available = set(rows[0].keys())
    for col in candidatos:
        if col in available:
            return col
    return None


def _parse_dt(text):
    """Tenta converter texto para datetime nos formatos conhecidos.
    Retorna None se falhar."""
    if not text or not isinstance(text, str):
        return None
    text = text.strip()
    if not text:
        return None
    formatos = [
        "%d/%m/%Y %H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y",
        "%Y-%m-%d",
    ]
    for fmt in formatos:
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            continue
    return None


def _parse_datetime_maybe_time(valor, base_dt):
    """
    Converte um valor de texto para datetime, lidando com casos onde apenas
    o horário é fornecido, usando uma data base como referência.
    """
    if valor is None:
        return None
    texto = str(valor).strip()
    if not texto:
        return None

    # Se contém "/", é data completa
    if "/" in texto:
        return _parse_dt(texto)

    # Se contém ":", é somente horário - combinar com data base
    if ":" in texto and base_dt is not None:
        # Tentar formatos HH:MM:SS e HH:MM
        for fmt in ("%H:%M:%S", "%H:%M"):
            try:
                t = datetime.strptime(texto, fmt).replace(tzinfo=timezone.utc)
                return base_dt.replace(
                    hour=t.hour,
                    minute=t.minute,
                    second=t.second,
                    microsecond=0,
                )
            except (ValueError, TypeError):
                continue
    return None


def _safe_str(val):
    """Converte valor para string limpa e em minúsculas."""
    if val is None:
        return ""
    return str(val).strip().lower()


def _calcular_prioridade(rows, col_prioridade):
    """Calcula distribuição por prioridade."""
    if not col_prioridade:
        return [], []
    pri_counter = Counter(row.get(col_prioridade, "") for row in rows)
    return list(pri_counter.keys()), list(pri_counter.values())


def _calcular_setor(rows, col_setor):
    """Calcula distribuição por setor (top 10)."""
    if not col_setor:
        return [], []
    setor_counter = Counter(row.get(col_setor, "") for row in rows)
    top_setor = setor_counter.most_common(10)
    labels_setor = [s[0] for s in top_setor]
    dados_setor = [s[1] for s in top_setor]
    return labels_setor, dados_setor


def _calcular_tempo_resolucao(
    rows, col_andamento, col_termino, col_status, status_finalizadas
):
    """Calcula tempo médio global e evolução mensal do tempo de resolução."""
    tempo_medio = "N/A"
    media_mes_labels = []
    media_mes_values = []

    if not (col_andamento and col_termino):
        return tempo_medio, media_mes_labels, media_mes_values

    deltas = []
    mes_deltas = defaultdict(list)

    for row in rows:
        base_ts = row.get("_ts")
        inicio = _parse_datetime_maybe_time(
            row.get(col_andamento, ""),
            base_ts,
        )
        termino = _parse_datetime_maybe_time(
            row.get(col_termino, ""),
            base_ts,
        )

        if inicio and termino:
            delta_h = (termino - inicio).total_seconds() / 3600
            if delta_h > 0:
                if _safe_str(row.get(col_status, "")) in status_finalizadas:
                    deltas.append(delta_h)
                if base_ts:
                    mes_key = f"{base_ts.year}-{base_ts.month:02d}"
                    mes_deltas[mes_key].append(delta_h)

    if deltas:
        media_h = sum(deltas) / len(deltas)
        if media_h < 1:
            tempo_medio = f"{int(media_h * 60)}min"
        else:
            tempo_medio = f"{media_h:.1f}h"

    for mes in sorted(mes_deltas.keys()):
        vals = mes_deltas[mes]
        media_mes_labels.append(mes)
        media_mes_values.append(round(sum(vals) / len(vals), 1))

    return tempo_medio, media_mes_labels, media_mes_values


def gerar_dados_relatorio(sheets_service):
    """
    Busca e processa dados de OS para gerar
    métricas e gráficos do relatório.

    Args:
        sheets_service: Uma instância do SheetsService.

    Returns:
        Um dicionário contendo todos os dados para o template de relatórios.
        Em caso de erro, o dicionário conterá uma chave 'mensagem_erro'.
    """
    _empty = {
        "labels_prioridade": [],
        "dados_prioridade": [],
        "labels_setor": [],
        "dados_setor": [],
        "labels_tempo_resolucao": [],
        "dados_tempo_resolucao": [],
        "labels_dia_semana": [],
        "dados_dia_semana": [],
        "total_os": 0,
        "taxa_conclusao": "0%",
        "total_finalizadas": 0,
        "total_andamento": 0,
        "tempo_medio": "N/A",
        "tabela_resumo": [],
    }

    if not sheets_service:
        return {**_empty, "mensagem_erro": "Serviço de planilhas indisponível"}

    disponivel, erro_msg = sheets_service.is_available()
    if not disponivel:
        return {**_empty, "mensagem_erro": erro_msg}

    os_list = sheets_service.get_all_os()
    if not os_list:
        return _empty

    # Normalizar: garantir que cada registro tenha todas as chaves como string
    rows = []
    for record in os_list:
        row = {}
        for key, val in record.items():
            row[key] = "" if val is None else val
        rows.append(row)

    col_timestamp = _first_col(rows, "Carimbo de data/hora")
    col_status = _first_col(rows, "Status da OS")
    col_prioridade = _first_col(rows, "Prioridade", "Nível de prioridade")
    col_setor = _first_col(
        rows,
        "Setor",
        "Setor em que será realizado o serviço",
    )
    col_solicitante = _first_col(rows, "Nome do solicitante")
    col_descricao = _first_col(
        rows, "Descrição", "Descrição do Problema ou Serviço Solicitado"
    )
    col_andamento = _first_col(rows, "Horario de Andamento")
    col_termino = _first_col(rows, "Horario de Término")

    # Adicionar _ts (timestamp) a cada registro
    for row in rows:
        if col_timestamp:
            row["_ts"] = _parse_dt(row.get(col_timestamp, ""))
        else:
            row["_ts"] = None

    # Filtrar canceladas
    if col_status:
        rows = [
            row
            for row in rows
            if _safe_str(row.get(col_status, "")) not in (
                "cancelada",
                "cancelado",
            )
        ]

    # Métricas calculadas via sub-funções
    labels_prioridade, dados_prioridade = _calcular_prioridade(rows, col_prioridade)
    labels_setor, dados_setor = _calcular_setor(rows, col_setor)

    total_os = len(rows)

    # Status
    status_finalizadas = {"finalizada", "concluido", "concluído"}
    status_andamento = {"em andamento"}
    if col_status:
        status_list = [_safe_str(row.get(col_status, "")) for row in rows]
        finalizadas = sum(1 for s in status_list if s in status_finalizadas)
        total_andamento = sum(1 for s in status_list if s in status_andamento)
    else:
        finalizadas = 0
        total_andamento = 0

    if total_os > 0:
        taxa_conclusao = f"{(finalizadas / total_os * 100):.1f}%"
    else:
        taxa_conclusao = "0%"

    # Tempo médio de resolução e evolução mensal
    tempo_medio, media_mes_labels, media_mes_values = _calcular_tempo_resolucao(
        rows, col_andamento, col_termino, col_status, status_finalizadas
    )

    # Distribuição por dia da semana
    dias_map = {
        0: "Seg",
        1: "Ter",
        2: "Qua",
        3: "Qui",
        4: "Sex",
        5: "Sáb",
        6: "Dom",
    }
    dia_counter = Counter()
    for row in rows:
        ts = row.get("_ts")
        if ts:
            dia_counter[ts.weekday()] += 1
    dia_sorted = sorted(dia_counter.items())
    labels_dia_semana = [dias_map.get(d, str(d)) for d, _ in dia_sorted]
    dados_dia_semana = [c for _, c in dia_sorted]

    # Tabela resumo (top 50 mais recentes)
    rows_with_ts = [row for row in rows if row.get("_ts")]
    rows_sorted = sorted(
        rows_with_ts,
        key=lambda r: r["_ts"],
        reverse=True,
    )[:50]
    tabela_resumo = [
        {
            "data": row.get(col_timestamp, "") if col_timestamp else "",
            "solicitante": (
                row.get(col_solicitante, "") if col_solicitante else ""
            ),
            "setor": row.get(col_setor, "") if col_setor else "",
            "status": row.get(col_status, "") if col_status else "",
            "descricao": row.get(col_descricao, "") if col_descricao else "",
        }
        for row in rows_sorted
    ]

    return {
        "labels_prioridade": labels_prioridade,
        "dados_prioridade": dados_prioridade,
        "labels_setor": labels_setor,
        "dados_setor": dados_setor,
        "labels_tempo_resolucao": media_mes_labels,
        "dados_tempo_resolucao": media_mes_values,
        "labels_dia_semana": labels_dia_semana,
        "dados_dia_semana": dados_dia_semana,
        "total_os": total_os,
        "taxa_conclusao": taxa_conclusao,
        "total_finalizadas": finalizadas,
        "total_andamento": total_andamento,
        "tempo_medio": tempo_medio,
        "tabela_resumo": tabela_resumo,
    }
