"""Completa a planilha da produção com os setores novos do fluxo.

Uso:
    PRODUCAO_SPREADSHEET_ID=<id ou URL> python scripts/migrar_setores_producao.py

Quando o fluxo ganha um setor (como aconteceu com Corte Painel, CNC, Policorte,
Vidros, Portas e Pass-through), as OPs que já existiam ficam sem a linha desse
setor. Este script cria as linhas que faltam:

* OP em andamento → setor novo entra como ``Não iniciado``;
* OP já concluída → setor novo entra como ``Não se aplica`` (para não reabrir
  trabalho antigo);

Nada além disso é gravado: nenhum dado fictício entra na planilha.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from appmodules.producao_web import setores as fluxo  # noqa: E402
from appmodules.producao_web.storage import (  # noqa: E402
    GoogleSheetsStorage,
    LocalStorage,
    criar_storage,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Completa os setores novos nas OPs existentes.")
    parser.add_argument("--planilha", default=None, help="ID ou URL da planilha da produção")
    parser.add_argument(
        "--credenciais", default=str(BASE / "credentials.json"), help="Caminho do credentials.json"
    )
    parser.add_argument(
        "--local",
        action="store_true",
        help="Usa o banco local (PRODUCAO_LOCAL_DB) em vez da planilha",
    )
    args = parser.parse_args()

    import os

    if args.local or os.getenv("PRODUCAO_STORAGE", "").strip().lower() == "local":
        caminho = os.getenv("PRODUCAO_LOCAL_DB") or str(BASE / "instance" / "producao_local.json")
        storage = LocalStorage(caminho)
        print(f"Banco local: {caminho}")
    else:
        planilha = args.planilha or os.getenv("PRODUCAO_SPREADSHEET_ID", "")
        if not planilha:
            print("✗ Informe PRODUCAO_SPREADSHEET_ID (ou use --local).")
            return 1
        storage = GoogleSheetsStorage(spreadsheet_id=planilha, credenciais=args.credenciais)
        disponivel, erro = storage.disponivel()
        if not disponivel:
            print(f"✗ {erro}")
            return 1
        print(f"Planilha: {planilha}")

    ops = storage.listar_ops()
    print(f"Fluxo atual: {len(fluxo.SETORES)} setores")
    for indice, setor in enumerate(fluxo.SETORES, start=1):
        print(f"  {indice:>2}. {setor.icone} {setor.nome}")
    print(f"\nOPs na base: {len(ops)}")

    desconhecidos = fluxo.nomes_desconhecidos(storage.listar_setores())
    if desconhecidos:
        print(
            "\n⚠ Setores na planilha que não existem mais no fluxo: "
            + ", ".join(sorted(desconhecidos))
            + "\n  (nada foi apagado — essas linhas são ignoradas pelo app)"
        )

    resultado = storage.garantir_setores()
    if not resultado["linhas_criadas"]:
        print("\n✓ Todas as OPs já têm os setores do fluxo. Nada a fazer.")
        return 0

    print(f"\n✓ {resultado['linhas_criadas']} linha(s) criadas em {resultado['ops_afetadas']} OP(s):")
    por_op: dict[str, list[dict]] = {}
    for linha in resultado["detalhes"]:
        por_op.setdefault(linha["op_id"], []).append(linha)
    for op_id, linhas in sorted(por_op.items()):
        print(f"  {op_id}: " + ", ".join(f"{l['setor']} ({l['status']})" for l in linhas))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
