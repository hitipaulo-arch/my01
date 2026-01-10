import datetime
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import os
import logging
from threading import Lock
import secrets
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf.csrf import CSRFProtect
from flask_caching import Cache
from typing import Optional, Dict, List, Tuple, Any
from dataclasses import dataclass 

# --- 1. CONFIGURAÇÃO INICIAL (Google Sheets & Flask) ---

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Inicializa estrutura de usuários em memória cedo para evitar NameError
USUARIOS = {}

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file'
]

# --- LÓGICA DE CREDENCIAIS SIMPLIFICADA (Lê o ficheiro 'credentials.json') ---
creds = None
client = None
sheet = None
sheet_error = None

try:
    CREDS_FILE = Path(__file__).parent / 'credentials.json'
    creds = Credentials.from_service_account_file(CREDS_FILE, scopes=SCOPES)
    logger.info("Credenciais carregadas com sucesso a partir do ficheiro (local ou Secret File).")
    
except FileNotFoundError:
    logger.error("ERRO: Ficheiro 'credentials.json' não encontrado na pasta do projeto.")
    logger.error("Por favor, baixe o JSON do Google Cloud e coloque-o na mesma pasta do 'app.py'")
    logger.error("Se estiver no Render, certifique-se que o 'Secret File' está configurado.")
    sheet_error = "Ficheiro de credenciais não encontrado."
except Exception as e:
    logger.error(f"ERRO CRÍTICO AO CARREGAR CREDENCIAIS: {e}")
    sheet_error = f"Erro ao carregar credenciais: {e}"

# Variáveis de ambiente para configuração (permite substituir via env vars)
SHEET_ID = os.getenv('GOOGLE_SHEET_ID', '1qs3cxlklTnzCp4RpQGhxIrEF4CbeUvid1S0Cp2tC3Xg')
SHEET_TAB_NAME = os.getenv('GOOGLE_SHEET_TAB', 'Respostas ao formulário 3')
SHEET_HORARIO_TAB = os.getenv('GOOGLE_SHEET_HORARIO_TAB', 'Controle de Horário')
SHEET_USUARIOS_TAB = os.getenv('GOOGLE_SHEET_USUARIOS_TAB', 'Usuários')

# Variável para planilha de controle de horário
sheet_horario = None
# Variável para planilha de usuários
sheet_usuarios = None

# Só tenta conectar se as credenciais foram carregadas
if creds:
    try:
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(SHEET_ID)
        sheet = spreadsheet.worksheet(SHEET_TAB_NAME)
        logger.info(f"Conectado com sucesso à planilha '{SHEET_TAB_NAME}'!")
        
        # Tenta conectar à aba de controle de horário (cria se não existir)
        try:
            sheet_horario = spreadsheet.worksheet(SHEET_HORARIO_TAB)
            logger.info(f"Conectado à aba '{SHEET_HORARIO_TAB}'")
        except:
            # Cria aba se não existir
            sheet_horario = spreadsheet.add_worksheet(title=SHEET_HORARIO_TAB, rows=1000, cols=10)
            # Adiciona cabeçalho
            sheet_horario.append_row(['Data', 'Funcionário', 'Pedido/OS', 'Tipo', 'Horário', 'Observação'])
            logger.info(f"Aba '{SHEET_HORARIO_TAB}' criada com sucesso")
        
        # Tenta conectar à aba de usuários (cria se não existir)
        try:
            sheet_usuarios = spreadsheet.worksheet(SHEET_USUARIOS_TAB)
            logger.info(f"Conectado à aba '{SHEET_USUARIOS_TAB}'")
        except:
            # Cria aba se não existir
            sheet_usuarios = spreadsheet.add_worksheet(title=SHEET_USUARIOS_TAB, rows=1000, cols=10)
            # Adiciona cabeçalho
            sheet_usuarios.append_row(['Username', 'Senha', 'Role'])
            # Adiciona usuários padrão
            sheet_usuarios.append_row(['admin', 'admin123', 'admin'])
            sheet_usuarios.append_row(['gestor', 'gestor123', 'admin'])
            sheet_usuarios.append_row(['operador', 'operador123', 'admin'])
            logger.info(f"Aba '{SHEET_USUARIOS_TAB}' criada com sucesso com usuários padrão")
            
    except Exception as e:
        logger.error(f"Erro ao conectar na planilha (verifique permissões de partilha): {e}")
        sheet_error = f"Erro ao conectar à planilha: {e}"

# Carrega usuários DEPOIS da conexão com Sheets estar estabelecida
try:
    USUARIOS = carregar_usuarios()
    logger.info(f"Sistema inicializado com {len(USUARIOS)} usuários")
except Exception as e:
    logger.error(f"Erro ao carregar usuários na inicialização: {e}")
    USUARIOS = {}
    
# --- FIM DA LÓGICA DE CREDENCIAIS ---

app = Flask(__name__)
# Gera chave secreta segura se não definida
app.secret_key = os.getenv('SECRET_KEY', secrets.token_hex(32))
app.config['SESSION_COOKIE_SECURE'] = os.getenv('FLASK_ENV') == 'production'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['WTF_CSRF_ENABLED'] = True
app.config['WTF_CSRF_TIME_LIMIT'] = None  # Token não expira

# Ativa proteção CSRF
csrf = CSRFProtect(app)

# --- CONFIGURAÇÃO DE CACHE ---
# Substitui cache manual por Flask-Caching
app.config['CACHE_TYPE'] = 'SimpleCache'  # Use 'RedisCache' em produção
app.config['CACHE_DEFAULT_TIMEOUT'] = int(os.getenv('CACHE_TTL_SECONDS', 300))
cache = Cache(app)

# Mantém variáveis para compatibilidade com código legado
CACHE_TTL = int(os.getenv('CACHE_TTL_SECONDS', 300))  # 5 minutos padrão
cache_lock = Lock()
cache_data = {
    'dashboard': {'data': None, 'timestamp': None},
    'gerenciar': {'data': None, 'timestamp': None},
    'relatorios': {'data': None, 'timestamp': None}
}

# --- CONFIGURAÇÃO DE USUÁRIOS (SIMPLIFICADO) ---
# Em produção, use banco de dados com senhas hasheadas (bcrypt/werkzeug.security)
import json

USERS_FILE = Path(__file__).parent / 'users.json'

# --- DATACLASSES PARA VALIDAÇÃO ---

@dataclass
class ValidacaoResultado:
    """Resultado de uma validação."""
    valido: bool
    erros: List[str]

class ValidadorOS:
    """Validador centralizado para Ordens de Serviço."""
    
    @staticmethod
    def validar_formulario(form_data: Dict[str, Any]) -> ValidacaoResultado:
        """Valida dados do formulário de OS."""
        erros = []
        
        # Validações obrigatórias
        if not form_data.get('nome_solicitante', '').strip():
            erros.append('Nome do solicitante é obrigatório.')
        
        if not form_data.get('setor', '').strip():
            erros.append('Setor é obrigatório.')
        
        if not form_data.get('equipamento', '').strip():
            erros.append('Equipamento ou local afetado é obrigatório.')
        
        descricao = form_data.get('descricao', '').strip()
        if not descricao:
            erros.append('Descrição do problema é obrigatória.')
        elif len(descricao) < 10:
            erros.append('Descrição deve ter pelo menos 10 caracteres.')
        
        prioridade = form_data.get('prioridade')
        if prioridade not in ['Baixa', 'Média', 'Alta', 'Urgente']:
            erros.append('Prioridade inválida.')
        
        return ValidacaoResultado(valido=len(erros) == 0, erros=erros)
    
    @staticmethod
    def validar_atualizacao(form_data: Dict[str, Any]) -> ValidacaoResultado:
        """Valida dados de atualização de OS."""
        erros = []
        
        if not form_data.get('row_id'):
            erros.append('ID da linha é obrigatório.')
        
        status = form_data.get('status_os')
        if status not in ['Aberto', 'Em Andamento', 'Concluído', 'Cancelado']:
            erros.append('Status inválido.')
        
        return ValidacaoResultado(valido=len(erros) == 0, erros=erros)

class ValidadorUsuario:
    """Validador centralizado para usuários."""
    
    @staticmethod
    def validar_cadastro(username: str, password: str, confirm_password: str = None) -> ValidacaoResultado:
        """Valida dados de cadastro de usuário."""
        erros = []
        
        if not username or not password:
            erros.append('Usuário e senha são obrigatórios.')
            return ValidacaoResultado(valido=False, erros=erros)
        
        if len(username) < 3:
            erros.append('Usuário deve ter no mínimo 3 caracteres.')
        
        if len(password) < 6:
            erros.append('Senha deve ter no mínimo 6 caracteres.')
        
        if confirm_password is not None and password != confirm_password:
            erros.append('As senhas não coincidem.')
        
        return ValidacaoResultado(valido=len(erros) == 0, erros=erros)

