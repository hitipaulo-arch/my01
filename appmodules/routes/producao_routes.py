"""Rotas de produção."""

import logging
from datetime import datetime, timezone

from flask import Blueprint, current_app, flash, jsonify, redirect, request, session, url_for

from appmodules.mobile import render_page
from appmodules.extensions import cache
from appmodules.models.usuario import Role
from appmodules.utils import admin_required, login_required, render_route_error
from appmodules.utils.formatters import _append_producao_info, _format_codigo_code, _format_mtc_code
from appmodules.utils.validators import _parse_int_field, validate_item_form_data
from config import Config

logger = logging.getLogger(__name__)
producao_bp = Blueprint("producao", __name__)


def _validate_item_form_data(nome_item, codigo_item, quantidade_raw, observacao):
    """Adapter que preserva a validação acumulada do monólito."""
    errors = []
    nome_normalizado = str(nome_item or "").strip()
    if not nome_normalizado:
        errors.append("Nome do item é obrigatório.")
    elif len(nome_normalizado) < Config.VALIDATION.MIN_NOME_ITEM_LENGTH:
        errors.append("Nome do item é muito curto.")
    if not codigo_item or not str(codigo_item).strip():
        errors.append("Código do item é obrigatório.")
    if quantidade_raw < 0 or quantidade_raw > Config.VALIDATION.MAX_QUANTIDADE:
        errors.append("Quantidade inválida.")
    if len(observacao or "") > Config.VALIDATION.MAX_OBSERVACAO_LENGTH:
        errors.append("Observação muito longa (máx. 500 caracteres).")
    if errors:
        return False, " ".join(errors)
    return validate_item_form_data(nome_item, codigo_item, quantidade_raw, observacao)


def _get_current_user_role():
    """Retorna a role do usuário logado, se disponível."""
    username = session.get("usuario")
    if not username:
        return None
    user_service = current_app.config.get("user_service")
    if not user_service:
        return session.get("role")
    user_data = user_service.get_usuario(username)
    if user_data:
        return user_data.role
    logger.warning("Usuário '%s' da sessão não encontrado. Invalidando sessão.", username)
    session.clear()
    return None


@producao_bp.route("/producao", methods=["GET", "POST"])
@login_required
def producao():
    """Página de cadastro e acompanhamento de produção."""
    sheets_service = current_app.config.get("sheets_service")
    if not sheets_service:
        return render_page("producao.html", itens=[], mensagem="Serviço de planilhas indisponível", read_only=True, tipo_mensagem="danger"), 503
    read_only = _get_current_user_role() != Role.ADMIN.value
    if request.method == "POST":
        if read_only:
            flash("Operadores têm acesso somente visualização nesta página.", "warning")
            return redirect(url_for("producao.producao"))
        try:
            nome_item = request.form.get("nome_item", "").strip()
            codigo_item = _format_codigo_code(request.form.get("codigo_item", "").strip())
            quantidade_produzida = _parse_int_field(request.form.get("quantidade_produzida", 0), 0)
            observacao = request.form.get("observacao", "").strip()
            valido, mensagem = _validate_item_form_data(nome_item, codigo_item, quantidade_produzida, observacao)
            if not valido:
                flash(mensagem, "danger")
                return redirect(url_for("producao.producao"))
            dados = [
                datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M:%S"), nome_item, codigo_item,
                _format_mtc_code(request.form.get("mtc_projeto", "")), str(quantidade_produzida),
                str(_parse_int_field(request.form.get("meta_producao", 0), 0)),
                request.form.get("status", "Em andamento").strip() or "Em andamento", observacao,
                request.form.get("responsavel", "").strip(), request.form.get("informacoes_adicionais", "").strip(), "produção",
            ]
            if not dados[1] or not dados[2]:
                flash("Nome do item e código são obrigatórios.", "danger")
                return redirect(url_for("producao.producao"))
            item_id = str(int(datetime.now(timezone.utc).timestamp() * 1000))
            if not sheets_service.add_producao([item_id] + dados):
                flash("Erro ao salvar item de produção.", "danger")
                return redirect(url_for("producao.producao"))
            flash("Item de produção cadastrado com sucesso!", "success")
            return redirect(url_for("producao.producao"))
        except (RuntimeError, ValueError, TypeError, OSError) as exc:
            logger.exception("Erro ao cadastrar produção")
            if current_app.config.get("APP_ENV", "production") == "production":
                flash("Erro ao cadastrar item.", "danger")
            else:
                flash(f"Erro ao cadastrar item: {exc}", "danger")
            return redirect(url_for("producao.producao"))
    try:
        itens = sheets_service.get_all_producao(use_cache=True)
        itens_ordenados = sorted(itens, key=lambda item: item.get("row_id", 0), reverse=True)
        return render_page("producao.html", itens=itens_ordenados, read_only=read_only)
    except (RuntimeError, ValueError, TypeError, OSError) as exc:
        logger.exception("Erro ao carregar produção")
        return render_page("erro.html", mensagem=f"Erro ao processar dados: {exc}"), 500


