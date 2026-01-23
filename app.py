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

# Inicializa serviços globais
CREDS_FILE = Path(__file__).parent / 'credentials.json'
SHEET_ID = os.getenv('GOOGLE_SHEET_ID', '1qs3cxlklTnzCp4RpQGhxIrEF4CbeUvid1S0Cp2tC3Xg')
SHEET_TAB = os.getenv('GOOGLE_SHEET_TAB', 'Respostas ao formulário 3')
HORARIO_TAB = os.getenv('GOOGLE_SHEET_HORARIO_TAB', 'Controle de Horário')
USUARIOS_TAB = os.getenv('GOOGLE_SHEET_USUARIOS_TAB', 'Usuários')
CENTRAIS_TAB = os.getenv('GOOGLE_SHEET_CENTRAIS_TAB', 'Controle de Centrais')

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
                role = request.form.get('role', 'admin').strip()
                
                if not senha:
                    mensagem = 'Senha é obrigatória.'
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


@app.route('/dashboard')
@admin_required
def dashboard():
    """Dashboard com gráficos."""
    sheets_service = app.config.get('sheets_service')
    if not sheets_service:
        return render_template('dashboard.html', 
            labels_meses=[], datasets_status=[], mensagem_erro="Serviço de planilhas indisponível"), 503
    
    disponivel, erro_msg = sheets_service.is_available()
    if not disponivel:
        return render_template('dashboard.html', 
            labels_meses=[], datasets_status=[], mensagem_erro=erro_msg)
    
    try:
        import pandas as pd
        
        os_list = sheets_service.get_all_os()
        if not os_list:
            return render_template('dashboard.html', 
                labels_meses=[], datasets_status=[])
        
        # Processa dados
        data_list = []
        for os_item in os_list:
            data_list.append({
                'timestamp': os_item.get('Carimbo de data/hora', ''),
                'status': os_item.get('Status da OS', '')
            })
        
        df = pd.DataFrame(data_list)
        df['timestamp'] = pd.to_datetime(df['timestamp'], 
            format='%d/%m/%Y %H:%M:%S', errors='coerce')
        df = df.dropna(subset=['timestamp'])
        
        df['MesAno'] = df['timestamp'].dt.to_period('M').astype(str)
        status_por_mes = df.groupby(['MesAno', 'status']).size().unstack(fill_value=0)
        
        labels_meses = status_por_mes.index.tolist()
        
        datasets_status = []
        cores = {
            'Concluído': 'rgba(75, 192, 192, 0.7)',
            'Em Andamento': 'rgba(54, 162, 235, 0.7)',
            'Aberto': 'rgba(108, 117, 125, 0.7)',
            'Cancelado': 'rgba(217, 83, 79, 0.7)'
        }
        
        for status in status_por_mes.columns:
            datasets_status.append({
                'label': status,
                'data': status_por_mes[status].values.tolist(),
                'backgroundColor': cores.get(status, 'rgba(201, 203, 207, 0.7)')
            })
        
        return render_template('dashboard.html',
            labels_meses=labels_meses,
            datasets_status=datasets_status)
    
    except Exception as e:
        logger.error(f"Erro ao carregar dashboard: {e}")
        return render_template('erro.html', 
            mensagem=f"Erro ao carregar dashboard: {e}"), 500


