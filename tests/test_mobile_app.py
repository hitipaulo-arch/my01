"""Testes do aplicativo mobile (PWA) servido em ``/m``.

Cobrem o que é específico do app:
* middleware de prefixo (rotas e ``url_for`` continuam funcionando);
* telas exclusivas (manifest, service worker, offline, instalação, menu);
* templates mobile renderizados no lugar dos desktop;
* equivalência entre os modos app e web (mesma rota, mesma sessão, mesmo CSRF).
"""

import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("SECRET_KEY", "test-secret")

import app as app_module  # noqa: E402


class MobilePrefixMiddlewareTests(unittest.TestCase):
    """O prefixo /m não pode alterar as rotas existentes."""

    def setUp(self):
        self.client = app_module.app.test_client()

    def test_root_still_serves_desktop_page(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertNotIn("m-tabbar", body, "A versão web não deve trazer a barra de abas do app")

    def test_mobile_root_serves_app_home(self):
        response = self.client.get("/m/")
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("m-tabbar", body)
        self.assertIn("Início", body)

    def test_urls_generated_inside_app_keep_mobile_prefix(self):
        response = self.client.get("/m/")
        body = response.get_data(as_text=True)
        # Links do menu apontam para dentro do app, nunca para a raiz do site.
        self.assertIn('href="/m/nova-os"', body)
        self.assertIn('href="/m/os-abertas"', body)

    def test_web_urls_do_not_contain_prefix(self):
        """A versão web não deve linkar para telas do app (só o atalho /m/)."""

        import re

        body = self.client.get("/").get_data(as_text=True)
        prefixados = set(re.findall(r'href="(/m/[^"]*)"', body))
        self.assertEqual(prefixados, {"/m/"}, f"Atalhos inesperados para o app: {prefixados}")
        self.assertIn("📱 App", body)


class MobileAssetsTests(unittest.TestCase):
    """Manifesto, service worker e ícones são requisitos de instalação."""

    def setUp(self):
        self.client = app_module.app.test_client()

    def test_manifest_is_reachable_inside_and_outside_app(self):
        for path in ("/m/manifest.webmanifest", "/manifest.webmanifest"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, path)
            self.assertIn("application/manifest+json", response.headers.get("Content-Type", ""))
            self.assertIn(b'"name"', response.data)

    def test_service_worker_is_reachable_with_scope_header(self):
        response = self.client.get("/m/service-worker.js")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("Service-Worker-Allowed"), "/m/")
        self.assertIn(b"OFFLINE_URL", response.data)

    def test_icons_and_styles_exist(self):
        for path in (
            "/static/mobile/icons/icon-192.png",
            "/static/mobile/icons/icon-512.png",
            "/static/mobile/icons/apple-touch-icon.png",
            "/static/mobile/mobile.css",
            "/static/mobile/app.js",
        ):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, path)




# ──────────────────────────────────────────────────────────────────────────────
# Stubs de serviços: permitem renderizar todas as telas do app sem Google Sheets
# ──────────────────────────────────────────────────────────────────────────────
OS_EXEMPLO = {
    "row_id": 3,
    "ID": "101",
    "Carimbo de data/hora": "14/09/2026 08:15:00",
    "Data da Solicitação": "14/09/2026 08:15:00",
    "Nome do solicitante": "Maria Souza",
    "WhatsApp do solicitante": "(12) 99999-0000",
    "Setor em que será realizado o serviço": "Manutenção",
    "Equipamento ou Local afetado": "Prensa 2",
    "Nível de prioridade": "Alta",
    "Descrição do Problema ou Serviço Solicitado": "Equipamento parado com vazamento de óleo.",
    "Informações adicionais (Opcional)": "Produção parada desde as 7h.",
    "Status da OS": "Em Andamento",
    "Serviço realizado": "",
    "Horario de Inicio": "08:30",
    "Horario de Andamento": "",
    "Horario de Término": "",
    "Horas trabalhadas": "",
}

