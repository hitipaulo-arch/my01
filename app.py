"""
Aplicação Flask Refatorada - Gestão de Ordens de Serviço

Ponto de entrada principal da aplicação.
"""

import os
import logging
import secrets
import pandas as pd
from pathlib import Path
from flask import Flask, render_template, jsonify, request, redirect, url_for, flash, session
from flask_wtf.csrf import CSRFProtect
from flask_caching import Cache

# Carrega variáveis do .env, se disponível
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv não instalado, usando variáveis de ambiente do sistema

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Imports dos serviços
from appmodules.services import SheetsService, NotificationService, UserService
from appmodules.routes.auth_routes import auth_bp
from appmodules.routes.os_routes import os_bp
from appmodules.utils import login_required, admin_required
from appmodules.models.usuario import Role

# Inicializa serviços globais
CREDS_FILE = Path(__file__).parent / 'credentials.json'
SHEET_ID = os.getenv('GOOGLE_SHEET_ID', '1qs3cxlklTnzCp4RpQGhxIrEF4CbeUvid1S0Cp2tC3Xg')
SHEET_TAB = os.getenv('GOOGLE_SHEET_TAB', 'Respostas ao formulário 3')
HORARIO_TAB = os.getenv('GOOGLE_SHEET_HORARIO_TAB', 'Controle de Horário')
USUARIOS_TAB = os.getenv('GOOGLE_SHEET_USUARIOS_TAB', 'Usuários')
CENTRAIS_TAB = os.getenv('GOOGLE_SHEET_CENTRAIS_TAB', 'Controle de Centrais')
FERRAMENTAS_TAB = os.getenv('GOOGLE_SHEET_FERRAMENTAS_TAB', 'Controle de Ferramentas')
HISTORICO_FERRAMENTAS_TAB = os.getenv('GOOGLE_SHEET_HISTORICO_FERRAMENTAS_TAB', 'Histórico de Ferramentas')

try:
    sheets_service = SheetsService(str(CREDS_FILE), SHEET_ID, SHEET_TAB, HORARIO_TAB, USUARIOS_TAB)
    user_service = UserService(sheets_service)
    logger.info("Serviços inicializados com sucesso")
except Exception as e:
    logger.error(f"Erro ao inicializar serviços: {e}")
    sheets_service = None
    user_service = None

# Flask App
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', secrets.token_hex(32))
app.config.update(
    SESSION_COOKIE_SECURE=os.getenv('FLASK_ENV') == 'production',
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    WTF_CSRF_ENABLED=True,
    WTF_CSRF_TIME_LIMIT=None,
    CACHE_TYPE=os.getenv('CACHE_TYPE', 'SimpleCache'),
    CACHE_DEFAULT_TIMEOUT=int(os.getenv('CACHE_TTL_SECONDS', 300))
)

csrf = CSRFProtect(app)
cache = Cache(app)

# Torna serviços disponíveis globalmente
app.config['sheets_service'] = sheets_service
app.config['user_service'] = user_service
app.config['notification_service'] = NotificationService

# Registra blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(os_bp)

# ════════════════════════════════════════════════════════════════════════════════
# ROTAS DE ADMINISTRAÇÃO
# ════════════════════════════════════════════════════════════════════════════════

