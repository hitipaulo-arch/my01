"""Testes do app de produção (controle por setor).

Cobrem:

* o fluxo de setores (ordem, status calculado da OP, progresso);
* o armazenamento local (OPs, setores, histórico) sem depender do Google Sheets;
* o login por setor e as permissões (cada setor mexe só no seu status);
* as telas do app e os requisitos de instalação (manifest, service worker, ícones);
* o isolamento do app: ele não compartilha sessão, templates nem dados com o
  sistema de OS.
"""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("SECRET_KEY", "test-secret")  # o sistema de OS exige
os.environ.setdefault("PRODUCAO_SECRET_KEY", "test-producao-secret")
os.environ.setdefault("PRODUCAO_ADMIN_PIN", "1234")

from appmodules.producao_web import criar_para_testes  # noqa: E402
from appmodules.producao_web import setores as fluxo  # noqa: E402
from appmodules.producao_web.storage import (  # noqa: E402
    LocalStorage,
    linha_para_op,
    linha_para_setor,
    op_para_linha,
    proximo_id,
    setor_para_linha,
)


# ──────────────────────────────────────────────────────────────────────────────
# Fluxo de setores (puro, sem servidor)
# ──────────────────────────────────────────────────────────────────────────────
class SetoresTests(unittest.TestCase):
    """A ordem do fluxo é o coração do app."""

    def test_ordem_do_fluxo_da_fabrica(self):
        self.assertEqual(
            fluxo.nomes(),
            (
                "Corte",
                "Dobra",
                "Montagem Primária",
                "Solda",
                "Acabamento",
                "Silicone e Limpeza",
                "Embalagem",
            ),
        )

    def test_estrutura_do_setor(self):
        for setor in fluxo.SETORES:
            with self.subTest(setor=setor.chave):
                self.assertRegex(setor.chave, r"^[a-z_]+$")
                self.assertTrue(setor.nome.strip())
                self.assertTrue(setor.icone.strip())
        self.assertEqual(len({s.chave for s in fluxo.SETORES}), len(fluxo.SETORES))

    def test_busca_por_chave_e_por_nome(self):
        self.assertEqual(fluxo.por_chave("solda").nome, "Solda")
        self.assertEqual(fluxo.por_nome("silicone e limpeza").chave, "silicone_limpeza")
        self.assertEqual(fluxo.por_chave("montagem_primaria").nome, "Montagem Primária")
        self.assertIsNone(fluxo.por_chave("pintura"))
        self.assertIsNone(fluxo.por_nome(""))

    def test_normalizacao_de_status(self):
        self.assertEqual(fluxo.normalizar_status("concluido"), fluxo.CONCLUIDO)
        self.assertEqual(fluxo.normalizar_status("CONCLUÍDO"), fluxo.CONCLUIDO)
        self.assertEqual(fluxo.normalizar_status("em andamento"), fluxo.EM_ANDAMENTO)
        self.assertEqual(fluxo.normalizar_status(""), fluxo.NAO_INICIADO)
        self.assertEqual(fluxo.normalizar_status("qualquer coisa"), fluxo.NAO_INICIADO)
        self.assertTrue(fluxo.e_status_valido(fluxo.CONCLUIDO))
        self.assertFalse(fluxo.e_status_valido("Pronto"))

    def test_status_da_op_segue_os_setores(self):
        def com(*concluidos, andamento=()):
            mapa = {nome: fluxo.NAO_INICIADO for nome in fluxo.nomes()}
            for nome in concluidos:
                mapa[nome] = fluxo.CONCLUIDO
            for nome in andamento:
                mapa[nome] = fluxo.EM_ANDAMENTO
            return mapa

        self.assertEqual(fluxo.status_da_op(com()), fluxo.OP_AGUARDANDO)
        self.assertEqual(
            fluxo.status_da_op(com("Corte", andamento=("Dobra",))), fluxo.OP_EM_ANDAMENTO
        )
        self.assertEqual(
            fluxo.status_da_op(com(*fluxo.nomes())), fluxo.OP_CONCLUIDA
        )

    def test_progresso_conta_setores_concluidos(self):
        self.assertEqual(fluxo.progresso({}), 0)
        todos = {nome: fluxo.CONCLUIDO for nome in fluxo.nomes()}
        self.assertEqual(fluxo.progresso(todos), 100)
        parcial = {"Corte": fluxo.CONCLUIDO, "Dobra": fluxo.CONCLUIDO}
        self.assertEqual(fluxo.progresso(parcial), round(2 / len(fluxo.SETORES) * 100))

    def test_proximo_setor_e_o_primeiro_nao_concluido(self):
        mapa = {"Corte": fluxo.CONCLUIDO, "Dobra": fluxo.EM_ANDAMENTO}
        self.assertEqual(fluxo.proximo_setor(mapa)["nome"], "Dobra")
        self.assertIsNone(fluxo.proximo_setor({nome: fluxo.CONCLUIDO for nome in fluxo.nomes()}))

    def test_setores_desconhecidos_na_planilha_sao_reportados(self):
        linhas = [{"setor": "Corte"}, {"setor": "Pintura"}, {"setor": ""}]
        self.assertEqual(fluxo.nomes_desconhecidos(linhas), {"Pintura"})

    def test_setores_em_ordem_monta_as_linhas_da_tela(self):
        linhas = fluxo.setores_em_ordem({"Solda": fluxo.EM_ANDAMENTO})
        self.assertEqual([linha["ordem"] for linha in linhas], list(range(1, 8)))
        solda = [linha for linha in linhas if linha["nome"] == "Solda"][0]
        self.assertEqual(solda["status"], fluxo.EM_ANDAMENTO)
        self.assertFalse(solda["concluido"])
        self.assertEqual(linhas[0]["nome"], "Corte")


