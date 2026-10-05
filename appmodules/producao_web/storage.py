"""Armazenamento do app de produção — planilha Google dedicada.

O app de produção é **independente** do sistema de OS, inclusive no
armazenamento: ele usa a sua própria planilha (``PRODUCAO_SPREADSHEET_ID``),
com as abas criadas automaticamente:

======  ==========================================================================
Aba      Conteúdo
======  ==========================================================================
``OPs``      uma linha por ordem de produção (o produto e seus dados)
``Setores``  uma linha por OP **por setor** — status e data/hora de cada etapa
``Histórico`` cada mudança de status, com quem alterou (auditoria)
``Acessos``  PIN de cada setor/gestão que pode entrar no app
======  ==========================================================================

A mesma interface é servida por dois backends:

* :class:`GoogleSheetsStorage` — produção (planilha própria, mesmas credenciais);
* :class:`LocalStorage` — arquivo JSON local, para desenvolvimento/teste sem
  Google (``PRODUCAO_STORAGE=local``). Começa **vazio**: nada de dado fictício.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping

from appmodules.producao_web import setores as fluxo

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Cabeçalhos / colunas (a ordem define a posição na planilha)
# ──────────────────────────────────────────────────────────────────────────────
OP_HEADERS = [
    "ID",
    "Carimbo de data/hora",
    "Nome do item",
    "Código",
    "Número do projeto MTC",
    "Quantidade",
    "Cliente / OS de origem",
    "Prazo de entrega",
    "Material",
    "Observação",
    "Criado por",
    "Concluída em",
]

SETOR_HEADERS = [
    "OP",
    "Setor",
    "Status",
    "Iniciado em",
    "Concluído em",
    "Última atualização",
    "Atualizado por",
    "Observação",
]

HISTORICO_HEADERS = [
    "OP",
    "Setor",
    "Status anterior",
    "Status novo",
    "Data/hora",
    "Quem alterou",
    "Observação",
]

ACESSO_HEADERS = [
    "Setor / Perfil",
    "Tipo",
    "Nome exibido",
    "PIN (criptografado)",
    "Ativo",
    "Criado em",
]

ABA_OP = "OPs"
ABA_SETORES = "Setores"
ABA_HISTORICO = "Histórico"
ABA_ACESSOS = "Acessos"


def agora() -> str:
    """Data/hora no mesmo formato usado no resto do projeto."""

    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")


def _int(valor: Any, padrao: int = 0) -> int:
    try:
        texto = str(valor).strip().replace(".", "").replace(",", ".")
        return int(float(texto)) if texto else padrao
    except (TypeError, ValueError):
        return padrao


def _texto(valor: Any) -> str:
    return str(valor if valor is not None else "").strip()


# ──────────────────────────────────────────────────────────────────────────────
# Conversão linha <-> dicionário (puro, coberto por teste)
# ──────────────────────────────────────────────────────────────────────────────
def op_para_linha(op: Mapping[str, Any]) -> list[str]:
    return [
        _texto(op.get("id")),
        _texto(op.get("criado_em")),
        _texto(op.get("nome_item")),
        _texto(op.get("codigo")),
        _texto(op.get("mtc")),
        str(_int(op.get("quantidade"), 0)),
        _texto(op.get("cliente")),
        _texto(op.get("prazo")),
        _texto(op.get("material")),
        _texto(op.get("observacao")),
        _texto(op.get("criado_por")),
        _texto(op.get("concluida_em")),
    ]


def linha_para_op(linha: Iterable[Any]) -> dict[str, Any]:
    valores = list(linha) + [""] * (len(OP_HEADERS) - len(list(linha)))
    return {
        "id": _texto(valores[0]),
        "criado_em": _texto(valores[1]),
        "nome_item": _texto(valores[2]),
        "codigo": _texto(valores[3]),
        "mtc": _texto(valores[4]),
        "quantidade": _int(valores[5], 0),
        "cliente": _texto(valores[6]),
        "prazo": _texto(valores[7]),
        "material": _texto(valores[8]),
        "observacao": _texto(valores[9]),
        "criado_por": _texto(valores[10]),
        "concluida_em": _texto(valores[11]),
    }


def setor_para_linha(registro: Mapping[str, Any]) -> list[str]:
    return [
        _texto(registro.get("op_id")),
        _texto(registro.get("setor")),
        _texto(registro.get("status")) or fluxo.NAO_INICIADO,
        _texto(registro.get("iniciado_em")),
        _texto(registro.get("concluido_em")),
        _texto(registro.get("atualizado_em")),
        _texto(registro.get("atualizado_por")),
        _texto(registro.get("observacao")),
    ]


def linha_para_setor(linha: Iterable[Any]) -> dict[str, Any]:
    valores = list(linha) + [""] * (len(SETOR_HEADERS) - len(list(linha)))
    return {
        "op_id": _texto(valores[0]),
        "setor": _texto(valores[1]),
        "status": _texto(valores[2]) or fluxo.NAO_INICIADO,
        "iniciado_em": _texto(valores[3]),
        "concluido_em": _texto(valores[4]),
        "atualizado_em": _texto(valores[5]),
        "atualizado_por": _texto(valores[6]),
        "observacao": _texto(valores[7]),
    }


def historico_para_linha(registro: Mapping[str, Any]) -> list[str]:
    return [
        _texto(registro.get("op_id")),
        _texto(registro.get("setor")),
        _texto(registro.get("status_anterior")),
        _texto(registro.get("status_novo")),
        _texto(registro.get("data_hora")),
        _texto(registro.get("quem")),
        _texto(registro.get("observacao")),
    ]


def linha_para_historico(linha: Iterable[Any]) -> dict[str, Any]:
    valores = list(linha) + [""] * (len(HISTORICO_HEADERS) - len(list(linha)))
    return {
        "op_id": _texto(valores[0]),
        "setor": _texto(valores[1]),
        "status_anterior": _texto(valores[2]),
        "status_novo": _texto(valores[3]),
        "data_hora": _texto(valores[4]),
        "quem": _texto(valores[5]),
        "observacao": _texto(valores[6]),
    }


def acesso_para_linha(registro: Mapping[str, Any]) -> list[str]:
    return [
        _texto(registro.get("chave")),
        _texto(registro.get("papel")) or fluxo.PAPEL_SETOR,
        _texto(registro.get("nome")),
        _texto(registro.get("pin_hash")),
        "sim" if registro.get("ativo", True) else "não",
        _texto(registro.get("criado_em")),
    ]


def linha_para_acesso(linha: Iterable[Any]) -> dict[str, Any]:
    valores = list(linha) + [""] * (len(ACESSO_HEADERS) - len(list(linha)))
    return {
        "chave": _texto(valores[0]),
        "papel": _texto(valores[1]) or fluxo.PAPEL_SETOR,
        "nome": _texto(valores[2]),
        "pin_hash": _texto(valores[3]),
        "ativo": _texto(valores[4]).casefold() not in ("não", "nao", "false", "0"),
        "criado_em": _texto(valores[5]),
    }


def proximo_id(ops: Iterable[Mapping[str, Any]]) -> str:
    """Gera o próximo identificador sequencial (``OP-0001``, ``OP-0002``…)."""

    maior = 0
    for op in ops:
        texto = _texto(op.get("id"))
        if texto.upper().startswith("OP-"):
            sufixo = texto[3:]
            if sufixo.isdigit():
                maior = max(maior, int(sufixo))
    return f"OP-{maior + 1:04d}"


# ──────────────────────────────────────────────────────────────────────────────
# Interface
# ──────────────────────────────────────────────────────────────────────────────
class ProducaoStorage(ABC):
    """Operações que o app precisa — independente de onde os dados moram."""

    nome = "storage"

    # leitura
    @abstractmethod
    def listar_ops(self) -> list[dict[str, Any]]: ...

    @abstractmethod
    def listar_setores(self) -> list[dict[str, Any]]: ...

    def obter_op(self, op_id: str) -> dict[str, Any] | None:
        alvo = _texto(op_id)
        for op in self.listar_ops():
            if op["id"] == alvo:
                return op
        return None

    def setores_da_op(self, op_id: str) -> list[dict[str, Any]]:
        alvo = _texto(op_id)
        return [linha for linha in self.listar_setores() if linha["op_id"] == alvo]

    def listar_historico(self, op_id: str | None = None) -> list[dict[str, Any]]:
        return []

    def listar_acessos(self) -> list[dict[str, Any]]:
        return []

    def obter_acesso(self, chave: str) -> dict[str, Any] | None:
        alvo = _texto(chave).casefold()
        for acesso in self.listar_acessos():
            if _texto(acesso.get("chave")).casefold() == alvo:
                return acesso
        return None

    def disponivel(self) -> tuple[bool, str | None]:
        """Diz se o armazenamento está acessível (para avisar na tela)."""

        return True, None

    # escrita
    @abstractmethod
    def criar_op(self, dados: Mapping[str, Any], criador: str) -> dict[str, Any]: ...

    @abstractmethod
    def atualizar_op(self, op_id: str, dados: Mapping[str, Any]) -> bool: ...

    @abstractmethod
    def excluir_op(self, op_id: str) -> bool: ...

    @abstractmethod
    def atualizar_status_setor(
        self,
        op_id: str,
        setor: str,
        status: str,
        quem: str,
        observacao: str = "",
    ) -> bool: ...

    def salvar_acesso(
        self,
        chave: str,
        papel: str,
        nome: str,
        pin_hash: str,
        ativo: bool = True,
    ) -> bool:
        raise NotImplementedError

    # ── fluxo de setores: OPs antigas quando o fluxo ganha setor novo ────────
    def _ops_cru(self) -> list[dict[str, Any]]:
        """Leitura sem efeitos colaterais (para conferir o que falta)."""

        return self.listar_ops()

    def _setores_cru(self) -> list[dict[str, Any]]:
        """Leitura sem efeitos colaterais (para conferir o que falta)."""

        return self.listar_setores()

    def setores_faltantes(self) -> list[dict[str, str]]:
        """OPs sem linha para algum setor do fluxo atual.

        Acontece quando o fluxo ganha um setor depois que já existiam OPs. Nesse
        caso a OP aparece com o setor novo como ``Não iniciado`` — e, se já
        estava concluída, voltaria a "Em andamento" indevidamente. Por isso as
        linhas novas de uma OP concluída nascem como ``Não se aplica``.
        """

        existentes: dict[str, set[str]] = {}
        for linha in self._setores_cru():
            existentes.setdefault(str(linha.get("op_id", "")), set()).add(
                str(linha.get("setor", ""))
            )

        faltantes: list[dict[str, str]] = []
        for op in self._ops_cru():
            atuais = existentes.get(op["id"], set())
            status_padrao = fluxo.NAO_SE_APLICA if op.get("concluida_em") else fluxo.NAO_INICIADO
            for setor in fluxo.SETORES:
                if setor.nome not in atuais:
                    faltantes.append(
                        {"op_id": op["id"], "setor": setor.nome, "status": status_padrao}
                    )
        return faltantes

    def garantir_setores(self) -> dict[str, Any]:
        """Cria as linhas de setor que faltam (planilha que já tinha OPs).

        Não cria dado fictício: a OP ganha apenas as etapas que o app passou a
        acompanhar, marcadas como ``Não iniciado`` (ou ``Não se aplica`` quando a
        OP já estava concluída — para não reabrir trabalho antigo).
        """

        faltantes = self.setores_faltantes()
        if not faltantes:
            return {"linhas_criadas": 0, "ops_afetadas": 0, "detalhes": []}

        gravadas = self.criar_linhas_setor(faltantes)
        afetadas = {linha["op_id"] for linha in faltantes}
        logger.info(
            "[produção] Fluxo novo: %s linha(s) de setor criadas em %s OP(s)",
            gravadas,
            len(afetadas),
        )
        return {
            "linhas_criadas": gravadas,
            "ops_afetadas": len(afetadas),
            "detalhes": faltantes,
        }

    def criar_linhas_setor(self, linhas: Iterable[Mapping[str, Any]]) -> int:
        """Grava linhas de setor novas. Cada backend implementa do seu jeito."""

        raise NotImplementedError

    # ── conveniências usadas pelas telas ─────────────────────────────────────
    def ops_com_fluxo(self) -> list[dict[str, Any]]:
        """OPs com status calculado, progresso, setor atual e setores detalhados."""

        por_op: dict[str, list[dict[str, Any]]] = {}
        for linha in self.listar_setores():
            por_op.setdefault(linha["op_id"], []).append(linha)

        resultado: list[dict[str, Any]] = []
        for op in self.listar_ops():
            registros = por_op.get(op["id"], [])
            status_por_setor = fluxo.resumir_setores(registros)
            item = dict(op)
            item["status_geral"] = fluxo.status_da_op(status_por_setor)
            item["progresso"] = fluxo.progresso(status_por_setor)
            item["setor_atual"] = fluxo.proximo_setor(status_por_setor)
            item["setores"] = [
                {**detalhe, **dados_por_nome(setores=registros, nome=detalhe["nome"])}
                for detalhe in fluxo.setores_em_ordem(status_por_setor)
            ]
            resultado.append(item)
        resultado.sort(key=lambda item: item.get("criado_em", ""), reverse=True)
        return resultado


def dados_por_nome(setores: Iterable[Mapping[str, Any]], nome: str) -> dict[str, Any]:
    """Dados de data/hora e responsável de um setor específico."""

    for registro in setores:
        if _texto(registro.get("setor")).casefold() == nome.casefold():
            return {
                "iniciado_em": _texto(registro.get("iniciado_em")),
                "concluido_em": _texto(registro.get("concluido_em")),
                "atualizado_em": _texto(registro.get("atualizado_em")),
                "atualizado_por": _texto(registro.get("atualizado_por")),
                "observacao_setor": _texto(registro.get("observacao")),
            }
    return {
        "iniciado_em": "",
        "concluido_em": "",
        "atualizado_em": "",
        "atualizado_por": "",
        "observacao_setor": "",
    }


# ──────────────────────────────────────────────────────────────────────────────
# Backend local (JSON) — desenvolvimento/teste sem Google Sheets
# ──────────────────────────────────────────────────────────────────────────────
class LocalStorage(ProducaoStorage):
    """Guarda tudo em um arquivo JSON (começa vazio, sem dados de exemplo)."""

    nome = "local"

    def __init__(self, caminho: str | Path):
        self.caminho = Path(caminho)
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        self._trava = threading.RLock()

    # ── infraestrutura ──────────────────────────────────────────────────────
    def _vazio(self) -> dict[str, list]:
        return {"ops": [], "setores": [], "historico": [], "acessos": []}

    def _ler(self) -> dict[str, list]:
        with self._trava:
            if not self.caminho.exists():
                return self._vazio()
            try:
                dados = json.loads(self.caminho.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as erro:
                logger.error("Banco local ilegível (%s): %s", self.caminho, erro)
                return self._vazio()
            base = self._vazio()
            for chave in base:
                if isinstance(dados.get(chave), list):
                    base[chave] = dados[chave]
            return base

    def _escrever(self, dados: Mapping[str, list]) -> None:
        with self._trava:
            temporario = self.caminho.with_suffix(".tmp")
            temporario.write_text(
                json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            os.replace(temporario, self.caminho)

    # ── leitura ─────────────────────────────────────────────────────────────
    def _garantir_setores_local(self) -> None:
        """No banco local a conferência é barata: completa sozinho na leitura."""

        with self._trava:
            base = self._ler()
            existentes: dict[str, set[str]] = {}
            for linha in base["setores"]:
                existentes.setdefault(str(linha.get("op_id", "")), set()).add(
                    str(linha.get("setor", ""))
                )
            criadas = 0
            for op in base["ops"]:
                atuais = existentes.get(op["id"], set())
                status_padrao = (
                    fluxo.NAO_SE_APLICA if op.get("concluida_em") else fluxo.NAO_INICIADO
                )
                for setor in fluxo.SETORES:
                    if setor.nome in atuais:
                        continue
                    base["setores"].append(
                        {
                            "op_id": op["id"],
                            "setor": setor.nome,
                            "status": status_padrao,
                            "iniciado_em": "",
                            "concluido_em": "",
                            "atualizado_em": "",
                            "atualizado_por": "",
                            "observacao": "",
                        }
                    )
                    criadas += 1
            if criadas:
                self._escrever(base)
                logger.info("[produção] Banco local completado com %s setor(es)", criadas)

    def listar_ops(self) -> list[dict[str, Any]]:
        self._garantir_setores_local()
        return [dict(op) for op in self._ler()["ops"]]

    def listar_setores(self) -> list[dict[str, Any]]:
        self._garantir_setores_local()
        return [dict(linha) for linha in self._ler()["setores"]]

    def _ops_cru(self) -> list[dict[str, Any]]:
        return [dict(op) for op in self._ler()["ops"]]

    def _setores_cru(self) -> list[dict[str, Any]]:
        return [dict(linha) for linha in self._ler()["setores"]]

    def criar_linhas_setor(self, linhas: Iterable[Mapping[str, Any]]) -> int:
        criadas = 0
        with self._trava:
            base = self._ler()
            existentes = {
                (str(item.get("op_id", "")), str(item.get("setor", "")))
                for item in base["setores"]
            }
            for linha in linhas:
                chave = (_texto(linha.get("op_id")), _texto(linha.get("setor")))
                if chave in existentes:
                    continue  # idempotente: nunca duplica setor de uma OP
                existentes.add(chave)
                base["setores"].append(
                    {
                        "op_id": _texto(linha.get("op_id")),
                        "setor": _texto(linha.get("setor")),
                        "status": _texto(linha.get("status")) or fluxo.NAO_INICIADO,
                        "iniciado_em": "",
                        "concluido_em": "",
                        "atualizado_em": "",
                        "atualizado_por": "",
                        "observacao": "",
                    }
                )
                criadas += 1
            if criadas:
                self._escrever(base)
        return criadas

    def listar_historico(self, op_id: str | None = None) -> list[dict[str, Any]]:
        registros = [dict(linha) for linha in self._ler()["historico"]]
        if op_id:
            registros = [linha for linha in registros if linha["op_id"] == _texto(op_id)]
        return registros

    def listar_acessos(self) -> list[dict[str, Any]]:
        return [dict(acesso) for acesso in self._ler()["acessos"]]

    # ── escrita ─────────────────────────────────────────────────────────────
    def _registrar_historico(
        self,
        dados: dict[str, list],
        op_id: str,
        setor: str,
        anterior: str,
        novo: str,
        quem: str,
        observacao: str = "",
    ) -> None:
        dados["historico"].append(
            {
                "op_id": op_id,
                "setor": setor,
                "status_anterior": anterior,
                "status_novo": novo,
                "data_hora": agora(),
                "quem": quem,
                "observacao": observacao,
            }
        )

    def criar_op(self, dados: Mapping[str, Any], criador: str) -> dict[str, Any]:
        with self._trava:
            base = self._ler()
            op = {
                "id": proximo_id(base["ops"]),
                "criado_em": agora(),
                "nome_item": _texto(dados.get("nome_item")),
                "codigo": _texto(dados.get("codigo")),
                "mtc": _texto(dados.get("mtc")),
                "quantidade": _int(dados.get("quantidade"), 0),
                "cliente": _texto(dados.get("cliente")),
                "prazo": _texto(dados.get("prazo")),
                "material": _texto(dados.get("material")),
                "observacao": _texto(dados.get("observacao")),
                "criado_por": criador,
                "concluida_em": "",
            }
            base["ops"].append(op)
            for setor in fluxo.SETORES:
                base["setores"].append(
                    {
                        "op_id": op["id"],
                        "setor": setor.nome,
                        "status": fluxo.NAO_INICIADO,
                        "iniciado_em": "",
                        "concluido_em": "",
                        "atualizado_em": "",
                        "atualizado_por": "",
                        "observacao": "",
                    }
                )
            self._escrever(base)
            return op

    def atualizar_op(self, op_id: str, dados: Mapping[str, Any]) -> bool:
        with self._trava:
            base = self._ler()
            for op in base["ops"]:
                if op["id"] != _texto(op_id):
                    continue
                for campo in (
                    "nome_item",
                    "codigo",
                    "mtc",
                    "cliente",
                    "prazo",
                    "material",
                    "observacao",
                ):
                    if campo in dados:
                        op[campo] = _texto(dados.get(campo))
                if "quantidade" in dados:
                    op["quantidade"] = _int(dados.get("quantidade"), 0)
                self._escrever(base)
                return True
            return False

    def excluir_op(self, op_id: str) -> bool:
        with self._trava:
            base = self._ler()
            alvo = _texto(op_id)
            antes = len(base["ops"])
            base["ops"] = [op for op in base["ops"] if op["id"] != alvo]
            if len(base["ops"]) == antes:
                return False
            base["setores"] = [linha for linha in base["setores"] if linha["op_id"] != alvo]
            base["historico"] = [linha for linha in base["historico"] if linha["op_id"] != alvo]
            self._escrever(base)
            return True

    def atualizar_status_setor(
        self,
        op_id: str,
        setor: str,
        status: str,
        quem: str,
        observacao: str = "",
    ) -> bool:
        status = fluxo.normalizar_status(status)
        alvo_setor = fluxo.por_nome(setor)
        if not alvo_setor:
            logger.warning("Setor desconhecido: %s", setor)
            return False

        with self._trava:
            base = self._ler()
            alvo_op = _texto(op_id)
            if not any(op["id"] == alvo_op for op in base["ops"]):
                return False

            momento = agora()
            for linha in base["setores"]:
                if linha["op_id"] != alvo_op or linha["setor"] != alvo_setor.nome:
                    continue

                anterior = fluxo.normalizar_status(linha.get("status", ""))
                linha["status"] = status
                linha["atualizado_em"] = momento
                linha["atualizado_por"] = _texto(quem)
                if observacao:
                    linha["observacao"] = _texto(observacao)
                if status == fluxo.EM_ANDAMENTO and not linha.get("iniciado_em"):
                    linha["iniciado_em"] = momento
                if status == fluxo.CONCLUIDO:
                    linha["iniciado_em"] = linha.get("iniciado_em") or momento
                    linha["concluido_em"] = momento
                if status in (fluxo.NAO_INICIADO, fluxo.NAO_SE_APLICA):
                    linha["iniciado_em"] = ""
                    linha["concluido_em"] = ""

                if anterior != status:
                    self._registrar_historico(
                        base, alvo_op, alvo_setor.nome, anterior, status, quem, observacao
                    )
                break
            else:
                return False

            # Marca/limpa a data de conclusão da OP inteira.
            resumo = fluxo.resumir_setores(
                [linha for linha in base["setores"] if linha["op_id"] == alvo_op]
            )
            concluida = fluxo.status_da_op(resumo) == fluxo.OP_CONCLUIDA
            for op in base["ops"]:
                if op["id"] == alvo_op:
                    op["concluida_em"] = momento if concluida else ""
                    break

            self._escrever(base)
            return True

    def salvar_acesso(
        self,
        chave: str,
        papel: str,
        nome: str,
        pin_hash: str,
        ativo: bool = True,
    ) -> bool:
        with self._trava:
            base = self._ler()
            alvo = _texto(chave).casefold()
            for acesso in base["acessos"]:
                if _texto(acesso.get("chave")).casefold() == alvo:
                    acesso.update(
                        {
                            "papel": papel,
                            "nome": nome,
                            "pin_hash": pin_hash,
                            "ativo": ativo,
                        }
                    )
                    self._escrever(base)
                    return True
            base["acessos"].append(
                {
                    "chave": alvo,
                    "papel": papel,
                    "nome": nome,
                    "pin_hash": pin_hash,
                    "ativo": ativo,
                    "criado_em": agora(),
                }
            )
            self._escrever(base)
            return True


# ──────────────────────────────────────────────────────────────────────────────
# Backend Google Sheets (planilha dedicada)
# ──────────────────────────────────────────────────────────────────────────────
class GoogleSheetsStorage(ProducaoStorage):
    """Planilha própria do app de produção, com as abas criadas sozinha."""

    nome = "google-sheets"

    def __init__(
        self,
        spreadsheet_id: str,
        credenciais: str = "credentials.json",
        escopos: Iterable[str] | None = None,
    ):
        self.spreadsheet_id = spreadsheet_id
        self.credenciais = credenciais
        self.escopos = list(
            escopos
            or [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive.file",
            ]
        )
        self._planilha = None
        self._erro: str | None = None
        self._abas: dict[str, Any] = {}

    # ── conexão ─────────────────────────────────────────────────────────────
    def _conectar(self):
        if self._abas:
            return
        if not self.spreadsheet_id:
            raise RuntimeError(
                "PRODUCAO_SPREADSHEET_ID não configurado (ID ou URL da planilha da produção)."
            )
        import gspread  # importado aqui para o app subir mesmo sem a lib instalada

        cliente = gspread.service_account(filename=self.credenciais, scopes=self.escopos)
        alvo = self.spreadsheet_id.strip()
        if "/" in alvo:  # aceita a URL completa da planilha
            alvo = alvo.split("/d/")[1].split("/")[0] if "/d/" in alvo else alvo
        self._planilha = cliente.open_by_key(alvo)

        for nome, cabecalho in (
            (ABA_OP, OP_HEADERS),
            (ABA_SETORES, SETOR_HEADERS),
            (ABA_HISTORICO, HISTORICO_HEADERS),
            (ABA_ACESSOS, ACESSO_HEADERS),
        ):
            self._abas[nome] = self._garantir_aba(nome, cabecalho)

    def _garantir_aba(self, nome: str, cabecalho: list[str]):
        try:
            aba = self._planilha.worksheet(nome)
        except Exception:
            aba = self._planilha.add_worksheet(title=nome, rows=1000, cols=len(cabecalho))
            aba.append_row(cabecalho)
            logger.info("Aba '%s' criada na planilha da produção", nome)
            return aba

        primeira = aba.row_values(1)
        if [c.strip() for c in primeira][: len(cabecalho)] != cabecalho:
            if not primeira:
                aba.append_row(cabecalho)
            else:
                logger.warning(
                    "Cabeçalho da aba '%s' difere do esperado do app de produção.", nome
                )
        return aba

    def disponivel(self) -> tuple[bool, str | None]:
        try:
            self._conectar()
            return True, None
        except FileNotFoundError:
            self._erro = f"Credenciais não encontradas ({self.credenciais})."
        except Exception as erro:  # credenciais inválidas, planilha sem permissão…
            self._erro = f"Não foi possível abrir a planilha da produção: {erro}"
        logger.error("[produção] %s", self._erro)
        return False, self._erro

    def _linhas(self, aba: str) -> list[list[str]]:
        self._conectar()
        try:
            return self._abas[aba].get_all_values()
        except Exception as erro:
            logger.error("Falha ao ler a aba %s: %s", aba, erro)
            raise

    # ── leitura ─────────────────────────────────────────────────────────────
    def listar_ops(self) -> list[dict[str, Any]]:
        linhas = self._linhas(ABA_OP)
        return [linha_para_op(linha) for linha in linhas[1:] if any(_texto(c) for c in linha)]

    def listar_setores(self) -> list[dict[str, Any]]:
        linhas = self._linhas(ABA_SETORES)
        return [linha_para_setor(linha) for linha in linhas[1:] if any(_texto(c) for c in linha)]

    def listar_historico(self, op_id: str | None = None) -> list[dict[str, Any]]:
        linhas = self._linhas(ABA_HISTORICO)
        registros = [linha_para_historico(linha) for linha in linhas[1:] if any(_texto(c) for c in linha)]
        if op_id:
            registros = [linha for linha in registros if linha["op_id"] == _texto(op_id)]
        return registros

    def listar_acessos(self) -> list[dict[str, Any]]:
        linhas = self._linhas(ABA_ACESSOS)
        return [linha_para_acesso(linha) for linha in linhas[1:] if any(_texto(c) for c in linha)]

    # ── escrita ─────────────────────────────────────────────────────────────
    def criar_op(self, dados: Mapping[str, Any], criador: str) -> dict[str, Any]:
        self._conectar()
        op = {
            "id": proximo_id(self.listar_ops()),
            "criado_em": agora(),
            "nome_item": _texto(dados.get("nome_item")),
            "codigo": _texto(dados.get("codigo")),
            "mtc": _texto(dados.get("mtc")),
            "quantidade": _int(dados.get("quantidade"), 0),
            "cliente": _texto(dados.get("cliente")),
            "prazo": _texto(dados.get("prazo")),
            "material": _texto(dados.get("material")),
            "observacao": _texto(dados.get("observacao")),
            "criado_por": criador,
            "concluida_em": "",
        }
        self._abas[ABA_OP].append_row(op_para_linha(op))
        self._abas[ABA_SETORES].append_rows(
            [
                setor_para_linha({"op_id": op["id"], "setor": setor.nome, "status": fluxo.NAO_INICIADO})
                for setor in fluxo.SETORES
            ]
        )
        return op

    def _buscar_linha(self, aba, valor: str, coluna: int = 1) -> int | None:
        """Número da linha (1-based) onde ``coluna`` vale ``valor``."""

        colunas = aba.col_values(coluna)
        for indice, conteudo in enumerate(colunas, start=1):
            if _texto(conteudo) == valor:
                return indice
        return None

    def atualizar_op(self, op_id: str, dados: Mapping[str, Any]) -> bool:
        linha = self._buscar_linha(self._abas[ABA_OP], _texto(op_id))
        if not linha:
            return False
        atual = linha_para_op(self._abas[ABA_OP].row_values(linha))
        for campo in (
            "nome_item",
            "codigo",
            "mtc",
            "cliente",
            "prazo",
            "material",
            "observacao",
        ):
            if campo in dados:
                atual[campo] = _texto(dados.get(campo))
        if "quantidade" in dados:
            atual["quantidade"] = _int(dados.get("quantidade"), 0)
        self._abas[ABA_OP].update(f"A{linha}", [op_para_linha(atual)])
        return True

    def excluir_op(self, op_id: str) -> bool:
        alvo = _texto(op_id)
        linha = self._buscar_linha(self._abas[ABA_OP], alvo)
        if not linha:
            return False
        # Remove de trás para frente para não bagunçar os índices.
        for aba, coluna in ((ABA_HISTORICO, 1), (ABA_SETORES, 1), (ABA_OP, 1)):
            linhas = self._abas[aba].get_all_values()
            indices = [
                indice
                for indice, valores in enumerate(linhas, start=1)
                if indice > 1 and _texto(valores[0] if valores else "") == alvo
            ]
            for indice in reversed(indices):
                self._abas[aba].delete_rows(indice)
        return True

    def atualizar_status_setor(
        self,
        op_id: str,
        setor: str,
        status: str,
        quem: str,
        observacao: str = "",
    ) -> bool:
        alvo_setor = fluxo.por_nome(setor)
        if not alvo_setor:
            return False
        status = fluxo.normalizar_status(status)

        linhas = self._abas[ABA_SETORES].get_all_values()
        alvo_op = _texto(op_id)
        for indice, valores in enumerate(linhas, start=1):
            if indice == 1:
                continue
            registro = linha_para_setor(valores)
            if registro["op_id"] != alvo_op or registro["setor"] != alvo_setor.nome:
                continue

            anterior = fluxo.normalizar_status(registro["status"])
            momento = agora()
            registro["status"] = status
            registro["atualizado_em"] = momento
            registro["atualizado_por"] = _texto(quem)
            if observacao:
                registro["observacao"] = _texto(observacao)
            if status == fluxo.EM_ANDAMENTO and not registro["iniciado_em"]:
                registro["iniciado_em"] = momento
            if status == fluxo.CONCLUIDO:
                registro["iniciado_em"] = registro["iniciado_em"] or momento
                registro["concluido_em"] = momento
            if status in (fluxo.NAO_INICIADO, fluxo.NAO_SE_APLICA):
                registro["iniciado_em"] = ""
                registro["concluido_em"] = ""

            self._abas[ABA_SETORES].update(
                f"A{indice}", [setor_para_linha(registro)]
            )

            if anterior != status:
                self._abas[ABA_HISTORICO].append_row(
                    historico_para_linha(
                        {
                            "op_id": alvo_op,
                            "setor": alvo_setor.nome,
                            "status_anterior": anterior,
                            "status_novo": status,
                            "data_hora": momento,
                            "quem": quem,
                            "observacao": observacao,
                        }
                    )
                )

            self._sincronizar_conclusao(alvo_op, momento)
            return True
        return False

    def criar_linhas_setor(self, linhas: Iterable[Mapping[str, Any]]) -> int:
        self._conectar()
        registros = [
            {
                "op_id": _texto(linha.get("op_id")),
                "setor": _texto(linha.get("setor")),
                "status": _texto(linha.get("status")) or fluxo.NAO_INICIADO,
            }
            for linha in linhas
        ]
        if not registros:
            return 0
        self._abas[ABA_SETORES].append_rows([setor_para_linha(r) for r in registros])
        return len(registros)

    def _sincronizar_conclusao(self, op_id: str, momento: str) -> None:
        """Escreve/limpa a data de conclusão da OP conforme os setores."""

        registros = [linha for linha in self.listar_setores() if linha["op_id"] == op_id]
        concluida = fluxo.status_da_op(fluxo.resumir_setores(registros)) == fluxo.OP_CONCLUIDA
        linha = self._buscar_linha(self._abas[ABA_OP], op_id)
        if not linha:
            return
        atual = linha_para_op(self._abas[ABA_OP].row_values(linha))
        atual["concluida_em"] = momento if concluida else ""
        self._abas[ABA_OP].update(f"A{linha}", [op_para_linha(atual)])

    def salvar_acesso(
        self,
        chave: str,
        papel: str,
        nome: str,
        pin_hash: str,
        ativo: bool = True,
    ) -> bool:
        alvo = _texto(chave).casefold()
        registro = {
            "chave": alvo,
            "papel": papel,
            "nome": nome,
            "pin_hash": pin_hash,
            "ativo": ativo,
            "criado_em": agora(),
        }
        linha = self._buscar_linha(self._abas[ABA_ACESSOS], alvo)
        if linha:
            existente = linha_para_acesso(self._abas[ABA_ACESSOS].row_values(linha))
            registro["criado_em"] = existente.get("criado_em") or registro["criado_em"]
            self._abas[ABA_ACESSOS].update(f"A{linha}", [acesso_para_linha(registro)])
            return True
        self._abas[ABA_ACESSOS].append_row(acesso_para_linha(registro))
        return True


def criar_storage(config: Mapping[str, Any]) -> ProducaoStorage:
    """Escolhe o backend conforme a configuração do app."""

    tipo = str(config.get("STORAGE") or "sheets").strip().lower()
    if tipo in ("local", "json", "arquivo"):
        return LocalStorage(config["LOCAL_DB_PATH"])
    return GoogleSheetsStorage(
        spreadsheet_id=str(config.get("SPREADSHEET_ID") or ""),
        credenciais=str(config.get("CREDENCIAIS") or "credentials.json"),
        escopos=config.get("ESCOPOS"),
    )
