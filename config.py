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
    SHEET_TAB: str = os.getenv('GOOGLE_SHEET_TAB', 'Respostas ao formulário 3')
    SHEET_HORARIO_TAB: str = os.getenv('GOOGLE_SHEET_HORARIO_TAB', 'Controle de Horário')
    SHEET_USUARIOS_TAB: str = os.getenv('GOOGLE_SHEET_USUARIOS_TAB', 'Usuários')
    SHEET_PRODUCAO_TAB: str = os.getenv('GOOGLE_SHEET_PRODUCAO_TAB', 'Controle de Produção')
    SHEET_CENTRAIS_TAB: str = os.getenv('GOOGLE_SHEET_CENTRAIS_TAB', 'Controle de Centrais')
    SHEET_FERRAMENTAS_TAB: str = os.getenv('GOOGLE_SHEET_FERRAMENTAS_TAB', 'Controle de Ferramentas')
    SHEET_HISTORICO_FERRAMENTAS_TAB: str = os.getenv(
        'GOOGLE_SHEET_HISTORICO_FERRAMENTAS_TAB', 'Histórico de Ferramentas'
    )

    # Alias para compatibilidade
    SHEET_TAB_NAME: str = SHEET_TAB



# --- CONFIGURAÇÕES DO FLASK ---
class FlaskConfig:
    """Configurações do Flask."""
    SECRET_KEY: str = os.getenv('SECRET_KEY', '')
    DEBUG: bool = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    PORT: int = int(os.getenv('PORT', 5000))
    HOST: str = '0.0.0.0'
    
    if not SECRET_KEY:
        raise ValueError(
            "\n" + "=" * 70 + "\n"
            "ERRO CRÍTICO: SECRET_KEY não configurada!\n"
            "=" * 70 + "\n"
            "A aplicação requer uma SECRET_KEY fixa para manter sessões após restart.\n"
            "\n"
            "GERE UMA CHAVE SEGURA:\n"
            "  python -c 'import secrets; print(secrets.token_hex(32))'\n"
            "\n"
            "CONFIGURE em variáveis de ambiente:\n"
            "  export SECRET_KEY=<chave_gerada>\n"
            "  OU adicione ao arquivo .env\n"
            "\n"
            "Sem esta configuração, todos os usuários serão desconectados\n"
            "quando o servidor for reiniciado.\n"
            "=" * 70
        )

    # Cookies de sessão
    SESSION_COOKIE_SECURE: bool = os.getenv('FLASK_ENV') == 'production'
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SAMESITE: str = 'Lax'
    
    # CSRF
    WTF_CSRF_ENABLED: bool = True
    WTF_CSRF_TIME_LIMIT: int = None  # Token não expira


# --- CONFIGURAÇÕES DE CACHE ---
class CacheConfig:
    """Configurações do cache.

    Por padrão, usa RedisCache quando REDIS_URL (ou REDIS_HOST) estiver
    configurado, evitando race conditions em ambientes com múltiplos workers
    (gunicorn -w N). Caso contrário, faz fallback para SimpleCache (in-memory,
    útil apenas em desenvolvimento single-worker).
    """
    # Detecta automaticamente o backend: Redis se REDIS_URL/REDIS_HOST estiver
    # definido, caso contrário SimpleCache.
    _redis_url_env: str = os.getenv('REDIS_URL', '').strip()
    _redis_host_env: str = os.getenv('REDIS_HOST', '').strip()
    _cache_type_env: str = os.getenv('CACHE_TYPE', '').strip()

    if _cache_type_env:
        CACHE_TYPE: str = _cache_type_env
    elif _redis_url_env or _redis_host_env:
        CACHE_TYPE: str = 'RedisCache'
    else:
        CACHE_TYPE: str = 'SimpleCache'

    # TTL padrão (5 minutos) usado pelo Flask-Caching quando nenhum TTL
    # específico é informado em cache.set().
    CACHE_DEFAULT_TIMEOUT: int = int(os.getenv('CACHE_TTL_SECONDS', 300))

    # Configurações do Redis (ativas quando CACHE_TYPE == 'RedisCache')
    CACHE_REDIS_HOST: str = os.getenv('REDIS_HOST', 'localhost')
    CACHE_REDIS_PORT: int = int(os.getenv('REDIS_PORT', 6379))
    CACHE_REDIS_DB: int = int(os.getenv('REDIS_DB', 0))
    CACHE_REDIS_PASSWORD: str = os.getenv('REDIS_PASSWORD', '') or None
    # Prefixo aplicado a todas as chaves para evitar colisão quando o mesmo
    # Redis é compartilhado entre aplicações.
    CACHE_KEY_PREFIX: str = os.getenv('CACHE_KEY_PREFIX', 'my01')

    # URL completa do Redis (sobrescreve host/port/db/password quando definida).
    # Suporta redis:// e rediss:// (TLS).
    _default_redis_url: str = (
        f"redis://{CACHE_REDIS_HOST}:{CACHE_REDIS_PORT}/{CACHE_REDIS_DB}"
    )
    CACHE_REDIS_URL: str = _redis_url_env or _default_redis_url


# --- CONFIGURAÇÕES DE VALIDAÇÃO ---
class ValidationConfig:
    """Regras de validação."""
    # Usuários
    MIN_USERNAME_LENGTH: int = 3
    MIN_PASSWORD_LENGTH: int = 6
    
    # OS
    MIN_DESCRICAO_LENGTH: int = 5
    PRIORIDADES_VALIDAS: List[str] = ['Baixa', 'Média', 'Alta', 'Urgente']
    STATUS_VALIDOS: List[str] = ['Aberto', 'Em Andamento', 'Concluído', 'Cancelado']

    # Itens / Compras
    MIN_NOME_ITEM_LENGTH: int = 2
    MAX_NOME_ITEM_LENGTH: int = 100
    MAX_OBSERVACAO_LENGTH: int = 500
    MAX_QUANTIDADE: int = 1_000_000
    ITEM_ALERT_THRESHOLD_DEFAULT: int = int(os.getenv('ITEM_ALERT_THRESHOLD', 10))
    # Limites específicos por nome de item (case-insensitive). Permite que
    # certos itens críticos tenham alerta em quantidade maior.
    ITEM_ALERT_THRESHOLDS: dict = {
        # 'parafuso m6': 50,
    }


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