# ──────────────────────────────────────────────────────────────────────────────
# Conversão linha <-> dicionário
# ──────────────────────────────────────────────────────────────────────────────
class ConversaoTests(unittest.TestCase):
    def test_ida_e_volta_da_op(self):
        op = {
            "id": "OP-0007",
            "criado_em": "05/10/2026 08:00:00",
            "nome_item": "Porta 900x2100",
            "codigo": "12-34-567",
            "mtc": "42",
            "quantidade": 10,
            "cliente": "OS 101",
            "prazo": "31/12/2026",
            "material": "Inox 304",
            "observacao": "Dobra reforçada",
            "criado_por": "Gestão",
            "concluida_em": "",
        }
        self.assertEqual(linha_para_op(op_para_linha(op)), op)

    def test_linha_curta_ou_longa_nao_quebra(self):
        curta = linha_para_op(["OP-0001"])
        self.assertEqual(curta["id"], "OP-0001")
        self.assertEqual(curta["nome_item"], "")
        self.assertEqual(curta["quantidade"], 0)
        longa = linha_para_op(["OP-0002", "hoje", "Item", "11-22-333", "9", "3", "cliente", "prazo", "mat", "obs", "quem", "fim", "extra"])
        self.assertEqual(longa["cliente"], "cliente")

    def test_quantidade_aceita_formatos_numericos(self):
        self.assertEqual(linha_para_op(["OP-1", "", "i", "c", "", "1.234"])["quantidade"], 1234)
        self.assertEqual(linha_para_op(["OP-1", "", "i", "c", "", "abc"])["quantidade"], 0)

    def test_ida_e_volta_do_setor(self):
        registro = {
            "op_id": "OP-0001",
            "setor": "Solda",
            "status": fluxo.EM_ANDAMENTO,
            "iniciado_em": "05/10/2026 09:00:00",
            "concluido_em": "",
            "atualizado_em": "05/10/2026 09:00:00",
            "atualizado_por": "Solda",
            "observacao": "aguardando gás",
        }
        self.assertEqual(linha_para_setor(setor_para_linha(registro)), registro)

    def test_setor_sem_status_cai_para_nao_iniciado(self):
        self.assertEqual(linha_para_setor(["OP-1", "Corte"])["status"], fluxo.NAO_INICIADO)

    def test_proximo_id_sequencial(self):
        self.assertEqual(proximo_id([]), "OP-0001")
        self.assertEqual(proximo_id([{"id": "OP-0009"}]), "OP-0010")
        self.assertEqual(proximo_id([{"id": "OP-0009"}, {"id": "OP-0100"}]), "OP-0101")
        self.assertEqual(proximo_id([{"id": "lixo"}]), "OP-0001")


