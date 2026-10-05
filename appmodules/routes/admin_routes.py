"""Rotas de administração."""

import logging

from flask import Blueprint, Response, current_app, request, session

from appmodules.mobile import render_page
from appmodules.logic import gerar_dados_relatorio
from appmodules.models.usuario import Role
from appmodules.services import MetricsService
from appmodules.services.ai_service import (
    build_admin_ai_context as default_build_admin_ai_context,
    get_ai_model_candidates as default_get_ai_model_candidates,
    get_nvidia_ai_client as default_get_nvidia_ai_client,
)
from appmodules.utils import admin_required
from appmodules.utils.validators import validate_user_payload
from config import Config

logger = logging.getLogger(__name__)
admin_bp = Blueprint("admin", __name__)


def _validate_user_payload(payload=None, *, username=None, senha=None, role=None):
    """Adapter para o payload JSON e a assinatura de formulário legada."""
    if payload is not None:
        return validate_user_payload(payload)
    errors = []
    if not username or len(str(username).strip()) < Config.VALIDATION.MIN_USERNAME_LENGTH:
        errors.append("Username deve ter no mínimo 3 caracteres.")
    if not senha or len(str(senha)) < Config.VALIDATION.MIN_PASSWORD_LENGTH:
        errors.append("Senha deve ter no mínimo 12 caracteres.")
    if role not in {item.value for item in Role}:
        errors.append("Role inválida.")
    if errors:
        return False, " ".join(errors)
    return True, ""


def _provider_config(name, fallback):
    return current_app.config.get(name, fallback)


def _texto_pdf(valor):
    """Escapa texto para o operador Tj do PDF usando a codificação Latin-1."""
    texto = str(valor or "").replace("\\", "\\\\")
    texto = texto.replace("(", "\\(").replace(")", "\\)")
    return texto.encode("latin-1", "replace").decode("latin-1")