@producao_bp.route("/producao/atualizar/<int:row_id>", methods=["POST"])
@admin_required
def atualizar_producao(row_id):
    """Atualiza um item de produção existente."""
    sheets_service = current_app.config.get("sheets_service")
    if not sheets_service:
        return jsonify({"success": False, "message": "Serviço indisponível"}), 503
    try:
        original = sheets_service.get_producao_by_row_id(row_id) or {}
        if not original:
            return jsonify({"success": False, "message": "Item não encontrado."}), 404
        nome_item = request.form.get("nome_item", original.get("Nome do item", "")).strip()
        codigo_item = _format_codigo_code(request.form.get("codigo_item", original.get("Código", "")).strip())
        quantidade_produzida = _parse_int_field(request.form.get("quantidade_produzida", original.get("Quantidade produzida", 0)), 0)
        observacao = request.form.get("observacao", original.get("Observação", "")).strip()
        valido, mensagem = _validate_item_form_data(nome_item, codigo_item, quantidade_produzida, observacao)
        if not valido:
            return jsonify({"success": False, "message": mensagem}), 400
        row_data = [
            str(original.get("ID", "") or original.get("id", "") or row_id), str(original.get("Carimbo de data/hora", "")).strip(),
            nome_item, codigo_item, _format_mtc_code(request.form.get("mtc_projeto", original.get("Número do projeto MTC", ""))),
            str(quantidade_produzida), str(_parse_int_field(request.form.get("meta_producao", original.get("Meta de produção", 0)), 0)),
            request.form.get("status", original.get("Status", "Em andamento")).strip() or "Em andamento", observacao,
            request.form.get("responsavel", original.get("Responsável", "")).strip(),
            _append_producao_info(original.get("Informações adicionais", ""), request.form.get("nova_informacao", "")),
            str(original.get("Origem", "produção")).strip() or "produção",
        ]
        if not row_data[2] or not row_data[3]:
            return jsonify({"success": False, "message": "Nome do item e código são obrigatórios."}), 400
        if not sheets_service.update_producao(row_id, row_data):
            return jsonify({"success": False, "message": "Não foi possível atualizar o item."}), 500
        return jsonify({"success": True, "message": "Item atualizado com sucesso!"}), 200
    except (RuntimeError, ValueError, TypeError, OSError) as exc:
        logger.exception("Erro ao atualizar produção")
        return jsonify({"success": False, "message": str(exc)}), 500


