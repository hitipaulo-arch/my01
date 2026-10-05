"""Rotas de itens e compras."""

import logging
from datetime import datetime, timezone

from flask import Blueprint, current_app, flash, redirect, request, url_for

from appmodules.mobile import render_page
from appmodules.models.usuario import Role
from appmodules.routes.producao_routes import _get_current_user_role, _validate_item_form_data
from appmodules.utils import login_required
from appmodules.utils.formatters import _format_codigo_code, _format_mtc_code
from appmodules.utils.validators import _parse_int_field
from config import Config

logger = logging.getLogger(__name__)
compras_bp = Blueprint("compras", __name__)


@compras_bp.route("/itens", methods=["GET", "POST"])
@compras_bp.route("/compras", methods=["GET", "POST"])
@login_required
def itens():
    """Exibe e cadastra itens com alerta automático de compra."""
    sheets_service = current_app.config.get("sheets_service")
    if not sheets_service:
        return render_page("compras.html", itens=[], read_only=True), 503
    read_only = _get_current_user_role() != Role.ADMIN.value
    val_cfg = Config.VALIDATION
    min_nome, max_nome = val_cfg.MIN_NOME_ITEM_LENGTH, val_cfg.MAX_NOME_ITEM_LENGTH
    max_obs, max_qtd = val_cfg.MAX_OBSERVACAO_LENGTH, val_cfg.MAX_QUANTIDADE
    threshold_default = val_cfg.ITEM_ALERT_THRESHOLD_DEFAULT
    thresholds_especificos = val_cfg.ITEM_ALERT_THRESHOLDS or {}

    def _threshold_para_item(nome_item):
        if not thresholds_especificos:
            return threshold_default
        return int(thresholds_especificos.get((nome_item or "").strip().lower(), threshold_default))

    def _processar_item_compra(item):
        quantidade = _parse_int_field(item.get("Quantidade produzida", item.get("Quantidade", item.get("Quantidade Item", item.get("Quantidade produzida ", 0)))), 0)
        nome_item_atual = str(item.get("Nome do item", "")).strip()
        threshold_item = _threshold_para_item(nome_item_atual)
        status_compra = "precisa solicitar comprar" if quantidade <= threshold_item else "não precisa solicitar comprar"
        return {"nome_item": nome_item_atual, "codigo_item": item.get("Código", ""), "mtc_projeto": _format_mtc_code(item.get("Número do projeto MTC", "")), "quantidade": quantidade, "status_compra": status_compra, "row_id": item.get("row_id"), "threshold": threshold_item}

    try:
        if request.method == "POST":
            if read_only:
                flash("Operadores têm acesso somente visualização nesta página.", "warning")
                return redirect(url_for("compras.itens"))
            nome_item = request.form.get("nome_item", "").strip()
            codigo_item = _format_codigo_code(request.form.get("codigo_item", "").strip())
            mtc_projeto = _format_mtc_code(request.form.get("mtc_projeto", ""))
            quantidade_raw = _parse_int_field(request.form.get("quantidade", 0), 0)
            observacao = request.form.get("observacao", "").strip()
            if len(nome_item) < min_nome:
                flash(f"O nome do item deve ter pelo menos {min_nome} caracteres.", "danger")
                return redirect(url_for("compras.itens"))
            if len(nome_item) > max_nome:
                flash(f"O nome do item deve ter no máximo {max_nome} caracteres.", "danger")
                return redirect(url_for("compras.itens"))
            if len(observacao) > max_obs:
                flash(f"A observação deve ter no máximo {max_obs} caracteres.", "danger")
                return redirect(url_for("compras.itens"))
            if quantidade_raw < 0:
                flash("A quantidade não pode ser negativa.", "danger")
                return redirect(url_for("compras.itens"))
            if quantidade_raw > max_qtd:
                flash(f"A quantidade não pode ser maior que {max_qtd:,}.".replace(",", "."), "danger")
                return redirect(url_for("compras.itens"))
            if not nome_item or not codigo_item:
                flash("Nome do item e código são obrigatórios.", "danger")
                return redirect(url_for("compras.itens"))
            try:
                for existente in sheets_service.get_all_producao(use_cache=True):
                    if str(existente.get("Origem", "")).strip().lower() != "item":
                        continue
                    if _format_codigo_code(str(existente.get("Código", "")).strip()) == codigo_item:
                        flash(f"Já existe um item cadastrado com o código {codigo_item}.", "warning")
                        return redirect(url_for("compras.itens"))
            except (RuntimeError, ValueError, TypeError, OSError) as dup_err:
                logger.warning("Não foi possível verificar duplicidade de itens: %s", dup_err)
            row_data = [str(int(datetime.now(timezone.utc).timestamp() * 1000)), datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M:%S"), nome_item, codigo_item, mtc_projeto, str(quantidade_raw), "0", "Em andamento", observacao, "", "", "item"]
            if not sheets_service.add_producao(row_data):
                flash("Não foi possível adicionar o item.", "danger")
                return redirect(url_for("compras.itens"))
            flash("Item adicionado com sucesso!", "success")
            return redirect(url_for("compras.itens"))
        sheets_service.marcar_origem_padrao_producao("produção")
        itens_alerta, itens_normais = [], []
        for item in sheets_service.get_all_producao(use_cache=True):
            if str(item.get("Origem", "")).strip().lower() != "item":
                continue
            item_compra = _processar_item_compra(item)
            (itens_alerta if item_compra["quantidade"] <= item_compra["threshold"] else itens_normais).append(item_compra)
        itens_alerta.sort(key=lambda item: item.get("quantidade", 0))
        itens_normais.sort(key=lambda item: item.get("quantidade", 0), reverse=True)
        return render_page("compras.html", itens_alerta=itens_alerta, itens_normais=itens_normais, read_only=read_only, stats={"total_itens": len(itens_alerta) + len(itens_normais), "total_alerta": len(itens_alerta), "total_normais": len(itens_normais), "total_estoque": sum(item.get("quantidade", 0) for item in itens_alerta + itens_normais), "threshold_default": threshold_default})
    except (RuntimeError, ValueError, TypeError, OSError) as exc:
        logger.exception("Erro ao carregar compras")
        return render_page("erro.html", mensagem=f"Erro ao processar dados: {exc}"), 500


def _extract_and_format_item_form(form_data, item_original):
    """Extrai, valida e formata os dados do formulário de edição."""
    nome_item = str(form_data.get("nome_item", "")).strip()
    codigo_item = _format_codigo_code(str(form_data.get("codigo_item", "")).strip())
    mtc_projeto = _format_mtc_code(str(form_data.get("mtc_projeto", "")).strip())
    quantidade_raw = _parse_int_field(form_data.get("quantidade", "0"), 0)
    observacao = str(form_data.get("observacao", "")).strip()
    valido, mensagem = _validate_item_form_data(nome_item, codigo_item, quantidade_raw, observacao)
    if not valido:
        return False, mensagem, None
    return True, "", [item_original.get("ID", ""), item_original.get("Carimbo de data/hora", ""), nome_item, codigo_item, mtc_projeto, str(quantidade_raw), item_original.get("Meta de produção", "0"), item_original.get("Status", "Em andamento"), observacao, item_original.get("Responsável", ""), item_original.get("Informações adicionais", ""), item_original.get("Origem", "item")]


@compras_bp.route("/itens/<int:row_id>/editar", methods=["GET", "POST"])
@login_required
def editar_item(row_id):
    """Edita um item de produção."""
    sheets_service = current_app.config.get("sheets_service")
    if not sheets_service:
        flash("Serviço de planilhas indisponível.", "danger")
        return redirect(url_for("compras.itens"))
    item = sheets_service.get_producao_by_row_id(row_id)
    if not item:
        flash("Item não encontrado.", "danger")
        return redirect(url_for("compras.itens"))
    if request.method == "POST":
        try:
            valido, mensagem, row_data = _extract_and_format_item_form(request.form, item)
            if not valido:
                flash(mensagem, "danger")
                return redirect(url_for("compras.editar_item", row_id=row_id))
            if not sheets_service.update_producao(row_id, row_data):
                flash("Não foi possível atualizar o item.", "danger")
                return redirect(url_for("compras.editar_item", row_id=row_id))
            flash("Item atualizado com sucesso!", "success")
            return redirect(url_for("compras.itens"))
        except (RuntimeError, ValueError, TypeError, OSError) as exc:
            logger.exception("Erro ao editar item")
            flash(f"Erro ao editar item: {exc}", "danger")
            return redirect(url_for("compras.editar_item", row_id=row_id))
    return render_page("editar_item.html", item=item, row_id=row_id)


@compras_bp.route("/itens/<int:row_id>/excluir", methods=["POST"])
@compras_bp.route("/itens/<int:row_id>/deletar", methods=["POST"])
@login_required
def excluir_item(row_id):
    """Exclui um item de produção."""
    sheets_service = current_app.config.get("sheets_service")
    if not sheets_service:
        flash("Serviço de planilhas indisponível.", "danger")
        return redirect(url_for("compras.itens"))
    try:
        if not sheets_service.delete_producao(row_id):
            flash("Não foi possível excluir o item.", "danger")
            return redirect(url_for("compras.itens"))
        flash("Item excluído com sucesso!", "success")
    except (RuntimeError, ValueError, TypeError, OSError) as exc:
        logger.exception("Erro ao excluir item")
        flash(f"Erro ao excluir item: {exc}", "danger")
    return redirect(url_for("compras.itens"))