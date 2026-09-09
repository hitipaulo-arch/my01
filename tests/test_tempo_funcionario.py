import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("SECRET_KEY", "test-secret")

from appmodules.services.metrics_service import MetricsService


def reg(data, funcionario, pedido, horario):
    return {
        "Data": data,
        "Funcionário": funcionario,
        "Pedido/OS": pedido,
        "Horário": horario,
    }


class TempoFuncionarioTests(unittest.TestCase):
    def setUp(self):
        self.service = MetricsService()

    def test_agrupa_pares_entrada_saida_por_dia(self):
        registros = [
            reg("05/09/2026", "João", "101", "08:00"),
            reg("05/09/2026", "João", "101", "12:00"),
            reg("05/09/2026", "João", "101", "13:00"),
            reg("05/09/2026", "João", "101", "17:00"),
            # Outro funcionário, mesmo dia
            reg("05/09/2026", "Maria", "202", "09:00"),
            reg("05/09/2026", "Maria", "202", "11:30"),
        ]
        resultado = self.service.calcular_tempo_por_funcionario(registros)
        self.assertEqual(resultado["total_registros"], 2)
        por_nome = {d["funcionario"]: d for d in resultado["dados"]}
        self.assertAlmostEqual(por_nome["João"]["horas"], 8.0, places=2)
        self.assertEqual(por_nome["João"]["tempo"], "8.0h")
        self.assertAlmostEqual(por_nome["Maria"]["horas"], 2.5, places=2)

    def test_ordena_decrescente_e_preenche_charts(self):
        registros = [
            reg("05/09/2026", "A", "1", "08:00"),
            reg("05/09/2026", "A", "1", "12:00"),
            reg("06/09/2026", "B", "2", "08:00"),
            reg("06/09/2026", "B", "2", "09:00"),
        ]
        resultado = self.service.calcular_tempo_por_funcionario(registros)
        self.assertEqual(resultado["dados"][0]["funcionario"], "A")
        self.assertEqual(len(resultado["chart_data"]["bar_labels"]), 2)
        self.assertEqual(len(resultado["chart_data"]["bar_values"]), 2)
        # sem OS, urgência não preenchida -> agrupada como "Sem urgência"
        self.assertEqual(resultado["chart_data"]["urg_labels"], ["Sem urgência"])

    def test_enriquece_urgencia_pela_os(self):
        registros = [
            reg("05/09/2026", "João", "999", "08:00"),
            reg("05/09/2026", "João", "999", "10:00"),
        ]
        os_list = [
            {"Número do Pedido": "999", "Prioridade": "Urgente"},
            {"Número do Pedido": "888", "Prioridade": "Baixa"},
        ]
        resultado = self.service.calcular_tempo_por_funcionario(registros, os_list=os_list)
        self.assertEqual(resultado["dados"][0]["urgencia"], "Urgente")
        self.assertEqual(
            resultado["chart_data"]["urg_labels"], ["Urgente"]
        )

    def test_filtro_por_funcionario_e_pedido(self):
        registros = [
            reg("05/09/2026", "João", "101", "08:00"),
            reg("05/09/2026", "João", "101", "12:00"),
            reg("05/09/2026", "Maria", "202", "09:00"),
            reg("05/09/2026", "Maria", "202", "11:00"),
        ]
        r1 = self.service.calcular_tempo_por_funcionario(
            registros, filtros={"funcionario": "jo"}
        )
        self.assertEqual(r1["total_registros"], 1)
        r2 = self.service.calcular_tempo_por_funcionario(
            registros, filtros={"pedido_os": "202"}
        )
        self.assertEqual(r2["dados"][0]["funcionario"], "Maria")

    def test_vazio_retorna_estado_seguro(self):
        resultado = self.service.calcular_tempo_por_funcionario([])
        self.assertEqual(resultado["dados"], [])
        self.assertEqual(resultado["total_registros"], 0)
        self.assertEqual(resultado["chart_data"]["bar_labels"], [])
        self.assertEqual(resultado["aviso_periodo"], "")

    def test_periodo_invalido_retorna_aviso(self):
        registros = [
            reg("05/09/2026", "João", "101", "08:00"),
            reg("05/09/2026", "João", "101", "12:00"),
        ]
        resultado = self.service.calcular_tempo_por_funcionario(
            registros, filtros={"data_inicio": "2026-09-10", "data_fim": "2026-09-01"}
        )
        self.assertIn("Período inválido", resultado["aviso_periodo"])


if __name__ == "__main__":
    unittest.main()


class TempoFuncionarioRouteTests(unittest.TestCase):
    """Renderização da rota /tempo-por-funcionario sem servidor externo."""

    @classmethod
    def setUpClass(cls):
        import app as app_module

        cls.app_module = app_module
        cls.client = app_module.app.test_client()

    def setUp(self):
        with self.client.session_transaction() as sess:
            sess["usuario"] = "admin"
            sess["role"] = "admin"

        class _FakeUsuario:
            role = "admin"

        class _FakeUserService:
            def get_usuario(self, username):
                return _FakeUsuario() if username == "admin" else None

        self._orig_user = self.app_module.app.config.get("user_service")
        self._orig_sheets = self.app_module.app.config.get("sheets_service")
        self.app_module.app.config["user_service"] = _FakeUserService()

        class _FakeSheets:
            """Substituto de SheetsService indisponível (o before_request
            global exige um objeto não-None; is_available()=False)."""

            def is_available(self):
                return False, "indisponível (teste)"

            def get_time_records(self):
                return []

            def get_all_os(self, use_cache=True):
                return []

        # Sem Google Sheets de verdade: a rota deve renderizar estado vazio, sem 500
        self.app_module.app.config["sheets_service"] = _FakeSheets()

    def tearDown(self):
        self.app_module.app.config["user_service"] = self._orig_user
        self.app_module.app.config["sheets_service"] = self._orig_sheets

    def test_pagina_renderiza_sem_sheets(self):
        r = self.client.get("/tempo-por-funcionario")
        self.assertEqual(r.status_code, 200)
        self.assertIn("Horas por Funcionário", r.get_data(as_text=True))

    def test_parametros_invalidos_nao_quebram(self):
        r = self.client.get(
            "/tempo-por-funcionario?per_page=abc&page=-9&funcionario=jo&data_inicio=2026-09-01"
        )
        self.assertEqual(r.status_code, 200)

    def test_export_csv(self):
        r = self.client.get("/tempo-por-funcionario?export=csv")
        self.assertEqual(r.status_code, 200)
        self.assertIn("text/csv", r.headers.get("Content-Type", ""))
        self.assertIn("filename=tempo_por_funcionario.csv", r.headers.get("Content-Disposition", ""))
        self.assertIn("Funcionário", r.get_data(as_text=True))

    def test_export_xlsx_fallback_nao_quebra(self):
        r = self.client.get("/tempo-por-funcionario?export=xlsx")
        self.assertIn(r.status_code, (200,))
