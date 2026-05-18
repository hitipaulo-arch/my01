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
        self.last_error: Optional[str] = None
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
                    # Tenta ler coluna de data de cadastro se existir (compatibilidade com planilhas antigas)
                    data_cadastro = str(record.get('Data de Cadastro') or record.get('DataCadastro') or record.get('Data') or '').strip()
                    self._usuarios_cache[username] = Usuario(
                        username=username,
                        senha_hash=senha,
                        role=role,
                        data_cadastro=data_cadastro
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
        # Exigir configuração explícita para permitir fallback (nunca usar padrões inseguros)
        if os.getenv('ALLOW_LOCAL_ADMIN_FALLBACK', 'false').lower() != 'true':
            logger.critical(
                "Google Sheets indisponível e ALLOW_LOCAL_ADMIN_FALLBACK não configurado. "
                "Nenhum usuário local será criado. Configure variáveis de ambiente explicitamente em produção."
            )
            return

        # Se permitido, EXIGIR credenciais via variáveis de ambiente (sem defaults inseguros)
        username = os.getenv('LOCAL_ADMIN_USER', '').strip()
        password = os.getenv('LOCAL_ADMIN_PASSWORD', '').strip()
        role = os.getenv('LOCAL_ADMIN_ROLE', 'admin').strip() or 'admin'
        
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
                username
            )
    
    def get_usuario(self, username: str) -> Optional[Usuario]:
        """Obtém um usuário pelo username."""
        username_normalizado = str(username or '').strip().lower()
        if not username_normalizado:
            return None

        for usuario in self._usuarios_cache.values():
            if str(usuario.username or '').strip().lower() == username_normalizado:
                return usuario
        return None
    
    def get_todos_usuarios(self) -> List[Usuario]:
        """Obtém todos os usuários."""
        return list(self._usuarios_cache.values())
    
    def criar_usuario(self, username: str, senha: str, role: str = 'admin') -> bool:
        """Cria novo usuário."""
        try:
            username = str(username or '').strip()
            role = str(role or Role.ADMIN.value).strip().lower()
            if role not in {r.value for r in Role}:
                logger.warning("Role inválida ao criar usuário: %s", role)
                self.last_error = "Role inválida"
                return False

            if not self.sheets_service:
                logger.error("Sheets service indisponível; não é possível criar usuário")
                self.last_error = "Sheets service indisponível"
                return False

            if self.get_usuario(username):
                logger.warning(f"Usuário {username} já existe")
                self.last_error = f"Usuário {username} já existe"
                return False
            
            usuario = Usuario.criar(username, senha, role)
            
            # Salva no Sheets
            if not self.sheets_service.add_usuario(username, usuario.senha_hash, role):
                erro_sheets = getattr(self.sheets_service, 'usuarios_error', None)
                if erro_sheets:
                    self.last_error = erro_sheets
                    logger.error(f"Falha ao salvar usuário {username} no Sheets: {erro_sheets}")
                else:
                    self.last_error = "Falha ao salvar usuário no Sheets"
                    logger.error(f"Falha ao salvar usuário {username} no Sheets")
                return False
            
            # Salva em cache
            self._usuarios_cache[username] = usuario
            self.last_error = None
            logger.info(f"Usuário {username} criado com sucesso")
            return True
        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Erro ao criar usuário: {e}")
            return False
    
    def atualizar_usuario(self, username: str, senha: Optional[str] = None, 
                         role: Optional[str] = None) -> bool:
        """Atualiza um usuário."""
        try:
            if not self.sheets_service:
                logger.error("Sheets service indisponível; não é possível atualizar usuário")
                return False
            
            usuario = self.get_usuario(username)
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
                if str(record.get('Username', '')).strip().lower() == str(username or '').strip().lower():
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

            usuario = self.get_usuario(username)
            if not usuario:
                logger.warning(f"Usuário {username} não encontrado")
                return False
            
            # Deleta do Sheets
            if not self.sheets_service.delete_usuario(usuario.username):
                logger.error(f"Falha ao deletar usuário {username} do Sheets")
                return False
            
            # Remove do cache
            self._usuarios_cache.pop(usuario.username, None)
            logger.info(f"Usuário {username} deletado")
            return True
        except Exception as e:
            logger.error(f"Erro ao deletar usuário: {e}")
            return False
    
    def recarregar(self) -> None:
        """Recarrega usuários do Sheets."""
        self._load_usuarios()
