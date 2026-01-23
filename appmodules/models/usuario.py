"""Model para Usuário."""

from dataclasses import dataclass
from enum import Enum
from werkzeug.security import generate_password_hash, check_password_hash


class Role(str, Enum):
    """Enum para roles de usuário."""
    ADMIN = 'admin'
    OPERADOR = 'operador'
    VISUALIZADOR = 'visualizador'


@dataclass
class Usuario:
    """Representa um usuário do sistema."""
    
    username: str
    senha_hash: str
    role: str = Role.ADMIN.value
    
    @classmethod
    def criar(cls, username: str, senha: str, role: str = Role.ADMIN.value) -> 'Usuario':
        """Cria novo usuário com senha hasheada."""
        senha_hash = generate_password_hash(senha, method='pbkdf2:sha256')
        return cls(username=username, senha_hash=senha_hash, role=role)
    
    def verificar_senha(self, senha: str) -> bool:
        """Verifica se a senha está correta."""
        # Compatibilidade com senhas legadas (texto plano)
        if not self.senha_hash.startswith(('pbkdf2:', 'scrypt:')):
            return self.senha_hash == senha
        return check_password_hash(self.senha_hash, senha)
    
    def atualizar_senha(self, nova_senha: str) -> None:
        """Atualiza senha do usuário."""
        self.senha_hash = generate_password_hash(nova_senha, method='pbkdf2:sha256')
    
    def to_dict(self) -> dict:
        """Converte para dicionário."""
        return {
            'senha': self.senha_hash,
            'role': self.role
        }
    
    def to_sheet_row(self) -> list:
        """Converte para linha do Google Sheets."""
        return [self.username, self.senha_hash, self.role]
