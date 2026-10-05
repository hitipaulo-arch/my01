"""Acesso ao app de produção — login **por setor**, independente do sistema de OS.

Regras:

* quem entra escolhe o setor (ou ``Gestão``) e digita um PIN;
* o PIN de cada setor fica cadastrado pelo gestor na tela **Acessos** (gravado
  criptografado na planilha da produção);
* enquanto não houver nenhum acesso cadastrado, vale o PIN de primeiro acesso da
  gestão vindo da variável ``PRODUCAO_ADMIN_PIN`` — assim o app pode ser aberto
  pela primeira vez sem dado fictício nenhum na planilha;
* cada setor só mexe no status **do próprio setor**; a gestão mexe em tudo.
"""

from __future__ import annotations

import hmac
import time
from functools import wraps
from typing import Any, Callable

from flask import current_app, flash, redirect, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from appmodules.producao_web import setores as fluxo

CHAVE_SESSAO = "producao_usuario"

#: Freio simples contra tentativa e erro de PIN (por processo).
_TENTATIVAS: dict[str, list[float]] = {}
LIMITE_TENTATIVAS = 6
JANELA_TENTATIVAS = 300  # segundos


# ──────────────────────────────────────────────────────────────────────────────
# Sessão
# ──────────────────────────────────────────────────────────────────────────────
def usuario_atual() -> dict[str, Any] | None:
    """Quem está logado no app de produção (``None`` se ninguém)."""

    dados = session.get(CHAVE_SESSAO)
    if not isinstance(dados, dict) or not dados.get("chave"):
        return None
    return dados


def entrar(chave: str, papel: str, nome: str) -> None:
    session.permanent = True
    session[CHAVE_SESSAO] = {"chave": chave, "papel": papel, "nome": nome}


def sair() -> None:
    session.pop(CHAVE_SESSAO, None)


def e_gestao() -> bool:
    usuario = usuario_atual()
    return bool(usuario and usuario.get("papel") == fluxo.PAPEL_GESTAO)


def setor_do_usuario() -> str | None:
    """Nome do setor do usuário logado (``None`` para a gestão)."""

    usuario = usuario_atual()
    if not usuario or usuario.get("papel") != fluxo.PAPEL_SETOR:
        return None
    setor = fluxo.por_chave(str(usuario.get("chave")))
    return setor.nome if setor else None


def pode_alterar_setor(nome_setor: str) -> bool:
    """A gestão altera qualquer setor; o setor altera somente o seu."""

    if e_gestao():
        return True
    return fluxo.por_nome(nome_setor) is not None and setor_do_usuario() == fluxo.por_nome(nome_setor).nome


# ──────────────────────────────────────────────────────────────────────────────
# Decoradores
# ──────────────────────────────────────────────────────────────────────────────
def login_necessario(view: Callable) -> Callable:
    @wraps(view)
    def interno(*args, **kwargs):
        if not usuario_atual():
            return redirect(url_for("producao.login", proximo=request.path))
        return view(*args, **kwargs)

    return interno


def gestao_necessaria(view: Callable) -> Callable:
    @wraps(view)
    def interno(*args, **kwargs):
        if not usuario_atual():
            return redirect(url_for("producao.login", proximo=request.path))
        if not e_gestao():
            flash("Essa área é da gestão.", "warning")
            return redirect(url_for("producao.painel"))
        return view(*args, **kwargs)

    return interno


# ──────────────────────────────────────────────────────────────────────────────
# PIN
# ──────────────────────────────────────────────────────────────────────────────
def gerar_hash(pin: str) -> str:
    return generate_password_hash(str(pin))


def pin_confere(registro: dict[str, Any] | None, pin: str) -> bool:
    """Confere o PIN contra o acesso cadastrado ou, na ausência, contra o env.

    * acesso com PIN cadastrado → compara com o hash da planilha;
    * setor ainda **sem** PIN → ninguém entra (a gestão cadastra o PIN na tela
      *Acessos*);
    * gestão sem PIN cadastrado → vale ``PRODUCAO_ADMIN_PIN``, o que permite o
      primeiro acesso a uma planilha nova sem dado fictício.
    """

    registro = registro or {}
    if str(registro.get("pin_hash") or "").strip():
        return check_password_hash(str(registro["pin_hash"]), str(pin))

    admin_pin = str(current_app.config.get("ADMIN_PIN") or "")
    eh_gestao = str(registro.get("papel") or fluxo.PAPEL_GESTAO) == fluxo.PAPEL_GESTAO
    chave = str(registro.get("chave") or fluxo.GESTAO).casefold()
    if admin_pin and eh_gestao and chave == fluxo.GESTAO:
        return hmac.compare_digest(admin_pin, str(pin))
    return False


def pin_utilizavel(pin: str) -> bool:
    """PIN de celular: 4 a 8 dígitos, sem espaço."""

    texto = str(pin or "").strip()
    return 4 <= len(texto) <= 8 and texto.isdigit()


# ──────────────────────────────────────────────────────────────────────────────
# Freio de tentativas
# ──────────────────────────────────────────────────────────────────────────────
def _chave_tentativa(identificador: str) -> str:
    return f"{identificador}|{request.remote_addr or 'local'}"


def registrar_tentativa(identificador: str) -> None:
    agora = time.time()
    chave = _chave_tentativa(identificador)
    historico = [momento for momento in _TENTATIVAS.get(chave, []) if agora - momento < JANELA_TENTATIVAS]
    historico.append(agora)
    _TENTATIVAS[chave] = historico


def bloqueado(identificador: str) -> bool:
    agora = time.time()
    chave = _chave_tentativa(identificador)
    historico = [momento for momento in _TENTATIVAS.get(chave, []) if agora - momento < JANELA_TENTATIVAS]
    _TENTATIVAS[chave] = historico
    return len(historico) >= LIMITE_TENTATIVAS


def limpar_tentativas(identificador: str) -> None:
    _TENTATIVAS.pop(_chave_tentativa(identificador), None)


def tentativas_restantes(identificador: str) -> int:
    agora = time.time()
    historico = [
        momento
        for momento in _TENTATIVAS.get(_chave_tentativa(identificador), [])
        if agora - momento < JANELA_TENTATIVAS
    ]
    return max(0, LIMITE_TENTATIVAS - len(historico))
