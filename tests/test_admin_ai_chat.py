import os
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("SECRET_KEY", "test-secret")

import app as app_module


class AdminAIChatTests(unittest.TestCase):
    def setUp(self):
        self.client = app_module.app.test_client()
        with self.client.session_transaction() as sess:
            sess["usuario"] = "admin"
            sess["role"] = "admin"

    def test_admin_ai_page_renders(self):
        response = self.client.get("/admin/ia")
        self.assertEqual(response.status_code, 200)
        self.assertIn("IA do Administrador", response.get_data(as_text=True))

    def test_admin_ai_keeps_chat_history_in_session(self):
        class FakeMessage:
            content = "Resposta de teste da IA"

        class FakeChoice:
            message = FakeMessage()

        class FakeResponse:
            choices = [FakeChoice()]

        class FakeClient:
            class chat:
                class completions:
                    @staticmethod
                    def create(*args, **kwargs):
                        self_key = kwargs.get("messages")
                        assert any("Contexto do sistema" in item.get("content", "") for item in self_key)
                        return FakeResponse()

        original_client_factory = app_module.get_nvidia_ai_client
        app_module.get_nvidia_ai_client = lambda: FakeClient()
        try:
            get_response = self.client.get("/admin/ia")
            self.assertEqual(get_response.status_code, 200)

            token_match = re.search(r'name="csrf_token" value="([^"]+)"', get_response.get_data(as_text=True))
            self.assertIsNotNone(token_match, "CSRF token não foi encontrado no formulário.")
            csrf_token = token_match.group(1)

            response = self.client.post(
                "/admin/ia",
                data={"q": "qual é o status do estoque?", "csrf_token": csrf_token},
            )
            self.assertEqual(response.status_code, 200)
            html = response.get_data(as_text=True)
            self.assertIn("Resposta de teste da IA", html)

            with self.client.session_transaction() as sess:
                history = sess.get("admin_ai_history", [])
                self.assertGreaterEqual(len(history), 2)
                self.assertEqual(history[0]["role"], "user")
                self.assertEqual(history[1]["role"], "user")
                self.assertEqual(history[-1]["role"], "assistant")
        finally:
            app_module.get_nvidia_ai_client = original_client_factory

    def test_admin_ai_summary_action_uses_default_prompt(self):
        class FakeMessage:
            content = "Resumo do dia gerado"

        class FakeChoice:
            message = FakeMessage()

        class FakeResponse:
            choices = [FakeChoice()]

        class FakeClient:
            class chat:
                class completions:
                    @staticmethod
                    def create(*args, **kwargs):
                        messages = kwargs.get("messages", [])
                        last_message = messages[-1].get("content", "")
                        self.assertIn("Resumo executivo do dia", last_message)
                        return FakeResponse()

        original_client_factory = app_module.get_nvidia_ai_client
        app_module.get_nvidia_ai_client = lambda: FakeClient()
        try:
            get_response = self.client.get("/admin/ia")
            self.assertEqual(get_response.status_code, 200)

            token_match = re.search(r'name="csrf_token" value="([^"]+)"', get_response.get_data(as_text=True))
            self.assertIsNotNone(token_match)
            csrf_token = token_match.group(1)

            response = self.client.post(
                "/admin/ia",
                data={"action": "summary", "csrf_token": csrf_token},
            )
            self.assertEqual(response.status_code, 200)
            self.assertIn("Resumo do dia gerado", response.get_data(as_text=True))
        finally:
            app_module.get_nvidia_ai_client = original_client_factory


if __name__ == "__main__":
    unittest.main()
