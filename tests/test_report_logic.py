import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from appmodules.logic.report_logic import gerar_dados_relatorio


class DummySheetsService:
    def is_available(self):
        return True, ""

    def get_all_os(self):
        return [
            {
                "Carimbo de data/hora": "15/06/2026 09:00:00",
                "Status da OS": "Finalizada",
                "Prioridade": "Alta",
                "Setor": "Manutenção",
                "Nome do solicitante": "João",
                "Descrição": "Troca de motor",
                "Horario de Andamento": "15/06/2026 09:10:00",
                "Horario de Término": "15/06/2026 10:00:00",
            }
        ]

    def get_all_producao(self, use_cache=True, force_refresh=False):
        return [
            {
                "Carimbo de data/hora": "16/06/2026 08:30:00",
                "Status": "Em andamento",
                "Nome do item": "Bobina A",
                "Código": "BOB-01",
                "Responsável": "Maria",
                "Observação": "Montagem da linha",
                "Origem": "produção",
            }
        ]


class ReportLogicTests(unittest.TestCase):
    def test_relatorio_mes_inclui_ops_junto_com_os(self):
        dados = gerar_dados_relatorio(DummySheetsService(), "2026-06")

        self.assertEqual(dados["total_os"], 1)
        self.assertEqual(dados["total_atividades_mes"], 2)
        self.assertEqual(len(dados["atividades_mes"]), 2)
        self.assertTrue(any("Bobina A" in item.get("descricao", "") for item in dados["atividades_mes"]))


if __name__ == "__main__":
    unittest.main()
