"""
Módulo de Lógica de Negócio para Geração de Relatórios.

Este módulo encapsula a complexidade de processar dados brutos das planilhas
e transformá-los em informações prontas para serem exibidas nos relatórios.
"""

import logging
import datetime as dt
import pandas as pd

logger = logging.getLogger(__name__)


def _first_col(df, *candidatos):
    """Encontra a primeira coluna existente no DataFrame a partir de uma lista de candidatos."""
    for col in candidatos:
        if col in df.columns:
            return col
    return None


def _parse_datetime_series_maybe_time(serie_valor, serie_base):
    """
    Converte uma série de strings para datetime, lidando com casos onde apenas
    o horário é fornecido, usando uma série de datas base como referência.
    """
    texto = serie_valor.fillna("").astype(str).str.strip()
    base = pd.to_datetime(serie_base, errors="coerce")
    resultado = pd.Series(pd.NaT, index=serie_valor.index, dtype="datetime64[ns]")

    mask_vazio = texto.eq("")
    mask_data_completa = (~mask_vazio) & texto.str.contains("/", regex=False)
    mask_somente_hora = (
        (~mask_vazio) & (~mask_data_completa) & texto.str.contains(":", regex=False)
    )

    if mask_data_completa.any():
        resultado.loc[mask_data_completa] = pd.to_datetime(
            texto.loc[mask_data_completa],
            format="%d/%m/%Y %H:%M:%S",
            errors="coerce",
        )

    if mask_somente_hora.any():
        base_text = base.dt.strftime("%Y-%m-%d")

        candidatos_hms = (
            base_text.loc[mask_somente_hora] + " " + texto.loc[mask_somente_hora]
        )
        parsed_hms = pd.to_datetime(
            candidatos_hms, format="%Y-%m-%d %H:%M:%S", errors="coerce"
        )

        faltantes = parsed_hms.isna()
        if faltantes.any():
            candidatos_hm = (
                base_text.loc[mask_somente_hora].loc[faltantes]
                + " "
                + texto.loc[mask_somente_hora].loc[faltantes]
            )
            parsed_hms.loc[faltantes] = pd.to_datetime(
                candidatos_hm, format="%Y-%m-%d %H:%M", errors="coerce"
            )

        resultado.loc[mask_somente_hora] = parsed_hms

    return resultado


