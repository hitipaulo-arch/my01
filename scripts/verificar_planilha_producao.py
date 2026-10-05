"""Verifica a planilha do app de produção e mostra o que falta configurar.

Uso:
    PRODUCAO_SPREADSHEET_ID=<id ou URL> python scripts/verificar_planilha_producao.py

O script:

1. mostra o e-mail da conta de serviço (é ele que precisa ter acesso **Editor**
   na planilha da produção);
2. abre a planilha e cria as abas que faltarem (``OPs``, ``Setores``,
   ``Histórico``, ``Acessos``);
3. informa quantas OPs e quantos acessos já existem.

Nenhum dado é gravado além dos cabeçalhos das abas e — se você pedir — do PIN de
gestão inicial (``--pin``). Nada de dado fictício.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from appmodules.producao_web import setores as fluxo  # noqa: E402
from appmodules.producao_web.storage import GoogleSheetsStorage  # noqa: E402


def email_da_conta(credenciais: Path) -> str | None:
    try:
        dados = json.loads(credenciais.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return dados.get("client_email")


def main() -> int:
    parser = argparse.ArgumentParser(description="Verifica a planilha do app de produção.")
    parser.add_argument(
        "--planilha",
        default=None,
        help="ID ou URL da planilha (padrão: variável PRODUCAO_SPREADSHEET_ID)",
    )
    parser.add_argument(
        "--credenciais",
        default=str(BASE / "credentials.json"),
        help="Caminho do credentials.json da conta de serviço",
    )
    parser.add_argument(
        "--pin",
        default=None,
        help="Define o PIN inicial da gestão (4 a 8 dígitos) e encerra",
    )
    args = parser.parse_args()

    import os

    planilha = args.planilha or os.getenv("PRODUCAO_SPREADSHEET_ID", "")
    credenciais = Path(args.credenciais)

    print("=" * 68)
    print("App de produção — verificação da planilha")
    print("=" * 68)

    if not credenciais.exists():
        print(f"\n✗ Não encontrei {credenciais}.")
        print("  Coloque o JSON da conta de serviço nesse caminho (o mesmo do sistema).")
        return 1

    email = email_da_conta(credenciais)
    print(f"\nConta de serviço: {email or '(não foi possível ler o client_email)'}")
    print("→ Compartilhe a planilha da produção com esse e-mail como **Editor**.")

    if not planilha:
        print("\n✗ PRODUCAO_SPREADSHEET_ID não informado.")
        print("  Pegue o ID na URL: docs.google.com/spreadsheets/d/<ID>/edit")
        print("  e exporte: export PRODUCAO_SPREADSHEET_ID=<ID ou URL>")
        return 1

    storage = GoogleSheetsStorage(spreadsheet_id=planilha, credenciais=str(credenciais))
    print(f"\nPlanilha: {planilha}")
    disponivel, erro = storage.disponivel()
    if not disponivel:
        print(f"\n✗ {erro}")
        print("  Confira se a planilha foi compartilhada com a conta de serviço acima.")
        return 1

    ops = storage.listar_ops()
    acessos = storage.listar_acessos()
    print("\n✓ Planilha acessível. Abas conferidas/criadas:")
    print("   OPs · Setores · Histórico · Acessos")
    print(f"\n   OPs cadastradas: {len(ops)}")
    print(f"   Setores por OP:  {len(fluxo.SETORES)} ({', '.join(fluxo.nomes())})")
    print(f"   Acessos cadastrados: {len(acessos)}")

    if args.pin:
        from werkzeug.security import generate_password_hash

        if not (4 <= len(args.pin) <= 8 and args.pin.isdigit()):
            print("\n✗ O PIN deve ter de 4 a 8 dígitos.")
            return 1
        storage.salvar_acesso(
            fluxo.GESTAO,
            fluxo.PAPEL_GESTAO,
            fluxo.GESTAO_NOME,
            generate_password_hash(args.pin),
            True,
        )
        print(f"\n✓ PIN da gestão definido ({len(args.pin)} dígitos).")

    if not acessos and not args.pin:
        print("\n⚠ Nenhum PIN cadastrado ainda.")
        print("  Defina o PIN da gestão com:")
        print("    python scripts/verificar_planilha_producao.py --pin 123456")
        print("  (os PINs de cada setor são cadastrados depois, na tela 'Acessos')")

    print("\nPronto. Suba o app com:")
    print("  gunicorn -w 2 --threads 4 -b 0.0.0.0:5001 producao_app:app")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
