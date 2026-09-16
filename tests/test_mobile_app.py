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
        try:
            row_id = int(row_id)
        except (TypeError, ValueError):
            return None
        if row_id in {PRODUCAO_EXEMPLO["row_id"], ITEM_EXEMPLO["row_id"]}:
            return dict(PRODUCAO_EXEMPLO)
        return None

    def update_producao(self, row_id, row_data):
        """Registra a escrita para que os testes confiram o que foi enviado."""

        self.ultima_atualizacao = {"row_id": row_id, "row_data": list(row_data)}
        return True

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
        # Devolve o papel da sessão para simular admin/operador/visualizador.
        from flask import session

        return _StubUsuario(session.get("role") or "admin")

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


class MobileItemEditTests(_StubbedTestCase):
    """A tela de edição de item também tem versão mobile (antes caía no desktop)."""

    def test_editar_item_renders_mobile_template(self):
        self.login("admin")
        response = self.client.get("/m/itens/5/editar")
        self.assertIn(response.status_code, {200, 302, 503})
        body = response.get_data(as_text=True)
        if response.status_code == 200:
            self.assertIn("Editar item", body)
            self.assertIn("m-tabbar", body)
            self.assertIn('action="/m/itens/5/editar"', body)
            self.assertIn("data-m-step", body)

    def test_editar_item_redirects_when_item_missing(self):
        self.login("admin")
        response = self.client.get("/m/itens/999999/editar")
        self.assertIn(response.status_code, {302, 404})


class MobileFilterAndQuickActionTests(_StubbedTestCase):
    """Filtros por status e atualização rápida de produção (+1/−1)."""

    def test_status_chips_present_on_lists(self):
        self.login("admin")
        for rota, alvo in (
            ("/m/os-abertas", "#listaOsAbertas .m-item"),
            ("/m/gerenciar", "#listaChamados .m-item"),
        ):
            with self.subTest(rota=rota):
                body = self.client.get(rota).get_data(as_text=True)
                self.assertIn("data-m-chip-filter", body)
                self.assertIn(alvo, body)
                self.assertIn("m-chip-active", body)

    def test_quick_buttons_available_for_admin_only(self):
        self.login("admin")
        admin_body = self.client.get("/m/producao").get_data(as_text=True)
        self.assertIn('data-m-quick="1"', admin_body)
        self.assertIn('data-m-quick="-1"', admin_body)
        self.assertIn("data-m-quick-url", admin_body)

        self.login("operador")
        operador_body = self.client.get("/m/producao").get_data(as_text=True)
        self.assertNotIn('data-m-quick="1"', operador_body)
        self.assertIn("somente visualização", operador_body)

    def test_install_banner_has_dismiss_button(self):
        body = self.client.get("/m/").get_data(as_text=True)
        self.assertIn("data-m-install-dismiss", body)
        self.assertIn("id=\"m-install-banner\"", body)


class MobileJavaScriptSyntaxTests(unittest.TestCase):
    """Verifica a sintaxe do JS do app (pulado quando o node não está instalado).

    Este teste pega erros que os testes de renderização não pegam: scripts
    inline quebrados por edições em templates não derrubam o HTML, mas quebram
    o app no celular.
    """

    @classmethod
    def setUpClass(cls):
        import shutil
        import subprocess

        if not shutil.which("node"):
            raise unittest.SkipTest("node não disponível para checagem de sintaxe JS")
        cls.subprocess = subprocess

    def _check(self, codigo: str, nome: str):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            caminho = Path(tmp) / f"{nome}.js"
            caminho.write_text(codigo, encoding="utf-8")
            resultado = self.subprocess.run(
                ["node", "--check", str(caminho)], capture_output=True, text=True
            )
        self.assertEqual(resultado.returncode, 0, f"{nome}: {resultado.stderr[:400]}")

    def test_arquivos_estaticos(self):
        for nome in ("app.js", "service-worker.js"):
            with self.subTest(arquivo=nome):
                caminho = ROOT / "static" / "mobile" / nome
                self._check(caminho.read_text(encoding="utf-8"), nome.replace(".js", ""))

    def test_scripts_inline_dos_templates(self):
        import re

        for arquivo in sorted((ROOT / "templates" / "mobile").glob("*.html")):
            html = arquivo.read_text(encoding="utf-8")
            blocos = re.findall(
                r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", html, flags=re.S
            )
            for indice, bloco in enumerate(blocos):
                js = re.sub(r"\{#.*?#\}", "", bloco, flags=re.S)
                js = re.sub(r"\{%.*?%\}", "", js, flags=re.S)
                js = re.sub(r"\{\{.*?\}\}", "0", js, flags=re.S)
                if not js.strip():
                    continue
                with self.subTest(template=arquivo.name, bloco=indice):
                    self._check(js, f"{arquivo.stem}_{indice}")


