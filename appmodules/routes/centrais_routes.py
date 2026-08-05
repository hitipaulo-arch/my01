from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
    current_app,
)
import pandas as pd
import logging

from appmodules.utils import admin_required

logger = logging.getLogger(__name__)

centrais_bp = Blueprint(
    "centrais", __name__, template_folder="../../templates", static_folder="../../static"
)


@centrais_bp.route("/centrais", methods=["GET", "POST"])
@admin_required
def centrais():
    """Página de controle de centrais."""
    repo = current_app.config.get("centrais_repository")
    if not repo:
        return render_template(
            "centrais.html",
            centrais=[],
            mensagem="Serviço de repositório de centrais indisponível",
            tipo_mensagem="danger",
        ), 503

    if request.method == "POST":
        try:
            dados = {
                "Número de Portas": request.form.get("num_portas", ""),
                "Código de Série": request.form.get("codigo_serie", ""),
                "Status": request.form.get("status", ""),
                "Obra Utilizada": request.form.get("obra", ""),
                "Data Cadastro": pd.Timestamp.now().strftime("%d/%m/%Y %H:%M:%S"),
                "Programação": "",
                "Programação Resumo": "",
            }
            repo.add(dados)
            flash("Central cadastrada com sucesso!", "success")
            return redirect(url_for("centrais.centrais"))
        except Exception as e:
            logger.error(f"Erro ao adicionar central: {e}", exc_info=True)
            flash(f"Erro ao adicionar central: {e}", "danger")
            return redirect(url_for("centrais.centrais"))

    # GET
    try:
        lista_centrais = repo.get_all()
        return render_template("centrais.html", centrais=lista_centrais)
    except Exception as e:
        logger.error(f"Erro ao listar centrais: {e}", exc_info=True)
        return render_template(
            "centrais.html",
            centrais=[],
            mensagem=f"Erro ao carregar dados: {e}",
            tipo_mensagem="danger",
        )


@centrais_bp.route("/centrais/atualizar/<int:row_id>", methods=["POST"])
@admin_required
def atualizar_central(row_id):
    """Atualiza status de uma central."""
    repo = current_app.config.get("centrais_repository")
    if not repo:
        return jsonify({"success": False, "message": "Serviço indisponível"}), 503

    try:
        status = request.form.get("status", "")
        obra = request.form.get("obra", "")
        repo.update(row_id, status, obra)
        return jsonify({"success": True, "message": "Central atualizada!"})
    except Exception as e:
        logger.error(f"Erro ao atualizar central: {e}", exc_info=True)
        return jsonify({"success": False, "message": str(e)}), 500


@centrais_bp.route("/centrais/programacao/<int:row_id>", methods=["POST"])
@admin_required
def atualizar_programacao_central(row_id):
    """Atualiza a programação de uma central."""
    repo = current_app.config.get("centrais_repository")
    if not repo:
        return jsonify({"success": False, "message": "Serviço indisponível"}), 503

    try:
        programacao = request.form.get("programacao", "")
        resumo = repo.update_programacao(row_id, programacao)
        return jsonify(
            {"success": True, "message": "Programação atualizada!", "resumo": resumo}
        )
    except Exception as e:
        logger.error(f"Erro ao atualizar programação da central: {e}", exc_info=True)
        return jsonify({"success": False, "message": str(e)}), 500


@centrais_bp.route("/centrais/deletar/<int:row_id>", methods=["POST"])
@admin_required
def deletar_central(row_id):
    """Deleta uma central."""
    repo = current_app.config.get("centrais_repository")
    if not repo:
        return jsonify({"success": False, "message": "Serviço indisponível"}), 503

    try:
        repo.delete(row_id)
        return jsonify({"success": True, "message": "Central deletada!"})
    except Exception as e:
        logger.error(f"Erro ao deletar central: {e}", exc_info=True)
        return jsonify({"success": False, "message": str(e)}), 500