@app.route('/relatorios')
@admin_required
def relatorios():
    """Página de relatórios."""
    sheets_service = app.config.get('sheets_service')
    if not sheets_service:
        return render_template('relatorios.html',
            labels_prioridade=[], dados_prioridade=[],
            labels_setor=[], dados_setor=[],
            labels_tempo_resolucao=[], dados_tempo_resolucao=[],
            labels_dia_semana=[], dados_dia_semana=[],
            total_os=0, taxa_conclusao='0%',
            total_finalizadas=0,
            mensagem_erro="Serviço de planilhas indisponível"), 503
    
    disponivel, erro_msg = sheets_service.is_available()
    if not disponivel:
        return render_template('relatorios.html',
            labels_prioridade=[], dados_prioridade=[],
            labels_setor=[], dados_setor=[],
            labels_tempo_resolucao=[], dados_tempo_resolucao=[],
            labels_dia_semana=[], dados_dia_semana=[],
            total_os=0, taxa_conclusao='0%',
            total_finalizadas=0)
    
    try:
        import pandas as pd
        
        os_list = sheets_service.get_all_os()
        if not os_list:
            return render_template('relatorios.html',
                labels_prioridade=[], dados_prioridade=[],
                labels_setor=[], dados_setor=[],
                labels_tempo_resolucao=[], dados_tempo_resolucao=[],
                labels_dia_semana=[], dados_dia_semana=[],
                total_os=0, taxa_conclusao='0%',
                total_finalizadas=0)
        
        df = pd.DataFrame(os_list)
        
        # Substitui todos os NaN/None por strings vazias
        df = df.fillna('')
        
        # Filtra canceladas/cancelado (case-insensitive)
        if 'Status da OS' in df.columns:
            status_series = df['Status da OS'].astype(str).str.strip().str.lower()
            df = df[~status_series.isin(['cancelada', 'cancelado'])]
        
        # Gráfico por prioridade
        if 'Prioridade' in df.columns:
            # Remove valores vazios antes de contar
            prioridade_series = df['Prioridade'].astype(str).str.strip()
            prioridade_count = prioridade_series[prioridade_series != ''].value_counts()
            labels_prioridade = [str(x) for x in prioridade_count.index.tolist()]
            dados_prioridade = [int(x) for x in prioridade_count.values.tolist()]
        else:
            labels_prioridade = []
            dados_prioridade = []
        
        # Gráfico por setor
        if 'Setor' in df.columns:
            # Remove valores vazios antes de contar
            setor_series = df['Setor'].astype(str).str.strip()
            setor_count = setor_series[setor_series != ''].value_counts().head(10)
            labels_setor = [str(x) for x in setor_count.index.tolist()]
            dados_setor = [int(x) for x in setor_count.values.tolist()]
        else:
            labels_setor = []
            dados_setor = []
        
        # Métricas
        total_os = len(df)
        # Conta finalizadas (aceita 'Finalizada' e 'Concluído')
        if 'Status da OS' in df.columns:
            status_series = df['Status da OS'].astype(str).str.strip().str.lower()
            finalizadas = int((status_series.isin(['finalizada', 'concluido', 'concluído'])).sum())
        else:
            finalizadas = 0
        taxa_conclusao = f"{(finalizadas/total_os*100):.1f}%" if total_os > 0 else "0%"
        
        return render_template('relatorios.html',
            labels_prioridade=labels_prioridade,
            dados_prioridade=dados_prioridade,
            labels_setor=labels_setor,
            dados_setor=dados_setor,
            labels_tempo_resolucao=[],
            dados_tempo_resolucao=[],
            labels_dia_semana=[],
            dados_dia_semana=[],
            total_os=total_os,
            taxa_conclusao=taxa_conclusao,
            total_finalizadas=finalizadas)
    
    except Exception as e:
        logger.error(f"Erro ao carregar relatórios: {e}")
        return render_template('erro.html',
            mensagem=f"Erro ao carregar relatórios: {e}"), 500


@app.route('/controle-horario', methods=['GET', 'POST'])
@admin_required
def controle_horario():
    """Página de controle de ponto."""
    sheets_service = app.config.get('sheets_service')
    if not sheets_service:
        return render_template('controle_horario.html',
            usuarios_ativos=[], registros=[],
            mensagem="Serviço de planilhas indisponível", tipo_mensagem='danger'), 503
    
    disponivel, erro_msg = sheets_service.is_available()
    if not disponivel:
        return render_template('controle_horario.html',
            usuarios_ativos=[], registros=[],
            mensagem="Sistema indisponível", tipo_mensagem='danger')
    
    return render_template('controle_horario.html',
        usuarios_ativos=[], registros=[],
        mensagem=None, tipo_mensagem='success')


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
