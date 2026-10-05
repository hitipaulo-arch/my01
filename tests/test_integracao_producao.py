"""Testes da integração do sistema de OS com o app dedicado de produção.

A integração é só um **atalho**: o site (web e app mobile) mostra o endereço do
app de produção e abre em outra aba. Nada de dado, sessão ou regra de negócio é
compartilhado — e há teste garantindo isso.
"""

from __future__ import annotations

import html
import os
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS = Path(__file__).resolve().parent
for caminho in (str(ROOT), str(TESTS)):
    if caminho not in sys.path:
        sys.path.insert(0, caminho)

os.environ.setdefault("SECRET_KEY", "test-secret")

import app as app_module  # noqa: E402
from appmodules.integracao import dados, porta, url, url_derivada  # noqa: E402

def _texto(resposta) -> str:
    """HTML com as entidades resolvidas (o menu web usa &#127981; etc.)."""

    return html.unescape(resposta.get_data(as_text=True))


from test_mobile_app import (  # noqa: E402
    ITEM_EXEMPLO,
    PRODUCAO_EXEMPLO,
    _StubCentraisRepository,
    _StubSheetsService,
    _StubUserService,
)


class _IntegracaoTestCase(unittest.TestCase):
    """Base: serviços simulados e configuração controlada do atalho."""

    def setUp(self):
        self.client = app_module.app.test_client()
        self._original = {
            chave: app_module.app.config.get(chave)
            for chave in ("sheets_service", "user_service", "centrais_repository")
        }
        app_module.app.config["sheets_service"] = _StubSheetsService()
        app_module.app.config["user_service"] = _StubUserService()
        app_module.app.config["centrais_repository"] = _StubCentraisRepository()
        self._config_original = {
            chave: app_module.app.config.get(chave)
            for chave in ("PRODUCAO_APP_URL", "PRODUCAO_APP_PORT", "PRODUCAO_APP_INTEGRADO")
        }
        app_module.app.config.update(
            {"PRODUCAO_APP_URL": "", "PRODUCAO_APP_PORT": 5001, "PRODUCAO_APP_INTEGRADO": True}
        )

    def tearDown(self):
        for chave, valor in self._original.items():
            app_module.app.config[chave] = valor
        for chave, valor in self._config_original.items():
            app_module.app.config[chave] = valor

    def login(self, role="admin"):
        with self.client.session_transaction() as sessao:
            sessao["usuario"] = "admin" if role == "admin" else "operador1"
            sessao["role"] = role
        return self.client

    def configurar(self, **valores):
        app_module.app.config.update(valores)
        return self.client


class ResolucaoDoEnderecoTests(_IntegracaoTestCase):
    """Como o endereço do app é descoberto."""

    def test_endereco_configurado_tem_prioridade(self):
        self.configurar(PRODUCAO_APP_URL="https://producao.minhaempresa.com/")
        with app_module.app.test_request_context("/"):
            self.assertEqual(url(), "https://producao.minhaempresa.com")

    def test_endereco_configurado_aparece_no_contexto(self):
        self.configurar(PRODUCAO_APP_URL="https://producao.minhaempresa.com")
        with app_module.app.test_request_context("/"):
            pacote = dados()
        self.assertTrue(pacote["mostrar"])
        self.assertEqual(pacote["url"], "https://producao.minhaempresa.com")
        self.assertTrue(pacote["configurado"])

    def test_endereco_deduzido_de_ip_local(self):
        with app_module.app.test_request_context("/", headers={"Host": "192.168.0.10:5000"}):
            self.assertEqual(url_derivada(), "http://192.168.0.10:5001")

    def test_endereco_deduzido_de_dominio_sem_porta(self):
        with app_module.app.test_request_context("/", headers={"Host": "sistema.gestaoos.com.br"}):
            self.assertEqual(url_derivada(), "http://sistema.gestaoos.com.br:5001")

    def test_publicacao_com_porta_no_host_assume_https(self):
        """Sem cabeçalho de proxy, publicação com porta no host é HTTPS."""

        with app_module.app.test_request_context("/", headers={"Host": "5000-abc.exemplo.com"}):
            self.assertEqual(url_derivada(), "https://5001-abc.exemplo.com")

    def test_publicacao_respeita_http_explicito_do_proxy(self):
        with app_module.app.test_request_context(
            "/", headers={"Host": "5000-abc.exemplo.com", "X-Forwarded-Proto": "http"}
        ):
            self.assertEqual(url_derivada(), "http://5001-abc.exemplo.com")

    def test_esquema_segue_proxy_https(self):
        with app_module.app.test_request_context(
            "/", headers={"Host": "5000-abc.exemplo.com", "X-Forwarded-Proto": "https"}
        ):
            self.assertEqual(url_derivada(), "https://5001-abc.exemplo.com")

    def test_porta_configuravel(self):
        self.configurar(PRODUCAO_APP_PORT=9000)
        with app_module.app.test_request_context("/", headers={"Host": "10.0.0.5:5000"}):
            self.assertEqual(url_derivada(), "http://10.0.0.5:9000")
            self.assertEqual(porta(), 9000)

    def test_porta_invalida_cai_no_padrao(self):
        self.configurar(PRODUCAO_APP_PORT="abc")
        with app_module.app.test_request_context("/"):
            self.assertEqual(porta(), 5001)
            self.assertTrue(url_derivada().endswith(":5001"))

    def test_integracao_pode_ser_desligada(self):
        self.configurar(PRODUCAO_APP_INTEGRADO=False, PRODUCAO_APP_URL="https://producao.x.com")
        with app_module.app.test_request_context("/"):
            self.assertFalse(dados()["mostrar"])
            self.assertIsNone(dados()["url"])

    def test_aceita_variacoes_de_booleano(self):
        for valor in (False, True):
            with self.subTest(valor=valor):
                self.configurar(PRODUCAO_APP_INTEGRADO=valor)
                with app_module.app.test_request_context("/"):
                    self.assertEqual(dados()["mostrar"], valor)