@app.route('/usuarios', methods=['GET', 'POST'])
@admin_required
def usuarios_admin():
    """Admin UI para gerenciar usuários."""
    from flask import flash
    
    user_service = app.config.get('user_service')
    mensagem = None
    tipo_mensagem = 'success'
    
    if request.method == 'POST':
        acao = request.form.get('acao')
        username = request.form.get('username', '').strip()
        
        if not username:
            mensagem = 'Username é obrigatório.'
            tipo_mensagem = 'danger'
        else:
            if acao == 'delete':
                if user_service.deletar_usuario(username):
                    mensagem = f'Usuário {username} removido com sucesso.'
                else:
                    mensagem = f'Erro ao remover usuário {username}.'
                    tipo_mensagem = 'danger'
            else:
                senha = request.form.get('senha', '').strip()
                role = request.form.get('role', Role.ADMIN.value).strip().lower()
                roles_validos = {r.value for r in Role}
                
                if not senha:
                    mensagem = 'Senha é obrigatória.'
                    tipo_mensagem = 'danger'
                elif role not in roles_validos:
                    mensagem = 'Role inválida.'
                    tipo_mensagem = 'danger'
                else:
                    if user_service.criar_usuario(username, senha, role):
                        mensagem = f'Usuário {username} criado com sucesso.'
                    else:
                        mensagem = f'Erro ao criar usuário {username}.'
                        tipo_mensagem = 'danger'
    
    usuarios = user_service.get_todos_usuarios() if user_service else []
    usuarios_dict = {u.username: u.to_dict() for u in usuarios}
    
    return render_template('usuarios.html', 
        usuarios=usuarios_dict, mensagem=mensagem, tipo_mensagem=tipo_mensagem)