class MobileScreenCoverageTests(unittest.TestCase):
    """Toda tela chamada por ``render_page`` precisa ter versão mobile.

    Sem esta trava, uma tela nova (ou renomeada) no sistema volta silenciosamente
    para o layout desktop dentro do app — foi o que aconteceu com
    ``editar_item.html``.
    """

    PADROES = (
        r'render_page\(\s*f?"([^"{}]+\.html)"',
        r'template_name\s*=\s*f?"([^"{}]+\.html)"',
    )

    @classmethod
    def setUpClass(cls):
        import re

        fontes = [ROOT / "app.py"] + sorted((ROOT / "appmodules").rglob("*.py"))
        cls.referencias: dict[str, set[str]] = {}
        for fonte in fontes:
            texto = fonte.read_text(encoding="utf-8")
            for padrao in cls.PADROES:
                for nome in re.findall(padrao, texto):
                    # render_page("mobile/home.html") já vem com o prefixo.
                    cls.referencias.setdefault(nome.removeprefix("mobile/"), set()).add(
                        str(fonte.relative_to(ROOT))
                    )
        cls.mobile_dir = ROOT / "templates" / "mobile"
        cls.desktop_dir = ROOT / "templates"

    def test_nenhuma_tela_fica_sem_versao_mobile(self):
        faltando = {
            nome: fontes
            for nome, fontes in self.referencias.items()
            if not (self.mobile_dir / nome).exists()
        }
        self.assertEqual(
            faltando,
            {},
            "Telas sem template mobile (o app cairia no layout desktop).",
        )

    def test_varredura_encontrou_as_telas_esperadas(self):
        """Evita um falso negativo caso os padrões deixem de casar."""
        esperadas = {
            "index.html",
            "os_abertas.html",
            "gerenciar.html",
            "editar_item.html",
            "producao.html",
            "relatorios.html",
            "usuarios.html",
        }
        self.assertTrue(
            esperadas.issubset(self.referencias),
            f"Varredura incompleta, faltaram: {esperadas - set(self.referencias)}",
        )

    def test_templates_mobile_tem_par_desktop_ou_sao_exclusivos_do_app(self):
        """Nomes em templates/mobile/ devem existir no desktop ou ser só do app."""

        exclusivos = {"home.html", "instalar.html", "offline.html", "mais.html"}
        for arquivo in sorted(self.mobile_dir.glob("*.html")):
            if arquivo.name in exclusivos or arquivo.name.startswith("_"):
                continue
            with self.subTest(template=arquivo.name):
                self.assertTrue(
                    (self.desktop_dir / arquivo.name).exists(),
                    f"{arquivo.name} não tem equivalente desktop — nome divergente?",
                )


