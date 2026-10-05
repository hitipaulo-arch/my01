#!/usr/bin/env python3
"""Empacota o app de produção por setor como programa independente.

O app de produção (``producao_app.py`` + ``appmodules/producao_web``) é um
programa separado do sistema de OS: login, sessão e planilha próprios. Este
script monta a pasta/arquivo que pode ser copiado para outra máquina e rodado
sozinho, sem nada do sistema de OS.

Uso:

    python scripts/empacotar_app_producao.py                 # gera o .zip
    python scripts/empacotar_app_producao.py --destino /tmp  # muda o destino
    python scripts/empacotar_app_producao.py --pasta         # só a pasta
    python scripts/empacotar_app_producao.py --saida /tmp/build

O que entra no pacote:

* ``producao_app.py`` — ponto de entrada (``gunicorn producao_app:app``);
* ``appmodules/producao_web/`` — todo o código do app;
* ``appmodules/__init__.py`` **mínimo** (o pacote não carrega o sistema de OS);
* ``templates/producao/`` e ``static/producao/`` — telas e PWA;
* ``tests/test_producao_web.py`` — a suíte do app roda dentro do pacote;
* ``requirements.txt``, ``pytest.ini``, ``LEIA-ME.txt`` e ``APP_PRODUCAO.md``.

O resultado é verificado ao final: a pasta é extraída em um diretório temporário
e a suíte de testes do app roda lá dentro (``pytest tests/test_producao_web.py``).
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
NOME_PACOTE = "app-producao-por-setor"

#: Arquivos/pastas copiados como estão.
ENTRADAS = [
    "producao_app.py",
    "appmodules/producao_web",
    "templates/producao",
    "static/producao",
    "scripts/migrar_setores_producao.py",
    "scripts/verificar_planilha_producao.py",
    "scripts/gerar_icones_producao.py",
    "tests/test_producao_web.py",
    "APP_PRODUCAO.md",
]

#: ``appmodules/__init__.py`` mínimo — sem a factory do sistema de OS, senão o
#: pacote passaria a exigir a configuração (SECRET_KEY, planilhas) do gestor.
INIT_MINIMO = '''"""Pacote do app de produção por setor (independente do sistema de OS)."""
'''

#: Configuração mínima do pytest para a suíte rodar dentro do pacote.
PYTEST_INI = """[pytest]
testpaths = tests
addopts = -q
"""

#: Dependências do app de produção (o pacote não leva as do sistema de OS).
REQUIREMENTS = """\
Flask==3.1.3
gspread==6.1.4
google-auth==2.35.0
qrcode==8.0
Pillow==11.0.0
gunicorn==21.2.0
pytest==9.1.1
"""

LEIA_ME = """\
APP DE PRODUÇÃO POR SETOR — pacote independente
===============================================

Este pacote é um programa separado do sistema de OS: tem login próprio (PIN por
setor), sessão própria e planilha própria. Nada aqui depende do gestor de OS.

1) INSTALAR

    python -m venv .venv
    . .venv/bin/activate          # Windows: .venv\\Scripts\\activate
    pip install -r requirements.txt

2) ESCOLHER O ARMAZENAMENTO

   Google Sheets (recomendado no dia a dia) — crie a planilha e informe:

    export PRODUCAO_SPREADSHEET_ID="<id ou URL da planilha>"
    export GOOGLE_APPLICATION_CREDENTIALS="./credentials.json"

   Teste local, sem planilha (começa vazio):

    export PRODUCAO_STORAGE=local
    export PRODUCAO_LOCAL_DB="instance/producao_local.json"

3) SUBIR O APP

    export PRODUCAO_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
    export PRODUCAO_ADMIN_PIN=123456          # PIN inicial da gestão

    gunicorn -w 2 --threads 4 -b 0.0.0.0:5001 producao_app:app
    # ou, para testar:  python producao_app.py

   Abra http://localhost:5001 e entre com o PIN da gestão para cadastrar os
   PINs de cada setor em "Acessos".

4) TESTES

    pytest tests/test_producao_web.py -v

5) INSTALAR NO CELULAR

   O app é um PWA: abra no celular e use "Adicionar à tela inicial". A própria
   tela /instalar tem o passo a passo e o QR code.

