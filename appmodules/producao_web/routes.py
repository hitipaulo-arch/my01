"""Telas do app de produção (controle por setor).

Rotas principais:

===============================================  =========================================
Rota                                             Para quê
===============================================  =========================================
``/login``                                       escolher o setor e digitar o PIN
``/``                                            fila do setor (ou painel, se gestão)
``/op/<id>``                                     ficha da OP + status de cada setor
``/op/<id>/setor/<setor>`` (POST)                marcar Não iniciado / Em andamento / Concluído
``/op/nova``, ``/op/<id>/editar``, ``/excluir``  cadastro da OP (gestão)
``/painel``                                      visão geral por setor (gestão)
``/acessos``                                     PIN de cada setor (gestão)
``/instalar``, ``/offline``, ``/manifest…``      instalação como app no celular
===============================================  =========================================
"""

from __future__ import annotations

import io
import logging
from datetime import datetime

from flask import (
    Blueprint,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    send_from_directory,
    url_for,
)
from werkzeug.security import generate_password_hash

from appmodules.producao_web import auth, setores as fluxo
from appmodules.producao_web.formatters import format_codigo_code, format_mtc_code

logger = logging.getLogger(__name__)

# Os estáticos do app ficam em ``static/producao`` e são servidos pela rota
# padrão do Flask (``/static/producao/...``), sem registrar uma segunda rota.
producao_bp = Blueprint("producao", __name__, template_folder="../../templates")


# ──────────────────────────────────────────────────────────────────────────────
# Serviços / contexto
# ──────────────────────────────────────────────────────────────────────────────
def storage():
    return current_app.config["producao_storage"]


def _contexto_base(**extra):
    usuario = auth.usuario_atual()
    contexto = {
        "usuario": usuario,
        "e_gestao": auth.e_gestao(),
        "setor_usuario": auth.setor_do_usuario(),
        "setores": fluxo.SETORES,
        "status_setor": fluxo.STATUS_SETOR,
        "abas": _abas(usuario),
    }
    contexto.update(extra)
    return contexto


def _abas(usuario: dict | None) -> list[dict]:
    """Navegação inferior, conforme o perfil de quem entrou."""

    if not usuario:
        return []
    if usuario.get("papel") == fluxo.PAPEL_GESTAO:
        return [
            {"rotulo": "Painel", "icone": "📊", "endpoint": "producao.home"},
            {"rotulo": "OPs", "icone": "📋", "endpoint": "producao.lista"},
            {"rotulo": "Nova", "icone": "➕", "endpoint": "producao.nova_op"},
            {"rotulo": "Acessos", "icone": "🔑", "endpoint": "producao.acessos"},
        ]
    return [
        {"rotulo": "Minha fila", "icone": "🏭", "endpoint": "producao.home"},
        {"rotulo": "Todas", "icone": "📋", "endpoint": "producao.lista"},
        {"rotulo": "Sair", "icone": "🚪", "endpoint": "producao.logout"},
    ]


def _render(template: str, **contexto):
    return render_template(f"producao/{template}", **_contexto_base(**contexto))


