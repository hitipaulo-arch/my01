import os
import re
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

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

        # O decorator @admin_required consulta user_service.get_usuario()
        # (Google Sheets). Sem credenciais/planilha disponíveis no CI, o
        # usuário 'admin' não existe e a rota redireciona (302). Para testar
        # o chat em si, injetamos um user_service fake que reconhece 'admin'.
        self._original_user_service = app_module.app.config.get("user_service")

        class _FakeUsuario:
            role = "admin"

        class _FakeUserService:
            def get_usuario(self, username):
                return _FakeUsuario() if username == "admin" else None

        app_module.app.config["user_service"] = _FakeUserService()

    def tearDown(self):
        app_module.app.config["user_service"] = self._original_user_service

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

    def test_get_nvidia_ai_client_uses_openai_fallback(self):
        with patch.dict(
            os.environ,
            {"NVIDIA_API_KEY": "", "OPENAI_API_KEY": "openai-key", "AI_PROVIDER": "openai"},
            clear=False,
        ):
            with patch("app.OpenAI") as mock_client:
                app_module.get_nvidia_ai_client()
                mock_client.assert_called_once_with(
                    base_url="https://api.openai.com/v1",
                    api_key="openai-key",
                )

    def test_get_nvidia_ai_client_uses_ollama_fallback(self):
        with patch.dict(
            os.environ,
            {
                "NVIDIA_API_KEY": "",
                "OPENAI_API_KEY": "",
                "AI_PROVIDER": "ollama",
                "OLLAMA_BASE_URL": "http://localhost:11434/v1",
                "OLLAMA_MODEL": "qwen2.5:3b",
            },
            clear=False,
        ):
            with patch("app.OpenAI") as mock_client:
                client = app_module.get_nvidia_ai_client()
                self.assertIsNotNone(client)
                mock_client.assert_called_once_with(
                    base_url="http://localhost:11434/v1",
                    api_key="ollama",
                )

    def test_admin_ai_retries_with_supported_nvidia_model_when_current_is_retired(self):
        class FakeRetiredError(Exception):
            pass

        class FakeMessage:
            content = "Resposta após fallback"

        class FakeChoice:
            message = FakeMessage()

        class FakeResponse:
            choices = [FakeChoice()]

        class FakeCompletions:
            def __init__(self):
                self.calls = []

            def create(self, **kwargs):
                self.calls.append(kwargs["model"])
                if kwargs["model"] == "z-ai/glm-5.2":
                    raise FakeRetiredError("The model 'z-ai/glm-5.2' has reached its end of life")
                return FakeResponse()

        class FakeClient:
            def __init__(self):
                self.chat = type("Chat", (), {"completions": FakeCompletions()})()

        original_factory = app_module.get_nvidia_ai_client
        original_model = app_module.get_ai_model_name
        try:
            app_module.get_nvidia_ai_client = lambda: FakeClient()
            app_module.get_ai_model_name = lambda: "z-ai/glm-5.2"
            with patch("app.get_ai_model_name", side_effect=["z-ai/glm-5.2", "meta/llama-3.1-8b-instruct"]):
                with patch("app.build_admin_ai_context", return_value="Contexto"):
                    with self.client.session_transaction() as sess:
                        sess["usuario"] = "admin"
                        sess["role"] = "admin"
                    get_response = self.client.get("/admin/ia")
                    token_match = re.search(r'name="csrf_token" value="([^"]+)"', get_response.get_data(as_text=True))
                    csrf_token = token_match.group(1)
                    response = self.client.post(
                        "/admin/ia",
                        data={"q": "teste do fallback", "csrf_token": csrf_token},
                    )
                    self.assertEqual(response.status_code, 200)
                    self.assertIn("Resposta após fallback", response.get_data(as_text=True))
        finally:
            app_module.get_nvidia_ai_client = original_factory
            app_module.get_ai_model_name = original_model


if __name__ == "__main__":
    unittest.main()
