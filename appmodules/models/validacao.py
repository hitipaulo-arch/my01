"""Classes de validação para o sistema."""

from dataclasses import dataclass
from typing import List, Dict, Any
import re


@dataclass
class ValidacaoResultado:
    """Resultado de uma validação."""
    valido: bool
    erros: List[str]


class ValidadorOS:
    """Validador centralizado para Ordens de Serviço."""
    
    PRIORIDADES_VALIDAS = ['Baixa', 'Média', 'Alta', 'Urgente']
    STATUS_VALIDOS = ['Aberto', 'Em Andamento', 'Aguardando Compra', 'Finalizada', 'Cancelada']
    MIN_DESCRICAO_LENGTH = 5
    
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

        whatsapp = form_data.get('whatsapp_solicitante', '').strip()
        if not whatsapp:
            erros.append('WhatsApp do solicitante é obrigatório.')
        else:
            numeros = re.sub(r'\D', '', whatsapp)
            if len(numeros) < 10:
                erros.append('WhatsApp do solicitante inválido. Informe DDD + número.')
        
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
        
        if not form_data.get('row_id'):
            erros.append('ID da linha é obrigatório.')
        
        # Validar status se fornecido
        status_provided = form_data.get('status_os', '').strip()
        if status_provided and status_provided not in ValidadorOS.STATUS_VALIDOS:
            status_list = ', '.join(ValidadorOS.STATUS_VALIDOS)
            erros.append(f'Status inválido: "{status_provided}". Valores aceitos: {status_list}')
        
        return ValidacaoResultado(valido=len(erros) == 0, erros=erros)


class ValidadorUsuario:
    """Validador centralizado para usuários."""
    
    MIN_USERNAME_LENGTH = 3
    MIN_PASSWORD_LENGTH = 12  # OWASP minimum - aumentado de 6 para 12
    
    # Caracteres obrigatórios para senha forte
    PASSWORD_MUST_HAVE_UPPERCASE = True
    PASSWORD_MUST_HAVE_DIGIT = True
    PASSWORD_MUST_HAVE_SPECIAL = True
    
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
        else:
            # Validar complexidade da senha
            if ValidadorUsuario.PASSWORD_MUST_HAVE_UPPERCASE and not any(c.isupper() for c in password):
                erros.append('Senha deve conter pelo menos 1 letra maiúscula.')
            if ValidadorUsuario.PASSWORD_MUST_HAVE_DIGIT and not any(c.isdigit() for c in password):
                erros.append('Senha deve conter pelo menos 1 número.')
            if ValidadorUsuario.PASSWORD_MUST_HAVE_SPECIAL and not any(c in '!@#$%^&*()_+-=[]{}|;:",.<>?/`~' for c in password):
                erros.append('Senha deve conter pelo menos 1 caractere especial (!@#$%...).')
        
        if confirm_password is not None and password != confirm_password:
            erros.append('As senhas não coincidem.')
        
        return ValidacaoResultado(valido=len(erros) == 0, erros=erros)