# --- CONFIGURAÇÃO DE USUÁRIOS (SIMPLIFICADO) ---
# Em produção, use banco de dados com senhas hasheadas (bcrypt/werkzeug.security)
import json

USERS_FILE = Path(__file__).parent / 'users.json'

# Carrega usuários do Google Sheets ou cria usuários padrão
def carregar_usuarios() -> Dict[str, Dict[str, str]]:
    """Carrega usuários do Google Sheets.
    Se a aba não estiver disponível ou ocorrer erro, retorna os usuários em memória
    (mantendo os existentes) em vez de valores padrão.
    """
    global sheet_usuarios, USUARIOS
    
    if not sheet_usuarios:
        logger.warning("Aba de usuários não disponível. Mantendo usuários em memória.")
        # Retorna os usuários já carregados em memória para evitar perda
        memoria = USUARIOS if isinstance(USUARIOS, dict) and USUARIOS else {
            'admin': {'senha': 'admin123', 'role': 'admin'}
        }
        return memoria
    
    try:
        # Lê todos os registros da aba de usuários
        records = sheet_usuarios.get_all_records()
        usuarios = {}
        
        for record in records:
            username = record.get('Username', '').strip()
            senha = record.get('Senha', '').strip()
            role = record.get('Role', 'admin').strip()
            
            if username and senha:
                usuarios[username] = {'senha': senha, 'role': role}
        
        logger.info(f"Carregados {len(usuarios)} usuários do Google Sheets")
        # Se por algum motivo não houver registros, mantém o que já está em memória ou retorna admin padrão
        if not usuarios:
            memoria = USUARIOS if isinstance(USUARIOS, dict) and USUARIOS else {
                'admin': {'senha': 'admin123', 'role': 'admin'}
            }
            return memoria
        return usuarios
    
    except Exception as e:
        logger.error(f"Erro ao carregar usuários do Google Sheets: {e}")
        # Em caso de erro, manter usuários atuais em memória para evitar apagar novos
        memoria = USUARIOS if isinstance(USUARIOS, dict) and USUARIOS else {
            'admin': {'senha': 'admin123', 'role': 'admin'}
        }
        return memoria

def salvar_usuarios(usuarios: Dict[str, Dict[str, str]]) -> bool:
    """Realiza upsert de usuários no Google Sheets sem apagar existentes.
    Mantém TODOS os registros atuais do Sheets e atualiza/inclui apenas os informados.
    
    Args:
        usuarios: Dicionário com username como chave e dict com senha/role como valor
    
    Returns:
        True se sucesso, False se erro
    """
    global sheet_usuarios

    if not sheet_usuarios:
        logger.error("Aba de usuários não disponível. Não foi possível salvar.")
        return False

    try:
        # Carrega TODOS os registros existentes no Sheets
        all_records = sheet_usuarios.get_all_records()
        header = sheet_usuarios.row_values(1) or ['Username', 'Senha', 'Role']
        username_idx = header.index('Username') + 1 if 'Username' in header else 1
        senha_idx = header.index('Senha') + 1 if 'Senha' in header else 2
        role_idx = header.index('Role') + 1 if 'Role' in header else 3

        # Mapeia usuários existentes no Sheets por linha
        existing_rows_by_username = {}
        for i, rec in enumerate(all_records, start=2):
            uname = str(rec.get('Username', '')).strip()
            if uname:
                existing_rows_by_username[uname] = {
                    'row': i,
                    'senha': rec.get('Senha', ''),
                    'role': rec.get('Role', 'admin')
                }

        # Para cada usuário no dict passado, atualiza linha existente ou adiciona nova
        for username, dados in usuarios.items():
            senha = dados.get('senha', '') if isinstance(dados, dict) else dados
            role = dados.get('role', 'admin') if isinstance(dados, dict) else 'admin'

            if username in existing_rows_by_username:
                # Atualiza usuário existente
                row = existing_rows_by_username[username]['row']
                sheet_usuarios.update_cell(row, username_idx, username)
                sheet_usuarios.update_cell(row, senha_idx, senha)
                sheet_usuarios.update_cell(row, role_idx, role)
                logger.info(f"Usuário {username} atualizado na linha {row}")
            else:
                # Adiciona novo usuário
                sheet_usuarios.append_row([username, senha, role])
                logger.info(f"Novo usuário {username} adicionado")

        logger.info(f"Upsert de {len(usuarios)} usuários concluído. Total no Sheets: {len(existing_rows_by_username)} existentes")
        return True

    except Exception as e:
        logger.error(f"Erro ao salvar usuários no Google Sheets (upsert): {e}")
        return False

def deletar_usuario_sheets(username: str) -> bool:
    """Deleta um usuário específico do Google Sheets.
    
    Args:
        username: Nome do usuário a ser deletado
    
    Returns:
        True se deletado com sucesso, False caso contrário
    """
    global sheet_usuarios
    
    if not sheet_usuarios:
        logger.error("Aba de usuários não disponível. Não foi possível deletar.")
        return False
    
    try:
        all_records = sheet_usuarios.get_all_records()
        
        # Encontra a linha do usuário (records começam na linha 2)
        for i, rec in enumerate(all_records, start=2):
            if str(rec.get('Username', '')).strip() == username:
                sheet_usuarios.delete_rows(i)
                logger.info(f"Usuário {username} deletado da linha {i} no Google Sheets")
                return True
        
        logger.warning(f"Usuário {username} não encontrado no Google Sheets")
        return False
        
    except Exception as e:
        logger.error(f"Erro ao deletar usuário {username} do Google Sheets: {e}")
        return False