class MobileManifestTests(unittest.TestCase):
    """O manifesto é requisito de instalação e não pode ficar fora do Git."""

    CAMINHO = ROOT / "static" / "mobile" / "manifest.json"

    @classmethod
    def setUpClass(cls):
        import json

        cls.manifest = json.loads(cls.CAMINHO.read_text(encoding="utf-8"))

    def test_arquivo_e_versionado(self):
        """``.gitignore`` ignora ``*.json``: o manifesto precisa da exceção."""

        import shutil
        import subprocess

        if not shutil.which("git") or not (ROOT / ".git").exists():
            self.skipTest("git não disponível")
        resultado = subprocess.run(
            ["git", "check-ignore", "-q", str(self.CAMINHO)],
            cwd=ROOT,
            capture_output=True,
        )
        self.assertNotEqual(
            resultado.returncode, 0, "manifest.json está sendo ignorado pelo git"
        )
        versionado = subprocess.run(
            ["git", "ls-files", "--error-unmatch", "static/mobile/manifest.json"],
            cwd=ROOT,
            capture_output=True,
        )
        self.assertEqual(
            versionado.returncode, 0, "manifest.json não está versionado no git"
        )

    def test_chaves_obrigatorias_do_pwa(self):
        for chave in ("name", "short_name", "start_url", "scope", "display", "icons"):
            with self.subTest(chave=chave):
                self.assertIn(chave, self.manifest)

        self.assertEqual(self.manifest["start_url"], "/m/")
        self.assertEqual(self.manifest["scope"], "/m/")
        self.assertEqual(self.manifest["display"], "standalone")
        self.assertEqual(self.manifest["theme_color"], "#5d6bd6")

        tamanhos = {(i.get("sizes"), i.get("purpose", "any")) for i in self.manifest["icons"]}
        self.assertIn(("192x192", "any"), tamanhos)
        self.assertIn(("512x512", "any"), tamanhos)
        self.assertIn(("512x512", "maskable"), tamanhos)

    def test_icones_declarados_existem_e_tem_o_tamanho_correto(self):
        try:
            from PIL import Image
        except ImportError:  # pragma: no cover - Pillow é opcional
            self.skipTest("Pillow não instalado")

        for icone in self.manifest["icons"]:
            with self.subTest(icone=icone["src"]):
                caminho = ROOT / icone["src"].lstrip("/")
                self.assertTrue(caminho.exists(), f"ícone ausente: {icone['src']}")
                with Image.open(caminho) as imagem:
                    largura, altura = imagem.size
                self.assertEqual(
                    f"{largura}x{altura}", icone["sizes"], f"tamanho divergente em {icone['src']}"
                )

    def test_atalhos_apontam_para_rotas_do_app(self):
        for atalho in self.manifest.get("shortcuts", []):
            with self.subTest(atalho=atalho.get("short_name")):
                self.assertTrue(atalho["url"].startswith("/m/"))

    def test_manifesto_servido_e_igual_ao_arquivo(self):
        import json

        resposta = app_module.app.test_client().get("/m/manifest.webmanifest")
        self.assertEqual(json.loads(resposta.get_data(as_text=True)), self.manifest)


class MobileSessionExpiryTests(unittest.TestCase):
    """Sessão expirada em chamadas AJAX não pode virar erro genérico na tela."""

    def test_app_js_intercepta_desvio_para_login(self):
        codigo = (ROOT / "static" / "mobile" / "app.js").read_text(encoding="utf-8")
        self.assertIn("interceptarSessaoExpirada", codigo)
        self.assertIn("Sessão expirada", codigo)
        self.assertIn('resp.redirected && destino.indexOf("/login") > -1', codigo)
        self.assertIn("window.fetch = function", codigo)

    def test_rota_de_login_aceita_retorno(self):
        """O aviso manda o usuário para /m/login?next=<tela atual>."""

        resposta = app_module.app.test_client().get("/m/login?next=/m/producao")
        self.assertEqual(resposta.status_code, 200)
        body = resposta.get_data(as_text=True)
        # Usa a tela mobile de login e mantém o destino no formulário.
        self.assertIn('action="/m/login', body)
        self.assertIn('name="username"', body)
        self.assertIn('name="password"', body)


