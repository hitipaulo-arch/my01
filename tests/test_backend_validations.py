import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("SECRET_KEY", "test-secret")

import app as app_module


class BackendValidationTests(unittest.TestCase):
    def test_validate_item_form_data_rejects_invalid_values(self):
        ok, message = app_module._validate_item_form_data(
            nome_item="A",
            codigo_item="",
            quantidade_raw=2_000_000,
            observacao="x" * 600,
        )

        self.assertFalse(ok)
        self.assertIn("Nome do item", message)
        self.assertIn("Código do item", message)
        self.assertIn("Quantidade", message)
        self.assertIn("Observação", message)

    def test_validate_user_payload_rejects_short_credentials(self):
        ok, message = app_module._validate_user_payload(
            username="ab",
            senha="123",
            role="admin",
        )

        self.assertFalse(ok)
        self.assertIn("Username", message)
        self.assertIn("Senha", message)


if __name__ == "__main__":
    unittest.main()