class AtalhosNoSiteTests(_IntegracaoTestCase):
    """Onde o atalho aparece na versão web."""

    def test_menu_do_admin_tem_o_atalho(self):
        self.configurar(PRODUCAO_APP_URL="https://producao.minhaempresa.com")
        html = _texto(self.login("admin").get("/"))
        self.assertIn("Produção por Setor", html)
        self.assertIn('href="https://producao.minhaempresa.com"', html)
        self.assertIn('target="_blank"', html)
        self.assertIn('rel="noopener"', html)

    def test_menu_do_operador_tem_o_atalho(self):
        self.configurar(PRODUCAO_APP_URL="https://producao.minhaempresa.com")
        html = _texto(self.login("operador").get("/"))
        self.assertIn("Produção por Setor", html)

    def test_telas_antigas_de_producao_mostram_o_cartao(self):
        self.configurar(PRODUCAO_APP_URL="https://producao.minhaempresa.com")
        self.login("admin")
        for rota in ("/producao", "/producao-abertas", "/dashboard-producao"):
            with self.subTest(rota=rota):
                resposta = self.client.get(rota)
                self.assertIn(resposta.status_code, (200, 503))
                html = resposta.get_data(as_text=True)
                self.assertIn("cardAppProducao", html, "o cartão do app novo não apareceu")
                self.assertIn("https://producao.minhaempresa.com", html)
                self.assertIn("continua funcionando", html)

    def test_sem_integracao_nenhum_vestigio_do_app_novo(self):
        self.configurar(PRODUCAO_APP_INTEGRADO=False)
        self.login("admin")
        for rota in ("/", "/producao", "/producao-abertas", "/dashboard-producao"):
            with self.subTest(rota=rota):
                html = _texto(self.client.get(rota))
                self.assertNotIn("Produção por Setor", html)
                self.assertNotIn("cardAppProducao", html)

    def test_atalho_nao_quebra_a_versao_publica(self):
        """Visitante sem login não deve ver o atalho para o app interno."""

        self.configurar(PRODUCAO_APP_URL="https://producao.minhaempresa.com")
        html = _texto(self.client.get("/os-abertas"))
        self.assertNotIn("Produção por Setor", html)

    def test_endereco_deduzido_aparece_no_menu(self):
        html = _texto(self.login("admin").get("/"))
        self.assertIn("Produção por Setor", html)
        self.assertIn(":5001", html)


