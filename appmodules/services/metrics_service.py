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