Documentação completa: APP_PRODUCAO.md
"""


def _copiar(origem: Path, destino: Path) -> None:
    if origem.is_dir():
        shutil.copytree(
            origem, destino, ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
        )
    else:
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origem, destino)


def montar_pacote(destino: Path) -> Path:
    """Monta a pasta do pacote e devolve o caminho da raiz dele."""

    if destino.exists():
        shutil.rmtree(destino)
    destino.mkdir(parents=True)

    faltando = []
    for entrada in ENTRADAS:
        origem = RAIZ / entrada
        if not origem.exists():
            faltando.append(entrada)
            continue
        _copiar(origem, destino / entrada)
    if faltando:
        raise SystemExit(f"Arquivos ausentes no repositório: {', '.join(faltando)}")

    # appmodules/__init__.py mínimo (substitui o do sistema de OS)
    (destino / "appmodules" / "__init__.py").write_text(INIT_MINIMO, encoding="utf-8")

    # pytest.ini e requirements próprios do pacote
    (destino / "pytest.ini").write_text(PYTEST_INI, encoding="utf-8")
    (destino / "requirements.txt").write_text(REQUIREMENTS, encoding="utf-8")

    # LEIA-ME com a lista de setores atual, lida do próprio código
    sys.path.insert(0, str(RAIZ))
    from appmodules.producao_web.setores import SETORES  # noqa: E402

    linhas = "\n".join(f"   {i:2d}. {s.icone} {s.nome}" for i, s in enumerate(SETORES, 1))
    conteudo = LEIA_ME + "\nSETORES ACOMPANHADOS (nesta ordem)\n" + linhas + "\n"
    (destino / "LEIA-ME.txt").write_text(conteudo, encoding="utf-8")

    return destino


def arquivos_do_pacote(raiz: Path):
    for caminho in sorted(raiz.rglob("*")):
        if caminho.is_file() and "__pycache__" not in caminho.parts:
            yield caminho


def compactar(raiz: Path, destino_zip: Path, destino_tar: Path | None = None) -> None:
    with zipfile.ZipFile(destino_zip, "w", zipfile.ZIP_DEFLATED) as z:
        for caminho in arquivos_do_pacote(raiz):
            z.write(caminho, Path(NOME_PACOTE) / caminho.relative_to(raiz))
    if destino_tar is not None:
        with tarfile.open(destino_tar, "w:gz") as t:
            t.add(raiz, arcname=NOME_PACOTE)


def verificar(raiz: Path, python: str = sys.executable) -> tuple[bool, str]:
    """Roda a suíte do app dentro de uma cópia isolada do pacote."""

    with tempfile.TemporaryDirectory() as tmp:
        copia = Path(tmp) / NOME_PACOTE
        shutil.copytree(raiz, copia)
        processo = subprocess.run(
            [python, "-m", "pytest", "tests/test_producao_web.py", "--tb=short"],
            cwd=str(copia),
            capture_output=True,
            text=True,
        )
        saida = (processo.stdout or "") + (processo.stderr or "")
        resumo = [
            linha.strip()
            for linha in saida.splitlines()
            if "passed" in linha or "failed" in linha or "error" in linha.lower()
        ]
        ultima = resumo[-1] if resumo else saida.strip().splitlines()[-1:] or ["sem saída"]
        return processo.returncode == 0, ultima[0] if isinstance(ultima, list) else ultima


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--saida", default="/tmp/pacote-app-producao", help="pasta de trabalho")
    parser.add_argument("--destino", default=str(Path.home()), help="onde gravar zip/tar.gz")
    parser.add_argument("--pasta", action="store_true", help="não compactar, só a pasta")
    parser.add_argument("--sem-testes", action="store_true", help="pular a verificação")
    args = parser.parse_args()

    raiz_pacote = montar_pacote(Path(args.saida))
    total = sum(1 for _ in arquivos_do_pacote(raiz_pacote))
    print(f"pacote montado: {raiz_pacote} ({total} arquivos)")

    if not args.sem_testes:
        ok, resumo = verificar(raiz_pacote)
        print(f"verificação no pacote: {'✅' if ok else '❌'} {resumo}")
        if not ok:
            return 1

    if args.pasta:
        return 0

    destino = Path(args.destino)
    destino.mkdir(parents=True, exist_ok=True)
    zip_path = destino / f"{NOME_PACOTE}.zip"
    tar_path = destino / f"{NOME_PACOTE}.tar.gz"
    compactar(raiz_pacote, zip_path, tar_path)
    print(f"zip: {zip_path} ({zip_path.stat().st_size // 1024} KB)")
    print(f"tar: {tar_path} ({tar_path.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
