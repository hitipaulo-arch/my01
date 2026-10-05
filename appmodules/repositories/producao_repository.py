"""Fachada fina para as operações de produção do ``SheetsService``."""


class ProducaoRepository:
    """Expõe operações de produção sem duplicar regras de persistência."""

    def __init__(self, sheets_service):
        self.sheets_service = sheets_service

    def add(self, row_data):
        return self.sheets_service.add_producao(row_data)

    def get_all(self, **kwargs):
        return self.sheets_service.get_all_producao(**kwargs)

    def get_by_row_id(self, row_id):
        return self.sheets_service.get_producao_by_row_id(row_id)

    def update(self, row_id, row_data):
        return self.sheets_service.update_producao(row_id, row_data)

    def delete(self, row_id):
        return self.sheets_service.delete_producao(row_id)

    def mark_default_origin(self, origin="produção"):
        return self.sheets_service.marcar_origem_padrao_producao(origin)


__all__ = ["ProducaoRepository"]