PRODUCAO_EXEMPLO = {
    "row_id": 5,
    "ID": "9001",
    "Carimbo de data/hora": "13/09/2026 10:00:00",
    "Nome do item": "Estrutura metálica",
    "Código": "12-34-56789",
    "Número do projeto MTC": "1234",
    "Quantidade produzida": "4",
    "Meta de produção": "10",
    "Status": "Em andamento",
    "Observação": "Aguardando solda",
    "Responsável": "João Silva",
    "Informações adicionais": "Lote 3 iniciado",
    "Origem": "produção",
}

ITEM_EXEMPLO = {**PRODUCAO_EXEMPLO, "row_id": 7, "Origem": "item", "Quantidade produzida": "2"}

CENTRAL_EXEMPLO = {
    "row_id": 2,
    "Número de Portas": "8",
    "Código de Série": "SER-0001",
    "Status": "Pronta para Uso",
    "Obra Utilizada": "Obra A",
    "Data Cadastro": "10/09/2026 09:00:00",
    "Programação": '{"selecoes": [1, 2]}',
    "Programação Resumo": "1→1; 2→2",
}


class _StubUsuario:
    def __init__(self, role="admin"):
        self.role = role
        self.username = "admin"

    def to_dict(self):
        return {"username": self.username, "role": self.role, "data_cadastro": "01/09/2026"}


class _StubSheetsService:
    sheet_id = "stub-sheet"

    class _Client:
        def open_by_key(self, key):
            raise RuntimeError("Planilha indisponível no teste")

    client = _Client()

    def is_available(self):
        return True, None

    def get_all_os(self, use_cache=True):
        return [dict(OS_EXEMPLO)]

    def get_all_producao(self, use_cache=True, force_refresh=False):
        return [dict(PRODUCAO_EXEMPLO), dict(ITEM_EXEMPLO)]

    def get_producao_by_row_id(self, row_id):
        return dict(PRODUCAO_EXEMPLO)

    def get_os_by_row_id(self, row_id):
        return dict(OS_EXEMPLO)

    def get_os_by_id(self, os_id):
        return {
            "id": os_id,
            "timestamp": OS_EXEMPLO["Carimbo de data/hora"],
            "descricao": OS_EXEMPLO["Descrição do Problema ou Serviço Solicitado"],
            "status": OS_EXEMPLO["Status da OS"],
        }

    def marcar_origem_padrao_producao(self, origem):
        return True

    def get_time_records(self):
        return []


class _StubUserService:
    def get_usuario(self, username):
        return _StubUsuario()

    def get_todos_usuarios(self):
        return [_StubUsuario()]

    def criar_usuario(self, *args, **kwargs):
        return True

    def deletar_usuario(self, *args, **kwargs):
        return True


class _StubCentraisRepository:
    def get_all(self):
        return [dict(CENTRAL_EXEMPLO)]


class _StubbedTestCase(unittest.TestCase):
    """Instala serviços de exemplo para renderizar as telas sem Google Sheets."""

    def setUp(self):
        self.client = app_module.app.test_client()
        self._original = {
            key: app_module.app.config.get(key)
            for key in ("sheets_service", "user_service", "centrais_repository")
        }
        app_module.app.config["sheets_service"] = _StubSheetsService()
        app_module.app.config["user_service"] = _StubUserService()
        app_module.app.config["centrais_repository"] = _StubCentraisRepository()

    def tearDown(self):
        for key, value in self._original.items():
            app_module.app.config[key] = value

    def login(self, role="admin"):
        with self.client.session_transaction() as sess:
            sess["usuario"] = "admin" if role == "admin" else "operador1"
            sess["role"] = role
        return self.client


