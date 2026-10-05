"""App de produção — ponto de entrada.

Roda **separado** do sistema de OS, em outra porta:

    # desenvolvimento
    python producao_app.py

    # produção (servidor)
    PRODUCAO_SPREADSHEET_ID=<id ou URL da planilha> \
    PRODUCAO_SECRET_KEY=<chave> \
    PRODUCAO_ADMIN_PIN=123456 \
    gunicorn -w 2 --threads 4 -b 0.0.0.0:5001 producao_app:app

O app usa o mesmo ``credentials.json`` do sistema (conta de serviço), mas uma
planilha **própria**, indicada em ``PRODUCAO_SPREADSHEET_ID``.

Para testar sem Google Sheets, use ``PRODUCAO_STORAGE=local``: os dados vão para
um arquivo JSON local (começa vazio) e nada é gravado na planilha.
"""

from __future__ import annotations

import os

from appmodules.producao_web import create_app

app = create_app()


if __name__ == "__main__":
    porta = int(os.getenv("PRODUCAO_PORT", app.config.get("PORT", 5001)))
    app.run(
        host="0.0.0.0",
        port=porta,
        debug=bool(app.config.get("DEBUG")),
    )
