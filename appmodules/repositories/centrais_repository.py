import logging
import json
from typing import List, Dict, Any

from appmodules.services import SheetsService
from config import Config

logger = logging.getLogger(__name__)


class CentraisRepository:
    """
    Repository para gerenciar a lógica de acesso e manipulação
    dos dados de 'Centrais' no Google Sheets.
    """

    def __init__(self, sheets_service: SheetsService):
        self.sheets_service = sheets_service
        self.tab_name = Config.SHEETS.SHEET_CENTRAIS_TAB

    @staticmethod
    def _normalizar_texto_basico(texto: str) -> str:
        """Normaliza texto para comparação simples de cabeçalhos."""
        return (
            str(texto or "")
            .strip()
            .lower()
            .replace("á", "a").replace("à", "a").replace("â", "a").replace("ã", "a")
            .replace("é", "e").replace("ê", "e")
            .replace("í", "i")
            .replace("ó", "o").replace("ô", "o").replace("õ", "o")
            .replace("ú", "u")
            .replace("ç", "c")
        )

    @staticmethod
    def _programacao_json_to_summary(programacao_raw: str, total_portas: int) -> str:
        """Converte JSON de programação em resumo legível: '1→2,3; 2→1'."""
        try:
            if not programacao_raw:
                return ""
            parsed = json.loads(programacao_raw)
        except Exception:
            return ""

        linhas = [[] for _ in range(max(0, int(total_portas or 0)))]

        def process_row_item(row_index, item):
            if row_index < 0 or row_index >= len(linhas):
                return
            if isinstance(item, list):
                numeric_elements = all(isinstance(x, (int, float)) or (isinstance(x, str) and str(x).strip().lstrip("-").isdigit()) for x in item)
                if numeric_elements:
                    for x in item:
                        try:
                            n = int(float(x)) - 1
                            if 0 <= n < len(linhas) and n not in linhas[row_index]:
                                linhas[row_index].append(n)
                        except Exception:
                            continue
                    return
                for idx, val in enumerate(item):
                    if str(val or "").strip().upper() == "X":
                        if idx not in linhas[row_index]:
                            linhas[row_index].append(idx)
                return
            if isinstance(item, (int, float)) or (isinstance(item, str) and str(item).strip().lstrip("-").isdigit()):
                try:
                    n = int(float(item)) - 1
                    if 0 <= n < len(linhas) and n not in linhas[row_index]:
                        linhas[row_index].append(n)
                except Exception:
                    pass

        if isinstance(parsed, dict) and "selecoes" in parsed and isinstance(parsed["selecoes"], list):
            for i, itm in enumerate(parsed["selecoes"]):
                process_row_item(i, itm)
        elif isinstance(parsed, list):
            for i, itm in enumerate(parsed):
                process_row_item(i, itm)

        parts = []
        for i, cols in enumerate(linhas):
            if not cols:
                continue
            cols_sorted = sorted(set(cols))
            cols_text = ",".join(str(c + 1) for c in cols_sorted)
            parts.append(f"{i + 1}→{cols_text}")

        return "; ".join(parts)

    def _get_or_create_worksheet(self):
        """Obtém ou cria a worksheet de centrais."""
        try:
            spreadsheet = self.sheets_service.client.open_by_key(self.sheets_service.sheet_id)
            headers_padrao = [
                "Número de Portas", "Código de Série", "Status", "Obra Utilizada",
                "Data Cadastro", "Programação", "Programação Resumo",
            ]
            try:
                worksheet = spreadsheet.worksheet(self.tab_name)
            except Exception:
                worksheet = spreadsheet.add_worksheet(title=self.tab_name, rows=100, cols=10)
                worksheet.append_row(headers_padrao)
                logger.info(f"Aba '{self.tab_name}' criada")
            else:
                current_headers = [str(valor or "").strip() for valor in worksheet.row_values(1)]
                need_prog = not any(self._normalizar_texto_basico(h) == "programacao" for h in current_headers)
                need_prog_resumo = not any(self._normalizar_texto_basico(h) == "programacao resumo" for h in current_headers)
                need_data_cadastro = not any(self._normalizar_texto_basico(h) in ("data cadastro", "data", "cadastro") for h in current_headers)
                if need_prog or need_prog_resumo or need_data_cadastro:
                    novos = list(current_headers)
                    if need_prog and "Programação" not in novos:
                        novos.append("Programação")
                    if need_prog_resumo and "Programação Resumo" not in novos:
                        novos.append("Programação Resumo")
                    if need_data_cadastro and "Data Cadastro" not in novos:
                        novos.append("Data Cadastro")
                    worksheet.update("A1", [novos])
            return worksheet
        except Exception as e:
            logger.error(f"Erro ao obter/criar worksheet de centrais: {e}")
            raise

    def get_all(self) -> List[Dict[str, Any]]:
        """Obtém lista de centrais."""
        try:
            worksheet = self._get_or_create_worksheet()
            data = worksheet.get_all_values()
            if len(data) < 2:
                return []

            headers = [str(h or "").strip() for h in data[0]]
            header_map = {}
            for i, h in enumerate(headers):
                if not h: continue
                key = self._normalizar_texto_basico(h)
                if key and key not in header_map:
                    header_map[key] = i

            def _get_val(row, *aliases):
                for alias in aliases:
                    idx = header_map.get(self._normalizar_texto_basico(alias))
                    if idx is not None and idx < len(row):
                        return str(row[idx] or "").strip()
                return ""

            centrais_normalizadas = []
            for i, linha in enumerate(data[1:]):
                if not any(str(c or "").strip() for c in linha):
                    continue
                central = {
                    "row_id": i,
                    "Número de Portas": _get_val(linha, "Número de Portas", "Numero de Portas", "Portas"),
                    "Código de Série": _get_val(linha, "Código de Série", "Codigo de Serie", "Codigo", "Série"),
                    "Status": _get_val(linha, "Status"),
                    "Obra Utilizada": _get_val(linha, "Obra Utilizada", "Obra"),
                    "Data Cadastro": _get_val(linha, "Data Cadastro", "Data de Cadastro", "Cadastro", "Data"),
                    "Programação": _get_val(linha, "Programação", "Programacao"),
                    "Programação Resumo": _get_val(linha, "Programação Resumo", "Programacao Resumo"),
                }
                centrais_normalizadas.append(central)
            return centrais_normalizadas
        except Exception as e:
            logger.warning(f"Erro ao obter centrais: {e}")
            return []

    def add(self, data: Dict[str, Any]):
        """Adiciona uma nova central."""
        worksheet = self._get_or_create_worksheet()
        headers = [h.strip() for h in worksheet.row_values(1)]
        row_values = [data.get(h, "") for h in headers]
        worksheet.append_row(row_values)

    def update(self, row_id: int, status: str, obra: str):
        """Atualiza status e obra de uma central."""
        worksheet = self._get_or_create_worksheet()
        row_num = row_id + 2

        headers = [str(h or "").strip() for h in worksheet.row_values(1)]
        header_map = {self._normalizar_texto_basico(h): i for i, h in enumerate(headers) if h}

        status_idx = header_map.get("status")
        obra_idx = header_map.get("obra utilizada") or header_map.get("obra")

        if status_idx is not None:
            worksheet.update_cell(row_num, status_idx + 1, status)
        if obra_idx is not None:
            worksheet.update_cell(row_num, obra_idx + 1, obra)

        if status_idx is None and obra_idx is None:
            worksheet.update(f"C{row_num}:D{row_num}", [[status, obra]])

    def update_programacao(self, row_id: int, programacao_json: str) -> str:
        """Atualiza a programação de uma central e retorna o resumo."""
        worksheet = self._get_or_create_worksheet()
        row_num = row_id + 2

        try:
            parsed = json.loads(programacao_json)
            programacao_compact = json.dumps(parsed, ensure_ascii=False, separators=(",", ":"))
        except Exception:
            programacao_compact = str(programacao_json)

        headers = [str(h or "").strip() for h in worksheet.row_values(1)]
        header_map = {self._normalizar_texto_basico(h): i for i, h in enumerate(headers) if h}

        prog_idx = header_map.get("programacao")
        resumo_idx = header_map.get("programacao resumo")
        portas_idx = header_map.get("numero de portas")

        if prog_idx is None or resumo_idx is None:
            raise ValueError("Colunas 'Programação' ou 'Programação Resumo' não encontradas.")

        row_values = worksheet.row_values(row_num)
        num_portas = 0
        if portas_idx is not None and portas_idx < len(row_values):
            try:
                num_portas = int(float(str(row_values[portas_idx]).strip().replace(",", ".")))
            except Exception:
                num_portas = 0

        resumo = self._programacao_json_to_summary(programacao_compact, num_portas)

        worksheet.update_cell(row_num, prog_idx + 1, programacao_compact)
        worksheet.update_cell(row_num, resumo_idx + 1, resumo)
        return resumo

    def delete(self, row_id: int):
        """Deleta uma central."""
        worksheet = self._get_or_create_worksheet()
        row_num = row_id + 2
        worksheet.delete_rows(row_num)
