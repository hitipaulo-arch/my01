"""Configuração do app de produção (variáveis de ambiente próprias).

Nenhuma variável aqui é obrigatória para o sistema de OS continuar funcionando:
o app de produção é independente e tem o seu próprio conjunto de configurações.
"""

from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]


def _booleano(nome: str, padrao: bool = False) -> bool:
    valor = os.getenv(nome)
    if valor is None:
        return padrao
    return valor.strip().lower() in ("1", "true", "sim", "yes", "on")


def _inteiro(nome: str, padrao: int) -> int:
    try:
        return int(str(os.getenv(nome, padrao)).strip())
    except (TypeError, ValueError):
        return padrao


class ProducaoConfig:
    """Configurações lidas do ambiente no momento em que o app sobe."""

    @staticmethod
    def carregar() -> dict:
        segredo = os.getenv("PRODUCAO_SECRET_KEY") or os.getenv("SECRET_KEY") or ""
        if not segredo:
            raise ValueError(
                "\n" + "=" * 70 + "\n"
                "ERRO: defina PRODUCAO_SECRET_KEY (ou SECRET_KEY) para o app de produção.\n"
                "  python -c 'import secrets; print(secrets.token_hex(32))'\n"
                + "=" * 70
            )

        storage = os.getenv("PRODUCAO_STORAGE", "sheets").strip().lower()
        local_db = os.getenv("PRODUCAO_LOCAL_DB") or str(
            BASE_DIR / "instance" / "producao_local.json"
        )

        return {
            "SECRET_KEY": segredo,
            "STORAGE": storage,
            "SPREADSHEET_ID": os.getenv("PRODUCAO_SPREADSHEET_ID", "").strip(),
            "CREDENCIAIS": os.getenv(
                "GOOGLE_APPLICATION_CREDENTIALS", str(BASE_DIR / "credentials.json")
            ),
            "ESCOPOS": [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive.file",
            ],
            "LOCAL_DB_PATH": local_db,
            # PIN de primeiro acesso da gestão, usado enquanto não houver nenhum
            # acesso cadastrado na planilha (depois o PIN da gestão vale o da aba).
            "ADMIN_PIN": os.getenv("PRODUCAO_ADMIN_PIN", "").strip(),
            "PORT": _inteiro("PRODUCAO_PORT", 5001),
            "DEBUG": _booleano("PRODUCAO_DEBUG", False),
            # Segurança de sessão/CSRF
            "SESSION_COOKIE_HTTPONLY": True,
            "SESSION_COOKIE_SAMESITE": "Lax",
            "SESSION_COOKIE_SECURE": _booleano("PRODUCAO_COOKIE_SECURE", False),
            "WTF_CSRF_ENABLED": True,
            "WTF_CSRF_TIME_LIMIT": None,
            "MAX_CONTENT_LENGTH": 4 * 1024 * 1024,
            # Sessão do chão de fábrica: longa, mas não infinita
            "PERMANENT_SESSION_LIFETIME": _inteiro("PRODUCAO_SESSAO_MINUTOS", 12 * 60) * 60,
            "TESTING": False,
        }
