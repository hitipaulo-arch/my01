"""Persistência das ferramentas e do histórico no Google Sheets."""

import logging
from datetime import datetime

from config import Config

logger = logging.getLogger(__name__)

FERRAMENTAS_HEADERS = ["Nome", "Patrocínio", "Data de Cadastro", "Última Manutenção", "Status", "Observação", "Responsável"]
HISTORICO_HEADERS = ["Ferramenta", "Evento", "Data/Hora", "Usuário", "Detalhes"]


def get_or_create_ferramentas_worksheet(sheets_service):
    """Obtém ou cria a worksheet de ferramentas, mantendo o schema legado."""
    try:
        spreadsheet = sheets_service.client.open_by_key(sheets_service.sheet_id)
        try:
            worksheet = spreadsheet.worksheet(Config.SHEETS.SHEET_FERRAMENTAS_TAB)
            headers = worksheet.row_values(1)
            if "Responsável" not in headers:
                worksheet.update("G1", [["Responsável"]])
        except Exception:
            worksheet = spreadsheet.add_worksheet(title=Config.SHEETS.SHEET_FERRAMENTAS_TAB, rows=500, cols=10)
            worksheet.append_row(FERRAMENTAS_HEADERS)
            logger.info("Aba '%s' criada", Config.SHEETS.SHEET_FERRAMENTAS_TAB)
        return worksheet
    except Exception as exc:
        logger.error("Erro ao obter/criar worksheet de ferramentas: %s", exc)
        raise


def get_ferramentas_list(sheets_service):
    """Obtém a lista de ferramentas."""
    try:
        dados = get_or_create_ferramentas_worksheet(sheets_service).get_all_records()
        return dados if dados else []
    except Exception as exc:
        logger.warning("Erro ao obter ferramentas: %s", exc)
        return []


def get_or_create_historico_worksheet(sheets_service):
    """Obtém ou cria a worksheet de histórico de ferramentas."""
    try:
        spreadsheet = sheets_service.client.open_by_key(sheets_service.sheet_id)
        try:
            worksheet = spreadsheet.worksheet(Config.SHEETS.SHEET_HISTORICO_FERRAMENTAS_TAB)
        except Exception:
            worksheet = spreadsheet.add_worksheet(title=Config.SHEETS.SHEET_HISTORICO_FERRAMENTAS_TAB, rows=1000, cols=5)
            worksheet.append_row(HISTORICO_HEADERS)
            logger.info("Aba '%s' criada", Config.SHEETS.SHEET_HISTORICO_FERRAMENTAS_TAB)
        return worksheet
    except Exception as exc:
        logger.error("Erro ao obter/criar worksheet de histórico: %s", exc)
        raise


def add_historico_entry(sheets_service, nome_ferramenta, evento, usuario, detalhes=""):
    """Adiciona uma entrada no histórico de ferramentas."""
    try:
        worksheet = get_or_create_historico_worksheet(sheets_service)
        data_hora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        worksheet.append_row([nome_ferramenta, evento, data_hora, usuario, detalhes])
    except Exception as exc:
        logger.warning("Erro ao adicionar histórico: %s", exc)


__all__ = ["add_historico_entry", "get_ferramentas_list", "get_or_create_ferramentas_worksheet", "get_or_create_historico_worksheet"]