@producao_bp.route("/producao/dados")
@admin_required
@cache.cached(timeout=30)
def producao_dados():
    """Retorna os dados agregados da produção para atualização em tempo real."""
    sheets_service = current_app.config.get("sheets_service")
    if not sheets_service:
        return jsonify({"success": False, "message": "Serviço indisponível"}), 503
    try:
        itens_brutos = sheets_service.get_all_producao(use_cache=False, force_refresh=True)
        itens = [item for item in itens_brutos if str(item.get("Status", "")).strip().lower() not in {"cancelado", "cancelada"}]
        summary = {"total_itens": len(itens), "total_produzido": 0, "total_meta": 0, "total_faltante": 0, "percentual_global": 0}
        barras, status_counts, responsavel_counts = [], {"Concluído": 0, "Em andamento": 0, "Pendente": 0}, {}

        def _status_bucket(valor):
            texto = str(valor or "").strip().lower()
            if texto in ("concluído", "concluido", "finalizado", "finalizada"):
                return "Concluído"
            if texto in ("em andamento", "andamento"):
                return "Em andamento"
            return "Pendente"

        for item in itens:
            produzido = _parse_int_field(item.get("Quantidade produzida", 0), 0)
            meta = _parse_int_field(item.get("Meta de produção", 0), 0)
            summary["total_produzido"] += produzido
            summary["total_meta"] += meta
            barras.append({"nome": item.get("Nome do item", ""), "produzido": produzido, "restante": max(meta - produzido, 0), "meta": meta, "status": item.get("Status", ""), "percentual": round((produzido / meta) * 100, 1) if meta else 0})
            status_counts[_status_bucket(item.get("Status", ""))] += 1
            responsavel = str(item.get("Responsável", "")).strip() or "Não atribuído"
            responsavel_counts[responsavel] = responsavel_counts.get(responsavel, 0) + 1
        summary["total_faltante"] = max(summary["total_meta"] - summary["total_produzido"], 0)
        summary["percentual_global"] = round((summary["total_produzido"] / summary["total_meta"]) * 100, 1) if summary["total_meta"] else 0
        status_order = [key for key, _ in sorted(status_counts.items(), key=lambda pair: -pair[1])]
        status_rank = {status: index for index, status in enumerate(status_order)}
        barras.sort(key=lambda item: (status_rank.get(item.get("status", ""), len(status_rank)), item.get("nome", "") or ""))
        return jsonify({"success": True, "summary": summary, "items": barras, "status_counts": status_counts, "responsavel_counts": responsavel_counts}), 200
    except (RuntimeError, ValueError, TypeError, OSError) as exc:
        logger.exception("Erro ao gerar dados de produção")
        return jsonify({"success": False, "message": str(exc)}), 500


@producao_bp.route("/producao-abertas")
@login_required
def producao_abertas():
    """Página que mostra as OPs de produção que não estão concluídas ou bloqueadas."""
    sheets_service = current_app.config.get("sheets_service")
    if not sheets_service:
        return render_page("producao_abertas.html", itens=[], mensagem="Serviço de planilhas indisponível", tipo_mensagem="danger"), 503
    try:
        itens = sheets_service.get_all_producao(use_cache=True)
        status_excluidos = {"concluído", "concluido", "bloqueado", "bloqueada", "cancelado", "cancelada"}
        itens_abertos = [item for item in itens if str(item.get("Status", "")).strip().lower() not in status_excluidos]
        total_itens = len(itens)
        itens_bloqueados = sum(1 for item in itens if str(item.get("Status", "")).strip().lower() in {"bloqueado", "bloqueada"})
        itens_concluidos = sum(1 for item in itens if str(item.get("Status", "")).strip().lower() in {"concluído", "concluido"})
        taxa_conclusao = round((itens_concluidos / total_itens * 100), 1) if total_itens > 0 else 0
        itens_ordenados = sorted(itens_abertos, key=lambda item: item.get("row_id", 0), reverse=True)
        return render_page("producao_abertas.html", itens=itens_ordenados, total_ops_abertas=len(itens_abertos), itens_bloqueados=itens_bloqueados, taxa_conclusao=taxa_conclusao)
    except (RuntimeError, ValueError, TypeError, OSError, AttributeError, KeyError) as exc:
        return render_route_error(exc, user_message="Erro ao carregar dados de produção em aberto.")


@producao_bp.route("/dashboard-producao")
@login_required
def dashboard_producao():
    """Exibe o painel visual de produção."""
    sheets_service = current_app.config.get("sheets_service")
    if not sheets_service:
        return render_page("dashboard_producao.html", mensagem_erro="Serviço indisponível"), 503
    return render_page("dashboard_producao.html")