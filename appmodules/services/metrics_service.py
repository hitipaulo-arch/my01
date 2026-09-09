"""Metrics Service - Centralized statistics calculations for production and OS routes."""

import datetime
from typing import Any


class MetricsService:
    """Service for calculating metrics and statistics from production/OS data."""

    # Status constants for production items
    PRODUCAO_STATUS_EXCLUIDOS = {
        "concluído",
        "concluido",
        "bloqueado",
        "bloqueada",
        "cancelado",
        "cancelada",
    }
    PRODUCAO_STATUS_BLOQUEADOS = {"bloqueado", "bloqueada"}
    PRODUCAO_STATUS_CONCLUIDOS = {"concluído", "concluido"}

    # Status constants for OS items
    OS_STATUS_ABERTOS = {"aberto", "em andamento"}
    OS_STATUS_FINALIZADAS = {"finalizada", "concluido", "concluído"}

    @staticmethod
    def _normalize_status(value: Any) -> str:
        """Normalize status value for comparison."""
        return str(value or "").strip().lower()

    @staticmethod
    def _parse_datetime_maybe_time(valor: Any, base_dt: datetime.datetime | None) -> datetime.datetime | None:
        """
        Parse datetime from various formats.
        Accepts: HH:MM, HH:MM:SS (combined with base_dt date), or full datetime DD/MM/YYYY HH:MM[:SS].
        """
        texto = str(valor or "").strip()
        if not texto:
            return None

        # Accept only time (HH:MM or HH:MM:SS) combined with base date
        if ":" in texto and "/" not in texto:
            if not isinstance(base_dt, datetime.datetime):
                return None
            for fmt in ("%H:%M:%S", "%H:%M"):
                try:
                    t = datetime.datetime.strptime(texto, fmt).time()
                    return datetime.datetime.combine(base_dt.date(), t)
                except ValueError:
                    continue

        for fmt in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M"):
            try:
                return datetime.datetime.strptime(texto, fmt)
            except ValueError:
                continue

        return None

    def calculate_production_metrics(self, itens: list[dict]) -> dict:
        """
        Calculate metrics for production items (producao_abertas route).

        Args:
            itens: List of production item dictionaries from sheets_service

        Returns:
            Dictionary with:
            - total_ops_abertas: Count of items not in excluded statuses
            - itens_bloqueados: Count of items with blocked status
            - taxa_conclusao: Completion rate percentage (rounded to 1 decimal)
        """
        if not itens:
            return {
                "total_ops_abertas": 0,
                "itens_bloqueados": 0,
                "taxa_conclusao": 0,
            }

        total_itens = len(itens)

        # Count blocked items
        itens_bloqueados = sum(
            1
            for item in itens
            if self._normalize_status(item.get("Status")) in self.PRODUCAO_STATUS_BLOQUEADOS
        )

        # Count completed items
        itens_concluidos = sum(
            1
            for item in itens
            if self._normalize_status(item.get("Status")) in self.PRODUCAO_STATUS_CONCLUIDOS
        )

        # Calculate completion rate
        taxa_conclusao = round((itens_concluidos / total_itens * 100), 1) if total_itens > 0 else 0

        # Count open items (not in excluded statuses)
        itens_abertos = [
            item
            for item in itens
            if self._normalize_status(item.get("Status")) not in self.PRODUCAO_STATUS_EXCLUIDOS
        ]
        total_ops_abertas = len(itens_abertos)

        return {
            "total_ops_abertas": total_ops_abertas,
            "itens_bloqueados": itens_bloqueados,
            "taxa_conclusao": taxa_conclusao,
        }

    def calculate_os_metrics(self, os_list: list[dict]) -> dict:
        """
        Calculate metrics for OS items (os_abertas route).

        Args:
            os_list: List of OS item dictionaries from sheets_service

        Returns:
            Dictionary with:
            - percentual_concluidas: Completion percentage formatted as "X,Y%"
            - tempo_medio_conclusao: Average duration formatted as "X min" or "X,Y h"
        """
        empty_metrics = {
            "percentual_concluidas": "0,0%",
            "tempo_medio_conclusao": "N/A",
        }

        if not os_list:
            return empty_metrics

        total_os = len(os_list)

        # Filter finalized OS
        finalizadas = [
            item
            for item in os_list
            if self._normalize_status(item.get("Status da OS")) in self.OS_STATUS_FINALIZADAS
        ]

        # Calculate completion percentage
        percentual_concluidas = "0,0%"
        if total_os > 0:
            percentual = (len(finalizadas) / total_os) * 100
            percentual_concluidas = f"{percentual:.1f}%".replace(".", ",")

        # Calculate average completion time
        duracoes_horas = []
        for item in finalizadas:
            ts_base = self._parse_datetime_maybe_time(item.get("Carimbo de data/hora", ""), None)
            inicio_txt = item.get("Horario de Andamento", "") or item.get("Horario de Inicio", "")
            termino_txt = item.get("Horario de Término", "")
            dt_inicio = self._parse_datetime_maybe_time(inicio_txt, ts_base)
            dt_fim = self._parse_datetime_maybe_time(termino_txt, ts_base)
            if not dt_inicio or not dt_fim:
                continue

            delta_h = (dt_fim - dt_inicio).total_seconds() / 3600
            if delta_h > 0:
                duracoes_horas.append(delta_h)

        tempo_medio_conclusao = "N/A"
        if duracoes_horas:
            media_h = sum(duracoes_horas) / len(duracoes_horas)
            if media_h < 1:
                tempo_medio_conclusao = f"{int(media_h * 60)} min"
            else:
                tempo_medio_conclusao = f"{media_h:.1f} h".replace(".", ",")

        return {
            "percentual_concluidas": percentual_concluidas,
            "tempo_medio_conclusao": tempo_medio_conclusao,
        }

    def filter_open_production_items(self, itens: list[dict]) -> list[dict]:
        """Filter production items to only open ones (not in excluded statuses)."""
        return [
            item
            for item in itens
            if self._normalize_status(item.get("Status")) not in self.PRODUCAO_STATUS_EXCLUIDOS
        ]

    def filter_open_os_items(self, os_list: list[dict]) -> list[dict]:
        """Filter OS items to only open ones (aberto, em andamento)."""
        return [
            item
            for item in os_list
            if self._normalize_status(item.get("Status da OS")) in self.OS_STATUS_ABERTOS
        ]

    def sort_production_items(self, itens: list[dict]) -> list[dict]:
        """Sort production items by row_id descending."""
        return sorted(itens, key=lambda item: item.get("row_id", 0), reverse=True)

    def sort_os_items(self, os_list: list[dict]) -> list[dict]:
        """Sort OS items by timestamp descending."""

        def sort_key(item):
            try:
                return datetime.datetime.strptime(
                    str(item.get("Carimbo de data/hora", "")).strip(),
                    "%d/%m/%Y %H:%M:%S",
                )
            except ValueError:
                return datetime.datetime.min

        return sorted(os_list, key=sort_key, reverse=True)
    # ------------------------------------------------------------------
    # Tempo por funcionário (controle de horário)
    # ------------------------------------------------------------------

    @staticmethod
    def _first_col(record: dict, *substrings: str, default: str = "") -> str:
        """Retorna o primeiro valor cuja chave contenha um dos substrings
        (comparação sem acentos/caixa). Útil para planilhas com cabeçalhos
        que variam entre 'Pedido/OS', 'Nº do Pedido', 'Número Pedido', etc."""
        key_map = {}
        for key, value in (record or {}).items():
            k = str(key or "").strip().lower()
            k = (
                k.replace("á", "a").replace("ã", "a").replace("à", "a")
                .replace("é", "e").replace("ê", "e")
                .replace("í", "i").replace("ó", "o").replace("ô", "o")
                .replace("ú", "u").replace("ç", "c").replace("º", "").replace("ª", "")
            )
            key_map.setdefault(k, key)
        for sub in substrings:
            s = (
                str(sub).strip().lower().replace("á", "a").replace("ã", "a")
                .replace("à", "a").replace("é", "e").replace("ê", "e")
                .replace("í", "i").replace("ó", "o").replace("ô", "o")
                .replace("ú", "u").replace("ç", "c").replace("º", "").replace("ª", "")
            )
            for k in key_map:
                if s in k:
                    val = record.get(key_map[k], "")
                    if str(val or "").strip():
                        return str(val).strip()
        return default

    @staticmethod
    def _parse_data_hora(data_txt: str, hora_txt: str) -> datetime.datetime | None:
        """Combina data e hora em datetime, tolerando formatos comuns."""
        data = str(data_txt or "").strip()
        hora = str(hora_txt or "").strip()
        if not data:
            return None
        base = None
        for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%Y/%m/%d", "%d/%m/%y"):
            try:
                base = datetime.datetime.strptime(data, fmt)
                break
            except ValueError:
                continue
        if base is None:
            # Pode vir data+hora juntas
            for fmt in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%Y-%m-%d %H:%M:%S"):
                try:
                    return datetime.datetime.strptime(data, fmt)
                except ValueError:
                    continue
            return None
        if hora:
            for fmt in ("%H:%M:%S", "%H:%M"):
                try:
                    t = datetime.datetime.strptime(hora, fmt).time()
                    return datetime.datetime.combine(base.date(), t)
                except ValueError:
                    continue
        return base

    def calcular_tempo_por_funcionario(
        self,
        registros: list[dict],
        os_list: list[dict] | None = None,
        filtros: dict | None = None,
    ) -> dict:
        """
        Calcula horas trabalhadas por funcionário/OS a partir dos registros de
        controle de horário (pares entrada/saída por dia).

        Args:
            registros: listas de dicts vindas de sheets_service.get_time_records()
            os_list: opcional, lista de OS (para enriquecer com urgência)
            filtros: opcional dict com 'funcionario', 'pedido_os',
                'data_inicio' (YYYY-MM-DD ou DD/MM/YYYY), 'data_fim'

        Returns:
            dict com 'dados', 'total_registros', 'chart_data' e 'aviso_periodo'.
        """
        filtros = filtros or {}
        dados = []
        if not registros:
            return self._empty_tempo_resultado()

        # (funcionario|pedido|data) -> eventos ordenados
        eventos_por_dia: dict[tuple, list[datetime.datetime]] = {}
        metadados: dict[tuple, dict] = {}

        def _chave(f, p, d):
            return (str(f or "").strip().lower(), str(p or "").strip().lower(), d)

        for reg in registros:
            if not isinstance(reg, dict):
                continue
            funcionario = MetricsService._first_col(
                reg, "funcionario", "nome", default=""
            ) or str(reg.get("funcionario", "") or "")
            pedido_os = MetricsService._first_col(
                reg, "pedido", "os", "numero", "nº", default=""
            )
            data_txt = MetricsService._first_col(reg, "data", "dia", default="")
            hora_txt = MetricsService._first_col(
                reg, "horario", "hora", "horário", default=""
            )
            dt = self._parse_data_hora(data_txt, hora_txt)
            if dt is None:
                continue
            chave = _chave(funcionario, pedido_os, dt.date().isoformat())
            eventos_por_dia.setdefault(chave, []).append(dt)
            metadados.setdefault(chave, {"funcionario": funcionario, "pedido_os": pedido_os})

        # Filtros de período (em cima das datas dos eventos)
        try:
            di = MetricsService._parse_data_hora(
                (filtros.get("data_inicio") or "").replace("-", "/"), ""
            )
            df = MetricsService._parse_data_hora(
                (filtros.get("data_fim") or "").replace("-", "/"), ""
            )
        except Exception:
            di = df = None

        urgencias_por_pedido = {}
        if os_list:
            for os_row in os_list:
                if not isinstance(os_row, dict):
                    continue
                numero = MetricsService._first_col(
                    os_row, "numero", "pedido", "nº", "os", default=""
                )
                if numero:
                    urgencias_por_pedido.setdefault(
                        str(numero).strip().lower(),
                        MetricsService._first_col(os_row, "prioridade", "urgencia", default=""),
                    )

        # Soma de horas por (funcionario, pedido) agregando dias
        totais: dict[tuple, float] = {}
        info: dict[tuple, dict] = {}
        avisos = []

        for chave, eventos in eventos_por_dia.items():
            meta = metadados[chave]
            eventos.sort()
            total_dia = 0.0
            inicio = None
            for ev in eventos:
                if inicio is None:
                    inicio = ev
                else:
                    delta = (ev - inicio).total_seconds() / 3600
                    if delta >= 0:
                        total_dia += delta
                    inicio = None
            if total_dia <= 0:
                continue

            if di and df and (di.date() > df.date()):
                avisos.append("Período inválido: data inicial maior que a final.")
                return self._empty_tempo_resultado(aviso=" ".join(avisos))

            data_ev = datetime.datetime.strptime(chave[2], "%Y-%m-%d").date()
            if di and data_ev < di.date():
                continue
            if df and data_ev > df.date():
                continue

            f_ped = meta["pedido_os"]
            f_nome = meta["funcionario"]
            f_filtro = str(filtros.get("funcionario") or "").strip().lower()
            if f_filtro and f_filtro not in str(f_nome or "").lower():
                continue
            p_filtro = str(filtros.get("pedido_os") or "").strip().lower()
            if p_filtro and p_filtro not in str(f_ped or "").lower():
                continue

            chave_agg = (str(f_nome or "").strip().lower(), str(f_ped or "").strip().lower())
            totais[chave_agg] = totais.get(chave_agg, 0.0) + total_dia
            info.setdefault(chave_agg, {"funcionario": f_nome, "pedido_os": f_ped})

        for chave_agg, horas in totais.items():
            meta = info[chave_agg]
            pedido = meta["pedido_os"]
            urgencia = urgencias_por_pedido.get(str(pedido or "").strip().lower(), "")
            dados.append(
                {
                    "funcionario": meta["funcionario"] or "—",
                    "pedido_os": pedido or "—",
                    "tempo": MetricsService._formatar_duracao(horas),
                    "horas": round(horas, 2),
                    "urgencia": urgencia,
                }
            )

        dados.sort(key=lambda d: d["horas"], reverse=True)
        chart_data = self._build_tempo_charts(dados)
        return {
            "dados": dados,
            "total_registros": len(dados),
            "chart_data": chart_data,
            "aviso_periodo": " ".join(avisos),
        }

    @staticmethod
    def _formatar_duracao(horas: float) -> str:
        if horas < 1:
            return f"{int(round(horas * 60))}min"
        return f"{horas:.1f}h"

    def _build_tempo_charts(self, dados: list[dict]) -> dict:
        """Monta dados p/ gráficos: barras (top 15) e rosca de urgência."""
        top = dados[:15]
        bar_labels = [
            f"{d['funcionario']} (#{d['pedido_os']})" if d["pedido_os"] != "—" else d["funcionario"]
            for d in top
        ]
        bar_values = [d["horas"] for d in top]

        urg_count: dict[str, int] = {}
        for d in dados:
            u = str(d.get("urgencia") or "Sem urgência").strip() or "Sem urgência"
            urg_count[u] = urg_count.get(u, 0) + 1
        urg_ordenada = sorted(urg_count.items(), key=lambda kv: kv[1], reverse=True)
        return {
            "bar_labels": bar_labels,
            "bar_values": bar_values,
            "urg_labels": [k for k, _ in urg_ordenada],
            "urg_values": [v for _, v in urg_ordenada],
        }

    def _empty_tempo_resultado(self, aviso: str = "") -> dict:
        return {
            "dados": [],
            "total_registros": 0,
            "chart_data": {"bar_labels": [], "bar_values": [], "urg_labels": [], "urg_values": []},
            "aviso_periodo": aviso,
        }
