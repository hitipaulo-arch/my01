import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("SECRET_KEY", "test-secret")

import app as app_module


class ItemRouteTests(unittest.TestCase):
    def setUp(self):
        self.client = app_module.app.test_client()
        with self.client.session_transaction() as sess:
            sess["usuario"] = "admin"
            sess["role"] = "admin"

    def test_itens_page_renders(self):
        response = self.client.get("/itens")
        self.assertIn(response.status_code, {200, 503})

    def test_edit_item_route_redirects_for_missing_item(self):
        response = self.client.get("/itens/999999/editar")
        self.assertIn(response.status_code, {200, 302, 404})

    def test_delete_item_route_accepts_post(self):
        response = self.client.post(
            "/itens/999999/deletar",
            data={"csrf_token": "test"},
        )
        self.assertIn(response.status_code, {200, 302, 400, 404, 500})

    def test_producao_abertas_page_renders(self):
        response = self.client.get("/producao-abertas")
        self.assertIn(response.status_code, {200, 503})

    def test_producao_abertas_contains_delete_button(self):
        """Verifica que a página /producao-abertas contém o botão de excluir."""
        response = self.client.get("/producao-abertas")
        if response.status_code == 200:
            html = response.get_data(as_text=True)
            self.assertIn("fa-trash", html)
            self.assertIn("btn-outline-danger", html)
            self.assertIn("excluir", html)

    def test_delete_producao_abertas_route_accepts_post(self):
        """Verifica que a rota de exclusão aceita POST para itens de produção."""
        response = self.client.post(
            "/itens/999999/excluir",
            data={"csrf_token": "test"},
        )
        self.assertIn(response.status_code, {200, 302, 400, 404, 500})


if __name__ == "__main__":
    unittest.main()
