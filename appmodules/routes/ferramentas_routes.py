"""Rotas administrativas de ferramentas."""

import logging
from datetime import datetime

from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, session, url_for

from appmodules.repositories.ferramentas_repository import add_historico_entry, get_ferramentas_list, get_or_create_ferramentas_worksheet, get_or_create_historico_worksheet
from appmodules.utils import admin_required

logger = logging.getLogger(__name__)
ferramentas_bp = Blueprint("ferramentas", __name__)


@ferramentas_bp.route("/ferramentas", methods=["GET", "POST"])
@admin_required
def ferramentas():
    """Página de controle de ferramentas."""
    sheets_service = current_app.config.get("sheets_service")
    if not sheets_service:
        return render_template("ferramentas.html", ferramentas=[], mensagem="Serviço de planilhas indisponível", tipo_mensagem="danger"), 503
    if request.method == "POST":
        try:
            dados = [request.form.get("nome", ""), request.form.get("patrocinio", ""), datetime.now().strftime("%d/%m/%Y"), request.form.get("ultima_manutencao", ""), request.form.get("status", "Disponível"), request.form.get("observacao", ""), request.form.get("responsavel", "")]
            get_or_create_ferramentas_worksheet(sheets_service).append_row(dados)
            detalhes_hist = f"Patrocínio: {dados[1]}, Responsável: {dados[6]}, Status: {dados[4]}, Obs: {dados[5]}"
            add_historico_entry(sheets_service, dados[0], "Cadastro", session.get("usuario", "desconhecido"), detalhes_hist)
            flash("Ferramenta cadastrada com sucesso!", "success")
            return redirect(url_for("ferramentas.ferramentas"))
        except Exception as exc:
            logger.error("Erro ao adicionar ferramenta: %s", exc, exc_info=True)
            flash(f"Erro ao adicionar ferramenta: {exc}", "danger")
            return redirect(url_for("ferramentas.ferramentas"))
    flashes = session.get("_flashes", [])
    tipo_mensagem, mensagem = flashes[0] if flashes else (None, None)
    return render_template("ferramentas.html", ferramentas=get_ferramentas_list(sheets_service), mensagem=mensagem, tipo_mensagem=tipo_mensagem)


@ferramentas_bp.route("/ferramentas/atualizar/<int:row_id>", methods=["POST"])
@admin_required
def atualizar_ferramenta(row_id):
    """Atualiza uma ferramenta."""
    sheets_service = current_app.config.get("sheets_service")
    if not sheets_service:
        return jsonify({"success": False, "message": "Serviço indisponível"}), 503
    try:
        worksheet = get_or_create_ferramentas_worksheet(sheets_service)
        row_num = row_id + 2
        dados_atuais = worksheet.row_values(row_num)
        nome_ferramenta = dados_atuais[0] if dados_atuais else "Desconhecida"
        novo_responsavel = request.form.get("responsavel", "")
        nova_manutencao = request.form.get("ultima_manutencao", "")
        novo_status = request.form.get("status", "")
        nova_observacao = request.form.get("observacao", "")
        old_manutencao = dados_atuais[3] if len(dados_atuais) > 3 else ""
        old_status = dados_atuais[4] if len(dados_atuais) > 4 else ""
        old_observacao = dados_atuais[5] if len(dados_atuais) > 5 else ""
        old_responsavel = dados_atuais[6] if len(dados_atuais) > 6 else ""
        worksheet.update(f"D{row_num}:G{row_num}", [[nova_manutencao, novo_status, nova_observacao, novo_responsavel]])
        changes = []
        if novo_responsavel != old_responsavel:
            changes.append(f"Responsável: {old_responsavel or '-'} → {novo_responsavel or '-'}")
        if nova_manutencao != old_manutencao:
            changes.append(f"Manutenção: {old_manutencao or '-'} → {nova_manutencao or '-'}")
        if novo_status != old_status:
            changes.append(f"Status: {old_status or '-'} → {novo_status or '-'}")
        if nova_observacao != old_observacao:
            changes.append(f"Obs: {old_observacao or '-'} → {nova_observacao or '-'}")
        add_historico_entry(sheets_service, nome_ferramenta, "Edição", session.get("usuario", "desconhecido"), ", ".join(changes) if changes else "Sem alterações")
        return jsonify({"success": True, "message": "Ferramenta atualizada!"})
    except Exception as exc:
        logger.error("Erro ao atualizar ferramenta: %s", exc, exc_info=True)
        return jsonify({"success": False, "message": str(exc)}), 500


@ferramentas_bp.route("/ferramentas/deletar/<int:row_id>", methods=["POST"])
@admin_required
def deletar_ferramenta(row_id):
    """Deleta uma ferramenta."""
    sheets_service = current_app.config.get("sheets_service")
    if not sheets_service:
        return jsonify({"success": False, "message": "Serviço indisponível"}), 503
    try:
        worksheet = get_or_create_ferramentas_worksheet(sheets_service)
        row_num = row_id + 2
        dados_atuais = worksheet.row_values(row_num)
        nome_ferramenta = dados_atuais[0] if dados_atuais else "Desconhecida"
        worksheet.delete_rows(row_num)
        add_historico_entry(sheets_service, nome_ferramenta, "Exclusão", session.get("usuario", "desconhecido"), "Ferramenta excluída")
        return jsonify({"success": True, "message": "Ferramenta deletada!"})
    except Exception as exc:
        logger.error("Erro ao deletar ferramenta: %s", exc, exc_info=True)
        return jsonify({"success": False, "message": str(exc)}), 500


@ferramentas_bp.route("/ferramentas/historico")
@admin_required
def historico_ferramentas():
    """Retorna o histórico de uma ferramenta em JSON."""
    sheets_service = current_app.config.get("sheets_service")
    if not sheets_service:
        return jsonify({"success": False, "historico": []})
    try:
        todos = get_or_create_historico_worksheet(sheets_service).get_all_records()
        nome = request.args.get("nome", "")
        filtrado = [registro for registro in todos if not nome or registro.get("Ferramenta", "").lower() == nome.lower()]
        return jsonify({"success": True, "historico": list(reversed(filtrado))})
    except Exception as exc:
        logger.error("Erro ao obter histórico: %s", exc)
        return jsonify({"success": False, "historico": [], "error": str(exc)})


__all__ = ["ferramentas_bp", "ferramentas", "atualizar_ferramenta", "deletar_ferramenta", "historico_ferramentas"]