class AtalhosNoAppMobileTests(_IntegracaoTestCase):
    """O app em /m também leva ao app de produção."""

    def test_menu_mais_tem_a_secao_do_app_de_producao(self):
        self.configurar(PRODUCAO_APP_URL="https://producao.minhaempresa.com")
        html = _texto(self.login("admin").get("/m/mais"))
        self.assertIn("App de produção", html)
        self.assertIn("https://producao.minhaempresa.com", html)
        self.assertIn('rel="noopener"', html)

    def test_telas_de_producao_do_app_mostram_o_cartao(self):
        self.configurar(PRODUCAO_APP_URL="https://producao.minhaempresa.com")
        self.login("admin")
        for rota in ("/m/producao", "/m/producao-abertas", "/m/dashboard-producao"):
            with self.subTest(rota=rota):
                html = _texto(self.client.get(rota))
                self.assertIn("m-app-prod", html, "o cartão mobile não apareceu")
                self.assertIn("https://producao.minhaempresa.com", html)

    def test_cartao_nao_aparece_com_integracao_desligada(self):
        self.configurar(PRODUCAO_APP_INTEGRADO=False)
        self.login("admin")
        for rota in ("/m/mais", "/m/producao"):
            with self.subTest(rota=rota):
                html = _texto(self.client.get(rota))
                self.assertNotIn("m-app-prod", html)

    def test_atalho_no_app_nao_sai_do_modo_app(self):
        """Os links internos continuam com /m; o atalho aponta para fora."""

        self.configurar(PRODUCAO_APP_URL="https://producao.minhaempresa.com")
        html = _texto(self.login("admin").get("/m/mais"))
        prefixados = set(re.findall(r'href="(/m/[^"]*)"', html))
        self.assertTrue(prefixados, "o menu do app deveria manter links internos")
        self.assertIn('href="https://producao.minhaempresa.com"', html)


class CookieDePreviewTests(unittest.TestCase):
    """Cookies de sessão do próprio sistema de OS em iframe/preview."""

    def _samesite(self, valor):
        import importlib
        import os as _os

        from unittest import mock

        import config as config_module

        ambiente = {k: v for k, v in _os.environ.items() if k != "FLASK_COOKIE_SAMESITE"}
        if valor is not None:
            ambiente["FLASK_COOKIE_SAMESITE"] = valor
        with mock.patch.dict(_os.environ, ambiente, clear=True):
            importlib.reload(config_module)
            return config_module.FlaskConfig.SESSION_COOKIE_SAMESITE

    def test_padrao_continua_lax(self):
        import importlib

        import config as config_module

        importlib.reload(config_module)
        self.assertEqual(config_module.FlaskConfig.SESSION_COOKIE_SAMESITE, "Lax")
        self.assertFalse(config_module.FlaskConfig.SESSION_COOKIE_PARTITIONED)

    def test_aceita_none_para_preview(self):
        for valor in ("None", "none", "null", ""):
            with self.subTest(valor=repr(valor)):
                self.assertIsNone(self._samesite(valor))

    def test_aceita_strict_e_lax(self):
        for valor in ("Strict", "Lax"):
            with self.subTest(valor=valor):
                self.assertEqual(self._samesite(valor), valor)


class IsolamentoDaIntegracaoTests(unittest.TestCase):
    """A ponte é só um link: nada de importar o outro app."""

    def test_modulo_de_integracao_nao_importa_o_app_de_producao(self):
        arquivo = ROOT / "appmodules" / "integracao" / "__init__.py"
        conteudo = arquivo.read_text(encoding="utf-8")
        self.assertNotIn("producao_web", conteudo)
        self.assertNotIn("SheetsService", conteudo)

    def test_app_de_producao_nao_conhece_o_sistema_de_os(self):
        for arquivo in sorted((ROOT / "appmodules" / "producao_web").rglob("*.py")):
            with self.subTest(arquivo=arquivo.name):
                self.assertNotIn("integracao", arquivo.read_text(encoding="utf-8"))

    def test_atalho_e_apenas_link_sem_envio_de_dados(self):
        """Nada de formulário/post para o app: o usuário entra e faz login lá."""

        cliente = _IntegracaoTestCase.__new__(_IntegracaoTestCase)
        cliente.setUp()
        try:
            cliente.configurar(PRODUCAO_APP_URL="https://producao.minhaempresa.com")
            cliente.login("admin")
            html = cliente.client.get("/").get_data(as_text=True)
        finally:
            cliente.tearDown()

        self.assertIn("https://producao.minhaempresa.com", html)
        for trecho in ('action="https://producao', 'method="post" action="https://producao'):
            self.assertNotIn(trecho, html)


if __name__ == "__main__":
    unittest.main(verbosity=2)