@producao_bp.app_context_processor
def _injetar_helpers():
    return {
        "url_do_app": lambda: url_for("producao.home", _external=True),
        "ano_atual": lambda: datetime.now().year,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Login por setor
# ──────────────────────────────────────────────────────────────────────────────
@producao_bp.route("/login", methods=["GET", "POST"])
def login():
    if auth.usuario_atual():
        return redirect(url_for("producao.home"))

    if request.method == "POST":
        chave = str(request.form.get("perfil", "")).strip()
        pin = str(request.form.get("pin", "")).strip()
        proximo = request.form.get("proximo") or request.args.get("proximo") or ""

        if not chave:
            flash("Escolha o seu setor.", "warning")
            return _render("login.html", proximo=proximo), 400

        if auth.bloqueado(chave):
            flash("Muitas tentativas. Aguarde alguns minutos.", "danger")
            return _render("login.html", proximo=proximo), 429

        setor = fluxo.por_chave(chave)
        registro = storage().obter_acesso(fluxo.GESTAO if chave == fluxo.GESTAO else chave)

        if chave == fluxo.GESTAO:
            papel, nome = fluxo.PAPEL_GESTAO, fluxo.GESTAO_NOME
        elif setor:
            papel, nome = fluxo.PAPEL_SETOR, setor.nome
        else:
            flash("Setor não encontrado.", "danger")
            return _render("login.html", proximo=proximo), 400

        # Setor sem PIN cadastrado ainda: o registro existe só para o freio de
        # tentativas — quem define o PIN é a gestão, na tela Acessos.
        registro = registro or {"chave": chave, "papel": papel, "nome": nome, "pin_hash": "", "ativo": True}

        if not registro.get("ativo", True):
            flash("Acesso desativado. Fale com a gestão.", "danger")
            return _render("login.html", proximo=proximo), 403

        if not auth.pin_confere(registro, pin):
            auth.registrar_tentativa(chave)
            restantes = auth.tentativas_restantes(chave)
            flash(
                f"PIN incorreto. Tentativas restantes: {restantes}."
                if restantes
                else "PIN incorreto. Acesso temporariamente bloqueado.",
                "danger",
            )
            return _render("login.html", proximo=proximo), 401

        auth.limpar_tentativas(chave)
        auth.entrar(chave=chave, papel=papel, nome=nome)
        logger.info("[produção] login: %s", nome)

        if proximo and proximo.startswith("/"):
            return redirect(proximo)
        return redirect(url_for("producao.home"))

    return _render("login.html", proximo=request.args.get("proximo", ""))


@producao_bp.route("/sair")
def logout():
    auth.sair()
    flash("Você saiu do app de produção.", "success")
    return redirect(url_for("producao.login"))


# ──────────────────────────────────────────────────────────────────────────────
# Fila / painel
# ──────────────────────────────────────────────────────────────────────────────
@producao_bp.route("/")
@auth.login_necessario
def home():
    if auth.e_gestao():
        return painel()
    return lista()


@producao_bp.route("/ops")
@auth.login_necessario
def lista():
    """Lista de OPs — para o setor, a fila dele; para a gestão, todas."""

    try:
        ops = storage().ops_com_fluxo()
    except Exception as erro:
        logger.error("Falha ao listar OPs: %s", erro, exc_info=True)
        return _render("erro.html", mensagem=f"Não foi possível ler a planilha da produção: {erro}"), 503

    setor_usuario = auth.setor_do_usuario()
    recorte = request.args.get("recorte", "").strip().lower()

    if setor_usuario:
        def pendente(op):
            for detalhe in op["setores"]:
                if detalhe["nome"] == setor_usuario:
                    return not detalhe["resolvido"]
            return False

        selecionadas = [op for op in ops if pendente(op)] if recorte in ("", "fila") else ops
    else:
        selecionadas = ops

    if recorte == "andamento":
        selecionadas = [op for op in selecionadas if op["status_geral"] == fluxo.OP_EM_ANDAMENTO]
    elif recorte == "concluidas":
        selecionadas = [op for op in selecionadas if op["status_geral"] == fluxo.OP_CONCLUIDA]
    elif recorte == "aguardando":
        selecionadas = [op for op in selecionadas if op["status_geral"] == fluxo.OP_AGUARDANDO]

    return _render(
        "fila.html",
        ops=selecionadas,
        total=len(selecionadas),
        recorte=recorte or ("fila" if setor_usuario else "todas"),
    )


@producao_bp.route("/painel")
@auth.login_necessario
def painel():
    """Visão da gestão: o que está em cada setor e o que está atrasado."""

    try:
        ops = storage().ops_com_fluxo()
    except Exception as erro:
        logger.error("Falha ao carregar o painel: %s", erro, exc_info=True)
        return _render("erro.html", mensagem=f"Não foi possível ler a planilha da produção: {erro}"), 503

    hoje = datetime.now().date()
    por_setor: list[dict] = []
    for setor in fluxo.SETORES:
        pendentes = [
            op for op in ops if not fluxo.resolvido(_status_no_setor(op, setor.nome))
        ]
        em_andamento = [
            op for op in ops if _status_no_setor(op, setor.nome) == fluxo.EM_ANDAMENTO
        ]
        concluidos = [op for op in ops if _status_no_setor(op, setor.nome) == fluxo.CONCLUIDO]
        nao_aplica = [op for op in ops if _status_no_setor(op, setor.nome) == fluxo.NAO_SE_APLICA]
        por_setor.append(
            {
                "setor": setor,
                "pendentes": len(pendentes),
                "em_andamento": len(em_andamento),
                "concluidos": len(concluidos),
                "nao_aplica": len(nao_aplica),
                "atrasados": sum(1 for op in pendentes if _atrasada(op, hoje)),
            }
        )

    atrasadas = [op for op in ops if op["status_geral"] != fluxo.OP_CONCLUIDA and _atrasada(op, hoje)]
    concluidas = [op for op in ops if op["status_geral"] == fluxo.OP_CONCLUIDA]

    pendencias = []
    try:
        pendencias = storage().setores_faltantes()
    except Exception as erro:  # não impede o painel de abrir
        logger.warning("Não foi possível conferir os setores das OPs: %s", erro)

    return _render(
        "painel.html",
        ops=ops,
        por_setor=por_setor,
        atrasadas=atrasadas,
        concluidas=concluidas,
        hoje=hoje,
        op_sem_setores=sorted({linha["op_id"] for linha in pendencias}),
    )


def _status_no_setor(op: dict, nome_setor: str) -> str:
    for detalhe in op.get("setores", []):
        if detalhe["nome"] == nome_setor:
            return detalhe["status"]
    return fluxo.NAO_INICIADO


def _parse_data(texto: str):
    for formato in ("%d/%m/%Y", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M"):
        try:
            return datetime.strptime(str(texto).strip(), formato).date()
        except (ValueError, TypeError):
            continue
    return None


def _atrasada(op: dict, hoje) -> bool:
    prazo = _parse_data(op.get("prazo", ""))
    return bool(prazo and prazo < hoje)


# ──────────────────────────────────────────────────────────────────────────────
# Ficha da OP
# ──────────────────────────────────────────────────────────────────────────────
@producao_bp.route("/op/<op_id>")
@auth.login_necessario
def detalhe(op_id: str):
    try:
        op = storage().obter_op(op_id)
        if not op:
            flash("OP não encontrada.", "warning")
            return redirect(url_for("producao.home"))
        registros = storage().setores_da_op(op_id)
        historico = storage().listar_historico(op_id)
    except Exception as erro:
        logger.error("Falha ao abrir a OP %s: %s", op_id, erro, exc_info=True)
        return _render("erro.html", mensagem=f"Não foi possível abrir a OP: {erro}"), 503

    status_por_setor = fluxo.resumir_setores(registros)
    op = dict(op)
    op["status_geral"] = fluxo.status_da_op(status_por_setor)
    op["progresso"] = fluxo.progresso(status_por_setor)
    op["setor_atual"] = fluxo.proximo_setor(status_por_setor)
    op["setores"] = [
        {**detalhe, **_dados_setor(registros, detalhe["nome"])}
        for detalhe in fluxo.setores_em_ordem(status_por_setor)
    ]

    return _render(
        "op_detalhe.html",
        op=op,
        historico=sorted(historico, key=lambda linha: linha.get("data_hora", ""), reverse=True),
        setor_usuario=auth.setor_do_usuario(),
    )


def _dados_setor(registros: list[dict], nome: str) -> dict:
    for registro in registros:
        if str(registro.get("setor", "")).casefold() == nome.casefold():
            return {
                "iniciado_em": registro.get("iniciado_em", ""),
                "concluido_em": registro.get("concluido_em", ""),
                "atualizado_em": registro.get("atualizado_em", ""),
                "atualizado_por": registro.get("atualizado_por", ""),
                "observacao_setor": registro.get("observacao", ""),
                "editavel": auth.pode_alterar_setor(nome),
            }
    return {
        "iniciado_em": "",
        "concluido_em": "",
        "atualizado_em": "",
        "atualizado_por": "",
        "observacao_setor": "",
        "editavel": auth.pode_alterar_setor(nome),
    }


@producao_bp.route("/op/<op_id>/setor/<chave_setor>", methods=["POST"])
@auth.login_necessario
def atualizar_setor(op_id: str, chave_setor: str):
    """Marca o status de um setor (o próprio setor ou a gestão)."""

    setor = fluxo.por_chave(chave_setor)
    if not setor:
        return _resposta({"success": False, "message": "Setor inválido."}, 400)

    if not auth.pode_alterar_setor(setor.nome):
        return _resposta(
            {"success": False, "message": "Você só pode atualizar o seu setor."}, 403
        )

    status = str(request.form.get("status", "")).strip()
    if not fluxo.e_status_valido(status):
        return _resposta({"success": False, "message": "Status inválido."}, 400)

    observacao = str(request.form.get("observacao", "")).strip()[:280]
    usuario = auth.usuario_atual()

    try:
        ok = storage().atualizar_status_setor(
            op_id, setor.nome, status, usuario.get("nome", "?"), observacao
        )
    except Exception as erro:
        logger.error("Falha ao atualizar o setor %s da OP %s: %s", setor.nome, op_id, erro, exc_info=True)
        return _resposta({"success": False, "message": f"Erro ao gravar: {erro}"}, 503)

    if not ok:
        return _resposta({"success": False, "message": "OP não encontrada."}, 404)

    logger.info("[produção] %s marcou %s como %s", usuario.get("nome"), setor.nome, status)
    if _e_ajax():
        return _resposta(
            {
                "success": True,
                "message": f"{setor.nome}: {status}",
                "setor": setor.nome,
                "status": status,
            }
        )
    flash(f"{setor.nome} marcado como “{status}”.", "success")
    return redirect(url_for("producao.detalhe", op_id=op_id))


def _e_ajax() -> bool:
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


def _resposta(dados: dict, codigo: int = 200):
    if _e_ajax():
        return jsonify(dados), codigo
    flash(dados.get("message", ""), "success" if dados.get("success") else "danger")
    return redirect(request.referrer or url_for("producao.home"))


# ──────────────────────────────────────────────────────────────────────────────
# Cadastro da OP (gestão)
# ──────────────────────────────────────────────────────────────────────────────
def _dados_formulario() -> dict:
    return {
        "nome_item": str(request.form.get("nome_item", "")).strip(),
        "codigo": format_codigo_code(str(request.form.get("codigo", "")).strip()),
        "mtc": format_mtc_code(str(request.form.get("mtc", "")).strip()),
        "quantidade": request.form.get("quantidade", "0"),
        "cliente": str(request.form.get("cliente", "")).strip(),
        "prazo": str(request.form.get("prazo", "")).strip(),
        "material": str(request.form.get("material", "")).strip(),
        "observacao": str(request.form.get("observacao", "")).strip(),
    }


def _validar(dados: dict) -> str | None:
    if len(dados["nome_item"]) < 2:
        return "Informe o nome do item (mínimo 2 caracteres)."
    if not dados["codigo"]:
        return "Informe o código do item."
    try:
        if int(str(dados["quantidade"]).strip() or 0) < 0:
            return "A quantidade não pode ser negativa."
    except ValueError:
        return "Quantidade inválida."
    if dados["prazo"] and not _parse_data(dados["prazo"]):
        return "Prazo deve estar no formato dd/mm/aaaa."
    return None


@producao_bp.route("/op/nova", methods=["GET", "POST"])
@auth.gestao_necessaria
def nova_op():
    dados = _dados_formulario() if request.method == "POST" else {}

    if request.method == "POST":
        erro = _validar(dados)
        if erro:
            flash(erro, "danger")
            return _render("op_form.html", op=dados, modo="nova"), 400
        try:
            criada = storage().criar_op(dados, auth.usuario_atual().get("nome", "?"))
        except Exception as falha:
            logger.error("Falha ao criar OP: %s", falha, exc_info=True)
            flash(f"Não foi possível salvar na planilha: {falha}", "danger")
            return _render("op_form.html", op=dados, modo="nova"), 503

        flash(f"OP {criada['id']} criada com os {len(fluxo.SETORES)} setores.", "success")
        return redirect(url_for("producao.detalhe", op_id=criada["id"]))

    return _render("op_form.html", op={}, modo="nova")


@producao_bp.route("/op/<op_id>/editar", methods=["GET", "POST"])
@auth.gestao_necessaria
def editar_op(op_id: str):
    try:
        op = storage().obter_op(op_id)
    except Exception as erro:
        logger.error("Falha ao carregar a OP %s: %s", op_id, erro, exc_info=True)
        return _render("erro.html", mensagem=f"Não foi possível abrir a OP: {erro}"), 503

    if not op:
        flash("OP não encontrada.", "warning")
        return redirect(url_for("producao.home"))

    if request.method == "POST":
        dados = _dados_formulario()
        erro = _validar(dados)
        if erro:
            flash(erro, "danger")
            return _render("op_form.html", op={**op, **dados}, modo="editar"), 400
        try:
            storage().atualizar_op(op_id, dados)
        except Exception as falha:
            logger.error("Falha ao editar a OP %s: %s", op_id, falha, exc_info=True)
            flash(f"Não foi possível salvar: {falha}", "danger")
            return _render("op_form.html", op={**op, **dados}, modo="editar"), 503
        flash("OP atualizada.", "success")
        return redirect(url_for("producao.detalhe", op_id=op_id))

    return _render("op_form.html", op=op, modo="editar")


@producao_bp.route("/op/<op_id>/excluir", methods=["POST"])
@auth.gestao_necessaria
def excluir_op(op_id: str):
    try:
        ok = storage().excluir_op(op_id)
    except Exception as erro:
        logger.error("Falha ao excluir a OP %s: %s", op_id, erro, exc_info=True)
        flash(f"Não foi possível excluir: {erro}", "danger")
        return redirect(url_for("producao.detalhe", op_id=op_id))

    flash(f"OP {op_id} excluída." if ok else "OP não encontrada.", "success" if ok else "warning")
    return redirect(url_for("producao.lista"))


# ──────────────────────────────────────────────────────────────────────────────
# Acessos (PIN por setor) — gestão
# ──────────────────────────────────────────────────────────────────────────────
@producao_bp.route("/acessos", methods=["GET", "POST"])
@auth.gestao_necessaria
def acessos():
    if request.method == "POST":
        chave = str(request.form.get("perfil", "")).strip()
        pin = str(request.form.get("pin", "")).strip()
        ativo = request.form.get("ativo", "sim") == "sim"

        if chave != fluxo.GESTAO and not fluxo.por_chave(chave):
            flash("Perfil inválido.", "danger")
            return redirect(url_for("producao.acessos"))
        if pin and not auth.pin_utilizavel(pin):
            flash("O PIN deve ter de 4 a 8 dígitos.", "danger")
            return redirect(url_for("producao.acessos"))

        existente = storage().obter_acesso(chave) or {}
        hash_novo = existente.get("pin_hash", "") if not pin else generate_password_hash(pin)
        if not hash_novo:
            flash("Defina um PIN para este perfil.", "danger")
            return redirect(url_for("producao.acessos"))

        papel = fluxo.PAPEL_GESTAO if chave == fluxo.GESTAO else fluxo.PAPEL_SETOR
        nome = fluxo.GESTAO_NOME if chave == fluxo.GESTAO else fluxo.por_chave(chave).nome
        try:
            storage().salvar_acesso(chave, papel, nome, hash_novo, ativo)
        except Exception as erro:
            logger.error("Falha ao salvar acesso %s: %s", chave, erro, exc_info=True)
            flash(f"Não foi possível salvar o acesso: {erro}", "danger")
            return redirect(url_for("producao.acessos"))

        flash(f"Acesso de {nome} salvo." if pin else f"Acesso de {nome} atualizado.", "success")
        return redirect(url_for("producao.acessos"))

    try:
        cadastrados = {acesso["chave"]: acesso for acesso in storage().listar_acessos()}
    except Exception as erro:
        logger.error("Falha ao listar acessos: %s", erro, exc_info=True)
        return _render("erro.html", mensagem=f"Não foi possível ler os acessos: {erro}"), 503

    perfis = [
        {
            "chave": fluxo.GESTAO,
            "nome": fluxo.GESTAO_NOME,
            "papel": fluxo.PAPEL_GESTAO,
            "cadastrado": fluxo.GESTAO in cadastrados,
            "ativo": cadastrados.get(fluxo.GESTAO, {}).get("ativo", True),
        }
    ] + [
        {
            "chave": setor.chave,
            "nome": setor.nome,
            "papel": fluxo.PAPEL_SETOR,
            "cadastrado": setor.chave in cadastrados,
            "ativo": cadastrados.get(setor.chave, {}).get("ativo", True),
        }
        for setor in fluxo.SETORES
    ]
    return _render("acessos.html", perfis=perfis, admin_pin_configurado=bool(current_app.config.get("ADMIN_PIN")))


# ──────────────────────────────────────────────────────────────────────────────
# PWA: manifest, service worker, instalação, offline, QR
# ──────────────────────────────────────────────────────────────────────────────
@producao_bp.route("/manifest.webmanifest")
def manifest():
    resposta = send_from_directory(
        current_app.static_folder, "producao/manifest.json", mimetype="application/manifest+json"
    )
    resposta.headers["Cache-Control"] = "public, max-age=3600"
    return resposta


@producao_bp.route("/service-worker.js")
def service_worker():
    resposta = send_from_directory(
        current_app.static_folder, "producao/service-worker.js", mimetype="application/javascript"
    )
    resposta.headers["Cache-Control"] = "no-cache"
    return resposta


@producao_bp.route("/instalar")
def instalar():
    return _render("instalar.html", usuario=auth.usuario_atual())


@producao_bp.route("/offline")
def offline():
    return _render("offline.html")


@producao_bp.route("/qr-app.png")
def qr_app():
    """QR code para o pessoal da fábrica abrir/instalar o app."""

    import qrcode

    destino = url_for("producao.login", _external=True)
    qr = qrcode.QRCode(
        version=1, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=4
    )
    qr.add_data(destino)
    qr.make(fit=True)
    buffer = io.BytesIO()
    qr.make_image(fill_color="black", back_color="white").save(buffer, format="PNG")
    buffer.seek(0)
    return send_file(buffer, mimetype="image/png", download_name="qr-producao.png")


@producao_bp.route("/healthz")
def healthz():
    disponivel, erro = True, None
    try:
        disponivel, erro = storage().disponivel()
    except Exception as falha:  # configuração ausente
        disponivel, erro = False, str(falha)
    return jsonify({"ok": disponivel, "storage": storage().nome, "erro": erro})
