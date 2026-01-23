"""Serviço para gerenciar Google Sheets."""

import gspread
import logging
import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from google.oauth2.service_account import Credentials

logger = logging.getLogger(__name__)


class SheetsService:
    """Gerencia conexão e operações com Google Sheets."""
    
    SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive.file'
    ]
    
    def __init__(self, creds_file: str, sheet_id: str, sheet_tab: str, 
                 horario_tab: str, usuarios_tab: str):
        """Inicializa o serviço de Sheets."""
        self.sheet_id = sheet_id
        self.sheet_tab = sheet_tab
        self.horario_tab = horario_tab
        self.usuarios_tab = usuarios_tab
        self.client = None
        self.sheet = None
        self.sheet_horario = None
        self.sheet_usuarios = None
        self.error = None
        
        self._init_connection(creds_file)
    
    def _init_connection(self, creds_file: str) -> None:
        """Inicializa conexão com Google Sheets."""
        try:
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
                    'Horario de Inicio', 'Horario de Término', 'Horas trabalhadas'
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
        
        except FileNotFoundError:
            logger.error("Arquivo 'credentials.json' não encontrado")
            self.error = "Credenciais não encontradas"
        except Exception as e:
            logger.error(f"Erro ao conectar à planilha: {e}")
            self.error = str(e)
    
    def is_available(self) -> Tuple[bool, Optional[str]]:
        """Verifica se a conexão está disponível."""
        if self.sheet is None:
            return False, self.error or "Sheets não disponível"
        return True, None
    
    def get_next_id(self) -> int:
        """Obtém o próximo ID disponível."""
        try:
            if not self.sheet:
                return int(datetime.datetime.now().timestamp())
            
            ids_column = self.sheet.col_values(1)
            if ids_column:
                ids_column = ids_column[1:]  # Remove cabeçalho
            
            ids_numericos = []
            for id_val in ids_column:
                try:
                    if id_val and str(id_val).strip():
                        ids_numericos.append(int(id_val))
                except ValueError:
                    continue
            
            return max(ids_numericos) + 1 if ids_numericos else 1
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
                if os_dict.get('Status da OS') != 'Cancelada':
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
            
            self.sheet.update(f'A{row_id}:N{row_id}', [row_data])
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
    
    def update_usuario(self, row_id: int, username: str, senha: str, role: str) -> bool:
        """Atualiza um usuário."""
        try:
            if not self.sheet_usuarios:
                return False
            
            self.sheet_usuarios.update_cell(row_id, 1, username)
            self.sheet_usuarios.update_cell(row_id, 2, senha)
            self.sheet_usuarios.update_cell(row_id, 3, role)
            logger.info(f"Usuário {username} atualizado")
            return True
        except Exception as e:
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
