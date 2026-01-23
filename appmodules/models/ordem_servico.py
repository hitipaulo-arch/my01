"""Model para Ordem de Serviço."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from enum import Enum


class Prioridade(str, Enum):
    """Enum para prioridades de OS."""
    BAIXA = 'Baixa'
    MEDIA = 'Média'
    ALTA = 'Alta'
    URGENTE = 'Urgente'


class StatusOS(str, Enum):
    """Enum para status de OS."""
    ABERTO = 'Aberto'
    EM_ANDAMENTO = 'Em Andamento'
    CONCLUIDO = 'Concluído'
    CANCELADO = 'Cancelado'


@dataclass
class OrdemServico:
    """Representa uma Ordem de Serviço."""
    
    id: str
    timestamp: str
    solicitante: str
    setor: str
    data_solicitacao: str
    descricao: str
    equipamento: str
    prioridade: str
    status: str
    info_adicional: str = ''
    servico_realizado: str = ''
    horario_inicio: str = ''
    horario_termino: str = ''
    horas_trabalhadas: str = ''
    
    @classmethod
    def from_form(cls, form_data: dict, numero_pedido: int) -> 'OrdemServico':
        """Cria OrdemServico a partir de dados do formulário."""
        agora = datetime.now()
        
        return cls(
            id=str(numero_pedido),
            timestamp=agora.strftime("%d/%m/%Y %H:%M:%S"),
            solicitante=form_data.get('nome_solicitante', '').strip(),
            setor=form_data.get('setor', '').strip(),
            data_solicitacao=agora.strftime("%d/%m/%Y"),
            descricao=form_data.get('descricao', '').strip(),
            equipamento=form_data.get('equipamento', '').strip(),
            prioridade=form_data.get('prioridade', 'Média'),
            status=StatusOS.ABERTO.value,
            info_adicional=form_data.get('info_adicional', '').strip()
        )
    
    def to_sheet_row(self) -> list:
        """Converte para linha do Google Sheets."""
        return [
            self.id,
            self.timestamp,
            self.solicitante,
            self.setor,
            self.data_solicitacao,
            self.descricao,
            self.equipamento,
            self.prioridade,
            self.status,
            self.info_adicional,
            self.servico_realizado,
            self.horario_inicio,
            self.horario_termino,
            self.horas_trabalhadas
        ]
