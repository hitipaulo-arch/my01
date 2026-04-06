"""Serviço para gerenciar Google Sheets."""

import gspread
import logging
import datetime
import json
import re
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from google.oauth2.service_account import Credentials
from gspread.exceptions import APIError

logger = logging.getLogger(__name__)


class SheetsService:
    """Gerencia conexão e operações com Google Sheets."""
    
    SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive.file'
    ]
    
    def __init__(self, creds_file: str, sheet_id: str, sheet_tab: str, 
                 horario_tab: str, usuarios_tab: str, audit_tab: str = 'Registro de Ações'):
        """Inicializa o serviço de Sheets."""
        self.sheet_id = sheet_id
        self.sheet_tab = sheet_tab
        self.horario_tab = horario_tab
        self.usuarios_tab = usuarios_tab
        self.audit_tab = audit_tab
        self.client = None
        self.sheet = None
        self.sheet_horario = None
        self.sheet_usuarios = None
        self.sheet_auditoria = None
        self.error = None
        self.last_error = None
        
        self._init_connection(creds_file)
    
    def _init_connection(self, creds_file: str) -> None:
        """Inicializa conexão com Google Sheets."""
        try:
            self._validate_credentials_file(creds_file)
            creds = Credentials.from_service_account_file(creds_file, scopes=self.SCOPES)
            logger.info("Credenciais carregadas com sucesso")
            
            self.client = gspread.authorize(creds)
            spreadsheet = self.client.open_by_key(self.sheet_id)
            
            # Conecta à aba principal
            try:
                self.sheet = spreadsheet.worksheet(self.sheet_tab)
                logger.info(f"Conectado à aba '{self.sheet_tab}'")
            except Exception:
                self.sheet = spreadsheet.add_worksheet(title=self.sheet_tab, rows=2000, cols=20)
                self.sheet.append_row([
                    'ID', 'Carimbo de data/hora', 'Nome do solicitante', 'Setor',
                    'Data da Solicitação', 'Descrição', 'Equipamento/Local', 'Prioridade',
                    'Status da OS', 'Informações adicionais', 'Serviço realizado',
                    'Horario de Inicio', 'Horario de Andamento', 'Horario de Término', 'Horas trabalhadas'
                ])
                logger.info(f"Aba '{self.sheet_tab}' criada com cabeçalho")
            
            # Conecta à aba de horário
            try:
                self.sheet_horario = spreadsheet.worksheet(self.horario_tab)
                logger.info(f"Conectado à aba '{self.horario_tab}'")
            except Exception:
                self.sheet_horario = spreadsheet.add_worksheet(title=self.horario_tab, rows=1000, cols=10)
                self.sheet_horario.append_row(['Data', 'Funcionário', 'Pedido/OS', 'Tipo', 'Horário', 'Observação'])
                logger.info(f"Aba '{self.horario_tab}' criada")
            
            # Conecta à aba de usuários
            try:
                self.sheet_usuarios = spreadsheet.worksheet(self.usuarios_tab)
                logger.info(f"Conectado à aba '{self.usuarios_tab}'")
            except Exception:
                self.sheet_usuarios = spreadsheet.add_worksheet(title=self.usuarios_tab, rows=1000, cols=10)
                self.sheet_usuarios.append_row(['Username', 'Senha', 'Role'])
                logger.info(f"Aba '{self.usuarios_tab}' criada")

            # Conecta à aba de auditoria
            try:
                self.sheet_auditoria = spreadsheet.worksheet(self.audit_tab)
                logger.info(f"Conectado à aba '{self.audit_tab}'")
            except Exception:
                self.sheet_auditoria = spreadsheet.add_worksheet(title=self.audit_tab, rows=1000, cols=10)
                self.sheet_auditoria.append_row(['Carimbo de data/hora', 'Usuário', 'Ação', 'Entidade', 'Identificador', 'Detalhes'])
                logger.info(f"Aba '{self.audit_tab}' criada")
        
        except FileNotFoundError:
            logger.error("Arquivo 'credentials.json' não encontrado")
            self.error = "Credenciais não encontradas"
        except ValueError as e:
            logger.error(f"Credenciais inválidas: {e}")
            self.error = str(e)
        except Exception as e:
            logger.error(f"Erro ao conectar à planilha: {e}")
            self.error = str(e)

    def _validate_credentials_file(self, creds_file: str) -> None:
        """Valida formato mínimo do credentials.json antes de autenticar."""
        creds_path = Path(creds_file)
        if not creds_path.exists():
            raise FileNotFoundError(creds_file)

        data = json.loads(creds_path.read_text(encoding='utf-8'))
        placeholders = {
            'SUBSTITUA',
            'SUBSTITUA_COM_SEU_PROJECT_ID',
            'SUA_PRIVATE_KEY_AQUI',
            'SEU_PROJECT_ID_AQUI'
        }

        private_key = str(data.get('private_key', '')).strip()
        client_email = str(data.get('client_email', '')).strip()
        project_id = str(data.get('project_id', '')).strip()

        if (
            not private_key
            or private_key in placeholders
            or 'BEGIN PRIVATE KEY' not in private_key
        ):
            raise ValueError(
                "credentials.json inválido: campo 'private_key' ausente/placeholder. "
                "Use JSON real de service account."
            )

        if not client_email or client_email in placeholders or '@' not in client_email:
            raise ValueError(
                "credentials.json inválido: campo 'client_email' ausente/placeholder."
            )

        if not project_id or project_id in placeholders:
            raise ValueError(
                "credentials.json inválido: campo 'project_id' ausente/placeholder."
            )
    
    def is_available(self) -> Tuple[bool, Optional[str]]:
        """Verifica se a conexão está disponível."""
        if self.sheet is None:
            return False, self.error or "Sheets não disponível"
        return True, None

    def get_last_error(self) -> Optional[str]:
        """Retorna a última mensagem de erro operacional do serviço."""
        return self.last_error
    
    def get_next_id(self) -> int:
        """Obtém o próximo ID disponível."""
        try:
            if not self.sheet:
                return int(datetime.datetime.now().timestamp())

            # Regra principal: sempre usar o último ID válido da coluna A e somar 1.
            dados = self.sheet.get_all_values()
            if len(dados) <= 1:
                return 1

            for row in reversed(dados[1:]):
                if not row:
                    continue

                id_str = str(row[0]).strip() if len(row) > 0 else ''
                if not id_str:
                    continue

                match_numero = re.search(r'\d+(?:[\.,]\d+)?', id_str)
                if not match_numero:
                    continue

                valor_normalizado = match_numero.group(0).replace(',', '.')
                return int(float(valor_normalizado)) + 1

            return 1
        except Exception as e:
            logger.error(f"Erro ao obter próximo ID: {e}")
            return int(datetime.datetime.now().timestamp())
    
    def add_os(self, row_data: list) -> bool:
        """Adiciona uma nova OS à planilha."""
        try:
            if not self.sheet:
                return False
            
            self.sheet.append_row(row_data, value_input_option='USER_ENTERED', 
                                 insert_data_option='INSERT_ROWS')
            logger.info(f"Nova OS adicionada (ID: {row_data[0]})")
            return True
        except Exception as e:
            logger.error(f"Erro ao adicionar OS: {e}")
            return False
    
    def get_all_os(self) -> List[dict]:
        """Obtém todas as OS (exceto canceladas)."""
        try:
            if not self.sheet:
                return []
            
            data = self.sheet.get_all_values()
            if len(data) < 2:
                return []
            
            headers = data[0]
            os_list = []
            
            for i, row in enumerate(data[1:], start=2):
                if not any(row):
                    continue
                
                full_row = row + [''] * (len(headers) - len(row))
                os_dict = dict(zip(headers, full_row))
                os_dict['row_id'] = i
                
                # Pula OS canceladas
                status = str(os_dict.get('Status da OS', '')).strip().lower()
                if status not in ('cancelada', 'cancelado'):
                    os_list.append(os_dict)
            
            return os_list
        except Exception as e:
            logger.error(f"Erro ao obter OS: {e}")
            return []
    
    def update_os(self, row_id: int, row_data: list) -> bool:
        """Atualiza uma OS."""
        try:
            if not self.sheet:
                return False

            # Define a faixa dinamicamente com base na quantidade de colunas.
            ultima_coluna = chr(ord('A') + len(row_data) - 1)
            self.sheet.update(f'A{row_id}:{ultima_coluna}{row_id}', [row_data])
            logger.info(f"OS (linha {row_id}) atualizada")
            return True
        except Exception as e:
            logger.error(f"Erro ao atualizar OS: {e}")
            return False
    
    def get_os_by_id(self, os_id: str) -> Optional[dict]:
        """Obtém uma OS específica pelo ID."""
        try:
            if not self.sheet:
                return None
            
            cell = self.sheet.find(str(os_id), in_column=1)
            if cell:
                row_data = self.sheet.row_values(cell.row)
                return {
                    'id': row_data[0] if len(row_data) > 0 else '',
                    'timestamp': row_data[1] if len(row_data) > 1 else '',
                    'status': row_data[8] if len(row_data) > 8 else '',
                    'descricao': row_data[5] if len(row_data) > 5 else ''
                }
            return None
        except Exception as e:
            logger.error(f"Erro ao obter OS: {e}")
            return None
    
    def add_time_record(self, data: str, funcionario: str, pedido_os: str, 
                       tipo: str, horario: str, observacao: str = '') -> bool:
        """Adiciona registro de controle de horário."""
        try:
            if not self.sheet_horario:
                return False
            
            self.sheet_horario.append_row([data, funcionario, pedido_os, tipo, horario, observacao])
            logger.info(f"Registro de {tipo} adicionado para {funcionario}")
            return True
        except Exception as e:
            logger.error(f"Erro ao adicionar registro de horário: {e}")
            return False

    def add_audit_record(self, usuario: str, acao: str, entidade: str,
                         identificador: str = '', detalhes: str = '') -> bool:
        """Adiciona um registro de auditoria de ações do usuário."""
        try:
            if not self.sheet_auditoria:
                return False

            timestamp = datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')
            self.sheet_auditoria.append_row([
                timestamp,
                usuario,
                acao,
                entidade,
                identificador,
                detalhes,
            ])
            logger.info("Auditoria registrada para %s: %s %s", usuario, acao, entidade)
            return True
        except Exception as e:
            logger.warning(f"Erro ao adicionar auditoria: {e}")
            return False

    def get_audit_records(self) -> List[dict]:
        """Obtém todos os registros de auditoria."""
        try:
            if not self.sheet_auditoria:
                return []

            data = self.sheet_auditoria.get_all_values()
            if len(data) < 2:
                return []

            headers = data[0]
            records = []

            for row in data[1:]:
                if not any(row):
                    continue

                full_row = row + [''] * (len(headers) - len(row))
                records.append(dict(zip(headers, full_row)))

            return records
        except Exception as e:
            logger.error(f"Erro ao obter registros de auditoria: {e}")
            return []
    
    def get_time_records(self) -> List[dict]:
        """Obtém todos os registros de controle de horário."""
        try:
            if not self.sheet_horario:
                return []
            
            data = self.sheet_horario.get_all_values()
            if len(data) < 2:
                return []
            
            headers = data[0]
            records = []
            
            for row in data[1:]:
                if not any(row):
                    continue
                
                full_row = row + [''] * (len(headers) - len(row))
                records.append(dict(zip(headers, full_row)))
            
            return records
        except Exception as e:
            logger.error(f"Erro ao obter registros de horário: {e}")
            return []
    
    def get_usuarios_raw(self) -> List[dict]:
        """Obtém todos os usuários do Sheets."""
        try:
            if not self.sheet_usuarios:
                return []
            
            records = self.sheet_usuarios.get_all_records()
            return records
        except Exception as e:
            logger.error(f"Erro ao obter usuários: {e}")
            return []
    
    def update_usuario(self, row_id: int, username: Optional[str] = None,
                       senha: Optional[str] = None, role: Optional[str] = None) -> bool:
        """Atualiza um usuário apenas nos campos alterados."""
        try:
            self.last_error = None
            if not self.sheet_usuarios:
                self.last_error = "Aba de usuários indisponível no Google Sheets."
                return False

            row_values = self.sheet_usuarios.row_values(row_id)
            current_username = row_values[0] if len(row_values) > 0 else ''
            current_senha = row_values[1] if len(row_values) > 1 else ''
            current_role = row_values[2] if len(row_values) > 2 else ''

            updates = []
            if username is not None and username != current_username:
                updates.append({'range': f'A{row_id}:A{row_id}', 'values': [[username]]})
            if senha is not None and senha != current_senha:
                updates.append({'range': f'B{row_id}:B{row_id}', 'values': [[senha]]})
            if role is not None and role != current_role:
                updates.append({'range': f'C{row_id}:C{row_id}', 'values': [[role]]})

            if not updates:
                logger.info(f"Nenhuma alteração para usuário na linha {row_id}")
                return True

            self.sheet_usuarios.batch_update(updates)
            logger.info(f"Usuário na linha {row_id} atualizado")
            return True
        except APIError as e:
            error_text = str(e)
            if 'protected cell' in error_text.lower() or 'protected object' in error_text.lower():
                self.last_error = (
                    "Não foi possível atualizar o usuário porque a linha/célula está protegida "
                    "na aba de usuários. Solicite ao proprietário da planilha a liberação "
                    "de edição para a conta de serviço."
                )
                logger.error(
                    "Erro ao atualizar usuário: a célula/linha está protegida na aba '%s' (linha %s)",
                    self.usuarios_tab,
                    row_id,
                )
            else:
                self.last_error = "Falha ao atualizar usuário no Google Sheets."
                logger.error(f"Erro ao atualizar usuário: {e}")
            return False
        except Exception as e:
            self.last_error = "Falha inesperada ao atualizar usuário no Google Sheets."
            logger.error(f"Erro ao atualizar usuário: {e}")
            return False
    
    def add_usuario(self, username: str, senha: str, role: str) -> bool:
        """Adiciona novo usuário."""
        try:
            if not self.sheet_usuarios:
                return False
            
            self.sheet_usuarios.append_row([username, senha, role])
            logger.info(f"Novo usuário {username} adicionado")
            return True
        except Exception as e:
            logger.error(f"Erro ao adicionar usuário: {e}")
            return False
    
    def delete_usuario(self, username: str) -> bool:
        """Deleta um usuário."""
        try:
            if not self.sheet_usuarios:
                return False
            
            records = self.sheet_usuarios.get_all_records()
            for i, rec in enumerate(records, start=2):
                if str(rec.get('Username', '')).strip() == username:
                    self.sheet_usuarios.delete_rows(i)
                    logger.info(f"Usuário {username} deletado")
                    return True
            
            return False
        except Exception as e:
            logger.error(f"Erro ao deletar usuário: {e}")
            return False