@app.route('/relatorios')
@admin_required
def relatorios():
    """Página de relatórios."""
    import datetime as dt

    def _first_col(df, *candidatos):
        for col in candidatos:
            if col in df.columns:
                return col
        return None

    def _parse_datetime_maybe_time(valor, base_dt):
        if valor is None:
            return pd.NaT
        texto = str(valor).strip()
        if not texto:
            return pd.NaT

        # Se vier só horário (HH:MM ou HH:MM:SS), combina com a data base.
        if ':' in texto and '/' not in texto:
            if pd.isna(base_dt):
                return pd.NaT
            for fmt in ('%H:%M:%S', '%H:%M'):
                try:
                    t = dt.datetime.strptime(texto, fmt).time()
                    return dt.datetime.combine(base_dt.date(), t)
                except ValueError:
                    continue

        try:
            return pd.to_datetime(texto, format='%d/%m/%Y %H:%M:%S', errors='coerce')
        except Exception:
            return pd.to_datetime(texto, errors='coerce')

    _empty = dict(
        labels_prioridade=[], dados_prioridade=[],
        labels_setor=[], dados_setor=[],
        labels_tempo_resolucao=[], dados_tempo_resolucao=[],
        labels_dia_semana=[], dados_dia_semana=[],
        total_os=0, taxa_conclusao='0%',
        total_finalizadas=0, total_andamento=0,
        tempo_medio='N/A', tabela_resumo=[])

    sheets_service = app.config.get('sheets_service')
    if not sheets_service:
        return render_template('relatorios.html', **_empty,
            mensagem_erro="Serviço de planilhas indisponível"), 503

    disponivel, erro_msg = sheets_service.is_available()
    if not disponivel:
        return render_template('relatorios.html', **_empty,
            mensagem_erro=erro_msg)

    try:
        os_list = sheets_service.get_all_os()
        if not os_list:
            return render_template('relatorios.html', **_empty)

        df = pd.DataFrame(os_list).fillna('')

        col_timestamp = _first_col(df, 'Carimbo de data/hora')
        col_status = _first_col(df, 'Status da OS')
        col_prioridade = _first_col(df, 'Prioridade', 'Nível de prioridade')
        col_setor = _first_col(df, 'Setor', 'Setor em que será realizado o serviço')
        col_solicitante = _first_col(df, 'Nome do solicitante')
        col_descricao = _first_col(df, 'Descrição', 'Descrição do Problema ou Serviço Solicitado')
        col_andamento = _first_col(df, 'Horario de Andamento')
        col_termino = _first_col(df, 'Horario de Término')

        # Parse timestamp
        if col_timestamp:
            df['_ts'] = pd.to_datetime(
                df[col_timestamp], format='%d/%m/%Y %H:%M:%S', errors='coerce')
        else:
            df['_ts'] = pd.NaT

        # Filtra canceladas
        if col_status:
            status_lower = df[col_status].astype(str).str.strip().str.lower()
            df = df[~status_lower.isin(['cancelada', 'cancelado'])]

        # --- Gráfico por prioridade ---
        if col_prioridade:
            pri = df[col_prioridade].astype(str).str.strip()
            pri_count = pri[pri != ''].value_counts()
            labels_prioridade = [str(x) for x in pri_count.index.tolist()]
            dados_prioridade = [int(x) for x in pri_count.values.tolist()]
        else:
            labels_prioridade, dados_prioridade = [], []

        # --- Gráfico por setor ---
        if col_setor:
            setor = df[col_setor].astype(str).str.strip()
            setor_count = setor[setor != ''].value_counts().head(10)
            labels_setor = [str(x) for x in setor_count.index.tolist()]
            dados_setor = [int(x) for x in setor_count.values.tolist()]
        else:
            labels_setor, dados_setor = [], []

        # --- Métricas ---
        total_os = len(df)
        status_lower = df[col_status].astype(str).str.strip().str.lower() if col_status else pd.Series(dtype=str)

        finalizadas = int(status_lower.isin(['finalizada', 'concluido', 'concluído']).sum())
        total_andamento = int(status_lower.isin(['em andamento']).sum())
        taxa_conclusao = f"{(finalizadas/total_os*100):.1f}%" if total_os > 0 else "0%"

        # --- Tempo médio de resolução (andamento -> término) ---
        tempo_medio = 'N/A'
        if col_andamento and col_termino:
            df_fin = df[status_lower.isin(['finalizada', 'concluido', 'concluído'])].copy()
            df_fin['_inicio'] = df_fin.apply(
                lambda r: _parse_datetime_maybe_time(r.get(col_andamento, ''), r.get('_ts', pd.NaT)),
                axis=1
            )
            df_fin['_termino'] = df_fin.apply(
                lambda r: _parse_datetime_maybe_time(r.get(col_termino, ''), r.get('_ts', pd.NaT)),
                axis=1
            )
            delta = (df_fin['_termino'] - df_fin['_inicio']).dropna()
            delta = delta[delta.dt.total_seconds() > 0]
            if not delta.empty:
                media_h = delta.mean().total_seconds() / 3600
                if media_h < 1:
                    tempo_medio = f"{int(media_h * 60)}min"
                else:
                    tempo_medio = f"{media_h:.1f}h"

        # --- Gráfico dia da semana ---
        labels_dia_semana, dados_dia_semana = [], []
        ts_valid = df['_ts'].dropna()
        if not ts_valid.empty:
            dias_map = {0: 'Seg', 1: 'Ter', 2: 'Qua', 3: 'Qui', 4: 'Sex', 5: 'Sáb', 6: 'Dom'}
            dia_counts = ts_valid.dt.dayofweek.value_counts().sort_index()
            labels_dia_semana = [dias_map.get(d, str(d)) for d in dia_counts.index]
            dados_dia_semana = [int(v) for v in dia_counts.values]

        # --- Gráfico tempo de resolução por mês (andamento -> término) ---
        labels_tempo_resolucao, dados_tempo_resolucao = [], []
        if col_andamento and col_termino:
            df_res = df.copy()
            df_res['_inicio'] = df_res.apply(
                lambda r: _parse_datetime_maybe_time(r.get(col_andamento, ''), r.get('_ts', pd.NaT)),
                axis=1
            )
            df_res['_termino'] = df_res.apply(
                lambda r: _parse_datetime_maybe_time(r.get(col_termino, ''), r.get('_ts', pd.NaT)),
                axis=1
            )
            df_res['_delta_h'] = (df_res['_termino'] - df_res['_inicio']).dt.total_seconds() / 3600
            df_res = df_res.dropna(subset=['_ts', '_delta_h'])
            df_res = df_res[df_res['_delta_h'] > 0]
            if not df_res.empty:
                df_res['_mes'] = df_res['_ts'].dt.to_period('M').astype(str)
                media_mes = df_res.groupby('_mes')['_delta_h'].mean().sort_index()
                labels_tempo_resolucao = media_mes.index.tolist()
                dados_tempo_resolucao = [round(v, 1) for v in media_mes.values]

        # --- Tabela resumo (últimas 50) ---
        tabela_resumo = []
        df_sorted = df.dropna(subset=['_ts']).sort_values('_ts', ascending=False).head(50)
        for _, row in df_sorted.iterrows():
            tabela_resumo.append({
                'data': row.get(col_timestamp, '') if col_timestamp else '',
                'solicitante': row.get(col_solicitante, '') if col_solicitante else '',
                'setor': row.get(col_setor, '') if col_setor else '',
                'status': row.get(col_status, '') if col_status else '',
                'descricao': row.get(col_descricao, '') if col_descricao else ''
            })

        return render_template('relatorios.html',
            labels_prioridade=labels_prioridade,
            dados_prioridade=dados_prioridade,
            labels_setor=labels_setor,
            dados_setor=dados_setor,
            labels_tempo_resolucao=labels_tempo_resolucao,
            dados_tempo_resolucao=dados_tempo_resolucao,
            labels_dia_semana=labels_dia_semana,
            dados_dia_semana=dados_dia_semana,
            total_os=total_os,
            taxa_conclusao=taxa_conclusao,
            total_finalizadas=finalizadas,
            total_andamento=total_andamento,
            tempo_medio=tempo_medio,
            tabela_resumo=tabela_resumo)

    except Exception as e:
        logger.error(f"Erro ao carregar relatórios: {e}")
        return render_template('erro.html',
            mensagem=f"Erro ao carregar relatórios: {e}"), 500


