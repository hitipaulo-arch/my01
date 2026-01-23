"""Classes de validação para o sistema."""

from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class ValidacaoResultado:
    """Resultado de uma validação."""
    valido: bool
    erros: List[str]


class ValidadorOS:
    """Validador centralizado para Ordens de Serviço."""
    
    PRIORIDADES_VALIDAS = ['Baixa', 'Média', 'Alta', 'Urgente']
    STATUS_VALIDOS = ['Aberto', 'Em Andamento', 'Aguardando Compra', 'Finalizada', 'Cancelada']
    MIN_DESCRICAO_LENGTH = 10
    
    @staticmethod
    def validar_formulario(form_data: Dict[str, Any]) -> ValidacaoResultado:
        """Valida dados do formulário de OS."""
        erros = []
        
        # Validações obrigatórias
        if not form_data.get('nome_solicitante', '').strip():
            erros.append('Nome do solicitante é obrigatório.')
        
        if not form_data.get('setor', '').strip():
            erros.append('Setor é obrigatório.')
        
        if not form_data.get('equipamento', '').strip():
            erros.append('Equipamento ou local afetado é obrigatório.')
        
        descricao = form_data.get('descricao', '').strip()
        if not descricao:
            erros.append('Descrição do problema é obrigatória.')
        elif len(descricao) < ValidadorOS.MIN_DESCRICAO_LENGTH:
            erros.append(f'Descrição deve ter pelo menos {ValidadorOS.MIN_DESCRICAO_LENGTH} caracteres.')
        
        prioridade = form_data.get('prioridade')
        if prioridade not in ValidadorOS.PRIORIDADES_VALIDAS:
            erros.append('Prioridade inválida.')
        
        return ValidacaoResultado(valido=len(erros) == 0, erros=erros)
    
    @staticmethod
    def validar_atualizacao(form_data: Dict[str, Any]) -> ValidacaoResultado:
        """Valida dados de atualização de OS."""
        erros = []
        
        # Apenas verifica row_id, sem validar status (aceita qualquer valor)
        if not form_data.get('row_id'):
            erros.append('ID da linha é obrigatório.')
        
        return ValidacaoResultado(valido=len(erros) == 0, erros=erros)


class ValidadorUsuario:
    """Validador centralizado para usuários."""
    
    MIN_USERNAME_LENGTH = 3
    MIN_PASSWORD_LENGTH = 6
    
    @staticmethod
    def validar_cadastro(username: str, password: str, confirm_password: str = None) -> ValidacaoResultado:
        """Valida dados de cadastro de usuário."""
        erros = []
        
        if not username or not password:
            erros.append('Usuário e senha são obrigatórios.')
            return ValidacaoResultado(valido=False, erros=erros)
        
        if len(username) < ValidadorUsuario.MIN_USERNAME_LENGTH:
            erros.append(f'Usuário deve ter no mínimo {ValidadorUsuario.MIN_USERNAME_LENGTH} caracteres.')
        
        if len(password) < ValidadorUsuario.MIN_PASSWORD_LENGTH:
            erros.append(f'Senha deve ter no mínimo {ValidadorUsuario.MIN_PASSWORD_LENGTH} caracteres.')
        
        if confirm_password is not None and password != confirm_password:
            erros.append('As senhas não coincidem.')
        
        return ValidacaoResultado(valido=len(erros) == 0, erros=erros)