def gerar_dados_relatorio(sheets_service):
    """
    Busca e processa os dados de OS para gerar as métricas e gráficos do relatório.

    Args:
        sheets_service: Uma instância do SheetsService.

    Returns:
        Um dicionário contendo todos os dados para o template de relatórios.
        Em caso de erro, o dicionário conterá uma chave 'mensagem_erro'.
    """
    _empty = dict(
        labels_prioridade=[],
        dados_prioridade=[],
        labels_setor=[],
        dados_setor=[],
        labels_tempo_resolucao=[],
        dados_tempo_resolucao=[],
        labels_dia_semana=[],
        dados_dia_semana=[],
        total_os=0,
        taxa_conclusao="0%",
        total_finalizadas=0,
        total_andamento=0,
        tempo_medio="N/A",
        tabela_resumo=[],
    )

    if not sheets_service:
        return {**_empty, "mensagem_erro": "Serviço de planilhas indisponível"}

    disponivel, erro_msg = sheets_service.is_available()
    if not disponivel:
        return {**_empty, "mensagem_erro": erro_msg}

    os_list = sheets_service.get_all_os()
    if not os_list:
        return _empty

    df = pd.DataFrame(os_list).fillna("")

    col_timestamp = _first_col(df, "Carimbo de data/hora")
    col_status = _first_col(df, "Status da OS")
    col_prioridade = _first_col(df, "Prioridade", "Nível de prioridade")
    col_setor = _first_col(df, "Setor", "Setor em que será realizado o serviço")
    col_solicitante = _first_col(df, "Nome do solicitante")
    col_descricao = _first_col(
        df, "Descrição", "Descrição do Problema ou Serviço Solicitado"
    )
    col_andamento = _first_col(df, "Horario de Andamento")
    col_termino = _first_col(df, "Horario de Término")

    if col_timestamp:
        df["_ts"] = pd.to_datetime(
            df[col_timestamp], format="%d/%m/%Y %H:%M:%S", errors="coerce"
        )
    else:
        df["_ts"] = pd.NaT

    if col_status:
        status_lower = df[col_status].astype(str).str.strip().str.lower()
        df = df[~status_lower.isin(["cancelada", "cancelado"])]

    pri_count = df[col_prioridade].value_counts() if col_prioridade else pd.Series()
    setor_count = (
        df[col_setor].value_counts().head(10) if col_setor else pd.Series()
    )

    total_os = len(df)
    status_lower = (
        df[col_status].astype(str).str.strip().str.lower()
        if col_status
        else pd.Series(dtype=str)
    )
    finalizadas = int(status_lower.isin(["finalizada", "concluido", "concluído"]).sum())
    total_andamento = int(status_lower.isin(["em andamento"]).sum())
    taxa_conclusao = f"{(finalizadas / total_os * 100):.1f}%" if total_os > 0 else "0%"

    tempo_medio = "N/A"
    if col_andamento and col_termino:
        df_fin = df[status_lower.isin(["finalizada", "concluido", "concluído"])].copy()
        df_fin["_inicio"] = _parse_datetime_series_maybe_time(
            df_fin[col_andamento], df_fin["_ts"]
        )
        df_fin["_termino"] = _parse_datetime_series_maybe_time(
            df_fin[col_termino], df_fin["_ts"]
        )
        delta = (df_fin["_termino"] - df_fin["_inicio"]).dropna()
        delta = delta[delta.dt.total_seconds() > 0]
        if not delta.empty:
            media_h = delta.mean().total_seconds() / 3600
            tempo_medio = f"{int(media_h * 60)}min" if media_h < 1 else f"{media_h:.1f}h"

    ts_valid = df["_ts"].dropna()
    dia_counts = ts_valid.dt.dayofweek.value_counts().sort_index() if not ts_valid.empty else pd.Series()
    dias_map = {0: "Seg", 1: "Ter", 2: "Qua", 3: "Qui", 4: "Sex", 5: "Sáb", 6: "Dom"}

    df_res = df.copy()
    if col_andamento and col_termino:
        df_res["_inicio"] = _parse_datetime_series_maybe_time(df_res[col_andamento], df_res["_ts"])
        df_res["_termino"] = _parse_datetime_series_maybe_time(df_res[col_termino], df_res["_ts"])
        df_res["_delta_h"] = (df_res["_termino"] - df_res["_inicio"]).dt.total_seconds() / 3600
        df_res = df_res.dropna(subset=["_ts", "_delta_h"])
        df_res = df_res[df_res["_delta_h"] > 0]

    media_mes = df_res.groupby(df_res["_ts"].dt.to_period("M").astype(str))["_delta_h"].mean().sort_index() if not df_res.empty else pd.Series()

    df_sorted = df.dropna(subset=["_ts"]).sort_values("_ts", ascending=False).head(50)
    tabela_resumo = [
        {
            "data": row.get(col_timestamp, ""),
            "solicitante": row.get(col_solicitante, ""),
            "setor": row.get(col_setor, ""),
            "status": row.get(col_status, ""),
            "descricao": row.get(col_descricao, ""),
        }
        for _, row in df_sorted.iterrows()
    ]

    return {
        "labels_prioridade": pri_count.index.tolist(),
        "dados_prioridade": pri_count.values.tolist(),
        "labels_setor": setor_count.index.tolist(),
        "dados_setor": setor_count.values.tolist(),
        "labels_tempo_resolucao": media_mes.index.tolist(),
        "dados_tempo_resolucao": [round(v, 1) for v in media_mes.values],
        "labels_dia_semana": [dias_map.get(d, str(d)) for d in dia_counts.index],
        "dados_dia_semana": dia_counts.values.tolist(),
        "total_os": total_os,
        "taxa_conclusao": taxa_conclusao,
        "total_finalizadas": finalizadas,
        "total_andamento": total_andamento,
        "tempo_medio": tempo_medio,
        "tabela_resumo": tabela_resumo,
    }