class MobileQuickProductionPostTests(_StubbedTestCase):
    """Fluxo real dos botões −1/＋1: POST no endereço usado pelo app."""

    def _csrf(self, rota="/m/producao"):
        import re

        body = self.login("admin").get(rota).get_data(as_text=True)
        return re.search(r'name="csrf_token"\s+value="([^"]+)"', body).group(1)

    def _post(self, row_id, token, quantidade):
        return self.client.post(
            f"/m/producao/atualizar/{row_id}",
            data={
                "csrf_token": token,
                "nome_item": PRODUCAO_EXEMPLO["Nome do item"],
                "codigo_item": PRODUCAO_EXEMPLO["Código"],
                "mtc_projeto": PRODUCAO_EXEMPLO["Número do projeto MTC"],
                "quantidade_produzida": str(quantidade),
                "meta_producao": str(PRODUCAO_EXEMPLO["Meta de produção"]),
                "status": PRODUCAO_EXEMPLO["Status"],
                "observacao": PRODUCAO_EXEMPLO["Observação"],
                "responsavel": PRODUCAO_EXEMPLO["Responsável"],
                "nova_informacao": "",
            },
            headers={"X-Requested-With": "XMLHttpRequest"},
        )

    def test_atualizacao_rapida_responde_json_e_grava_quantidade(self):
        import json

        token = self._csrf()
        resposta = self._post(PRODUCAO_EXEMPLO["row_id"], token, 7)

        self.assertEqual(resposta.status_code, 200, resposta.get_data(as_text=True)[:300])
        self.assertEqual(resposta.mimetype, "application/json")
        self.assertTrue(json.loads(resposta.get_data(as_text=True))["success"])

        gravado = self.client.application.config["sheets_service"].ultima_atualizacao
        self.assertEqual(gravado["row_id"], PRODUCAO_EXEMPLO["row_id"])
        # Coluna 5 (índice 5) é "Quantidade produzida" na planilha.
        self.assertEqual(gravado["row_data"][5], "7")
        self.assertEqual(gravado["row_data"][2], PRODUCAO_EXEMPLO["Nome do item"])

    def test_atualizacao_rapida_sem_csrf_e_bloqueada(self):
        """O app envia o token do formulário; sem ele a escrita não passa."""

        self.login("admin")
        resposta = self.client.post(
            f"/m/producao/atualizar/{PRODUCAO_EXEMPLO['row_id']}",
            data={"quantidade_produzida": "5"},
        )
        self.assertEqual(resposta.status_code, 400, "CSRF deveria bloquear a escrita")
        self.assertFalse(
            getattr(self.client.application.config["sheets_service"], "ultima_atualizacao", None),
            "nada deveria ter sido gravado na planilha",
        )

    def test_item_inexistente_devolve_json_de_erro(self):
        import json

        token = self._csrf()
        resposta = self._post(999999, token, 1)
        self.assertEqual(resposta.status_code, 404)
        corpo = json.loads(resposta.get_data(as_text=True))
        self.assertFalse(corpo["success"])
        self.assertIn("não encontrado", corpo["message"].lower())

    def test_versao_web_usa_o_mesmo_endpoint(self):
        """O app não duplica rota: o mesmo POST funciona fora do prefixo /m."""

        import json

        token = self._csrf()
        resposta = self.client.post(
            f"/producao/atualizar/{PRODUCAO_EXEMPLO['row_id']}",
            data={
                "csrf_token": token,
                "nome_item": PRODUCAO_EXEMPLO["Nome do item"],
                "codigo_item": PRODUCAO_EXEMPLO["Código"],
                "quantidade_produzida": "42",
            },
        )
        self.assertEqual(resposta.status_code, 200, resposta.get_data(as_text=True)[:300])
        self.assertTrue(json.loads(resposta.get_data(as_text=True))["success"])
        gravado = self.client.application.config["sheets_service"].ultima_atualizacao
        self.assertEqual(gravado["row_data"][5], "42")
        # O GET continua não permitido (rota é de escrita).
        self.assertEqual(self.client.get("/producao/atualizar/3").status_code, 405)


class MobileListCounterTests(_StubbedTestCase):
    """O contador ao lado dos filtros precisa mostrar o total recebido da rota."""

    def _contador(self, rota):
        import re

        body = self.login("admin").get(rota).get_data(as_text=True)
        return re.search(r'id="contadorChamados">([^<]*)<', body).group(1).strip()

    def test_os_abertas_usa_total_chamados_da_rota(self):
        """``total_chamados`` é fornecido pela rota; sem ele o Jinja renderiza vazio."""

        rota = "/m/os-abertas"
        esperado = len([o for o in [OS_EXEMPLO] if str(o["Status da OS"]).lower() in {"aberto", "em andamento"}])
        valor = self._contador(rota)
        self.assertNotEqual(valor, "", "o contador ficou vazio — variável ausente no contexto")
        self.assertTrue(valor.isdigit(), f"contador não numérico: {valor!r}")
        self.assertEqual(int(valor), esperado)

    def test_gerenciar_usa_tamanho_da_lista(self):
        valor = self._contador("/m/gerenciar")
        self.assertTrue(valor.isdigit(), f"contador não numérico: {valor!r}")
        self.assertEqual(int(valor), 1)

    def test_contador_zerado_quando_a_planilha_esta_indisponivel(self):
        """Planilha fora do ar: a tela avisa o erro e o contador mostra zero."""

        class _Indisponivel(_StubSheetsService):
            def is_available(self):
                return False, "Planilha indisponível no momento"

        self.login("admin")
        app_module.app.config["sheets_service"] = _Indisponivel()
        try:
            html = self.client.get("/m/os-abertas")
        finally:
            app_module.app.config["sheets_service"] = _StubSheetsService()

        self.assertEqual(html.status_code, 503)
        body = html.get_data(as_text=True)
        self.assertIn("Planilha indisponível no momento", body)
        self.assertIn('id="contadorChamados">0<', body)
