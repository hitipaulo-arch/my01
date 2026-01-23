"""Rotas de autenticação."""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from werkzeug.security import check_password_hash, generate_password_hash
from appmodules.models import ValidadorUsuario

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Página de login do sistema."""
    if 'usuario' in session:
        return redirect(url_for('os.homepage'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        user_service = current_app.config.get('user_service')
        if not user_service:
            flash('Serviço de usuários não disponível.', 'danger')
            return render_template('login.html', erro='Erro interno')
        
        usuario = user_service.get_usuario(username)
        if not usuario:
            return render_template('login.html', erro='Usuário ou senha inválidos.')
        
        # Verifica senha
        if usuario.verificar_senha(password):
            session['usuario'] = username
            session['role'] = usuario.role
            session.permanent = True
            flash(f'Bem-vindo, {username}!', 'success')
            
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            return redirect(url_for('os.homepage'))
        
        return render_template('login.html', erro='Usuário ou senha inválidos.')
    
    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    """Faz logout do usuário."""
    usuario = session.get('usuario', 'Usuário')
    session.clear()
    flash(f'Logout realizado com sucesso. Até logo, {usuario}!', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    """Página de cadastro de novos usuários."""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        
        validacao = ValidadorUsuario.validar_cadastro(username, password, confirm_password)
        if not validacao.valido:
            return render_template('cadastro.html', erro=' '.join(validacao.erros))
        
        user_service = current_app.config.get('user_service')
        if not user_service:
            flash('Serviço de usuários não disponível.', 'danger')
            return render_template('cadastro.html', erro='Erro interno')
        
        if user_service.get_usuario(username):
            return render_template('cadastro.html', erro='Usuário já existe.')
        
        if user_service.criar_usuario(username, password, 'admin'):
            flash('Cadastro realizado com sucesso! Você pode fazer login agora.', 'success')
            return redirect(url_for('auth.login'))
        else:
            return render_template('cadastro.html', erro='Erro ao criar usuário.')
    
    return render_template('cadastro.html')
