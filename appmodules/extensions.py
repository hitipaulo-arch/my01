"""Extensões Flask compartilhadas pela aplicação."""

try:
    from flask_limiter import Limiter
except ImportError:  # pragma: no cover
    Limiter = None

from flask_caching import Cache
from flask import request
from flask_wtf.csrf import CSRFProtect


csrf = CSRFProtect()
cache = Cache()
limiter = (
    Limiter(key_func=lambda: request.remote_addr or "unknown")
    if Limiter is not None
    else None
)

__all__ = ["Cache", "CSRFProtect", "Limiter", "cache", "csrf", "limiter"]