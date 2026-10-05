"""Fluxo de setores do app de produção.

O app dedicado acompanha cada ordem de produção (OP) pelos setores da fábrica.
Cada setor tem seu próprio status, com data/hora — assim é possível saber em que
ponto a peça está e quando cada etapa começou e terminou.

Para mudar o fluxo (acrescentar, renomear ou reordenar setores) basta editar a
tupla ``SETORES`` abaixo: o armazenamento, as telas, o painel e os testes leem
tudo daqui, e as linhas de setor são criadas automaticamente ao abrir uma OP.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

# ──────────────────────────────────────────────────────────────────────────────
# Status possíveis de cada setor
# ──────────────────────────────────────────────────────────────────────────────
NAO_INICIADO = "Não iniciado"
EM_ANDAMENTO = "Em andamento"
CONCLUIDO = "Concluído"

STATUS_SETOR: tuple[str, ...] = (NAO_INICIADO, EM_ANDAMENTO, CONCLUIDO)

#: Status calculado da OP inteira (não é digitado: vem dos setores)
OP_AGUARDANDO = "Aguardando"
OP_EM_ANDAMENTO = "Em andamento"
OP_CONCLUIDA = "Concluída"


@dataclass(frozen=True)
class Setor:
    """Um setor do fluxo de fabricação."""

    chave: str
    nome: str
    icone: str


#: Ordem real do fluxo na fábrica — usada para saber "próximo setor".
SETORES: tuple[Setor, ...] = (
    Setor("corte", "Corte", "🪚"),
    Setor("dobra", "Dobra", "📐"),
    Setor("montagem_primaria", "Montagem Primária", "🔧"),
    Setor("solda", "Solda", "🔥"),
    Setor("acabamento", "Acabamento", "🎨"),
    Setor("silicone_limpeza", "Silicone e Limpeza", "🧴"),
    Setor("embalagem", "Embalagem", "📦"),
)

#: Perfil de quem entra no app
GESTAO = "gestao"
GESTAO_NOME = "Gestão"

PAPEL_GESTAO = "gestao"
PAPEL_SETOR = "setor"


def comparavel(texto: str) -> str:
    """Texto sem acento e em minúsculas — para comparar nomes digitados à mão."""

    limpo = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode()
    return " ".join(limpo.split()).casefold()


def nomes() -> tuple[str, ...]:
    """Nomes dos setores na ordem do fluxo."""

    return tuple(setor.nome for setor in SETORES)


def por_chave(chave: str) -> Setor | None:
    """Busca um setor pela chave (``solda``, ``montagem_primaria``…)."""

    alvo = str(chave or "").strip().lower()
    for setor in SETORES:
        if setor.chave == alvo:
            return setor
    return None


def por_nome(nome: str) -> Setor | None:
    """Busca um setor pelo nome, ignorando acento e caixa.

    A coluna ``Setor`` da planilha pode ser editada à mão: ``silicone e limpeza``,
    ``Montagem primaria`` e ``SILICONE E LIMPEZA`` precisam cair no mesmo setor.
    """

    alvo = comparavel(nome)
    for setor in SETORES:
        if comparavel(setor.nome) == alvo:
            return setor
    return None


def normalizar_status(valor: str) -> str:
    """Converte qualquer variação em um dos três status válidos."""

    alvo = comparavel(valor)
    for status in STATUS_SETOR:
        if comparavel(status) == alvo:
            return status
    if alvo in ("concluida", "concluído", "finalizado", "ok", "pronto"):
        return CONCLUIDO
    if alvo in ("andamento", "iniciado", "fazendo", "em produção"):
        return EM_ANDAMENTO
    return NAO_INICIADO


def e_status_valido(valor: str) -> bool:
    """Confere o status exatamente como o app envia (``STATUS_SETOR``)."""

    return str(valor or "").strip() in STATUS_SETOR


def setores_em_ordem(status_por_setor: Mapping[str, str]) -> list[dict]:
    """Junta a ordem do fluxo com os status informados (para as telas)."""

    linhas: list[dict] = []
    for indice, setor in enumerate(SETORES, start=1):
        status = normalizar_status(status_por_setor.get(setor.nome, NAO_INICIADO))
        linhas.append(
            {
                "ordem": indice,
                "chave": setor.chave,
                "nome": setor.nome,
                "icone": setor.icone,
                "status": status,
                "concluido": status == CONCLUIDO,
            }
        )
    return linhas


def proximo_setor(status_por_setor: Mapping[str, str]) -> dict | None:
    """Primeiro setor ainda não concluído — onde a peça está agora."""

    for setor in SETORES:
        status = normalizar_status(status_por_setor.get(setor.nome, NAO_INICIADO))
        if status != CONCLUIDO:
            return {"chave": setor.chave, "nome": setor.nome, "icone": setor.icone, "status": status}
    return None


def status_da_op(status_por_setor: Mapping[str, str]) -> str:
    """Status geral da OP, calculado a partir dos setores.

    * todos concluídos → ``Concluída``
    * algum já começou → ``Em andamento``
    * ninguém começou → ``Aguardando``
    """

    statuses = [normalizar_status(status_por_setor.get(setor.nome, NAO_INICIADO)) for setor in SETORES]
    if statuses and all(status == CONCLUIDO for status in statuses):
        return OP_CONCLUIDA
    if any(status != NAO_INICIADO for status in statuses):
        return OP_EM_ANDAMENTO
    return OP_AGUARDANDO


def progresso(status_por_setor: Mapping[str, str]) -> int:
    """Percentual de setores concluídos (0–100), para a barra de progresso."""

    total = len(SETORES)
    if not total:
        return 0
    concluidos = sum(
        1
        for setor in SETORES
        if normalizar_status(status_por_setor.get(setor.nome, NAO_INICIADO)) == CONCLUIDO
    )
    return round((concluidos / total) * 100)


def resumir_setores(linhas_setor: Sequence[Mapping[str, object]]) -> dict[str, str]:
    """Reduz as linhas da aba ``Setores`` em ``{nome do setor: status}``."""

    resumo: dict[str, str] = {}
    for linha in linhas_setor:
        nome = str(linha.get("setor", "")).strip()
        if not nome:
            continue
        resumo[nome] = normalizar_status(str(linha.get("status", "")))
    return resumo


def nomes_desconhecidos(linhas_setor: Iterable[Mapping[str, object]]) -> set[str]:
    """Setores gravados na planilha que não existem mais no fluxo do código."""

    conhecidos = {setor.nome.casefold() for setor in SETORES}
    return {
        str(linha.get("setor", "")).strip()
        for linha in linhas_setor
        if str(linha.get("setor", "")).strip()
        and str(linha.get("setor", "")).strip().casefold() not in conhecidos
    }