def _gerar_pdf_relatorio(dados_relatorio):
    """Gera um PDF visual com resumo, graficos e atividades do mes."""
    mes = dados_relatorio.get("mes_relatorio", "")
    atividades = dados_relatorio.get("atividades_mes", [])
    paginas = []

    def texto(x, y, valor, tamanho=9, cor="0.12 0.16 0.22"):
        return (
            f"{cor} rg BT /F1 {tamanho} Tf {x} {y} Td "
            f"({_texto_pdf(str(valor)[:90])}) Tj ET"
        )

    def grafico_barras(comandos, x, y, largura, altura, titulo, labels, valores, cor):
        comandos.extend([
            "0.97 0.98 1 rg",
            f"{x} {y} {largura} {altura} re f",
            texto(x + 12, y + altura - 20, titulo, 11, "0.08 0.25 0.42"),
        ])
        if not valores:
            comandos.append(texto(x + 12, y + altura / 2, "Sem dados para exibir", 9, "0.45 0.48 0.52"))
            return
        maior = max([float(valor or 0) for valor in valores] + [1])
        largura_barra = (largura - 120) / max(len(valores), 1)
        for indice, valor in enumerate(valores[:8]):
            altura_barra = max(2, (float(valor or 0) / maior) * (altura - 75))
            barra_x = x + 55 + indice * largura_barra
            comandos.extend([
                "0.12 0.47 0.68 rg",
                f"{barra_x:.1f} {y + 35:.1f} {max(largura_barra - 10, 4):.1f} {altura_barra:.1f} re f",
                texto(barra_x, y + 22, str(labels[indice])[:11], 7, "0.25 0.29 0.34"),
                texto(barra_x, y + 40 + altura_barra, str(valores[indice]), 7, "0.08 0.25 0.42"),
            ])

    capa = [
        "1 1 1 rg 0 0 595 842 re f",
        "0.08 0.25 0.42 rg 0 765 595 77 re f",
        texto(40, 808, "RELATORIO DE ATIVIDADES", 20, "1 1 1"),
        texto(40, 785, f"Resumo mensal - {mes}", 10, "0.82 0.91 0.96"),
    ]
    cards = [
        ("Total de atividades", dados_relatorio.get("total_atividades_mes", 0)),
        ("Total de OS", dados_relatorio.get("total_os", 0)),
        ("Finalizadas", dados_relatorio.get("total_finalizadas", 0)),
        ("Taxa de conclusao", dados_relatorio.get("taxa_conclusao", "0%")),
        ("Tempo medio", dados_relatorio.get("tempo_medio", "N/A")),
    ]
    for indice, (rotulo, valor) in enumerate(cards):
        x = 40 + indice * 105
        capa.extend([
            "0.95 0.97 0.99 rg",
            f"{x} 680 95 55 re f",
            texto(x + 10, 718, rotulo, 7, "0.35 0.40 0.46"),
            texto(x + 10, 692, valor, 17, "0.08 0.25 0.42"),
        ])
    grafico_barras(
        capa, 40, 435, 250, 215, "Distribuicao por prioridade",
        dados_relatorio.get("labels_prioridade", []),
        dados_relatorio.get("dados_prioridade", []),
        "0.12 0.47 0.68",
    )
    grafico_barras(
        capa, 305, 435, 250, 215, "Atividades por setor",
        dados_relatorio.get("labels_setor", []),
        dados_relatorio.get("dados_setor", []),
        "0.12 0.47 0.68",
    )
    capa.extend([
        texto(40, 400, "Atividades detalhadas", 13, "0.08 0.25 0.42"),
        texto(40, 380, "Consulte as paginas seguintes para ver todos os registros do periodo.", 9, "0.35 0.40 0.46"),
    ])
    paginas.append(capa)

    for inicio in range(0, len(atividades), 32):
        comandos = [
            "1 1 1 rg 0 0 595 842 re f",
            "0.08 0.25 0.42 rg 0 785 595 57 re f",
            texto(40, 810, "ATIVIDADES DO MES", 16, "1 1 1"),
            texto(40, 793, f"Periodo: {mes}", 9, "0.82 0.91 0.96"),
        ]
        colunas = [
            (40, "Data", 85),
            (125, "Solicitante", 110),
            (235, "Setor", 85),
            (320, "Status", 85),
            (405, "Tempo", 70),
            (475, "Descricao", 75),
        ]
        for x, titulo, largura in colunas:
            comandos.extend([
                "0.12 0.47 0.68 rg",
                f"{x} 750 {largura} 24 re f",
                texto(x + 5, 758, titulo, 8, "1 1 1"),
            ])
        registros = atividades[inicio:inicio + 32]
        for linha, atividade in enumerate(registros):
            y = 730 - linha * 20
            if linha % 2 == 0:
                comandos.extend(["0.95 0.97 0.99 rg", f"40 {y - 5} 510 20 re f"])
            valores = [
                atividade.get("data", ""),
                atividade.get("solicitante", ""),
                atividade.get("setor", ""),
                atividade.get("status", ""),
                atividade.get("tempo_conclusao", "N/A"),
                atividade.get("descricao", ""),
            ]
            for (x, _, _), valor in zip(colunas, valores):
                texto_valor = str(valor)
                if len(texto_valor) > 35:
                    texto_valor = texto_valor[:35] + "..."
                comandos.append(texto(x + 5, y, texto_valor, 7, "0.12 0.16 0.22"))
        comandos.append(texto(40, 25, f"Pagina {len(paginas) + 1}", 8, "0.45 0.48 0.52"))
        paginas.append(comandos)
    if not atividades:
        paginas.append(["1 1 1 rg 0 0 595 842 re f", texto(40, 780, "Nenhuma atividade encontrada para este periodo.", 11)])

    objetos = []
    objetos.append("<< /Type /Catalog /Pages 2 0 R >>")
    objetos.append("")
    objetos.append("")
    objetos.append("<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>")

    paginas_referencias = []
    for comandos in paginas:
        conteudo = "\n".join(comandos).encode("latin-1", "replace")
        conteudo_id = len(objetos) + 1
        objetos.append(f"<< /Length {len(conteudo)} >>\nstream\n{conteudo.decode('latin-1')}\nendstream")
        pagina_id = len(objetos) + 1
        objetos.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            f"/Resources << /Font << /F1 4 0 R >> >> /Contents {conteudo_id} 0 R >>"
        )
        paginas_referencias.append(f"{pagina_id} 0 R")

    objetos[1] = f"<< /Type /Pages /Kids [{' '.join(paginas_referencias)}] /Count {len(paginas_referencias)} >>"
    objetos[2] = "<< /Title (Relatorio de atividades) /Author (Sistema de OS) >>"

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for indice, objeto in enumerate(objetos, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{indice} 0 obj\n{objeto}\nendobj\n".encode("latin-1", "replace"))
    xref = len(pdf)
    pdf.extend(f"xref\n0 {len(objetos) + 1}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode())
    pdf.extend(
        f"trailer\n<< /Size {len(objetos) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    return bytes(pdf)


@admin_bp.route("/usuarios", methods=["GET", "POST"])
@admin_required
def usuarios_admin():
    """Admin UI para gerenciar usuários."""
    user_service = current_app.config.get("user_service")
    mensagem = None
    tipo_mensagem = "success"
    if request.method == "POST":
        if not user_service:
            mensagem = "Serviço de usuários não disponível."
            tipo_mensagem = "danger"
        else:
            acao = request.form.get("acao")
            username = request.form.get("username", "").strip()
            if not username:
                mensagem = "Username é obrigatório."
                tipo_mensagem = "danger"
            elif acao == "delete":
                if user_service.deletar_usuario(username):
                    mensagem = f"Usuário {username} removido com sucesso."
                else:
                    mensagem = f"Erro ao remover usuário {username}."
                    tipo_mensagem = "danger"
            else:
                senha = request.form.get("senha", "").strip()
                role = request.form.get("role", Role.VISUALIZADOR.value).strip().lower()
                valido, mensagem_validacao = _validate_user_payload(
                    username=username, senha=senha, role=role
                )
                if not valido:
                    mensagem = mensagem_validacao
                    tipo_mensagem = "danger"
                elif user_service.criar_usuario(username, senha, role):
                    mensagem = f"Usuário {username} criado com sucesso."
                else:
                    erro_detalhe = getattr(user_service, "last_error", None)
                    if erro_detalhe and "protected" in erro_detalhe.lower():
                        mensagem = (
                            f"Erro ao criar usuário {username}: a aba de usuários está protegida no Google Sheets. "
                            "Remova a proteção ou conceda permissão de edição à service account."
                        )
                    elif erro_detalhe:
                        mensagem = f"Erro ao criar usuário {username}: {erro_detalhe}"
                    else:
                        mensagem = f"Erro ao criar usuário {username}."
                    tipo_mensagem = "danger"
    usuarios = user_service.get_todos_usuarios() if user_service else []
    usuarios_dict = {user.username: user.to_dict() for user in usuarios}
    return render_page(
        "usuarios.html", usuarios=usuarios_dict, mensagem=mensagem, tipo_mensagem=tipo_mensagem
    )


@admin_bp.route("/relatorios")
@admin_bp.route("/auditoria")
@admin_required
def relatorios():
    """Página de relatórios."""
    try:
        mes_referencia = request.args.get("mes", "").strip()
        dados_relatorio = gerar_dados_relatorio(
            current_app.config.get("sheets_service"), mes_referencia
        )
        if request.args.get("download") == "1" and dados_relatorio.get("mes_relatorio"):
            conteudo_pdf = _gerar_pdf_relatorio(dados_relatorio)
            nome_arquivo = f"relatorio_atividades_{dados_relatorio['mes_relatorio']}.pdf"
            return Response(
                conteudo_pdf,
                mimetype="application/pdf",
                headers={
                    "Content-Disposition": f'attachment; filename="{nome_arquivo}"'
                },
            )
        return render_page("relatorios.html", **dados_relatorio)
    except (RuntimeError, ValueError, TypeError, OSError) as exc:
        logger.exception("Erro ao carregar relatórios")
        return render_page("erro.html", mensagem=f"Erro ao carregar relatórios: {exc}"), 500


@admin_bp.route("/tempo-por-funcionario")
@admin_required
def tempo_por_funcionario():
    """Página com tempo de trabalho por funcionário (controle de horário)."""
    sheets_service = current_app.config.get("sheets_service")

    funcionario = request.args.get("funcionario", "").strip()
    pedido_os = request.args.get("pedido_os", "").strip()
    data_inicio = request.args.get("data_inicio", "").strip()
    data_fim = request.args.get("data_fim", "").strip()
    export = request.args.get("export", "").strip().lower()

    try:
        per_page = min(max(int(request.args.get("per_page", 20)), 5), 100)
    except (TypeError, ValueError):
        per_page = 20
    try:
        page = max(int(request.args.get("page", 1)), 1)
    except (TypeError, ValueError):
        page = 1

    registros = []
    os_list = []
    if sheets_service:
        try:
            if sheets_service.is_available()[0]:
                registros = sheets_service.get_time_records() or []
                os_list = sheets_service.get_all_os(use_cache=True) or []
        except Exception as exc:
            logger.error(f"Erro ao carregar dados de tempo por funcionário: {exc}")

    metrics = MetricsService()
    resultado = metrics.calcular_tempo_por_funcionario(
        registros,
        os_list=os_list,
        filtros={
            "funcionario": funcionario,
            "pedido_os": pedido_os,
            "data_inicio": data_inicio,
            "data_fim": data_fim,
        },
    )

    todos = resultado["dados"]
    total = resultado["total_registros"]

    if export == "csv":
        import csv
        import io as _io

        buffer = _io.StringIO()
        buffer.write("\ufeff")  # BOM p/ Excel reconhecer UTF-8
        writer = csv.writer(buffer, delimiter=";")
        writer.writerow(["Funcionário", "Pedido/OS", "Tempo", "Horas", "Urgência"])
        for d in todos:
            writer.writerow(
                [
                    d["funcionario"],
                    d["pedido_os"],
                    d["tempo"],
                    f"{d['horas']:.2f}".replace(".", ","),
                    d["urgencia"],
                ]
            )
        nome_arquivo = "tempo_por_funcionario.csv"
        return Response(
            buffer.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename={nome_arquivo}"},
        )

    if export == "xlsx":
        try:
            import io as _io

            from openpyxl import Workbook
            from openpyxl.styles import Font

            wb = Workbook()
            ws = wb.active
            ws.title = "Tempo por Funcionário"
            ws.append(["Funcionário", "Pedido/OS", "Tempo", "Horas", "Urgência"])
            for cell in ws[1]:
                cell.font = Font(bold=True)
            for d in todos:
                ws.append(
                    [d["funcionario"], d["pedido_os"], d["tempo"], d["horas"], d["urgencia"]]
                )
            nome_arquivo = "tempo_por_funcionario.xlsx"
            buffer = _io.BytesIO()
            wb.save(buffer)
            buffer.seek(0)
            return Response(
                buffer.getvalue(),
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": f"attachment; filename={nome_arquivo}"},
            )
        except Exception as exc:
            logger.warning(f"Exportação XLSX indisponível (openpyxl ausente?): {exc}")
            resultado["aviso_periodo"] = (
                "Exportação XLSX indisponível neste ambiente (openpyxl não instalado). "
                "Use a exportação CSV."
            )
            export = ""

    if export and export not in ("csv", "xlsx"):
        resultado["aviso_periodo"] = "Formato de exportação não reconhecido."
        export = ""

    inicio = (page - 1) * per_page
    pagina = todos[inicio : inicio + per_page]

    # Normaliza datas p/ os campos <input type="date"> (YYYY-MM-DD)
    def _iso(data_txt: str) -> str:
        t = MetricsService._parse_data_hora(data_txt.replace("-", "/"), "")
        return t.strftime("%Y-%m-%d") if t else data_txt

    return render_page(
        "tempo_por_funcionario.html",
        dados=pagina,
        total_registros=total,
        chart_data=resultado["chart_data"],
        aviso_periodo=resultado["aviso_periodo"],
        funcionario=funcionario,
        pedido_os=pedido_os,
        data_inicio=data_inicio,
        data_fim=data_fim,
        data_inicio_iso=_iso(data_inicio),
        data_fim_iso=_iso(data_fim),
        per_page=per_page,
        page=page,
    )


@admin_bp.route("/admin/ia", methods=["GET", "POST"])
@admin_required
def admin_ia():
    """Chat de IA do painel administrativo com histórico em sessão."""
    pergunta = ""
    resposta = ""
    erro = None
    history = session.get("admin_ai_history", [])
    if request.method == "POST":
        action = request.form.get("action", "send")
        if action == "clear_history":
            session["admin_ai_history"] = []
            return render_page("admin_ai.html", pergunta="", resposta="", erro=None, history=[])
        if action == "summary":
            pergunta = (
                "Resumo executivo do dia. Analise a produção, itens em aberto, "
                "atrasos, responsáveis e status geral. Destaque os principais pontos de atenção, "
                "suas possíveis causas e uma recomendação objetiva para o administrador."
            )
        else:
            pergunta = (request.form.get("q") or request.form.get("pesquisa") or "").strip()
        if not pergunta:
            erro = "Digite uma busca ou pergunta para consultar a IA."
        else:
            try:
                history = history.copy()
                context_provider = _provider_config("build_admin_ai_context", default_build_admin_ai_context)
                client_provider = _provider_config("get_nvidia_ai_client", default_get_nvidia_ai_client)
                models_provider = _provider_config("get_ai_model_candidates", default_get_ai_model_candidates)
                history.append({"role": "user", "content": context_provider()})
                history.append({"role": "user", "content": pergunta})
                client = client_provider()
                last_exception = None
                for model_name in models_provider():
                    try:
                        completion = client.chat.completions.create(
                            model=model_name, messages=history, temperature=0.7,
                            top_p=1, max_tokens=1024, stream=False,
                        )
                        resposta = completion.choices[0].message.content or ""
                        history.append({"role": "assistant", "content": resposta})
                        session["admin_ai_history"] = history
                        break
                    except Exception as exc:
                        last_exception = exc
                        if "end of life" in str(exc).lower() or "410" in str(exc) or "gone" in str(exc).lower():
                            logger.warning("Modelo de IA retirado. Tentando próximo modelo disponível: %s", model_name)
                            continue
                        raise
                else:
                    if last_exception is not None:
                        raise last_exception
            except Exception as exc:
                logger.exception("Erro ao consultar a API da IA")
                if any(token in str(exc) for token in [
                    "NVIDIA_API_KEY", "OPENAI_API_KEY", "OLLAMA_BASE_URL",
                    "Nenhuma chave de IA configurada", "não foi configurada",
                ]):
                    erro = (
                        "A IA está indisponível porque nenhuma chave de provedor foi configurada.\n\n"
                        "Opções válidas:\n- NVIDIA: NVIDIA_API_KEY=...\n- OpenAI: OPENAI_API_KEY=...\n"
                        "- Ollama local: AI_PROVIDER=ollama e OLLAMA_BASE_URL=http://localhost:11434/v1\n\n"
                        "Exemplos:\n- PowerShell: $env:NVIDIA_API_KEY='sua-chave'\n"
                        "- CMD: set NVIDIA_API_KEY=sua-chave\n- Arquivo .env: NVIDIA_API_KEY=sua-chave\n\n"
                        "Depois reinicie o servidor."
                    )
                else:
                    erro = f"Erro ao consultar a IA: {exc}"
    return render_page("admin_ai.html", pergunta=pergunta, resposta=resposta, erro=erro, history=history)
