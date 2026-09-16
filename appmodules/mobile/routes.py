"""Rotas exclusivas do aplicativo (nada de regra de negócio aqui).

Estas rotas existem apenas porque o app precisa de telas que a versão web não
tem: manifesto PWA, service worker, tela offline, instruções de instalação,
menu completo e um atalho direto para o formulário de abertura de OS.

Elas são registradas sem o prefixo ``/m`` — quem adiciona o prefixo é o
:class:`~appmodules.mobile.middleware.MobilePrefixMiddleware`. Ou seja:
``url_for('mobile.nova_os')`` devolve ``/m/nova-os`` no modo app.
"""

from __future__ import annotations

import logging

from flask import (
    Blueprint,
    current_app,
    redirect,
    render_template,
    send_from_directory,
    url_for,
)

from appmodules.mobile.context import MOBILE_PREFIX

logger = logging.getLogger(__name__)

mobile_bp = Blueprint(
    "mobile",
    __name__,
    static_folder="../../static",
    template_folder="../../templates",
)


def _static_dir(filename: str):
    """Caminho absoluto de um arquivo em ``static/``."""

    import os

    static_root = os.path.join(current_app.root_path, "static")
    return os.path.join(static_root, filename), os.path.dirname(
        os.path.join(static_root, filename)
    )


@mobile_bp.route("/nova-os")
def nova_os():
    """Formulário de abertura de OS (o POST continua indo para ``os.criar_os``)."""

    return render_template("mobile/index.html", form_data=None, erros=None)


@mobile_bp.route("/mais")
def mais():
    """Menu completo do app (todos os módulos liberados para o perfil)."""

    return render_template("mobile/mais.html")


@mobile_bp.route("/instalar")
def instalar():
    """Instruções para instalar o app na tela inicial do celular."""

    return render_template("mobile/instalar.html")


@mobile_bp.route("/offline")
def offline():
    """Página exibida pelo service worker quando não há internet."""

    return render_template("mobile/offline.html")


@mobile_bp.route("/manifest.webmanifest")
def manifest():
    """Manifesto PWA (ícone, nome, cor e escopo do app)."""

    static_root, _ = _static_dir("mobile/manifest.json")
    response = send_from_directory(
        current_app.static_folder, "mobile/manifest.json", mimetype="application/manifest+json"
    )
    response.headers["Cache-Control"] = "public, max-age=3600"
    logger.debug("Manifesto servido de %s", static_root)
    return response


@mobile_bp.route("/service-worker.js")
def service_worker():
    """Service worker do app (cache do shell + fallback offline)."""

    response = send_from_directory(
        current_app.static_folder,
        "mobile/service-worker.js",
        mimetype="application/javascript",
    )
    # Permite que o worker controle todo o escopo do app (/m/).
    response.headers["Service-Worker-Allowed"] = "/m/"
    response.headers["Cache-Control"] = "no-cache"
    return response


@mobile_bp.route("/app")
def atalho():
    """Atalho amigável: ``/m/app`` volta para o início do app."""

    return redirect(url_for("os.homepage"))


@mobile_bp.route("/qr-app.png")
def qr_app_png():
    """QR Code do endereço do app, para instalar direto pelo celular.

    Diferente do QR do formulário (que aponta para a raiz do site), este aponta
    sempre para ``<host>/m/`` — inclusive quando gerado a partir da versão web.
    """

    import io

    import qrcode
    from flask import request, send_file

    app_url = f"{request.host_url.rstrip('/')}{MOBILE_PREFIX}/"

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(app_url)
    qr.make(fit=True)

    buffer = io.BytesIO()
    qr.make_image(fill_color="black", back_color="white").save(buffer, format="PNG")
    buffer.seek(0)

    return send_file(buffer, mimetype="image/png", download_name="qr-app.png")