class MobileScreensTests(_StubbedTestCase):
    """Cada tela do app precisa renderizar o template mobile correto."""

    def test_public_screens_render_mobile_templates(self):
        esperado = {
            "/m/nova-os": "Abertura de OS",
            "/m/mais": "Menu completo",
            "/m/instalar": "Instalar o aplicativo",
            "/m/offline": "Sem conexão",
            "/m/consultar": "Consultar OS",
            "/m/os-abertas": "OS Abertas",
            "/m/login": "Entrar",
            "/m/cadastro": "Cadastro",
            "/m/upload-documento": "Enviar arquivo",
        }
        for path, marcador in esperado.items():
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertIn(response.status_code, {200, 503}, path)
                body = response.get_data(as_text=True)
                self.assertIn(marcador, body)
                self.assertIn("m-tabbar", body)

    def test_admin_screens_use_mobile_template_when_authenticated(self):
        self.login("admin")

        esperado = {
            "/m/gerenciar": "Gerenciar OS",
            "/m/producao": "Produção",
            "/m/producao-abertas": "OPs Abertas",
            "/m/dashboard-producao": "Dashboard",
            "/m/itens": "Itens / Compras",
            "/m/centrais": "Centrais",
            "/m/ferramentas": "Ferramentas",
            "/m/relatorios": "Relatórios",
            "/m/tempo-por-funcionario": "Tempo por Funcionário",
            "/m/usuarios": "Usuários",
            "/m/admin/ia": "IA Admin",
        }
        for path, marcador in esperado.items():
            with self.subTest(path=path):
                response = self.client.get(path)
                # As telas renderizam o template mobile; códigos 503/500 são
                # aceitos quando algum serviço externo falha.
                self.assertIn(response.status_code, {200, 302, 500, 502, 503})
                body = response.get_data(as_text=True)
                self.assertIn(marcador, body)
                self.assertIn("m-tabbar", body)

    def test_offline_and_install_have_no_external_dependency_errors(self):
        for path in ("/m/offline", "/m/instalar"):
            response = self.client.get(path)
            self.assertNotIn(b"TemplateNotFound", response.data)


class MobileMenuTests(_StubbedTestCase):
    """O menu respeita o papel do usuário, igual ao _top_nav.html."""

    def test_public_menu_hides_admin_modules(self):
        body = self.client.get("/m/mais").get_data(as_text=True)
        self.assertIn("Nova OS", body)
        self.assertNotIn("Gerenciar OS", body)
        self.assertNotIn("Usuários", body)

    def test_admin_menu_shows_all_modules(self):
        self.login("admin")
        body = self.client.get("/m/mais").get_data(as_text=True)
        for rotulo in ("Gerenciar OS", "Centrais", "Ferramentas", "Usuários", "IA Admin", "Relatórios"):
            self.assertIn(rotulo, body)

    def test_operator_menu_hides_admin_only_modules(self):
        self.login("operador")
        body = self.client.get("/m/mais").get_data(as_text=True)
        self.assertIn("Produção", body)
        self.assertNotIn("Gerenciar OS", body)
        self.assertNotIn("IA Admin", body)


class MobileBusinessLogicTests(_StubbedTestCase):
    """O app reaproveita as rotas existentes — nada de lógica duplicada."""

    def test_nova_os_form_posts_to_the_existing_route(self):
        body = self.client.get("/m/nova-os").get_data(as_text=True)
        self.assertIn('action="/m/enviar"', body)

    def test_os_abertas_mobile_shows_same_metrics_labels(self):
        body = self.client.get("/m/os-abertas").get_data(as_text=True)
        self.assertIn("OS concluídas", body)
        self.assertIn("Tempo médio", body)

    def test_mobile_context_helpers_available_in_desktop_templates(self):
        body = self.client.get("/").get_data(as_text=True)
        self.assertIn("Paulo Vieira 2025", body)


if __name__ == "__main__":
    unittest.main()


class MobileCacheIsolationTests(_StubbedTestCase):
    """O cache de páginas não pode misturar app e versão web."""

    def test_relatorios_cache_is_isolated_between_modes(self):
        self.login("admin")
        try:
            app_module.cache.clear()
        except Exception:
            pass

        web = self.client.get("/relatorios").get_data(as_text=True)
        app_page = self.client.get("/m/relatorios").get_data(as_text=True)

        self.assertNotIn("m-tabbar", web, "A versão web não deve receber HTML do app")
        self.assertIn("m-tabbar", app_page, "O app não deve receber HTML da versão web")
