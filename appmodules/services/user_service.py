"""Serviço de gerenciamento de usuários."""

import logging
import os
from typing import Dict, Optional, List
from appmodules.models import Usuario
from appmodules.models.usuario import Role
from appmodules.services.sheets_service import SheetsService

logger = logging.getLogger(__name__)


class UserService:
    """Gerencia usuários do sistema."""
    
    def __init__(self, sheets_service: SheetsService):
        """Inicializa serviço de usuários."""
        self.sheets_service = sheets_service
        self._usuarios_cache: Dict[str, Usuario] = {}
        self._load_usuarios()
    
    def _load_usuarios(self) -> None:
        """Carrega usuários do Sheets ou memória."""
        try:
            if not self.sheets_service:
                logger.warning("Sheets service indisponível; cache de usuários vazio")
                self._usuarios_cache = {}
                self._load_local_fallback_user()
                return
            
            records = self.sheets_service.get_usuarios_raw()
            self._usuarios_cache = {}
            
            roles_validos = {r.value for r in Role}
            for i, record in enumerate(records, start=2):
                username = str(record.get('Username', '')).strip()
                senha = str(record.get('Senha', '')).strip()
                role = str(record.get('Role', Role.ADMIN.value)).strip().lower()
                if role not in roles_validos:
                    role = Role.ADMIN.value
                
                if username and senha:
                    if not Usuario.is_hash_valido(senha):
                        senha = Usuario.criar(username, senha, role).senha_hash
                        if not self.sheets_service.update_usuario(i, username, senha, role):
                            logger.warning("Falha ao migrar senha legada do usuário %s", username)
                    self._usuarios_cache[username] = Usuario(
                        username=username,
                        senha_hash=senha,
                        role=role
                    )
            
            if not self._usuarios_cache:
                logger.warning("Nenhum usuário cadastrado no Sheets. Cadastre pelo menos um administrador.")
                self._load_local_fallback_user()
            else:
                logger.info(f"Carregados {len(self._usuarios_cache)} usuários")
        except Exception as e:
            logger.warning(f"Erro ao carregar usuários: {e}; cache de usuários permanecerá vazio")
            self._load_local_fallback_user()

    def _load_local_fallback_user(self) -> None:
        """Cria usuário admin local para ambiente de desenvolvimento."""
        if os.getenv('DISABLE_LOCAL_ADMIN_FALLBACK', 'false').lower() == 'true':
            return

        username = os.getenv('LOCAL_ADMIN_USER', 'admin').strip()
        password = os.getenv('LOCAL_ADMIN_PASSWORD', 'admin123').strip()
        role = os.getenv('LOCAL_ADMIN_ROLE', 'admin').strip() or 'admin'

        if not username or not password:
            return

        if username not in self._usuarios_cache:
            self._usuarios_cache[username] = Usuario.criar(username, password, role)
            logger.warning(
                "Usuário local de fallback carregado para login (dev): %s. "
                "Defina LOCAL_ADMIN_USER/LOCAL_ADMIN_PASSWORD para alterar.",
                username
            )
    
    def get_usuario(self, username: str) -> Optional[Usuario]:
        """Obtém um usuário pelo username."""
        return self._usuarios_cache.get(username)
    
    def get_todos_usuarios(self) -> List[Usuario]:
        """Obtém todos os usuários."""
        return list(self._usuarios_cache.values())
    
    def criar_usuario(self, username: str, senha: str, role: str = 'admin') -> bool:
        """Cria novo usuário."""
        try:
            role = str(role or Role.ADMIN.value).strip().lower()
            if role not in {r.value for r in Role}:
                logger.warning("Role inválida ao criar usuário: %s", role)
                return False

            if not self.sheets_service:
                logger.error("Sheets service indisponível; não é possível criar usuário")
                return False

            if username in self._usuarios_cache:
                logger.warning(f"Usuário {username} já existe")
                return False
            
            usuario = Usuario.criar(username, senha, role)
            
            # Salva no Sheets
            if not self.sheets_service.add_usuario(username, usuario.senha_hash, role):
                logger.error(f"Falha ao salvar usuário {username} no Sheets")
                return False
            
            # Salva em cache
            self._usuarios_cache[username] = usuario
            logger.info(f"Usuário {username} criado com sucesso")
            return True
        except Exception as e:
            logger.error(f"Erro ao criar usuário: {e}")
            return False
    
    def atualizar_usuario(self, username: str, senha: Optional[str] = None, 
                         role: Optional[str] = None) -> bool:
        """Atualiza um usuário."""
        try:
            if not self.sheets_service:
                logger.error("Sheets service indisponível; não é possível atualizar usuário")
                return False
            
            usuario = self._usuarios_cache.get(username)
            if not usuario:
                logger.warning(f"Usuário {username} não encontrado")
                return False
            
            if senha:
                usuario.atualizar_senha(senha)
            if role:
                role = str(role).strip().lower()
                if role not in {r.value for r in Role}:
                    logger.warning("Role inválida ao atualizar usuário: %s", role)
                    return False
                usuario.role = role
            
            # Atualiza no Sheets (busca por row_id)
            records = self.sheets_service.get_usuarios_raw()
            for i, record in enumerate(records, start=2):
                if str(record.get('Username', '')).strip() == username:
                    if not self.sheets_service.update_usuario(i, username, usuario.senha_hash, usuario.role):
                        logger.error(f"Falha ao atualizar usuário {username} no Sheets")
                        return False
                    break
            
            logger.info(f"Usuário {username} atualizado")
            return True
        except Exception as e:
            logger.error(f"Erro ao atualizar usuário: {e}")
            return False
    
    def deletar_usuario(self, username: str) -> bool:
        """Deleta um usuário."""
        try:
            if not self.sheets_service:
                logger.error("Sheets service indisponível; não é possível deletar usuário")
                return False

            if username not in self._usuarios_cache:
                logger.warning(f"Usuário {username} não encontrado")
                return False
            
            # Deleta do Sheets
            if not self.sheets_service.delete_usuario(username):
                logger.error(f"Falha ao deletar usuário {username} do Sheets")
                return False
            
            # Remove do cache
            del self._usuarios_cache[username]
            logger.info(f"Usuário {username} deletado")
            return True
        except Exception as e:
            logger.error(f"Erro ao deletar usuário: {e}")
            return False
    
    def recarregar(self) -> None:
        """Recarrega usuários do Sheets."""
        self._load_usuarios()
