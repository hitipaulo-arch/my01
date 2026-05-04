"""Serviço para gerenciar Google Sheets."""

import gspread
import logging
import datetime
import json
import os
import time
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from google.oauth2.service_account import Credentials

logger = logging.getLogger(__name__)


class SheetsService:
    """Gerencia conexão e operações com Google Sheets."""
    WHATSAPP_HEADER = 'WhatsApp do solicitante'
    
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
        self.usuarios_error = None
        self._os_cache: List[dict] = []
        self._os_cache_expires_at = 0.0
        self._os_cache_ttl_seconds = max(5, int(os.getenv('OS_CACHE_TTL_SECONDS', '120')))
        
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
                    'Horario de Inicio', 'Horario de Andamento', 'Horario de Término', 'Horas trabalhadas',
                    self.WHATSAPP_HEADER
                ])
                logger.info(f"Aba '{self.sheet_tab}' criada com cabeçalho")

            self._ensure_whatsapp_column()
            
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
                try:
                    self.sheet_usuarios = spreadsheet.add_worksheet(title=self.usuarios_tab, rows=1000, cols=10)
                    self.sheet_usuarios.append_row(['Username', 'Senha', 'Role'])
                    logger.info(f"Aba '{self.usuarios_tab}' criada")
                except Exception as e:
                    self.sheet_usuarios = None
                    self.usuarios_error = str(e)
                    logger.warning(f"Não foi possível inicializar a aba '{self.usuarios_tab}': {e}")
        
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

    def _ensure_usuarios_sheet(self) -> bool:
        """Garante que a aba de usuários esteja disponível."""
        if self.sheet_usuarios:
            return True

        if not self.client:
            self.usuarios_error = self.usuarios_error or "Cliente do Google Sheets indisponível"
            return False

        try:
            spreadsheet = self.client.open_by_key(self.sheet_id)
            try:
                self.sheet_usuarios = spreadsheet.worksheet(self.usuarios_tab)
            except Exception:
                self.sheet_usuarios = spreadsheet.add_worksheet(title=self.usuarios_tab, rows=1000, cols=10)
                self.sheet_usuarios.append_row(['Username', 'Senha', 'Role'])
            self.usuarios_error = None
            return True
        except Exception as e:
            self.usuarios_error = str(e)
            logger.error(f"Erro ao garantir aba de usuários '{self.usuarios_tab}': {e}")
            return False

    def _normalize_os_ids(self) -> None:
        """Compatibilidade: migração automática de IDs desativada para preservar rastreabilidade."""
        return

    def _invalidate_os_cache(self) -> None:
        """Invalida cache local de OS após qualquer mutação."""
        self._os_cache = []
        self._os_cache_expires_at = 0.0

    @staticmethod
    def _normalize_headers(headers: List[Any]) -> List[str]:
        """Normaliza cabeçalhos da planilha mantendo compatibilidade com legado."""
        normalized_headers = []
        for idx, header in enumerate(headers):
            header_text = str(header or '').strip()
            if idx == 0 and header_text in ('', '/'):
                header_text = 'ID'
            normalized_headers.append(header_text)
        return normalized_headers

    def _build_os_list_from_values(self, data: List[List[str]]) -> List[dict]:
        """Converte matriz da planilha em lista de dicionários de OS."""
        if len(data) < 2:
            return []

        normalized_headers = self._normalize_headers(data[0])
        os_list = []

        for i, row in enumerate(data[1:], start=2):
            if not any(row):
                continue

            full_row = row + [''] * (len(normalized_headers) - len(row))
            os_dict = dict(zip(normalized_headers, full_row))
            os_dict['row_id'] = i

            if str(os_dict.get('Status da OS', '')).strip().lower() not in ('cancelada', 'cancelado'):
                os_list.append(os_dict)

        return os_list
    
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

    def _ensure_whatsapp_column(self) -> None:
        """Garante a existência da coluna de WhatsApp do solicitante no cabeçalho."""
        try:
            if not self.sheet:
                return

            headers = self.sheet.row_values(1)
            if self.WHATSAPP_HEADER in headers:
                return

            next_col = len(headers) + 1
            self.sheet.update_cell(1, next_col, self.WHATSAPP_HEADER)
            logger.info("Coluna '%s' adicionada na aba '%s'", self.WHATSAPP_HEADER, self.sheet_tab)
        except Exception as e:
            logger.warning("Falha ao garantir coluna de WhatsApp na aba '%s': %s", self.sheet_tab, e)
    
    def add_os(self, row_data: list) -> bool:
        """Adiciona uma nova OS à planilha."""
        try:
            if not self.sheet:
                return False
            
            self.sheet.append_row(row_data, value_input_option='USER_ENTERED', 
                                 insert_data_option='INSERT_ROWS')
            self._invalidate_os_cache()
            logger.info(f"Nova OS adicionada (ID: {row_data[0]})")
            return True
        except Exception as e:
            logger.error(f"Erro ao adicionar OS: {e}")
            return False
    
    def get_all_os(self, use_cache: bool = True, force_refresh: bool = False) -> List[dict]:
        """Obtém todas as OS (exceto canceladas)."""
        try:
            if not self.sheet:
                return []

            now = time.time()
            if use_cache and not force_refresh and self._os_cache and now < self._os_cache_expires_at:
                return list(self._os_cache)
            
            data = self.sheet.get_all_values()
            os_list = self._build_os_list_from_values(data)
            self._os_cache = os_list
            self._os_cache_expires_at = now + self._os_cache_ttl_seconds
            return os_list
        except Exception as e:
            logger.error(f"Erro ao obter OS: {e}")
            return []

    def get_open_os(self, use_cache: bool = True) -> List[dict]:
        """Obtém somente OS em aberto ou em andamento."""
        status_validos = {'aberto', 'em andamento'}
        chamados = self.get_all_os(use_cache=use_cache)
        return [
            os_item for os_item in chamados
            if str(os_item.get('Status da OS', '')).strip().lower() in status_validos
        ]
    
    def update_os(self, row_id: int, row_data: list) -> bool:
        """Atualiza uma OS."""
        try:
            if not self.sheet:
                return False

            # Define a faixa dinamicamente com base na quantidade de colunas.
            ultima_coluna = chr(ord('A') + len(row_data) - 1)
            self.sheet.update(f'A{row_id}:{ultima_coluna}{row_id}', [row_data])
            self._invalidate_os_cache()
            logger.info(f"OS (linha {row_id}) atualizada")
            return True
        except Exception as e:
            logger.error(f"Erro ao atualizar OS: {e}")
            return False

    def get_os_by_row_id(self, row_id: int) -> Optional[dict]:
        """Obtém uma OS específica pelo número da linha na planilha."""
        try:
            if not self.sheet or row_id < 2:
                return None

            headers = self._normalize_headers(self.sheet.row_values(1))
            row_data = self.sheet.row_values(row_id)
            if not row_data or not any(str(v).strip() for v in row_data):
                return None

            full_row = row_data + [''] * (len(headers) - len(row_data))
            os_dict = dict(zip(headers, full_row))
            os_dict['row_id'] = row_id
            return os_dict
        except Exception as e:
            logger.error(f"Erro ao obter OS por row_id: {e}")
            return None
    
    def get_os_by_id(self, os_id: str) -> Optional[dict]:
        """Obtém uma OS específica pelo ID."""
        try:
            if not self.sheet:
                return None

            for os_item in self.get_all_os(use_cache=True):
                if str(os_item.get('ID', '')).strip() == str(os_id).strip():
                    return {
                        'id': os_item.get('ID', ''),
                        'timestamp': os_item.get('Carimbo de data/hora', ''),
                        'status': os_item.get('Status da OS', ''),
                        'descricao': os_item.get('Descrição', '') or os_item.get('Descrição do Problema ou Serviço Solicitado', '')
                    }
            
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
            if not self._ensure_usuarios_sheet():
                return []
            
            records = self.sheet_usuarios.get_all_records()
            return records
        except Exception as e:
            logger.error(f"Erro ao obter usuários: {e}")
            return []
    
    def update_usuario(self, row_id: int, username: str, senha: str, role: str) -> bool:
        """Atualiza um usuário."""
        try:
            if not self._ensure_usuarios_sheet():
                return False
            
            self.sheet_usuarios.update(f'A{row_id}:C{row_id}', [[username, senha, role]])
            logger.info(f"Usuário {username} atualizado")
            return True
        except Exception as e:
            logger.error(f"Erro ao atualizar usuário: {e}")
            return False
    
    def add_usuario(self, username: str, senha: str, role: str) -> bool:
        """Adiciona novo usuário."""
        try:
            if not self._ensure_usuarios_sheet():
                return False
            
            self.sheet_usuarios.append_row([username, senha, role])
            logger.info(f"Novo usuário {username} adicionado")
            return True
        except Exception as e:
            self.usuarios_error = str(e)
            logger.error(f"Erro ao adicionar usuário: {e}", exc_info=True)
            return False
    
    def delete_usuario(self, username: str) -> bool:
        """Deleta um usuário."""
        try:
            if not self._ensure_usuarios_sheet():
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
