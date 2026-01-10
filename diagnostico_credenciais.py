import json
import os
from pathlib import Path

import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]


def check_credentials(creds_path: Path) -> dict:
    if not creds_path.exists():
        print(f"❌ credentials.json não encontrado em {creds_path}")
        raise SystemExit(1)
    try:
        data = json.loads(creds_path.read_text())
    except Exception as e:
        print(f"❌ Erro lendo credentials.json: {e}")
        raise SystemExit(1)
    required = [
        "type",
        "project_id",
        "private_key_id",
        "private_key",
        "client_email",
        "client_id",
        "token_uri",
    ]
    missing = [k for k in required if not str(data.get(k, "")).strip()]
    if missing:
        print(f"❌ credentials.json incompleto. Faltando: {', '.join(missing)}")
        raise SystemExit(1)
    if data.get("type") != "service_account":
        print(f"❌ type inválido: {data.get('type')} (esperado service_account)")
        raise SystemExit(1)
    print("✅ credentials.json parece válido (estrutura)\n")
    return data


def list_sheets_and_preview() -> None:
    creds = Credentials.from_service_account_file(Path(__file__).parent / "credentials.json", scopes=SCOPES)
    client = gspread.authorize(creds)

    sheet_id = os.getenv("GOOGLE_SHEET_ID", "1qs3cxlklTnzCp4RpQGhxIrEF4CbeUvid1S0Cp2tC3Xg")
    tab = os.getenv("GOOGLE_SHEET_TAB", "Respostas ao formulário 3")

    print(f"🔗 Abrindo planilha: {sheet_id}")
    ss = client.open_by_key(sheet_id)
    tabs = [ws.title for ws in ss.worksheets()]
    print(f"✅ Abas encontradas ({len(tabs)}): {', '.join(tabs)}")

    if tab not in tabs:
        print(f"⚠️ Aba alvo '{tab}' não encontrada.")
        return

    ws = ss.worksheet(tab)
    rows = ws.get_values(range_name="A1:N5")
    print("\n📄 Prévia (A1:N5):")
    for r in rows:
        print("  ", r)


if __name__ == "__main__":
    try:
        check_credentials(Path(__file__).parent / "credentials.json")
        list_sheets_and_preview()
        print("\n🎉 Conexão OK e planilha lida com sucesso.")
    except Exception as e:
        print(f"\n❌ Falha ao conectar/listar: {e}")
        print("Dicas:")
        print("- Substitua credentials.json por um JSON real de service account (não placeholders)")
        print("- Compartilhe a planilha com o client_email do JSON (Editor)")
        print("- Ajuste GOOGLE_SHEET_ID/GOOGLE_SHEET_TAB se necessário")