@app.route('/tempo-por-funcionario')
@admin_required
def tempo_por_funcionario():
    """Página com tempo de trabalho por funcionário."""
    return render_template('tempo_por_funcionario.html',
        dados=[], chart_data={}, total_registros=0)


# ════════════════════════════════════════════════════════════════════════════════
# ERROR HANDLERS
# ════════════════════════════════════════════════════════════════════════════════

@app.errorhandler(404)
def page_not_found(e):
    """Handler para páginas não encontradas."""
    logger.warning(f"Página não encontrada: {request.url}")
    return render_template('erro.html',
        mensagem="Página não encontrada."), 404


@app.errorhandler(500)
def internal_server_error(e):
    """Handler para erros internos."""
    logger.error(f"Erro interno: {e}", exc_info=True)
    return render_template('erro.html',
        mensagem="Erro interno do servidor."), 500


@app.errorhandler(Exception)
def handle_exception(e):
    """Handler genérico para exceções."""
    if hasattr(e, 'code'):
        return e
    
    logger.error(f"Erro não tratado: {e}", exc_info=True)
    return render_template('erro.html',
        mensagem="Ocorreu um erro inesperado."), 500


@app.route('/centrais', methods=['GET', 'POST'])
@admin_required
def centrais():
    """Página de controle de centrais."""
    sheets_service = app.config.get('sheets_service')
    if not sheets_service:
        return render_template('centrais.html',
            centrais=[], mensagem="Serviço de planilhas indisponível",
            tipo_mensagem='danger'), 503
    
    if request.method == 'POST':
        try:
            # Adiciona nova central
            dados = {
                'Número de Portas': request.form.get('num_portas', ''),
                'Código de Série': request.form.get('codigo_serie', ''),
                'Status': request.form.get('status', ''),
                'Obra Utilizada': request.form.get('obra', ''),
                'Data Cadastro': pd.Timestamp.now().strftime('%d/%m/%Y %H:%M:%S')
            }
            
            # Garante que a aba existe
            worksheet = get_or_create_centrais_worksheet(sheets_service)
            
            # Adiciona nova linha
            worksheet.append_row(list(dados.values()))
            
            # Redireciona para evitar resubmissão (padrão PRG - Post-Redirect-Get)
            flash("Central cadastrada com sucesso!", "success")
            return redirect(url_for('centrais'))
        except Exception as e:
            logger.error(f"Erro ao adicionar central: {e}", exc_info=True)
            flash(f"Erro ao adicionar central: {e}", "danger")
            return redirect(url_for('centrais'))
    
    # GET - lista centrais e mostra mensagens flash
    mensagem = None
    tipo_mensagem = None
    if '_flashes' in session:
        flashes = session.get('_flashes', [])
        if flashes:
            tipo_mensagem, mensagem = flashes[0]
    
    return render_template('centrais.html',
        centrais=get_centrais_list(sheets_service),
        mensagem=mensagem,
        tipo_mensagem=tipo_mensagem)


