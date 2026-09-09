"""Serviço de gerenciamento de usuários."""

import logging
import os
from typing import Dict, Optional, List
from flask import current_app
from appmodules.models import Usuario
from appmodules.models.usuario import Role
from appmodules.services.sheets_service import SheetsService
from config import Config

logger = logging.getLogger(__name__)

# Chave usada no Flask-Caching (Redis em produção, SimpleCache em dev single-worker)
_CACHE_PREFIX = os.getenv("CACHE_KEY_PREFIX", "my01").strip() or "my01"
CACHE_KEY_USUARIOS = f"{_CACHE_PREFIX}:sheets:usuarios:all"


class UserService:
    """Gerencia usuários do sistema."""

    def __init__(self, sheets_service: SheetsService):
        """Inicializa serviço de usuários."""
        self.sheets_service = sheets_service
        self._usuarios_cache: Dict[str, Usuario] = {}
        self.last_error: Optional[str] = None
        # TTL configurável — fonte única em Config.CACHE (padrão 300s = 5min)
        self._usuarios_cache_ttl_seconds = Config.CACHE.USUARIOS_CACHE_TTL_SECONDS
        self._load_usuarios()

    def _get_cache(self):
        """Retorna instância do Flask-Caching ou None se indisponível."""
        try:
            ext = current_app.extensions.get("cache")
            if ext is None:
                return None
            # Flask-Caching armazena {Cache_instance: backend} em extensions['cache']
            if isinstance(ext, dict):
                for backend in ext.values():
                    return backend
                return None
            return ext
        except RuntimeError:
            return None

    def _invalidate_usuarios_cache(self) -> None:
        """Invalida cache compartilhado de usuários após qualquer mutação."""
        cache = self._get_cache()
        if cache is not None:
            try:
                cache.delete(CACHE_KEY_USUARIOS)
                return
            except Exception as e:
                logger.warning(f"Falha ao invalidar cache usuários no Redis: {e}")

    @staticmethod
    def _normalize_role(role: Optional[str], default: str = Role.VISUALIZADOR.value) -> str:
        """Normaliza roles legadas para o conjunto oficial do sistema."""
        normalized = str(role or default).strip().lower()
        if normalized in {r.value for r in Role}:
            return normalized
        return default

    def _sync_usuarios_cache(self) -> None:
        """Persiste o estado atual do cache local no backend compartilhado."""
        self._persist_usuarios_cache()

    def _build_usuario_from_record(
        self, record: dict, row_number: int
    ) -> Optional[Usuario]:
        """Constrói um usuário a partir de uma linha do Sheets."""
        username = str(record.get("Username", "")).strip()
        senha = str(record.get("Senha", "")).strip()
        role = self._normalize_role(record.get("Role"), Role.ADMIN.value)

        if not username or not senha:
            return None

        senha_migrada = senha
        if not Usuario.is_hash_valido(senha):
            senha_migrada = Usuario.criar(username, senha, role).senha_hash
            if not self.sheets_service.update_usuario(
                row_number, username, senha_migrada, role
            ):
                logger.warning(
                    "Falha ao migrar senha legada do usuário %s", username
                )

        data_cadastro = str(
            record.get("Data de Cadastro")
            or record.get("DataCadastro")
            or record.get("Data")
            or ""
        ).strip()

        return Usuario(
            username=username,
            senha_hash=senha_migrada,
            role=role,
            data_cadastro=data_cadastro,
        )

    def _load_usuarios(self) -> None:
        """Carrega usuários do Sheets ou memória."""
        # Tenta ler do cache compartilhado (Redis) primeiro
        cache = self._get_cache()
        if cache is not None:
            try:
                cached = cache.get(CACHE_KEY_USUARIOS)
                if cached is not None:
                    self._usuarios_cache = cached
                    logger.debug(
                        f"Cache hit: {len(self._usuarios_cache)} usuários do Redis"
                    )
                    return
            except Exception as e:
                logger.warning(f"Falha ao ler cache usuários do Redis: {e}")

        try:
            if not self.sheets_service:
                logger.warning("Sheets service indisponível; cache de usuários vazio")
                self._usuarios_cache = {}
                self._load_local_fallback_user()
                self._persist_usuarios_cache()
                return

            records = self.sheets_service.get_usuarios_raw()
            self._usuarios_cache = {}

            for i, record in enumerate(records, start=2):
                usuario = self._build_usuario_from_record(record, i)
                if usuario is not None:
                    self._usuarios_cache[usuario.username] = usuario

            if not self._usuarios_cache:
                logger.warning(
                    "Nenhum usuário cadastrado no Sheets. Cadastre pelo menos um administrador."
                )
                self._load_local_fallback_user()
            else:
                logger.info(f"Carregados {len(self._usuarios_cache)} usuários")

            self._sync_usuarios_cache()
        except Exception as e:
            logger.warning(
                f"Erro ao carregar usuários: {e}; cache de usuários permanecerá vazio"
            )
            self._load_local_fallback_user()
            self._sync_usuarios_cache()

    def _persist_usuarios_cache(self) -> None:
        """Persiste o cache local no Flask-Caching (Redis) com TTL configurável."""
        cache = self._get_cache()
        if cache is None:
            return
        try:
            cache.set(
                CACHE_KEY_USUARIOS,
                self._usuarios_cache,
                timeout=self._usuarios_cache_ttl_seconds,
            )
        except Exception as e:
            logger.warning(f"Falha ao gravar cache usuários no Redis: {e}")

    def _load_local_fallback_user(self) -> None:
        """Cria usuário admin local para ambiente de desenvolvimento."""
        # Exigir configuração explícita para permitir fallback (nunca usar padrões inseguros)
        if os.getenv("ALLOW_LOCAL_ADMIN_FALLBACK", "false").lower() != "true":
            logger.critical(
                "Google Sheets indisponível e ALLOW_LOCAL_ADMIN_FALLBACK não configurado. "
                "Nenhum usuário local será criado. Configure variáveis de ambiente explicitamente em produção."
            )
            return

        # Se permitido, EXIGIR credenciais via variáveis de ambiente (sem defaults inseguros)
        username = os.getenv("LOCAL_ADMIN_USER", "").strip()
        password = os.getenv("LOCAL_ADMIN_PASSWORD", "").strip()
        role = self._normalize_role(
            os.getenv("LOCAL_ADMIN_ROLE", Role.ADMIN.value), Role.ADMIN.value
        )

        if not username or not password:
            logger.critical(
                "LOCAL_ADMIN_USER ou LOCAL_ADMIN_PASSWORD não definidos. "
                "Fallback local exigido mas credenciais faltando."
            )
            return

        if not username or not password:
            return

        if username not in self._usuarios_cache:
            self._usuarios_cache[username] = Usuario.criar(username, password, role)
            logger.warning(
                "Usuário local de fallback carregado para login (dev): %s. "
                "Defina LOCAL_ADMIN_USER/LOCAL_ADMIN_PASSWORD para alterar.",
                username,
            )

    def get_usuario(self, username: str) -> Optional[Usuario]:
        """Obtém um usuário pelo username."""
        username_normalizado = str(username or "").strip().lower()
        if not username_normalizado:
            return None

        # Garante que o cache local esteja populado (lê do Redis se necessário)
        if not self._usuarios_cache:
            self._load_usuarios()

        for usuario in self._usuarios_cache.values():
            if str(usuario.username or "").strip().lower() == username_normalizado:
                return usuario
        return None

    def get_todos_usuarios(self) -> List[Usuario]:
        """Obtém todos os usuários."""
        if not self._usuarios_cache:
            self._load_usuarios()
        return list(self._usuarios_cache.values())

    def criar_usuario(
        self, username: str, senha: str, role: str = Role.VISUALIZADOR.value
    ) -> bool:
        """Cria novo usuário."""
        try:
            username = str(username or "").strip()
            role = self._normalize_role(role, Role.VISUALIZADOR.value)
            if role not in {r.value for r in Role}:
                logger.warning("Role inválida ao criar usuário: %s", role)
                self.last_error = "Role inválida"
                return False

            if not self.sheets_service:
                logger.error(
                    "Sheets service indisponível; não é possível criar usuário"
                )
                self.last_error = "Sheets service indisponível"
                return False

            if self.get_usuario(username):
                logger.warning(f"Usuário {username} já existe")
                self.last_error = f"Usuário {username} já existe"
                return False

            usuario = Usuario.criar(username, senha, role)

            # Salva no Sheets
            if not self.sheets_service.add_usuario(username, usuario.senha_hash, role):
                erro_sheets = getattr(self.sheets_service, "usuarios_error", None)
                if erro_sheets:
                    self.last_error = erro_sheets
                    logger.error(
                        f"Falha ao salvar usuário {username} no Sheets: {erro_sheets}"
                    )
                else:
                    self.last_error = "Falha ao salvar usuário no Sheets"
                    logger.error(f"Falha ao salvar usuário {username} no Sheets")
                return False

            # Salva em cache local e propaga para Redis
            self._usuarios_cache[username] = usuario
            self._sync_usuarios_cache()
            self.last_error = None
            logger.info(f"Usuário {username} criado com sucesso")
            return True
        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Erro ao criar usuário: {e}")
            return False

    def atualizar_usuario(
        self, username: str, senha: Optional[str] = None, role: Optional[str] = None
    ) -> bool:
        """Atualiza um usuário."""
        try:
            if not self.sheets_service:
                logger.error(
                    "Sheets service indisponível; não é possível atualizar usuário"
                )
                return False

            usuario = self.get_usuario(username)
            if not usuario:
                logger.warning(f"Usuário {username} não encontrado")
                return False

            if senha:
                usuario.atualizar_senha(senha)
            if role:
                role = self._normalize_role(role, usuario.role)
                if role not in {r.value for r in Role}:
                    logger.warning("Role inválida ao atualizar usuário: %s", role)
                    return False
                usuario.role = role

            # Atualiza no Sheets (busca por row_id)
            records = self.sheets_service.get_usuarios_raw()
            for i, record in enumerate(records, start=2):
                if (
                    str(record.get("Username", "")).strip().lower()
                    == str(username or "").strip().lower()
                ):
                    if not self.sheets_service.update_usuario(
                        i, username, usuario.senha_hash, usuario.role
                    ):
                        logger.error(f"Falha ao atualizar usuário {username} no Sheets")
                        return False
                    break

            # Atualiza cache local e propaga para Redis (corrige bug de cache desatualizado)
            self._usuarios_cache[usuario.username] = usuario
            self._sync_usuarios_cache()
            logger.info(f"Usuário {username} atualizado")
            return True
        except Exception as e:
            logger.error(f"Erro ao atualizar usuário: {e}")
            return False

    def deletar_usuario(self, username: str) -> bool:
        """Deleta um usuário."""
        try:
            if not self.sheets_service:
                logger.error(
                    "Sheets service indisponível; não é possível deletar usuário"
                )
                return False

            usuario = self.get_usuario(username)
            if not usuario:
                logger.warning(f"Usuário {username} não encontrado")
                return False

            # Deleta do Sheets
            if not self.sheets_service.delete_usuario(usuario.username):
                logger.error(f"Falha ao deletar usuário {username} do Sheets")
                return False

            # Remove do cache local e propaga invalidação para Redis
            self._usuarios_cache.pop(usuario.username, None)
            self._sync_usuarios_cache()
            logger.info(f"Usuário {username} deletado")
            return True
        except Exception as e:
            logger.error(f"Erro ao deletar usuário: {e}")
            return False

    def recarregar(self) -> None:
        """Recarrega usuários do Sheets."""
        # Limpa cache local e Redis antes de recarregar para evitar dados obsoletos
        self._usuarios_cache.clear()
        cache = self._get_cache()
        if cache:
            try:
                cache.delete(CACHE_KEY_USUARIOS)
            except Exception as e:
                logger.warning(f"Falha ao invalidar cache de usuários no recarregar: {e}")
        self._load_usuarios()