# --- DECORATOR DE AUTENTICAÇÃO ---
def login_required(f):
    """Decorator para proteger rotas que requerem autenticação."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario' not in session:
            flash('Por favor, faça login para acessar esta página.', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator para rotas que requerem privilégios de admin."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario' not in session:
            flash('Por favor, faça login para acessar esta página.', 'warning')
            return redirect(url_for('login', next=request.url))
        
        usuario = session.get('usuario')
        if USUARIOS.get(usuario, {}).get('role') != 'admin':
            flash('Acesso negado. Apenas administradores podem acessar esta página.', 'danger')
            return redirect(url_for('homepage'))
        
        return f(*args, **kwargs)
    return decorated_function

# USUARIOS já foi carregado após a conexão com Sheets (linha ~105)

@app.route('/usuarios', methods=['GET', 'POST'])
@admin_required
def usuarios_admin():
    """Admin UI to list/add/update/delete users stored in Google Sheets."""
    global USUARIOS
    mensagem = None
    tipo_mensagem = 'success'

    # Handle create/update/delete
    if request.method == 'POST':
        acao = request.form.get('acao')
        username = request.form.get('username', '').strip()
        if not username:
            mensagem = 'Username é obrigatório.'
            tipo_mensagem = 'danger'
        else:
            if acao == 'delete':
                # Remove do dict e do Google Sheets
                if username in USUARIOS:
                    USUARIOS.pop(username, None)
                    # Deleta fisicamente do Sheets
                    if deletar_usuario_sheets(username):
                        mensagem = f'Usuário {username} removido com sucesso.'
                    else:
                        mensagem = f'Usuário {username} removido do sistema, mas erro ao deletar do Sheets.'
                        tipo_mensagem = 'warning'
                else:
                    mensagem = 'Usuário não encontrado.'
                    tipo_mensagem = 'warning'
            else:
                senha = request.form.get('senha', '').strip()
                role = request.form.get('role', 'admin').strip()
                if not senha:
                    mensagem = 'Senha é obrigatória.'
                    tipo_mensagem = 'danger'
                else:
                    # Gera hash da senha antes de salvar
                    senha_hash = generate_password_hash(senha, method='pbkdf2:sha256')
                    USUARIOS[username] = {'senha': senha_hash, 'role': role}
                    salvar_usuarios(USUARIOS)
                    mensagem = f'Usuário {username} salvo com sucesso.'

    # Refresh from Sheets to show latest (mantém em memória se indisponível)
    USUARIOS = carregar_usuarios()
    return render_template('usuarios.html', usuarios=USUARIOS, mensagem=mensagem, tipo_mensagem=tipo_mensagem)

# --- FUNÇÕES AUXILIARES ---

def validar_formulario(form_data: Dict[str, Any]) -> List[str]:
    """Valida formulário usando ValidadorOS (mantido para compatibilidade).
    
    Args:
        form_data: Dados do formulário
    
    Returns:
        Lista de erros (vazia se válido)
    """
    resultado = ValidadorOS.validar_formulario(form_data)
    return resultado.erros

def obter_proximo_id() -> str:
    """Obtém o próximo ID disponível para uma nova OS.
    
    Returns:
        String com o próximo ID no formato adequado
    """
    """Valida os campos do formulário de abertura de OS."""
    erros = []
    
    if not form_data.get('nome_solicitante', '').strip():
        erros.append('Nome do solicitante é obrigatório.')
    elif len(form_data.get('nome_solicitante', '')) > 100:
        erros.append('Nome do solicitante muito longo (máx 100 caracteres).')
    
    if not form_data.get('setor', '').strip():
        erros.append('Setor é obrigatório.')
    
    if not form_data.get('descricao', '').strip():
        erros.append('Descrição é obrigatória.')
    elif len(form_data.get('descricao', '')) > 1000:
        erros.append('Descrição muito longa (máx 1000 caracteres).')
    
    if not form_data.get('equipamento', '').strip():
        erros.append('Equipamento/Local é obrigatório.')
    
    if not form_data.get('prioridade'):
        erros.append('Prioridade é obrigatória.')
    
    return erros

def obter_proximo_id():
    """Busca o último ID da planilha e retorna o próximo número disponível."""
    try:
        # Obtém todos os valores da coluna A (IDs)
        ids_column = sheet.col_values(1)
        
        # Remove o cabeçalho
        if ids_column:
            ids_column = ids_column[1:]
        
        # Converte para inteiros, ignorando valores vazios ou inválidos
        ids_numericos = []
        for id_val in ids_column:
            try:
                if id_val and str(id_val).strip():
                    ids_numericos.append(int(id_val))
            except ValueError:
                continue
        
        # Retorna o máximo + 1, ou 1 se não houver IDs
        if ids_numericos:
            return max(ids_numericos) + 1
        else:
            return 1
    except Exception as e:
        logger.error(f"Erro ao obter próximo ID: {e}")
        # Fallback: usar timestamp como ID
        return int(datetime.datetime.now().timestamp())

def verificar_sheet_disponivel():
    """Verifica se a conexão com a planilha está disponível."""
    if sheet is None:
        logger.warning("Tentativa de acesso à planilha sem conexão estabelecida.")
        return False, sheet_error or "Conexão com Google Sheets não disponível."
    return True, None

def obter_cache(chave):
    """Obtém dados do cache se ainda válidos."""
    with cache_lock:
        cache_entry = cache_data.get(chave)
        if cache_entry and cache_entry['timestamp']:
            idade = (datetime.datetime.now() - cache_entry['timestamp']).total_seconds()
            if idade < CACHE_TTL:
                logger.info(f"Cache HIT para '{chave}' (idade: {idade:.1f}s)")
                return cache_entry['data']
            else:
                logger.info(f"Cache EXPIRED para '{chave}' (idade: {idade:.1f}s)")
        else:
            logger.info(f"Cache MISS para '{chave}'")
    return None

def salvar_cache(chave: str, dados: Any) -> None:
    """Armazena dados no cache com timestamp.
    
    Args:
        chave: Chave para armazenar os dados
        dados: Dados a serem cacheados
    """
    with cache_lock:
        cache_data[chave] = {
            'data': dados,
            'timestamp': datetime.datetime.now()
        }
        logger.info(f"Cache SAVED para '{chave}'")

def limpar_cache(chave: Optional[str] = None) -> None:
    """Limpa o cache (específico ou todo).
    
    Args:
        chave: Chave específica para limpar, ou None para limpar tudo
    """
    with cache_lock:
        if chave:
            if chave in cache_data:
                cache_data[chave] = {'data': None, 'timestamp': None}
                logger.info(f"Cache limpo para '{chave}'")
        else:
            for key in cache_data:
                cache_data[key] = {'data': None, 'timestamp': None}
            logger.info("Todo o cache foi limpo")

# --- CONFIGURAÇÃO DE USUÁRIOS (SIMPLIFICADO) ---
# Em produção, use banco de dados com senhas hasheadas (bcrypt/werkzeug.security)
USUARIOS = {
    'admin': 'admin123',
    'gestor': 'gestor123',
    'operador': 'operador123'
}

# --- ROTAS DE AUTENTICAÇÃO ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Página de login do sistema."""
    # Se já estiver logado, redireciona para dashboard
    if 'usuario' in session:
        return redirect(url_for('homepage'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        # Valida credenciais com hash seguro
        if username in USUARIOS:
            user_data = USUARIOS[username]
            senha_hash = None
            role = 'admin'
            
            # Se for formato antigo (string sem hash), converte
            if isinstance(user_data, str):
                # Senha em texto plano (formato legado)
                if user_data == password:
                    # Atualiza para formato com hash
                    senha_hash = generate_password_hash(password, method='pbkdf2:sha256')
                    USUARIOS[username] = {'senha': senha_hash, 'role': 'admin'}
                    salvar_usuarios(USUARIOS)
                    role = 'admin'
                else:
                    return render_template('login.html', erro='Usuário ou senha inválidos.')
            # Formato novo (dict)
            elif isinstance(user_data, dict):
                senha_hash = user_data['senha']
                role = user_data.get('role', 'admin')
                
                # Verifica se é senha em texto plano ou hash
                if senha_hash.startswith('pbkdf2:sha256:') or senha_hash.startswith('scrypt:'):
                    # Senha com hash - valida com check_password_hash
                    if not check_password_hash(senha_hash, password):
                        return render_template('login.html', erro='Usuário ou senha inválidos.')
                else:
                    # Senha em texto plano (migração) - valida e atualiza para hash
                    if senha_hash != password:
                        return render_template('login.html', erro='Usuário ou senha inválidos.')
                    # Atualiza para hash
                    senha_hash = generate_password_hash(password, method='pbkdf2:sha256')
                    USUARIOS[username] = {'senha': senha_hash, 'role': role}
                    salvar_usuarios(USUARIOS)
            
            # Login bem-sucedido
            session['usuario'] = username
            session['role'] = role
            session.permanent = True
            flash(f'Bem-vindo, {username}!', 'success')
            
            # Redireciona para a página solicitada ou homepage
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            return redirect(url_for('homepage'))
        
        return render_template('login.html', erro='Usuário ou senha inválidos.')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Faz logout do usuário."""
    usuario = session.get('usuario', 'Usuário')
    session.clear()
    flash(f'Logout realizado com sucesso. Até logo, {usuario}!', 'info')
    return redirect(url_for('login'))

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    """Página de cadastro de novos usuários."""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        
        # Usa validador centralizado
        validacao = ValidadorUsuario.validar_cadastro(username, password, confirm_password)
        if not validacao.valido:
            return render_template('cadastro.html', erro=' '.join(validacao.erros))
        
        if username in USUARIOS:
            return render_template('cadastro.html', erro='Usuário já existe. Escolha outro nome.')
        
        # Cria novo usuário com senha hasheada e role 'admin'
        senha_hash = generate_password_hash(password, method='pbkdf2:sha256')
        USUARIOS[username] = {'senha': senha_hash, 'role': 'admin'}
        salvar_usuarios(USUARIOS)
        
        flash(f'Cadastro realizado com sucesso! Você pode fazer login agora.', 'success')
        return redirect(url_for('login'))
    
    return render_template('cadastro.html')

# --- 2. ROTA PRINCIPAL (Formulário de Abertura) ---

@app.route('/')
def homepage():
    """Exibe a página inicial com o formulário (index.html)."""
    return render_template('index.html')

# --- 3. ROTA DE ENVIO (Recebe dados do Formulário) ---

@app.route('/enviar', methods=['POST'])
def receber_requerimento():
    """Recebe os dados do formulário e adiciona como uma nova linha na planilha."""
    # Verifica disponibilidade da planilha
    disponivel, erro_msg = verificar_sheet_disponivel()
    if not disponivel:
        logger.error(f"Tentativa de envio sem sheet disponível: {erro_msg}")
        return render_template('erro.html', mensagem=erro_msg), 503
    
    # Valida os dados do formulário
    erros = validar_formulario(request.form)
    if erros:
        logger.warning(f"Validação falhou: {erros}")
        return render_template('index.html', erros=erros), 400
    
    try:
        solicitante = request.form.get('nome_solicitante').strip()
        setor = request.form.get('setor').strip()
        descricao = request.form.get('descricao').strip()
        equipamento = request.form.get('equipamento').strip()
        prioridade = request.form.get('prioridade')
        info_adicional = request.form.get('info_adicional', '').strip() 

        agora = datetime.datetime.now()
        data_solicitacao = agora.strftime("%d/%m/%Y")
        timestamp = agora.strftime("%d/%m/%Y %H:%M:%S")
        status_os = "Aberto"
        
        coluna_id_temporaria = "" 
        servico_realizado = ""
        horario_inicio = ""
        horario_termino = ""
        horas_trabalhadas = ""

        nova_linha = [
            coluna_id_temporaria, # A: / (Será preenchido abaixo)
            timestamp,          # B: Carimbo de data/hora
            solicitante,        # C: Nome do solicitante
            setor,              # D: Setor em que será realizado o serviço
            data_solicitacao,   # E: Data da Solicitação (Formato dd/mm/YYYY)
            descricao,          # F: Descrição do Problema...
            equipamento,        # G: Equipamento ou Local afetado
            prioridade,         # H: Nível de prioridade
            status_os,          # I: Status da OS
            info_adicional,     # J: Informações adicionais (Opcional)
            servico_realizado,  # K: Serviço realizado
            horario_inicio,     # L: Horario de Inicio
            horario_termino,    # M: Horario de Término
            horas_trabalhadas   # N: Horas trabalhadas
        ]

        # Obtém o próximo ID de forma robusta
        numero_pedido = obter_proximo_id()
        
        # Atualiza a primeira coluna com o ID correto
        nova_linha[0] = numero_pedido
        
        try:
            # Garante que a linha será adicionada ao final da planilha
            result = sheet.append_row(nova_linha, value_input_option='USER_ENTERED', insert_data_option='INSERT_ROWS')
            
            # Invalida cache após inserção
            limpar_cache()
            
            logger.info(f"Nova OS (Pedido #{numero_pedido}) adicionada por: {solicitante}")
            
            return render_template('sucesso.html', nome=solicitante, os_numero=numero_pedido)
            
        except Exception as e:
            logger.error(f"ERRO ao adicionar linha na planilha: {e}")
            return render_template('erro.html', 
                mensagem="Erro ao salvar OS. Por favor, tente novamente."), 500

    except Exception as e:
        logger.error(f"Erro ao salvar dados: {e}")
        return render_template('erro.html', 
            mensagem=f"Erro ao salvar seu requerimento: {e}"), 500

# --- 4. ROTA DO DASHBOARD (Gráficos) ---

@app.route('/dashboard')
@admin_required
def dashboard():
    """Exibe o dashboard com gráficos de análise dos chamados."""
    disponivel, erro_msg = verificar_sheet_disponivel()
    if not disponivel:
        return render_template('dashboard.html', labels_meses=[], datasets_status=[], 
            mensagem_erro=erro_msg)
    
    # Tenta obter do cache primeiro
    cache_result = obter_cache('dashboard')
    if cache_result:
        return render_template('dashboard.html', 
            labels_meses=cache_result['labels_meses'],
            datasets_status=cache_result['datasets_status'])
    
    try:
        data = sheet.get_all_values()
        if not data or len(data) < 2:
            return render_template('dashboard.html', labels_meses=[], datasets_status=[])

        headers = data.pop(0) 
        df = pd.DataFrame(data, columns=headers)

        if 'Carimbo de data/hora' not in df.columns or 'Status da OS' not in df.columns:
            raise Exception("Planilha não contém 'Carimbo de data/hora' ou 'Status da OS'.")

        df['Carimbo de data/hora'] = pd.to_datetime(df['Carimbo de data/hora'], format='%d/%m/%Y %H:%M:%S', errors='coerce')
        df = df.dropna(subset=['Carimbo de data/hora'])
        
        df['MesAno'] = df['Carimbo de data/hora'].dt.to_period('M').astype(str)

        status_por_mes = df.groupby(['MesAno', 'Status da OS']).size().unstack(fill_value=0)

        labels_meses = status_por_mes.index.tolist()
        
        datasets_status = []
        cores = {
            'Finalizada': 'rgba(75, 192, 192, 0.7)',  # Verde
            'Em Andamento': 'rgba(54, 162, 235, 0.7)', # Azul
            'Aguardando Compra': 'rgba(255, 159, 64, 0.7)', # Laranja
            'Cancelada': 'rgba(217, 83, 79, 0.7)', # Vermelho
            'Aberto': 'rgba(108, 117, 125, 0.7)' # Cinza
         }

        for status in status_por_mes.columns:
            dataset = {
                'label': status,
                'data': status_por_mes[status].values.tolist(),
                'backgroundColor': cores.get(status, 'rgba(201, 203, 207, 0.7)')
            }
            datasets_status.append(dataset)
        
        # Salva no cache antes de retornar
        resultado = {
            'labels_meses': labels_meses,
            'datasets_status': datasets_status
        }
        salvar_cache('dashboard', resultado)
        
        return render_template(
            'dashboard.html',
            labels_meses=labels_meses,
            datasets_status=datasets_status
        )
    except Exception as e:
        logger.error(f"Erro ao carregar dashboard: {e}")
        return render_template('erro.html', 
            mensagem=f"Erro ao carregar o dashboard: {e}"), 500

# --- 5. ROTA DE GERENCIAMENTO (Listar e Editar Chamados) ---

@app.route('/gerenciar')
@admin_required
def gerenciar():
    """Exibe a página de gerenciamento com a lista de todos os chamados."""
    disponivel, erro_msg = verificar_sheet_disponivel()
    if not disponivel:
        return render_template('gerenciar.html', chamados=[], 
            current_sort='Carimbo de data/hora', current_order='desc',
            mensagem_erro=erro_msg)
    
    sort_by = request.args.get('sort_by', 'Carimbo de data/hora')
    order = request.args.get('order', 'desc')
    
    # Tenta obter do cache primeiro
    cache_result = obter_cache('gerenciar')
    if cache_result:
        chamados_filtrados = cache_result
    else:
        try:
            data = sheet.get_all_values()
            if not data or len(data) < 2:
                return render_template('gerenciar.html', chamados=[], current_sort=sort_by, current_order=order)

            headers = data.pop(0)
            
            if 'Status da OS' not in headers:
                raise ValueError("A coluna 'Status da OS' não foi encontrada na planilha. Verifique o cabeçalho.")
            
            status_index = headers.index('Status da OS')
            
            chamados_filtrados = []
            
            for i, row in enumerate(data):
                if not any(row):
                    continue

                if len(row) > status_index and row[status_index] == 'Cancelada':
                    continue
                    
                chamado = {'row_id': i + 2}
                
                full_row = row + [''] * (len(headers) - len(row))
                
                chamado.update(zip(headers, full_row))
                chamados_filtrados.append(chamado)
            
            # Salva os dados filtrados no cache
            salvar_cache('gerenciar', chamados_filtrados)
            
        except Exception as e:
            logger.error(f"Erro ao carregar dados da planilha: {e}")
            return render_template('erro.html', 
                mensagem=f"Erro ao carregar dados: {e}"), 500
    
    # Aplica ordenação (sempre executada, mesmo com cache)
    try:
        def sort_key(item):
            try:
                if sort_by == 'Carimbo de data/hora':
                    return datetime.datetime.strptime(item.get(sort_by, ''), '%d/%m/%Y %H:%M:%S')
                return item.get(sort_by, '').lower()
            except ValueError:
                return datetime.datetime.min

        chamados_ordenados = sorted(chamados_filtrados, key=sort_key, reverse=(order == 'desc'))
        
        return render_template(
            'gerenciar.html',
            chamados=chamados_ordenados,
            current_sort=sort_by,
            current_order=order
        )
    except Exception as e:
        logger.error(f"Erro ao ordenar chamados: {e}")
        return render_template('erro.html', 
            mensagem=f"Erro ao processar dados: {e}"), 500

# --- 6. ROTA DE ATUALIZAÇÃO (Recebe dados do Modal de Edição) ---

@app.route('/atualizar_chamado', methods=['POST'])
@admin_required
def atualizar_chamado():
    """Atualiza uma linha inteira na planilha com os dados do modal de edição."""
    disponivel, erro_msg = verificar_sheet_disponivel()
    if not disponivel:
        logger.error(f"Tentativa de atualização sem sheet disponível: {erro_msg}")
        return render_template('erro.html', mensagem=erro_msg), 503
    
    try:
        solicitante = request.form.get('nome_solicitante', '')
        setor = request.form.get('setor', '')
        data_solicitacao = request.form.get('data_solicitacao', '')
        descricao = request.form.get('descricao', '')
        equipamento = request.form.get('equipamento', '')
        prioridade = request.form.get('prioridade', '')
        info_adicional = request.form.get('info_adicional', '')
        
        status_os = request.form.get('status_os', '')
        servico_realizado = request.form.get('servico_realizado', '')
        horario_inicio = request.form.get('horario_inicio', '')
        horario_termino = request.form.get('horario_termino', '')
        horas_trabalhadas = request.form.get('horas_trabalhadas', '')
        
        row_id = int(request.form.get('row_id'))
        
        timestamp = sheet.cell(row_id, 2).value # Coluna B = 2
        os_id = sheet.cell(row_id, 1).value # Coluna A = 1

        linha_atualizada = [
            os_id,              # A: / (Preservado)
            timestamp,          # B: Carimbo de data/hora (Preservado)
            solicitante,        # C: Nome do solicitante
            setor,              # D: Setor
            data_solicitacao,   # E: Data da Solicitação
            descricao,          # F: Descrição
            equipamento,        # G: Equipamento
            prioridade,         # H: Prioridade
            status_os,          # I: Status da OS (Atualizado)
            info_adicional,     # J: Informações Adicionais
            servico_realizado,  # K: Serviço Realizado (Atualizado)
            horario_inicio,     # L: Horário Início (Atualizado)
            horario_termino,    # M: Horário Término (Atualizado)
            horas_trabalhadas   # N: Horas Trabalhadas (Atualizado)
        ]

        sheet.update(f'A{row_id}:N{row_id}', [linha_atualizada])
        
        # Invalida cache após atualização
        limpar_cache()

        logger.info(f"Chamado (Linha {row_id}) atualizado com status: {status_os}")

        return redirect(url_for('gerenciar'))
        
    except Exception as e:
        logger.error(f"Erro ao atualizar chamado: {e}")
        return render_template('erro.html', 
            mensagem=f"Erro ao atualizar o chamado: {e}"), 500

# --- 7. ROTA DE SUCESSO (Página de confirmação) ---

@app.route('/sucesso')
@login_required
def sucesso():
    """Página de sucesso (para caso o /enviar fosse GET)."""
    return render_template('sucesso.html', nome="Usuário")

# --- 7.1. ROTA ADMINISTRATIVA - LIMPAR CACHE ---

@app.route('/admin/limpar-cache', methods=['POST', 'GET'])
@admin_required
def admin_limpar_cache():
    """Limpa o cache manualmente (útil para admins/devs)."""
    try:
        limpar_cache()
        logger.info("Cache limpo manualmente via rota /admin/limpar-cache")
        flash('Cache limpo com sucesso!', 'success')
        return redirect(request.referrer or url_for('homepage'))
    except Exception as e:
        logger.error(f"Erro ao limpar cache: {e}")
        return render_template('erro.html', mensagem=f"Erro ao limpar cache: {e}"), 500


# --- 8. ROTA DE CONTROLE DE HORÁRIO ---

@app.route('/controle-horario', methods=['GET', 'POST'])
@admin_required
def controle_horario():
    """Página de controle de ponto com registros de entrada, saída e pausas para múltiplos usuários."""
    disponivel, erro_msg = verificar_sheet_disponivel()
    
    mensagem = None
    tipo_mensagem = 'success'
    usuarios_ativos = []
    registros = []
    total_registros = 0
    page = int(request.args.get('page', '1'))
    per_page = int(request.args.get('per_page', '20'))
    usuario_filtro = request.args.get('usuario', '').strip()
    os_filtro = request.args.get('pedido_os', '').strip()
    data_inicio = request.args.get('data_inicio', '').strip()
    data_fim = request.args.get('data_fim', '').strip()
    export_param = request.args.get('export', '').strip().lower()
    export_csv = export_param == 'csv'
    export_xlsx = export_param == 'xlsx'
    tipo_filtro = request.args.get('tipo', '').strip().lower()  # entrada|pausa|retorno|saída
    
    if not disponivel or sheet_horario is None:
        return render_template('controle_horario.html',
            usuarios_ativos=[],
            registros=[],
            mensagem="Sistema de controle de horário indisponível. Verifique a conexão com Google Sheets.",
            tipo_mensagem='error')
    
    try:
        hoje_dt = datetime.datetime.now()
        hoje = hoje_dt.strftime('%d/%m/%Y')
        agora = hoje_dt
        
        # Processa ação se for POST
        if request.method == 'POST':
            acao = request.form.get('acao')
            
            if acao == 'fechar_os':
                # Fechar OS específica
                funcionario = request.form.get('funcionario_fechar')
                pedido_os = request.form.get('pedido_fechar')
                
                if funcionario and pedido_os:
                    # Busca se já tem saída para essa OS hoje
                    all_data = sheet_horario.get_all_values()
                    ja_tem_saida = False
                    
                    if len(all_data) > 1:
                        for row in all_data[1:]:
                            if (len(row) > 3 and row[0] == hoje and 
                                row[1] == funcionario and row[2] == pedido_os and 
                                row[3].lower() == 'saída'):
                                ja_tem_saida = True
                                break
                    
                    if not ja_tem_saida:
                        horario_registro = agora.strftime('%H:%M:%S')
                        nova_linha = [hoje, funcionario, pedido_os, 'Saída', horario_registro, 'Fechamento de OS']
                        sheet_horario.append_row(nova_linha, value_input_option='USER_ENTERED')
                        logger.info(f"OS {pedido_os} fechada por {funcionario} às {horario_registro}")
                        mensagem = f"OS #{pedido_os} fechada com sucesso!"
                    else:
                        mensagem = f"OS #{pedido_os} já foi fechada."
                        tipo_mensagem = 'warning'
            else:
                # Registro normal (entrada, pausa, retorno, saída)
                nome_usuario = request.form.get('nome_usuario', 'Usuário').strip() or 'Usuário'
                pedido_os = request.form.get('pedido_os', '').strip()
                
                if not pedido_os:
                    mensagem = "Número do Pedido/OS é obrigatório!"
                    tipo_mensagem = 'error'
                else:
                    horario_registro = agora.strftime('%H:%M:%S')
                    
                    tipo_map = {
                        'entrada': 'Entrada',
                        'saida': 'Saída',
                        'pausa': 'Pausa',
                        'retorno': 'Retorno'
                    }
                    
                    # Registra na planilha
                    nova_linha = [
                        hoje,
                        nome_usuario,
                        pedido_os,
                        tipo_map.get(acao, acao),
                        horario_registro,
                        ''
                    ]
                    
                    sheet_horario.append_row(nova_linha, value_input_option='USER_ENTERED')
                    logger.info(f"Registro de {acao} - {nome_usuario} - OS {pedido_os} às {horario_registro}")
                    
                    mensagem = f"{tipo_map.get(acao, acao)} registrada para OS #{pedido_os}"
            
            limpar_cache()
        
        # Busca registros de período (por padrão: hoje)
        all_data = sheet_horario.get_all_values()
        if len(all_data) > 1:
            headers = all_data[0]
            registros_raw = all_data[1:]
            
            # Constrói filtro de datas (suporta dd/mm/YYYY e YYYY-mm-dd)
            def parse_data(d):
                if not d:
                    return None
                for fmt in ('%d/%m/%Y', '%Y-%m-%d'):
                    try:
                        return datetime.datetime.strptime(d, fmt)
                    except:
                        continue
                return None

            def to_iso(dstr):
                dt = parse_data(dstr)
                return dt.strftime('%Y-%m-%d') if dt else ''

            dt_inicio = parse_data(data_inicio) if data_inicio else hoje_dt
            dt_fim = parse_data(data_fim) if data_fim else hoje_dt

            # Normaliza ordem das datas
            if dt_inicio and dt_fim and dt_inicio > dt_fim:
                dt_inicio, dt_fim = dt_fim, dt_inicio

            registros_periodo = []
            aviso_periodo = None
            # Limite de 30 dias no período
            if dt_inicio and dt_fim:
                delta = (dt_fim - dt_inicio).days
                if delta > 30:
                    # Cap período para últimos 30 dias
                    dt_inicio = dt_fim - datetime.timedelta(days=30)
                    aviso_periodo = 'Período limitado aos últimos 30 dias.'
            for row in registros_raw:
                if len(row) == 0:
                    continue
                data_str = row[0]
                dreg = parse_data(data_str)
                if not dreg:
                    continue
                if dt_inicio and dreg < dt_inicio:
                    continue
                if dt_fim and dreg > dt_fim:
                    continue

                reg = {
                    'data': row[0],
                    'funcionario': row[1] if len(row) > 1 else '',
                    'pedido_os': row[2] if len(row) > 2 else '',
                    'tipo': (row[3].lower() if len(row) > 3 else ''),
                    'tipo_nome': row[3] if len(row) > 3 else '',
                    'horario': row[4] if len(row) > 4 else '',
                    'observacao': row[5] if len(row) > 5 else ''
                }

                # Filtros de usuário, OS, tipo
                if usuario_filtro and usuario_filtro.lower() not in reg['funcionario'].lower():
                    continue
                if os_filtro and os_filtro.lower() not in str(reg['pedido_os']).lower():
                    continue
                if tipo_filtro and reg['tipo'] != tipo_filtro:
                    continue

                registros_periodo.append(reg)

            # Ordena decrescente por data e horário
            registros_periodo.sort(key=lambda x: (x['data'], x['horario']), reverse=True)

            # CSV export
            if export_csv:
                import csv
                from io import StringIO
                si = StringIO()
                writer = csv.DictWriter(si, fieldnames=['data','funcionario','pedido_os','tipo_nome','horario','observacao'])
                writer.writeheader()
                for r in registros_periodo:
                    writer.writerow(r)
                from flask import Response
                filename = f"historico_{(dt_inicio or hoje_dt).strftime('%Y%m%d')}_{(dt_fim or hoje_dt).strftime('%Y%m%d')}.csv"
                return Response(
                    si.getvalue(),
                    mimetype='text/csv',
                    headers={
                        'Content-Disposition': f'attachment; filename="{filename}"'
                    }
                )

            # XLSX export
            if export_xlsx:
                try:
                    from io import BytesIO
                    import pandas as pd
                    buffer = BytesIO()
                    df = pd.DataFrame(registros_periodo)
                    # Reordenar e renomear colunas
                    cols = ['data','funcionario','pedido_os','tipo_nome','horario','observacao']
                    df = df[cols]
                    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                        df.to_excel(writer, index=False, sheet_name='Historico')
                    buffer.seek(0)
                    from flask import Response
                    filename = f"historico_{(dt_inicio or hoje_dt).strftime('%Y%m%d')}_{(dt_fim or hoje_dt).strftime('%Y%m%d')}.xlsx"
                    return Response(
                        buffer.read(),
                        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                        headers={
                            'Content-Disposition': f'attachment; filename="{filename}"'
                        }
                    )
                except Exception as e:
                    logger.error(f"Erro ao exportar XLSX: {e}")
                    mensagem = f"Falha ao exportar XLSX: {e}"
                    tipo_mensagem = 'error'

            # Paginação
            total_registros = len(registros_periodo)
            inicio = (page - 1) * per_page
            fim = inicio + per_page
            registros = registros_periodo[inicio:fim]
            
            # Agrupa por usuário e OS para calcular status (apenas para o dia atual)
            os_por_usuario = {}
            registros_dia_atual = [r for r in registros_periodo if r['data'] == hoje]
            for reg in registros_dia_atual:
                chave = f"{reg['funcionario']}|{reg['pedido_os']}"
                if chave not in os_por_usuario:
                    os_por_usuario[chave] = []
                os_por_usuario[chave].append(reg)
            
            # Processa cada OS ativa
            for chave, regs in os_por_usuario.items():
                funcionario, pedido_os = chave.split('|')
                if not pedido_os:
                    continue
                
                # Ordena registros por horário
                regs_ordenados = sorted(regs, key=lambda x: x['horario'])
                ultimo_reg = regs_ordenados[-1]
                
                # Verifica se ainda está ativa (sem saída)
                if ultimo_reg['tipo'] != 'saída':
                    # Calcula tempo trabalhado
                    total_trabalho = datetime.timedelta()
                    tempo_inicio = None
                    em_pausa = False
                    pausa_inicio = None
                    
                    for reg in regs_ordenados:
                        horario = datetime.datetime.strptime(reg['horario'], '%H:%M:%S')
                        
                        if reg['tipo'] == 'entrada':
                            tempo_inicio = horario
                            em_pausa = False
                        elif reg['tipo'] == 'pausa' and tempo_inicio:
                            if not em_pausa:
                                total_trabalho += horario - tempo_inicio
                                pausa_inicio = horario
                                em_pausa = True
                        elif reg['tipo'] == 'retorno' and pausa_inicio:
                            tempo_inicio = horario
                            em_pausa = False
                    
                    # Se ainda está trabalhando
                    if tempo_inicio and not em_pausa:
                        total_trabalho += agora - tempo_inicio.replace(year=agora.year, month=agora.month, day=agora.day)
                    
                    horas = int(total_trabalho.total_seconds() // 3600)
                    minutos = int((total_trabalho.total_seconds() % 3600) // 60)
                    
                    primeira_entrada = regs_ordenados[0]['horario']
                    
                    usuarios_ativos.append({
                        'funcionario': funcionario,
                        'pedido_os': pedido_os,
                        'status': 'pausa' if ultimo_reg['tipo'] == 'pausa' else 'ativo',
                        'horario_entrada': primeira_entrada,
                        'tempo_trabalhado': f"{horas}h {minutos}m"
                    })
        
        return render_template('controle_horario.html',
            usuarios_ativos=usuarios_ativos,
            registros=registros,
            total_registros=total_registros,
            page=page,
            per_page=per_page,
            usuario_filtro=usuario_filtro,
            os_filtro=os_filtro,
            tipo_filtro=tipo_filtro,
            data_inicio=(data_inicio or hoje),
            data_fim=(data_fim or hoje),
            data_inicio_iso=to_iso(data_inicio) if data_inicio else hoje_dt.strftime('%Y-%m-%d'),
            data_fim_iso=to_iso(data_fim) if data_fim else hoje_dt.strftime('%Y-%m-%d'),
            mensagem=mensagem,
            tipo_mensagem=tipo_mensagem,
            aviso_periodo=aviso_periodo)
            
    except Exception as e:
        logger.error(f"Erro no controle de horário: {e}")
        return render_template('erro.html',
            mensagem=f"Erro ao processar controle de horário: {e}"), 500

# --- 9. ENDPOINT DE HEALTHCHECK ---

@app.route('/health')
def health_check():
    """Endpoint para monitoramento de saúde da aplicação."""
    status = {
        'status': 'healthy',
        'timestamp': datetime.datetime.now().isoformat(),
        'sheets_connected': sheet is not None,
        'cache_enabled': True
    }
    return jsonify(status), 200

# --- 10. ROTA DE RELATÓRIOS DETALHADOS ---

@app.route('/relatorios')
@admin_required
def relatorios():
    """Exibe página de relatórios com gráficos detalhados."""
    disponivel, erro_msg = verificar_sheet_disponivel()
    if not disponivel:
        return render_template('relatorios.html', 
            mensagem_erro=erro_msg,
            labels_prioridade=[], dados_prioridade=[],
            labels_setor=[], dados_setor=[],
            labels_tempo_resolucao=[], dados_tempo_resolucao=[],
            labels_dia_semana=[], dados_dia_semana=[],
            total_os=0, tempo_medio='0 dias', taxa_conclusao='0%')
    
    # Tenta obter do cache primeiro
    cache_result = obter_cache('relatorios')
    if cache_result:
        return render_template('relatorios.html', **cache_result)
    
    try:
        data = sheet.get_all_values()
        if not data or len(data) < 2:
            return render_template('relatorios.html',
                labels_prioridade=[], dados_prioridade=[],
                labels_setor=[], dados_setor=[],
                labels_tempo_resolucao=[], dados_tempo_resolucao=[],
                labels_dia_semana=[], dados_dia_semana=[],
                total_os=0, tempo_medio='0 dias', taxa_conclusao='0%')

        headers = data.pop(0)
        df = pd.DataFrame(data, columns=headers)

        # Converte timestamps
        df['Carimbo de data/hora'] = pd.to_datetime(df['Carimbo de data/hora'], 
            format='%d/%m/%Y %H:%M:%S', errors='coerce')
        df = df.dropna(subset=['Carimbo de data/hora'])
        
        # Filtra OS canceladas
        if 'Status da OS' in df.columns:
            df = df[df['Status da OS'] != 'Cancelada']
            logger.info(f"Relatórios: {len(df)} OS após filtrar canceladas")
        
        # 1. Gráfico de Pizza - Distribuição por Prioridade
        prioridade_count = df['Nível de prioridade'].value_counts()
        labels_prioridade = prioridade_count.index.tolist()
        dados_prioridade = prioridade_count.values.tolist()
        
        # 2. Gráfico de Barras Horizontal - OS por Setor
        setor_count = df['Setor em que será realizado o serviço'].value_counts().head(10)
        labels_setor = setor_count.index.tolist()
        dados_setor = setor_count.values.tolist()
        
        # 3. Gráfico de Linha - Tempo médio de resolução por mês
        df_finalizada = df[df['Status da OS'] == 'Finalizada'].copy()
        if not df_finalizada.empty and 'Horário de Início' in df.columns:
            df_finalizada['Horário de Início'] = pd.to_datetime(
                df_finalizada['Horário de Início'], format='%H:%M', errors='coerce')
            df_finalizada['Horário de Término'] = pd.to_datetime(
                df_finalizada['Horário de Término'], format='%H:%M', errors='coerce')
            
            df_finalizada['Tempo'] = (df_finalizada['Horário de Término'] - 
                df_finalizada['Horário de Início']).dt.total_seconds() / 3600
            
            df_finalizada['MesAno'] = df_finalizada['Carimbo de data/hora'].dt.to_period('M').astype(str)
            tempo_por_mes = df_finalizada.groupby('MesAno')['Tempo'].mean()
            
            labels_tempo_resolucao = tempo_por_mes.index.tolist()
            dados_tempo_resolucao = tempo_por_mes.values.tolist()
        else:
            labels_tempo_resolucao = []
            dados_tempo_resolucao = []
        
        # 4. Gráfico de Barras - OS abertas por dia da semana
        df['DiaSemana'] = df['Carimbo de data/hora'].dt.day_name()
        dias_ordem = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        dias_pt = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
        
        dia_count = df['DiaSemana'].value_counts()
        labels_dia_semana = []
        dados_dia_semana = []
        for dia_en, dia_pt in zip(dias_ordem, dias_pt):
            labels_dia_semana.append(dia_pt)
            dados_dia_semana.append(int(dia_count.get(dia_en, 0)))
        
        # Métricas gerais
        total_os = len(df)
        finalizadas = len(df[df['Status da OS'] == 'Finalizada'])
        taxa_conclusao = f"{(finalizadas/total_os*100):.1f}%" if total_os > 0 else "0%"
        
        # Tempo médio de resolução
        if not df_finalizada.empty and 'Tempo' in df_finalizada.columns:
            tempo_medio = f"{df_finalizada['Tempo'].mean():.1f} horas"
        else:
            tempo_medio = "N/A"
        
        # Monta uma tabela resumida (últimas 50 OS)
        df_sorted = df.sort_values('Carimbo de data/hora', ascending=False)
        df_table = df_sorted.head(50)[[
            'Carimbo de data/hora',
            'Nome do solicitante',
            'Setor em que será realizado o serviço',
            'Status da OS',
            'Descrição do Problema ou Serviço Solicitado'
        ]].copy()
        tabela_resumo = [
            {
                'data': row['Carimbo de data/hora'].strftime('%d/%m/%Y %H:%M'),
                'solicitante': row['Nome do solicitante'],
                'setor': row['Setor em que será realizado o serviço'],
                'status': row['Status da OS'],
                'descricao': row['Descrição do Problema ou Serviço Solicitado']
            }
            for _, row in df_table.iterrows()
        ]

        resultado = {
            'labels_prioridade': labels_prioridade,
            'dados_prioridade': dados_prioridade,
            'labels_setor': labels_setor,
            'dados_setor': dados_setor,
            'labels_tempo_resolucao': labels_tempo_resolucao,
            'dados_tempo_resolucao': dados_tempo_resolucao,
            'labels_dia_semana': labels_dia_semana,
            'dados_dia_semana': dados_dia_semana,
            'total_os': total_os,
            'tempo_medio': tempo_medio,
            'taxa_conclusao': taxa_conclusao,
            'total_finalizadas': finalizadas,
            'total_abertas': len(df[df['Status da OS'] == 'Aberto']),
            'total_andamento': len(df[df['Status da OS'] == 'Em Andamento']),
            'tabela_resumo': tabela_resumo
        }
        
        salvar_cache('relatorios', resultado)
        return render_template('relatorios.html', **resultado)
        
    except Exception as e:
        logger.error(f"Erro ao carregar relatórios: {e}")
        return render_template('erro.html', 
            mensagem=f"Erro ao carregar relatórios: {e}"), 500

# --- 10.1 ROTA TEMPO POR FUNCIONÁRIO ---

@app.route('/tempo-por-funcionario')
@admin_required
def tempo_por_funcionario():
    """Exibe página com o tempo que cada funcionário trabalhou em cada OS e gráficos de urgência."""
    disponivel, erro_msg = verificar_sheet_disponivel()
    if not disponivel or sheet_horario is None:
        return render_template('tempo_por_funcionario.html', dados=[], chart_data={}, 
                               mensagem_erro=erro_msg or "Sheets indisponível",
                               funcionario='', pedido_os='', page=1, per_page=20,
                               data_inicio='', data_fim='', data_inicio_iso='', data_fim_iso='',
                               total_registros=0, aviso_periodo=None)

    try:
        # Query params
        funcionario_q = request.args.get('funcionario', '').strip()
        pedido_q = request.args.get('pedido_os', '').strip()
        page = int(request.args.get('page', '1'))
        per_page = int(request.args.get('per_page', '20'))
        data_inicio = request.args.get('data_inicio', '').strip()
        data_fim = request.args.get('data_fim', '').strip()
        export_param = request.args.get('export', '').strip().lower()
        export_csv = export_param == 'csv'
        export_xlsx = export_param == 'xlsx'

        hoje_dt = datetime.datetime.now()

        def parse_data(d):
            if not d:
                return None
            for fmt in ('%d/%m/%Y', '%Y-%m-%d'):
                try:
                    return datetime.datetime.strptime(d, fmt)
                except:
                    continue
            return None

        def to_iso(dstr):
            dt = parse_data(dstr)
            return dt.strftime('%Y-%m-%d') if dt else hoje_dt.strftime('%Y-%m-%d')

        dt_inicio = parse_data(data_inicio) or hoje_dt - datetime.timedelta(days=7)
        dt_fim = parse_data(data_fim) or hoje_dt
        if dt_inicio > dt_fim:
            dt_inicio, dt_fim = dt_fim, dt_inicio

        aviso_periodo = None
        if (dt_fim - dt_inicio).days > 30:
            dt_inicio = dt_fim - datetime.timedelta(days=30)
            aviso_periodo = 'Período limitado aos últimos 30 dias.'

        # Carrega registros de controle de horário (todos)
        all_data = sheet_horario.get_all_values()
        if len(all_data) <= 1:
            return render_template('tempo_por_funcionario.html', dados=[], chart_data={}, mensagem_erro=None,
                                   funcionario=funcionario_q, pedido_os=pedido_q, page=page, per_page=per_page,
                                   data_inicio=dt_inicio.strftime('%d/%m/%Y'), data_fim=dt_fim.strftime('%d/%m/%Y'),
                                   data_inicio_iso=dt_inicio.strftime('%Y-%m-%d'), data_fim_iso=dt_fim.strftime('%Y-%m-%d'),
                                   total_registros=0, aviso_periodo=aviso_periodo)

        registros = []
        for row in all_data[1:]:
            if len(row) < 5:
                continue
            try:
                data = row[0]
                funcionario = row[1]
                pedido_os = row[2]
                tipo = row[3].lower()
                horario = row[4]
                dt_data = datetime.datetime.strptime(data, '%d/%m/%Y')
                dt_hora = datetime.datetime.strptime(horario, '%H:%M:%S')
                dt = dt_hora.replace(year=dt_data.year, month=dt_data.month, day=dt_data.day)
            except:
                continue
            # filtro de período bruto
            if dt < dt_inicio or dt > dt_fim:
                continue
            # filtros por funcionario e pedido
            if funcionario_q and funcionario_q.lower() not in (funcionario or '').lower():
                continue
            if pedido_q and pedido_q.lower() not in str(pedido_os or '').lower():
                continue
            registros.append({'data': dt_data, 'funcionario': funcionario, 'pedido_os': pedido_os, 'tipo': tipo, 'dt': dt})

        # Agrega tempo por funcionário + OS
        tempo_map = {}  # {(funcionario, os): total_seconds}
        from collections import defaultdict
        regs_por_chave = defaultdict(list)
        for r in registros:
            chave = (r['funcionario'], r['pedido_os'])
            regs_por_chave[chave].append(r)

        for chave, regs in regs_por_chave.items():
            regs.sort(key=lambda x: x['dt'])
            trabalhando_inicio = None
            em_pausa = False
            pausa_inicio = None
            total = datetime.timedelta()
            for r in regs:
                if r['tipo'] == 'entrada':
                    trabalhando_inicio = r['dt']
                    em_pausa = False
                elif r['tipo'] == 'pausa' and trabalhando_inicio and not em_pausa:
                    total += (r['dt'] - trabalhando_inicio)
                    pausa_inicio = r['dt']
                    em_pausa = True
                elif r['tipo'] == 'retorno' and pausa_inicio:
                    trabalhando_inicio = r['dt']
                    em_pausa = False
                elif r['tipo'] in ('saída', 'saida') and trabalhando_inicio:
                    if not em_pausa:
                        total += (r['dt'] - trabalhando_inicio)
                    trabalhando_inicio = None
                    em_pausa = False
                    pausa_inicio = None
            tempo_map[chave] = int(total.total_seconds())

        # Carrega urgência (prioridade) da planilha principal
        prioridade_por_os = {}
        try:
            data_main = sheet.get_all_values()
            if len(data_main) > 1:
                headers = data_main[0]
                idx_prior = headers.index('Nível de prioridade') if 'Nível de prioridade' in headers else 7
                for row in data_main[1:]:
                    if len(row) > idx_prior:
                        os_id = str(row[0]).strip()
                        prioridade = row[idx_prior]
                        if os_id:
                            prioridade_por_os[os_id] = prioridade
        except Exception as e:
            logger.warning(f"Falha ao carregar prioridade: {e}")

        # Monta dados para tabela e gráficos
        dados_all = []
        urg_counts = {}
        for (func, osid), secs in tempo_map.items():
            horas = secs // 3600
            mins = (secs % 3600) // 60
            urg = prioridade_por_os.get(str(osid), 'Desconhecida')
            dados_all.append({'funcionario': func, 'pedido_os': osid, 'tempo': f"{horas}h {mins}m", 'segundos': secs, 'urgencia': urg})
            urg_counts[urg] = urg_counts.get(urg, 0) + 1

        # Ordena por funcionário e tempo desc
        dados_all.sort(key=lambda x: (x['funcionario'], -x['segundos']))
        total_registros = len(dados_all)
        inicio = (page - 1) * per_page
        fim = inicio + per_page
        dados = dados_all[inicio:fim]

        # Chart datasets (Top 20 no conjunto filtrado)
        top = sorted(dados_all, key=lambda x: x['segundos'], reverse=True)[:20]
        bar_labels = [f"{d['funcionario']} - OS {d['pedido_os']}" for d in top]
        bar_values = [round(d['segundos']/3600, 2) for d in top]

        urg_labels = list(urg_counts.keys())
        urg_values = [urg_counts[k] for k in urg_labels]

        chart_data = {
            'bar_labels': bar_labels,
            'bar_values': bar_values,
            'urg_labels': urg_labels,
            'urg_values': urg_values
        }

        # Exportações
        if export_csv:
            import csv
            from io import StringIO
            si = StringIO()
            writer = csv.DictWriter(si, fieldnames=['funcionario','pedido_os','tempo','segundos','urgencia'])
            writer.writeheader()
            for r in dados_all:
                writer.writerow(r)
            from flask import Response
            filename = f"tempo_func_{dt_inicio.strftime('%Y%m%d')}_{dt_fim.strftime('%Y%m%d')}.csv"
            return Response(si.getvalue(), mimetype='text/csv', headers={'Content-Disposition': f'attachment; filename="{filename}"'})

        if export_xlsx:
            try:
                from io import BytesIO
                import pandas as pd
                buffer = BytesIO()
                df = pd.DataFrame(dados_all)
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False, sheet_name='Tempo')
                buffer.seek(0)
                from flask import Response
                filename = f"tempo_func_{dt_inicio.strftime('%Y%m%d')}_{dt_fim.strftime('%Y%m%d')}.xlsx"
                return Response(buffer.read(), mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', headers={'Content-Disposition': f'attachment; filename="{filename}"'})
            except Exception as e:
                logger.error(f"Erro ao exportar XLSX (tempo por funcionário): {e}")

        return render_template('tempo_por_funcionario.html', dados=dados, chart_data=chart_data, mensagem_erro=None,
                               funcionario=funcionario_q, pedido_os=pedido_q, page=page, per_page=per_page,
                               data_inicio=dt_inicio.strftime('%d/%m/%Y'), data_fim=dt_fim.strftime('%d/%m/%Y'),
                               data_inicio_iso=dt_inicio.strftime('%Y-%m-%d'), data_fim_iso=dt_fim.strftime('%Y-%m-%d'),
                               total_registros=total_registros, aviso_periodo=aviso_periodo)
    except Exception as e:
        logger.error(f"Erro em tempo_por_funcionario: {e}")
        return render_template('erro.html', mensagem=f"Erro ao carregar tempo por funcionário: {e}"), 500
# --- 11. ROTA DE CONSULTA DE STATUS (PÚBLICA) ---

@app.route('/consultar', methods=['GET', 'POST'])
def consultar_pedido():
    """Página pública para um solicitante consultar o status de um pedido."""
    disponivel, erro_msg = verificar_sheet_disponivel()
    if not disponivel:
        return render_template('consultar.html', 
            resultado={'erro': erro_msg}, pedido_buscado=None)
    
    resultado = None
    pedido_buscado = None

    if request.method == 'POST':
        # Usuário enviou o formulário de consulta
        pedido_buscado = request.form.get('numero_pedido')
    elif request.method == 'GET' and 'numero_pedido' in request.args:
        # Usuário clicou no link da página de sucesso (pré-preenchido)
        pedido_buscado = request.args.get('numero_pedido')
    
    if pedido_buscado:
        try:
            # Tenta encontrar o pedido na Coluna A (in_column=1)
            # sheet.find() procura pela string formatada, o que é perfeito para nós
            cell = sheet.find(str(pedido_buscado), in_column=1) 
            
            if cell:
                # Se encontrou, pega os dados daquela linha
                all_data = sheet.row_values(cell.row)
                
                # Monta o dicionário de resultado
                resultado = {
                    'id': all_data[0],       # Col A (ID)
                    'data': all_data[4],     # Col E (Data Solicitação)
                    'descricao': all_data[5], # Col F (Descrição)
                    'status': all_data[8]    # Col I (Status)
                }
            else:
                # Se não encontrou, define uma mensagem de erro
                resultado = {'erro': f"Pedido número '{pedido_buscado}' não encontrado."}
        
        except Exception as e:
            # Captura erros de conexão ou outros problemas
            logger.error(f"Erro ao buscar pedido: {e}")
            resultado = {'erro': 'Ocorreu um erro ao consultar o pedido.'}
    
    # Renderiza a página de consulta, passando o resultado e o número buscado
    return render_template('consultar.html', resultado=resultado, pedido_buscado=pedido_buscado)


# --- 12. ERROR HANDLERS GLOBAIS ---

@app.errorhandler(404)
def page_not_found(e):
    """Handler para páginas não encontradas."""
    logger.warning(f"Página não encontrada: {request.url}")
    return render_template('erro.html', 
        mensagem="Página não encontrada. Verifique o endereço e tente novamente."), 404

@app.errorhandler(500)
def internal_server_error(e):
    """Handler para erros internos do servidor."""
    logger.error(f"Erro interno do servidor: {e}", exc_info=True)
    return render_template('erro.html', 
        mensagem="Erro interno do servidor. Tente novamente mais tarde."), 500

@app.errorhandler(Exception)
def handle_exception(e):
    """Handler genérico para exceptions não tratadas."""
    # Se for um HTTPException, deixa o Flask tratar normalmente
    if hasattr(e, 'code'):
        return e
    
    logger.error(f"Erro não tratado: {e}", exc_info=True)
    return render_template('erro.html', 
        mensagem="Ocorreu um erro inesperado. Nossa equipe foi notificada."), 500


# --- 13. ROTA PARA FAVICON ---

@app.route('/favicon.ico')
def favicon():
    """Retorna um favicon vazio para evitar erro 404."""
    return '', 204

# --- Ponto de Entrada Principal ---
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Iniciando aplicação na porta {port} (debug={debug_mode})")
    
    # debug=False é crucial para produção
    # host='0.0.0.0' permite que o Render se conecte
    app.run(host='0.0.0.0', port=port, debug=debug_mode)