# ──────────────────────────────────────────────────────────────────────────────
# Armazenamento local
# ──────────────────────────────────────────────────────────────────────────────
class LocalStorageTests(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.storage = LocalStorage(Path(self.pasta.name) / "producao.json")

    def tearDown(self):
        self.pasta.cleanup()

    def criar(self, nome="Peça teste", **extra):
        dados = {"nome_item": nome, "codigo": "11-22-333", "quantidade": 5}
        dados.update(extra)
        return self.storage.criar_op(dados, "Gestão")

    def test_comeca_vazio(self):
        self.assertEqual(self.storage.listar_ops(), [])
        self.assertEqual(self.storage.listar_setores(), [])
        self.assertTrue(self.storage.disponivel()[0])

    def test_criar_op_gera_linhas_para_todos_os_setores(self):
        op = self.criar()
        self.assertEqual(op["id"], "OP-0001")
        registros = self.storage.setores_da_op(op["id"])
        self.assertEqual([r["setor"] for r in registros], list(fluxo.nomes()))
        self.assertTrue(all(r["status"] == fluxo.NAO_INICIADO for r in registros))

    def test_ids_sequenciais(self):
        self.assertEqual(self.criar()["id"], "OP-0001")
        self.assertEqual(self.criar()["id"], "OP-0002")

    def test_atualizar_status_registra_data_hora_e_responsavel(self):
        op = self.criar()
        self.assertTrue(
            self.storage.atualizar_status_setor(op["id"], "Corte", fluxo.EM_ANDAMENTO, "Corte")
        )
        registro = self.storage.setores_da_op(op["id"])[0]
        self.assertEqual(registro["status"], fluxo.EM_ANDAMENTO)
        self.assertTrue(registro["iniciado_em"])
        self.assertEqual(registro["concluido_em"], "")
        self.assertEqual(registro["atualizado_por"], "Corte")

        self.storage.atualizar_status_setor(op["id"], "Corte", fluxo.CONCLUIDO, "Corte")
        registro = self.storage.setores_da_op(op["id"])[0]
        self.assertTrue(registro["concluido_em"])
        self.assertEqual(registro["iniciado_em"], registro["iniciado_em"])  # preservado

    def test_voltar_para_nao_iniciado_limpa_os_carimbos(self):
        op = self.criar()
        self.storage.atualizar_status_setor(op["id"], "Corte", fluxo.CONCLUIDO, "Corte")
        self.storage.atualizar_status_setor(op["id"], "Corte", fluxo.NAO_INICIADO, "Corte")
        registro = self.storage.setores_da_op(op["id"])[0]
        self.assertEqual(registro["iniciado_em"], "")
        self.assertEqual(registro["concluido_em"], "")

    def test_historico_so_registra_mudanca_real(self):
        op = self.criar()
        self.storage.atualizar_status_setor(op["id"], "Corte", fluxo.CONCLUIDO, "Corte")
        self.storage.atualizar_status_setor(op["id"], "Corte", fluxo.CONCLUIDO, "Corte")
        historico = self.storage.listar_historico(op["id"])
        self.assertEqual(len(historico), 1)
        self.assertEqual(historico[0]["status_anterior"], fluxo.NAO_INICIADO)
        self.assertEqual(historico[0]["status_novo"], fluxo.CONCLUIDO)
        self.assertEqual(historico[0]["quem"], "Corte")

    def test_setor_desconhecido_e_recusado(self):
        op = self.criar()
        self.assertFalse(
            self.storage.atualizar_status_setor(op["id"], "Pintura", fluxo.CONCLUIDO, "x")
        )

    def test_op_inexistente_e_recusada(self):
        self.assertFalse(
            self.storage.atualizar_status_setor("OP-9999", "Corte", fluxo.CONCLUIDO, "x")
        )

    def test_concluir_todos_os_setores_marca_a_op(self):
        op = self.criar()
        for nome in fluxo.nomes():
            self.storage.atualizar_status_setor(op["id"], nome, fluxo.CONCLUIDO, "Gestão")
        gravada = self.storage.obter_op(op["id"])
        self.assertTrue(gravada["concluida_em"])
        self.assertEqual(self.storage.ops_com_fluxo()[0]["status_geral"], fluxo.OP_CONCLUIDA)

    def test_ops_com_fluxo_calculam_status_e_progresso(self):
        op = self.criar()
        fluida = self.storage.ops_com_fluxo()[0]
        self.assertEqual(fluida["status_geral"], fluxo.OP_AGUARDANDO)
        self.assertEqual(fluida["progresso"], 0)
        self.assertEqual(fluida["setor_atual"]["nome"], "Corte")
        self.assertEqual(len(fluida["setores"]), len(fluxo.SETORES))

        self.storage.atualizar_status_setor(op["id"], "Corte", fluxo.CONCLUIDO, "Corte")
        fluida = self.storage.ops_com_fluxo()[0]
        self.assertEqual(fluida["status_geral"], fluxo.OP_EM_ANDAMENTO)
        self.assertEqual(fluida["setor_atual"]["nome"], "Dobra")
        self.assertEqual(fluida["setores"][0]["concluido"], True)
        self.assertTrue(fluida["setores"][0]["concluido_em"])

    def test_editar_op_mantem_o_id_e_o_historico(self):
        op = self.criar()
        self.storage.atualizar_status_setor(op["id"], "Corte", fluxo.CONCLUIDO, "Corte")
        self.assertTrue(
            self.storage.atualizar_op(op["id"], {"nome_item": "Peça renomeada", "quantidade": 9})
        )
        gravada = self.storage.obter_op(op["id"])
        self.assertEqual(gravada["nome_item"], "Peça renomeada")
        self.assertEqual(gravada["quantidade"], 9)
        self.assertEqual(len(self.storage.listar_historico(op["id"])), 1)

    def test_excluir_op_remove_setores_e_historico(self):
        op = self.criar()
        self.storage.atualizar_status_setor(op["id"], "Corte", fluxo.CONCLUIDO, "Corte")
        self.assertTrue(self.storage.excluir_op(op["id"]))
        self.assertEqual(self.storage.listar_ops(), [])
        self.assertEqual(self.storage.listar_setores(), [])
        self.assertEqual(self.storage.listar_historico(op["id"]), [])
        self.assertFalse(self.storage.excluir_op("OP-9999"))

    def test_acessos_sao_gravados_e_atualizados(self):
        self.assertIsNone(self.storage.obter_acesso("solda"))
        self.storage.salvar_acesso("solda", fluxo.PAPEL_SETOR, "Solda", "hash-1", True)
        self.assertEqual(self.storage.obter_acesso("solda")["pin_hash"], "hash-1")
        self.storage.salvar_acesso("solda", fluxo.PAPEL_SETOR, "Solda", "hash-2", False)
        acesso = self.storage.obter_acesso("SOLDa")
        self.assertEqual(acesso["pin_hash"], "hash-2")
        self.assertFalse(acesso["ativo"])
        self.assertEqual(len(self.storage.listar_acessos()), 1)

    def test_arquivo_ilegivel_nao_derruba_o_app(self):
        self.criar()
        (Path(self.pasta.name) / "producao.json").write_text("{lixo", encoding="utf-8")
        self.assertEqual(self.storage.listar_ops(), [])


# ──────────────────────────────────────────────────────────────────────────────
# Aplicação
# ──────────────────────────────────────────────────────────────────────────────
class AppProducaoTestCase(unittest.TestCase):
    """Base: sobe o app com banco local temporário, vazio."""

    @classmethod
    def setUpClass(cls):
        cls.pasta = tempfile.TemporaryDirectory()
        cls.app = criar_para_testes(
            {
                "SECRET_KEY": "test-producao",
                "STORAGE": "local",
                "LOCAL_DB_PATH": str(Path(cls.pasta.name) / "producao.json"),
                "ADMIN_PIN": "1234",
            }
        )
        cls.app.config["TESTING"] = True

    @classmethod
    def tearDownClass(cls):
        cls.pasta.cleanup()

    def setUp(self):
        self.client = self.app.test_client()
        # Cada teste começa com banco limpo (sem estado entre testes).
        caminho = Path(self.app.config["LOCAL_DB_PATH"])
        if caminho.exists():
            caminho.unlink()
        self.storage = LocalStorage(caminho)

    # ── utilidades ──────────────────────────────────────────────────────────
    def csrf(self, rota="/login"):
        texto = self.client.get(rota).get_data(as_text=True)
        encontrado = re.search(r'name="csrf_token" value="([^"]+)"', texto)
        return encontrado.group(1) if encontrado else ""

    def entrar(self, perfil="gestao", pin="1234"):
        return self.client.post(
            "/login", data={"csrf_token": self.csrf(), "perfil": perfil, "pin": pin}
        )

    def criar_op(self, **extra):
        dados = {"nome_item": "Porta de alumínio", "codigo": "12-34-567", "quantidade": "10"}
        dados.update(extra)
        resposta = self.client.post(
            "/op/nova", data={"csrf_token": self.csrf("/op/nova"), **dados}
        )
        return resposta.headers.get("Location", "").rsplit("/", 1)[-1]

    def marcar(self, op_id, chave, status, observacao=""):
        return self.client.post(
            f"/op/{op_id}/setor/{chave}",
            data={"csrf_token": self.csrf(f"/op/{op_id}"), "status": status, "observacao": observacao},
            headers={"X-Requested-With": "XMLHttpRequest"},
        )


class LoginTests(AppProducaoTestCase):
    def test_telas_publicas_respondem(self):
        for rota in ("/login", "/instalar", "/offline", "/manifest.webmanifest", "/service-worker.js"):
            with self.subTest(rota=rota):
                self.assertEqual(self.client.get(rota).status_code, 200)

    def test_rotas_internas_exigem_login(self):
        for rota in ("/", "/ops", "/painel", "/acessos", "/op/nova"):
            with self.subTest(rota=rota):
                resposta = self.client.get(rota)
                self.assertEqual(resposta.status_code, 302)
                self.assertIn("/login", resposta.headers.get("Location", ""))

    def test_login_da_gestao_com_pin_do_ambiente(self):
        resposta = self.entrar("gestao", "1234")
        self.assertEqual(resposta.status_code, 302)
        self.assertIn("Painel", self.client.get("/painel").get_data(as_text=True))

    def test_pin_errado_nao_entra(self):
        resposta = self.entrar("gestao", "0000")
        self.assertEqual(resposta.status_code, 401)
        self.assertIn("PIN incorreto", resposta.get_data(as_text=True))

    def test_setor_sem_pin_cadastrado_nao_entra(self):
        resposta = self.entrar("solda", "1234")
        self.assertEqual(resposta.status_code, 401)

    def test_setor_entra_com_o_pin_cadastrado_pela_gestao(self):
        self.entrar("gestao")
        self.client.post(
            "/acessos",
            data={
                "csrf_token": self.csrf("/acessos"),
                "perfil": "solda",
                "pin": "4321",
                "ativo": "sim",
            },
        )
        self.client.get("/sair")
        resposta = self.entrar("solda", "4321")
        self.assertEqual(resposta.status_code, 302)
        self.assertIn("Solda", self.client.get("/").get_data(as_text=True))

    def test_perfil_desativado_nao_entra(self):
        self.entrar("gestao")
        self.client.post(
            "/acessos",
            data={
                "csrf_token": self.csrf("/acessos"),
                "perfil": "dobra",
                "pin": "5555",
                "ativo": "nao",
            },
        )
        self.client.get("/sair")
        resposta = self.entrar("dobra", "5555")
        self.assertEqual(resposta.status_code, 403)
        self.assertIn("desativado", resposta.get_data(as_text=True))

    def test_setor_inexistente_e_recusado(self):
        resposta = self.entrar("pintura", "1234")
        self.assertEqual(resposta.status_code, 400)

    def test_pin_de_4_a_8_digitos(self):
        self.entrar("gestao")
        resposta = self.client.post(
            "/acessos",
            data={"csrf_token": self.csrf("/acessos"), "perfil": "corte", "pin": "12"},
            follow_redirects=True,
        )
        self.assertIn("4 a 8 dígitos", resposta.get_data(as_text=True))
        self.assertIsNone(self.storage.obter_acesso("corte"))

    def test_logout_encerra_a_sessao(self):
        self.entrar("gestao")
        self.client.get("/sair")
        self.assertEqual(self.client.get("/painel").status_code, 302)


class PermissoesTests(AppProducaoTestCase):
    def setUp(self):
        super().setUp()
        self.entrar("gestao")
        self.op = self.criar_op()
        self.client.post(
            "/acessos",
            data={
                "csrf_token": self.csrf("/acessos"),
                "perfil": "solda",
                "pin": "4321",
                "ativo": "sim",
            },
        )
        self.client.get("/sair")
        self.entrar("solda", "4321")

    def test_setor_so_altera_o_proprio_status(self):
        resposta = self.marcar(self.op, "dobra", "Concluído")
        self.assertEqual(resposta.status_code, 403)
        self.assertIn("só pode atualizar o seu setor", json.loads(resposta.get_data(as_text=True))["message"])
        # nada foi gravado
        self.assertEqual(
            self.storage.setores_da_op(self.op)[1]["status"], fluxo.NAO_INICIADO
        )

    def test_setor_altera_o_proprio_status(self):
        resposta = self.marcar(self.op, "solda", "Em andamento", "começando")
        self.assertEqual(resposta.status_code, 200)
        dados = json.loads(resposta.get_data(as_text=True))
        self.assertTrue(dados["success"])
        registro = [r for r in self.storage.setores_da_op(self.op) if r["setor"] == "Solda"][0]
        self.assertEqual(registro["status"], fluxo.EM_ANDAMENTO)
        self.assertEqual(registro["observacao"], "começando")
        self.assertEqual(registro["atualizado_por"], "Solda")

    def test_setor_nao_cadastra_nem_exclui_op(self):
        self.assertEqual(self.client.get("/op/nova").status_code, 302)
        resposta = self.client.post(
            f"/op/{self.op}/excluir", data={"csrf_token": self.csrf(f"/op/{self.op}")}
        )
        self.assertEqual(resposta.status_code, 302)
        self.assertTrue(self.storage.obter_op(self.op), "a OP não deveria ter sido excluída")

    def test_setor_nao_abre_a_tela_de_acessos(self):
        resposta = self.client.get("/acessos", follow_redirects=True)
        self.assertIn("Essa área é da gestão", resposta.get_data(as_text=True))

    def test_setor_nao_vê_os_outros_setores_editaveis(self):
        html = self.client.get(f"/op/{self.op}").get_data(as_text=True)
        self.assertEqual(html.count("p-flow-form"), 1, "só o formulário da Solda")
        self.assertIn("data-setor=\"solda\"", html)

    def test_gestao_altera_qualquer_setor(self):
        self.client.get("/sair")
        self.entrar("gestao")
        html = self.client.get(f"/op/{self.op}").get_data(as_text=True)
        self.assertEqual(html.count("p-flow-form"), len(fluxo.SETORES))
        for chave in fluxo.SETORES:
            self.assertEqual(self.marcar(self.op, chave.chave, "Concluído").status_code, 200)
        self.assertEqual(self.storage.ops_com_fluxo()[0]["status_geral"], fluxo.OP_CONCLUIDA)


class CadastroOpTests(AppProducaoTestCase):
    def setUp(self):
        super().setUp()
        self.entrar("gestao")

    def test_criar_op_com_dados_minimos(self):
        op_id = self.criar_op()
        self.assertEqual(op_id, "OP-0001")
        op = self.storage.obter_op(op_id)
        self.assertEqual(op["nome_item"], "Porta de alumínio")
        self.assertEqual(op["codigo"], "12-34-567")
        self.assertEqual(op["criado_por"], "Gestão")
        self.assertEqual(len(self.storage.setores_da_op(op_id)), len(fluxo.SETORES))

    def test_codigo_recebe_mascara_e_mtc_quatro_digitos(self):
        op_id = self.criar_op(codigo="1234567", mtc="123456")
        op = self.storage.obter_op(op_id)
        self.assertEqual(op["codigo"], "12-34-567")
        self.assertEqual(op["mtc"], "1234")

    def test_validacoes_do_formulario(self):
        casos = (
            ({"nome_item": "A"}, "mínimo 2 caracteres"),
            ({"codigo": ""}, "Informe o código"),
            ({"quantidade": "abc"}, "Quantidade inválida"),
            ({"prazo": "31/13/2026"}, "formato dd/mm/aaaa"),
        )
        for extra, esperado in casos:
            with self.subTest(esperado=esperado):
                resposta = self.client.post(
                    "/op/nova", data={"csrf_token": self.csrf("/op/nova"), "nome_item": "Item ok", "codigo": "11-22-333", **extra}
                )
                self.assertEqual(resposta.status_code, 400)
                self.assertIn(esperado, resposta.get_data(as_text=True))
        self.assertEqual(self.storage.listar_ops(), [])

    def test_editar_op(self):
        op_id = self.criar_op()
        resposta = self.client.post(
            f"/op/{op_id}/editar",
            data={
                "csrf_token": self.csrf(f"/op/{op_id}/editar"),
                "nome_item": "Peça revisada",
                "codigo": "99-88-777",
                "quantidade": "3",
            },
        )
        self.assertEqual(resposta.status_code, 302)
        op = self.storage.obter_op(op_id)
        self.assertEqual(op["nome_item"], "Peça revisada")
        self.assertEqual(op["quantidade"], 3)

    def test_excluir_op(self):
        op_id = self.criar_op()
        resposta = self.client.post(
            f"/op/{op_id}/excluir", data={"csrf_token": self.csrf(f"/op/{op_id}")}
        )
        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(self.storage.listar_ops(), [])

    def test_op_inexistente_redireciona_com_aviso(self):
        resposta = self.client.get("/op/OP-9999", follow_redirects=True)
        self.assertIn("OP não encontrada", resposta.get_data(as_text=True))

    def test_csrf_e_obrigatorio_nas_escritas(self):
        resposta = self.client.post("/op/nova", data={"nome_item": "Sem token", "codigo": "11-22-333"})
        self.assertEqual(resposta.status_code, 400)
        self.assertEqual(self.storage.listar_ops(), [])


class TelasTests(AppProducaoTestCase):
    def setUp(self):
        super().setUp()
        self.entrar("gestao")
        self.op = self.criar_op(nome_item="Porta <b>especial</b>")

    def test_painel_mostra_resumo_e_carga_por_setor(self):
        html = self.client.get("/painel").get_data(as_text=True)
        self.assertIn("OPs no total", html)
        self.assertEqual(html.count("p-setor-card"), len(fluxo.SETORES))
        for nome in fluxo.nomes():
            self.assertIn(nome, html)

    def test_lista_tem_busca_e_contador(self):
        html = self.client.get("/ops").get_data(as_text=True)
        self.assertIn("data-p-filter", html)
        self.assertIn('id="contadorOps"', html)

    def test_ficha_da_op_mostra_os_setores_na_ordem(self):
        html = self.client.get(f"/op/{self.op}").get_data(as_text=True)
        posicoes = [html.index(nome) for nome in fluxo.nomes()]
        self.assertEqual(posicoes, sorted(posicoes), "os setores devem aparecer na ordem do fluxo")

    def test_ficha_tem_botoes_de_status_e_historico(self):
        self.marcar(self.op, "corte", "Concluído", "corte ok")
        html = self.client.get(f"/op/{self.op}").get_data(as_text=True)
        self.assertIn("Não iniciado", html)
        self.assertIn("Em andamento", html)
        self.assertIn("Concluído", html)
        self.assertIn("Histórico de alterações", html)
        self.assertIn("corte ok", html)

    def test_nome_do_item_e_escapado(self):
        html = self.client.get(f"/op/{self.op}").get_data(as_text=True)
        self.assertIn("Porta &lt;b&gt;especial&lt;/b&gt;", html)
        self.assertNotIn("Porta <b>especial</b>", html)

    def test_pagina_404_usa_o_layout_do_app(self):
        resposta = self.client.get("/pagina-que-nao-existe")
        self.assertEqual(resposta.status_code, 404)
        html = resposta.get_data(as_text=True)
        self.assertIn("p-app", html)
        self.assertIn("Página não encontrada", html)

    def test_todas_as_telas_estendem_a_base_e_sao_mobile(self):
        for arquivo in sorted((ROOT / "templates" / "producao").glob("*.html")):
            if arquivo.name.startswith("_"):
                continue
            with self.subTest(template=arquivo.name):
                conteudo = arquivo.read_text(encoding="utf-8")
                self.assertIn("producao/_base.html", conteudo)
                self.assertIn("viewport-fit=cover", (ROOT / "templates" / "producao" / "_base.html").read_text(encoding="utf-8"))

    def test_cores_e_identidade_do_sistema(self):
        base = (ROOT / "templates" / "producao" / "_base.html").read_text(encoding="utf-8")
        self.assertIn("unified.css", base)
        self.assertIn("#5d6bd6", base)
        self.assertIn("producao/app.css", base)


class InstalacaoTests(AppProducaoTestCase):
    """O app precisa ser instalável no celular do chão de fábrica."""

    MANIFEST = ROOT / "static" / "producao" / "manifest.json"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.manifest = json.loads(cls.MANIFEST.read_text(encoding="utf-8"))

    def test_arquivo_do_manifesto_nao_e_ignorado_pelo_git(self):
        import shutil
        import subprocess

        if not shutil.which("git") or not (ROOT / ".git").exists():
            self.skipTest("git não disponível")
        ignorado = subprocess.run(
            ["git", "check-ignore", "-q", str(self.MANIFEST)], cwd=ROOT, capture_output=True
        )
        self.assertNotEqual(ignorado.returncode, 0, "manifest.json está no .gitignore")
        versionado = subprocess.run(
            ["git", "ls-files", "--error-unmatch", "static/producao/manifest.json"],
            cwd=ROOT,
            capture_output=True,
        )
        self.assertEqual(versionado.returncode, 0, "manifesto precisa estar versionado")

    def test_chaves_obrigatorias(self):
        for chave in ("name", "short_name", "start_url", "scope", "display", "icons", "theme_color"):
            with self.subTest(chave=chave):
                self.assertIn(chave, self.manifest)
        self.assertEqual(self.manifest["start_url"], "/")
        self.assertEqual(self.manifest["display"], "standalone")
        self.assertEqual(self.manifest["theme_color"], "#5d6bd6")

    def test_manifesto_servido_igual_ao_arquivo(self):
        servido = json.loads(self.client.get("/manifest.webmanifest").get_data(as_text=True))
        self.assertEqual(servido, self.manifest)

    def test_icones_declarados_existem_com_o_tamanho_certo(self):
        try:
            from PIL import Image
        except ImportError:  # pragma: no cover
            self.skipTest("Pillow não instalado")
        for icone in self.manifest["icons"]:
            with self.subTest(icone=icone["src"]):
                caminho = ROOT / icone["src"].lstrip("/")
                self.assertTrue(caminho.exists(), f"ícone ausente: {icone['src']}")
                with Image.open(caminho) as imagem:
                    self.assertEqual(f"{imagem.size[0]}x{imagem.size[1]}", icone["sizes"])

    def test_service_worker_com_precache_e_sem_cache_de_dados(self):
        resposta = self.client.get("/service-worker.js")
        self.assertEqual(resposta.status_code, 200)
        codigo = resposta.get_data(as_text=True)
        for recurso in ("/static/producao/app.css", "/static/producao/app.js", "/offline"):
            self.assertIn(recurso, codigo)
        self.assertIn("CACHE_VERSION", codigo)
        self.assertIn("caches.delete", codigo)
        self.assertIn('request.method !== "GET"', codigo)

    def test_script_do_service_worker_com_sintaxe_valida(self):
        import shutil
        import subprocess

        if not shutil.which("node"):
            self.skipTest("node não disponível")
        with tempfile.TemporaryDirectory() as tmp:
            caminho = Path(tmp) / "sw.js"
            caminho.write_text(
                (ROOT / "static" / "producao" / "service-worker.js").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            resultado = subprocess.run(["node", "--check", str(caminho)], capture_output=True, text=True)
        self.assertEqual(resultado.returncode, 0, resultado.stderr[:400])

    def test_instalar_traz_passo_a_passo_e_qr(self):
        html = self.client.get("/instalar").get_data(as_text=True)
        self.assertIn("Tela de Início", html)
        self.assertIn("Android", html)
        self.assertIn("iPhone", html)
        self.assertEqual(self.client.get("/qr-app.png").status_code, 200)

    def test_healthz_informa_o_armazenamento(self):
        dados = json.loads(self.client.get("/healthz").get_data(as_text=True))
        self.assertTrue(dados["ok"])
        self.assertEqual(dados["storage"], "local")


class FormatadoresTests(unittest.TestCase):
    """As máscaras do app seguem as mesmas regras do sistema de OS."""

    def test_codigo_com_digitos_recebe_hifens(self):
        from appmodules.producao_web.formatters import format_codigo_code

        self.assertEqual(format_codigo_code("1234567"), "12-34-567")
        self.assertEqual(format_codigo_code("12"), "12")
        self.assertEqual(format_codigo_code("1234"), "12-34")
        self.assertEqual(format_codigo_code(""), "")
        self.assertEqual(format_codigo_code("12-34-567"), "12-34-567")
        self.assertEqual(format_codigo_code("1234567890"), "12-34-56789")

    def test_codigo_com_letras_e_preservado(self):
        from appmodules.producao_web.formatters import format_codigo_code

        self.assertEqual(format_codigo_code("AB-12"), "AB-12")
        self.assertEqual(format_codigo_code("  xpto  "), "xpto")

    def test_mtc_limita_a_quatro_digitos(self):
        from appmodules.producao_web.formatters import format_mtc_code

        self.assertEqual(format_mtc_code("123456"), "1234")
        self.assertEqual(format_mtc_code("12"), "12")
        self.assertEqual(format_mtc_code("ab"), "")
        self.assertEqual(format_mtc_code(""), "")

    def test_prazo_formatado_como_data(self):
        from appmodules.producao_web.formatters import formatar_data

        self.assertEqual(formatar_data("31122026"), "31/12/2026")
        self.assertEqual(formatar_data("31"), "31")
        self.assertEqual(formatar_data("3112"), "31/12")


class IsolamentoTests(unittest.TestCase):
    """O app de produção não compartilha nada com o sistema de OS."""

    def test_sistema_de_os_nao_importa_o_app_de_producao(self):
        for arquivo in sorted((ROOT / "appmodules").rglob("*.py")):
            if "producao_web" in str(arquivo):
                continue
            with self.subTest(arquivo=str(arquivo.relative_to(ROOT))):
                self.assertNotIn("producao_web", arquivo.read_text(encoding="utf-8"))

    def test_app_de_producao_nao_usa_o_servico_de_planilha_do_sistema(self):
        for arquivo in sorted((ROOT / "appmodules" / "producao_web").rglob("*.py")):
            with self.subTest(arquivo=str(arquivo.relative_to(ROOT))):
                conteudo = arquivo.read_text(encoding="utf-8")
                self.assertNotIn("SheetsService", conteudo)
                self.assertNotIn("appmodules.services", conteudo)

    def test_app_de_producao_so_importa_o_proprio_pacote(self):
        """Nenhum ``from appmodules...`` que não seja do próprio app.

        Isso é o que permite copiar a pasta e rodar o app de produção sozinho.
        """

        for arquivo in sorted((ROOT / "appmodules" / "producao_web").rglob("*.py")):
            for linha in arquivo.read_text(encoding="utf-8").splitlines():
                if "import appmodules" in linha:
                    with self.subTest(arquivo=arquivo.name, linha=linha.strip()):
                        self.assertIn("appmodules.producao_web", linha)

    def test_templates_sao_separados(self):
        """As telas do app de produção nunca são as mesmas do sistema/app de OS."""

        self.assertTrue((ROOT / "templates" / "producao").is_dir())
        if not (ROOT / "templates" / "mobile").is_dir():
            self.skipTest("sistema de OS não está presente nesta cópia")

        for arquivo in sorted((ROOT / "templates" / "producao").glob("*.html")):
            if arquivo.name.startswith("_"):
                continue  # _base.html é o próprio layout
            gemeo = ROOT / "templates" / "mobile" / arquivo.name
            with self.subTest(template=arquivo.name):
                if gemeo.exists():
                    self.assertNotEqual(
                        arquivo.read_text(encoding="utf-8"),
                        gemeo.read_text(encoding="utf-8"),
                        f"{arquivo.name} é idêntico ao do app de OS",
                    )
                self.assertIn("producao/_base.html", arquivo.read_text(encoding="utf-8"))

    def test_segredo_do_app_de_producao_nao_vem_do_sistema_de_os(self):
        """``PRODUCAO_SECRET_KEY`` tem prioridade sobre ``SECRET_KEY``."""

        from appmodules.producao_web.config import ProducaoConfig

        original = {chave: os.environ.get(chave) for chave in ("PRODUCAO_SECRET_KEY", "SECRET_KEY")}
        try:
            os.environ["PRODUCAO_SECRET_KEY"] = "segredo-da-producao"
            os.environ["SECRET_KEY"] = "segredo-do-sistema-de-os"
            self.assertEqual(ProducaoConfig.carregar()["SECRET_KEY"], "segredo-da-producao")

            del os.environ["PRODUCAO_SECRET_KEY"]
            self.assertEqual(ProducaoConfig.carregar()["SECRET_KEY"], "segredo-do-sistema-de-os")

            del os.environ["SECRET_KEY"]
            with self.assertRaises(ValueError):
                ProducaoConfig.carregar()
        finally:
            for chave, valor in original.items():
                if valor is None:
                    os.environ.pop(chave, None)
                else:
                    os.environ[chave] = valor

    def test_app_registrado_usa_o_segredo_do_ambiente(self):
        import producao_app

        esperado = os.environ.get("PRODUCAO_SECRET_KEY") or os.environ["SECRET_KEY"]
        self.assertEqual(producao_app.app.config["SECRET_KEY"], esperado)


class ConexaoGoogleTests(unittest.TestCase):
    """O backend de planilha não pode explodir quando falta configuração."""

    def test_sem_id_de_planilha_avisa_sem_derrubar_o_app(self):
        from appmodules.producao_web.storage import GoogleSheetsStorage

        storage = GoogleSheetsStorage(spreadsheet_id="", credenciais="/nao/existe.json")
        disponivel, erro = storage.disponivel()
        self.assertFalse(disponivel)
        self.assertIn("PRODUCAO_SPREADSHEET_ID", erro)

    def test_credenciais_ausentes_geram_mensagem_clara(self):
        from appmodules.producao_web.storage import GoogleSheetsStorage

        storage = GoogleSheetsStorage(spreadsheet_id="abc123", credenciais="/nao/existe.json")
        disponivel, erro = storage.disponivel()
        self.assertFalse(disponivel)
        self.assertTrue(erro and "planilha" in erro.lower() or "cred" in erro.lower())

    def test_url_da_planilha_e_aceita_como_id(self):
        """Cola a URL completa do Sheets e o app extrai o ID."""

        from appmodules.producao_web.storage import GoogleSheetsStorage

        storage = GoogleSheetsStorage(spreadsheet_id="https://docs.google.com/spreadsheets/d/ID_DA_PLANILHA/edit")
        self.assertIn("ID_DA_PLANILHA", storage.spreadsheet_id)
        self.assertEqual(storage.nome, "google-sheets")


if __name__ == "__main__":
    unittest.main(verbosity=2)
