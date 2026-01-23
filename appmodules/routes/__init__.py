"""Rotas da aplicação."""

from .auth_routes import auth_bp
from .os_routes import os_bp

__all__ = ['auth_bp', 'os_bp']
