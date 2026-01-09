"""
Configuração centralizada do sistema de Ordem de Serviço.
"""
import os
from typing import List

# --- CONFIGURAÇÕES DO GOOGLE SHEETS ---
class SheetsConfig:
    """Configurações do Google Sheets."""
    SCOPES: List[str] = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive.file'
    ]
    
    # IDs e nomes das abas (podem ser sobrescritos por variáveis de ambiente)
    SHEET_ID: str = os.getenv('GOOGLE_SHEET_ID', '1qs3cxlklTnzCp4RpQGhxIrEF4CbeUvid1S0Cp2tC3Xg')
    SHEET_TAB_NAME: str = os.getenv('GOOGLE_SHEET_TAB', 'Respostas ao formulário 3')
    SHEET_HORARIO_TAB: str = os.getenv('GOOGLE_SHEET_HORARIO_TAB', 'Controle de Horário')
    SHEET_USUARIOS_TAB: str = os.getenv('GOOGLE_SHEET_USUARIOS_TAB', 'Usuários')


# --- CONFIGURAÇÕES DO FLASK ---
class FlaskConfig:
    """Configurações do Flask."""
    SECRET_KEY: str = os.getenv('SECRET_KEY')
    DEBUG: bool = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    PORT: int = int(os.getenv('PORT', 5000))
    HOST: str = '0.0.0.0'
    
    # Cookies de sessão
    SESSION_COOKIE_SECURE: bool = os.getenv('FLASK_ENV') == 'production'
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SAMESITE: str = 'Lax'
    
    # CSRF
    WTF_CSRF_ENABLED: bool = True
    WTF_CSRF_TIME_LIMIT: int = None  # Token não expira


# --- CONFIGURAÇÕES DE CACHE ---
class CacheConfig:
    """Configurações do cache."""
    # Tipo de cache: 'SimpleCache', 'RedisCache', 'FileSystemCache'
    CACHE_TYPE: str = os.getenv('CACHE_TYPE', 'SimpleCache')
    CACHE_DEFAULT_TIMEOUT: int = int(os.getenv('CACHE_TTL_SECONDS', 300))  # 5 minutos
    
    # Configurações do Redis (se usar RedisCache)
    CACHE_REDIS_HOST: str = os.getenv('REDIS_HOST', 'localhost')
    CACHE_REDIS_PORT: int = int(os.getenv('REDIS_PORT', 6379))
    CACHE_REDIS_DB: int = int(os.getenv('REDIS_DB', 0))
    CACHE_REDIS_URL: str = os.getenv('REDIS_URL', f'redis://{CACHE_REDIS_HOST}:{CACHE_REDIS_PORT}/{CACHE_REDIS_DB}')


# --- CONFIGURAÇÕES DE VALIDAÇÃO ---
class ValidationConfig:
    """Regras de validação."""
    # Usuários
    MIN_USERNAME_LENGTH: int = 3
    MIN_PASSWORD_LENGTH: int = 6
    
    # OS
    MIN_DESCRICAO_LENGTH: int = 10
    PRIORIDADES_VALIDAS: List[str] = ['Baixa', 'Média', 'Alta', 'Urgente']
    STATUS_VALIDOS: List[str] = ['Aberto', 'Em Andamento', 'Concluído', 'Cancelado']


# --- CONFIGURAÇÕES DE LOGGING ---
class LoggingConfig:
    """Configurações de logging."""
    LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    FORMAT: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'


# --- CONFIGURAÇÕES GERAIS ---
class Config:
    """Configuração geral do sistema (agregador)."""
    SHEETS = SheetsConfig
    FLASK = FlaskConfig
    CACHE = CacheConfig
    VALIDATION = ValidationConfig
    LOGGING = LoggingConfig