def get_or_create_centrais_worksheet(sheets_service):
    """Obtém ou cria a worksheet de centrais."""
    try:
        spreadsheet = sheets_service.client.open_by_key(sheets_service.sheet_id)
        try:
            worksheet = spreadsheet.worksheet(CENTRAIS_TAB)
        except:
            # Aba não existe, cria
            worksheet = spreadsheet.add_worksheet(title=CENTRAIS_TAB, rows=100, cols=10)
            worksheet.append_row(['Número de Portas', 'Código de Série', 'Status', 'Obra Utilizada', 'Data Cadastro'])
            logger.info(f"Aba '{CENTRAIS_TAB}' criada")
        return worksheet
    except Exception as e:
        logger.error(f"Erro ao obter/criar worksheet: {e}")
        raise


def get_centrais_list(sheets_service):
    """Obtém lista de centrais."""
    try:
        worksheet = get_or_create_centrais_worksheet(sheets_service)
        dados = worksheet.get_all_records()
        return dados if dados else []
    except Exception as e:
        logger.warning(f"Erro ao obter centrais: {e}")
        return []


@app.route('/centrais/atualizar/<int:row_id>', methods=['POST'])
@admin_required
def atualizar_central(row_id):
    """Atualiza status de uma central."""
    sheets_service = app.config.get('sheets_service')
    if not sheets_service:
        return jsonify({'success': False, 'message': 'Serviço indisponível'}), 503
    
    try:
        worksheet = get_or_create_centrais_worksheet(sheets_service)
        
        # row_id é baseado em 1, mas começa do header, então +2
        row_num = row_id + 2
        
        status = request.form.get('status', '')
        obra = request.form.get('obra', '')
        
        # Atualiza células específicas (colunas C=Status, D=Obra)
        worksheet.update_cell(row_num, 3, status)
        worksheet.update_cell(row_num, 4, obra)
        
        return jsonify({'success': True, 'message': 'Central atualizada!'})
    except Exception as e:
        logger.error(f"Erro ao atualizar central: {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/centrais/deletar/<int:row_id>', methods=['POST'])
@admin_required
def deletar_central(row_id):
    """Deleta uma central."""
    sheets_service = app.config.get('sheets_service')
    if not sheets_service:
        return jsonify({'success': False, 'message': 'Serviço indisponível'}), 503
    
    try:
        worksheet = get_or_create_centrais_worksheet(sheets_service)
        row_num = row_id + 2  # +2 por causa do header
        worksheet.delete_rows(row_num)
        
        return jsonify({'success': True, 'message': 'Central deletada!'})
    except Exception as e:
        logger.error(f"Erro ao deletar central: {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/ferramentas', methods=['GET', 'POST'])
@admin_required
def ferramentas():
    """Página de controle de ferramentas."""
    sheets_service = app.config.get('sheets_service')
    if not sheets_service:
        return render_template('ferramentas.html',
            ferramentas=[], mensagem="Serviço de planilhas indisponível",
            tipo_mensagem='danger'), 503

    if request.method == 'POST':
        try:
            dados = [
                request.form.get('nome', ''),
                request.form.get('patrocinio', ''),
                pd.Timestamp.now().strftime('%d/%m/%Y'),
                request.form.get('ultima_manutencao', ''),
                request.form.get('status', 'Disponível'),
                request.form.get('observacao', ''),
                request.form.get('responsavel', '')
            ]
            worksheet = get_or_create_ferramentas_worksheet(sheets_service)
            worksheet.append_row(dados)
            usuario_atual = session.get('usuario', 'desconhecido')
            detalhes_hist = f"Patrocínio: {dados[1]}, Responsável: {dados[6]}, Status: {dados[4]}, Obs: {dados[5]}"
            add_historico_entry(sheets_service, dados[0], 'Cadastro', usuario_atual, detalhes_hist)
            flash("Ferramenta cadastrada com sucesso!", "success")
            return redirect(url_for('ferramentas'))
        except Exception as e:
            logger.error(f"Erro ao adicionar ferramenta: {e}", exc_info=True)
            flash(f"Erro ao adicionar ferramenta: {e}", "danger")
            return redirect(url_for('ferramentas'))

    mensagem = None
    tipo_mensagem = None
    if '_flashes' in session:
        flashes = session.get('_flashes', [])
        if flashes:
            tipo_mensagem, mensagem = flashes[0]

    return render_template('ferramentas.html',
        ferramentas=get_ferramentas_list(sheets_service),
        mensagem=mensagem,
        tipo_mensagem=tipo_mensagem)


def get_or_create_ferramentas_worksheet(sheets_service):
    """Obtém ou cria a worksheet de ferramentas."""
    try:
        spreadsheet = sheets_service.client.open_by_key(sheets_service.sheet_id)
        try:
            worksheet = spreadsheet.worksheet(FERRAMENTAS_TAB)
            headers = worksheet.row_values(1)
            if 'Responsável' not in headers:
                worksheet.update_cell(1, 7, 'Responsável')
        except Exception:
            worksheet = spreadsheet.add_worksheet(title=FERRAMENTAS_TAB, rows=500, cols=10)
            worksheet.append_row(['Nome', 'Patrocínio', 'Data de Cadastro',
                                   'Última Manutenção', 'Status', 'Observação', 'Responsável'])
            logger.info(f"Aba '{FERRAMENTAS_TAB}' criada")
        return worksheet
    except Exception as e:
        logger.error(f"Erro ao obter/criar worksheet de ferramentas: {e}")
        raise


def get_ferramentas_list(sheets_service):
    """Obtém lista de ferramentas."""
    try:
        worksheet = get_or_create_ferramentas_worksheet(sheets_service)
        dados = worksheet.get_all_records()
        return dados if dados else []
    except Exception as e:
        logger.warning(f"Erro ao obter ferramentas: {e}")
        return []


def get_or_create_historico_worksheet(sheets_service):
    """Obtém ou cria a worksheet de histórico de ferramentas."""
    try:
        spreadsheet = sheets_service.client.open_by_key(sheets_service.sheet_id)
        try:
            worksheet = spreadsheet.worksheet(HISTORICO_FERRAMENTAS_TAB)
        except Exception:
            worksheet = spreadsheet.add_worksheet(title=HISTORICO_FERRAMENTAS_TAB, rows=1000, cols=5)
            worksheet.append_row(['Ferramenta', 'Evento', 'Data/Hora', 'Usuário', 'Detalhes'])
            logger.info(f"Aba '{HISTORICO_FERRAMENTAS_TAB}' criada")
        return worksheet
    except Exception as e:
        logger.error(f"Erro ao obter/criar worksheet de histórico: {e}")
        raise


def add_historico_entry(sheets_service, nome_ferramenta, evento, usuario, detalhes=''):
    """Adiciona uma entrada no histórico de ferramentas."""
    try:
        worksheet = get_or_create_historico_worksheet(sheets_service)
        data_hora = pd.Timestamp.now().strftime('%d/%m/%Y %H:%M:%S')
        worksheet.append_row([nome_ferramenta, evento, data_hora, usuario, detalhes])
    except Exception as e:
        logger.warning(f"Erro ao adicionar histórico: {e}")


@app.route('/ferramentas/atualizar/<int:row_id>', methods=['POST'])
@admin_required
def atualizar_ferramenta(row_id):
    """Atualiza uma ferramenta."""
    sheets_service = app.config.get('sheets_service')
    if not sheets_service:
        return jsonify({'success': False, 'message': 'Serviço indisponível'}), 503

    try:
        worksheet = get_or_create_ferramentas_worksheet(sheets_service)
        row_num = row_id + 2  # +2 pelo cabeçalho
        dados_atuais = worksheet.row_values(row_num)
        nome_ferramenta = dados_atuais[0] if dados_atuais else 'Desconhecida'
        novo_responsavel = request.form.get('responsavel', '')
        nova_manutencao = request.form.get('ultima_manutencao', '')
        novo_status = request.form.get('status', '')
        nova_observacao = request.form.get('observacao', '')
        old_manutencao = dados_atuais[3] if len(dados_atuais) > 3 else ''
        old_status = dados_atuais[4] if len(dados_atuais) > 4 else ''
        old_observacao = dados_atuais[5] if len(dados_atuais) > 5 else ''
        old_responsavel = dados_atuais[6] if len(dados_atuais) > 6 else ''
        worksheet.update_cell(row_num, 4, nova_manutencao)
        worksheet.update_cell(row_num, 5, novo_status)
        worksheet.update_cell(row_num, 6, nova_observacao)
        worksheet.update_cell(row_num, 7, novo_responsavel)
        changes = []
        if novo_responsavel != old_responsavel:
            changes.append(f"Responsável: {old_responsavel or '-'} → {novo_responsavel or '-'}")
        if nova_manutencao != old_manutencao:
            changes.append(f"Manutenção: {old_manutencao or '-'} → {nova_manutencao or '-'}")
        if novo_status != old_status:
            changes.append(f"Status: {old_status or '-'} → {novo_status or '-'}")
        if nova_observacao != old_observacao:
            changes.append(f"Obs: {old_observacao or '-'} → {nova_observacao or '-'}")
        detalhes_hist = ', '.join(changes) if changes else 'Sem alterações'
        usuario_atual = session.get('usuario', 'desconhecido')
        add_historico_entry(sheets_service, nome_ferramenta, 'Edição', usuario_atual, detalhes_hist)
        return jsonify({'success': True, 'message': 'Ferramenta atualizada!'})
    except Exception as e:
        logger.error(f"Erro ao atualizar ferramenta: {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/ferramentas/deletar/<int:row_id>', methods=['POST'])
@admin_required
def deletar_ferramenta(row_id):
    """Deleta uma ferramenta."""
    sheets_service = app.config.get('sheets_service')
    if not sheets_service:
        return jsonify({'success': False, 'message': 'Serviço indisponível'}), 503

    try:
        worksheet = get_or_create_ferramentas_worksheet(sheets_service)
        row_num = row_id + 2
        dados_atuais = worksheet.row_values(row_num)
        nome_ferramenta = dados_atuais[0] if dados_atuais else 'Desconhecida'
        usuario_atual = session.get('usuario', 'desconhecido')
        worksheet.delete_rows(row_num)
        add_historico_entry(sheets_service, nome_ferramenta, 'Exclusão', usuario_atual, 'Ferramenta excluída')
        return jsonify({'success': True, 'message': 'Ferramenta deletada!'})
    except Exception as e:
        logger.error(f"Erro ao deletar ferramenta: {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/ferramentas/historico')
@admin_required
def historico_ferramentas():
    """Retorna histórico de uma ferramenta em JSON."""
    sheets_service = app.config.get('sheets_service')
    if not sheets_service:
        return jsonify({'success': False, 'historico': []})
    nome = request.args.get('nome', '')
    try:
        worksheet = get_or_create_historico_worksheet(sheets_service)
        todos = worksheet.get_all_records()
        if nome:
            filtrado = [r for r in todos if r.get('Ferramenta', '').lower() == nome.lower()]
        else:
            filtrado = todos
        filtrado = list(reversed(filtrado))
        return jsonify({'success': True, 'historico': filtrado})
    except Exception as e:
        logger.error(f"Erro ao obter histórico: {e}")
        return jsonify({'success': False, 'historico': [], 'error': str(e)})


@app.route('/favicon.ico')
def favicon():
    """Favicon vazio para evitar erro 404."""
    return '', 204


# ════════════════════════════════════════════════════════════════════════════════
# PONTO DE ENTRADA
# ════════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Iniciando aplicação na porta {port} (debug={debug_mode})")
    
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
