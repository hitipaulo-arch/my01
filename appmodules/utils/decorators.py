"""Decoradores de segurança e utilidades."""

from functools import wraps
from flask import session, redirect, url_for, flash, current_app, request


def login_required(f):
    """Decorador para proteger rotas que requerem autenticação."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario' not in session:
            flash('Por favor, faça login para acessar esta página.', 'warning')
            return redirect(url_for('auth.login', next=request.url) if 'request' in dir() else url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Decorador para rotas que requerem privilégios de admin."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario' not in session:
            flash('Por favor, faça login para acessar esta página.', 'warning')
            return redirect(url_for('auth.login'))
        
        usuario = session.get('usuario')
        user_service = current_app.config.get('user_service')
        
        if not user_service:
            flash('Serviço de usuários não disponível.', 'danger')
            return redirect(url_for('os.homepage'))
        
        user_data = user_service.get_usuario(usuario)
        if not user_data or user_data.role != 'admin':
            flash('Acesso negado. Apenas administradores podem acessar.', 'danger')
            return redirect(url_for('os.homepage'))
        
        return f(*args, **kwargs)
    return decorated_function
