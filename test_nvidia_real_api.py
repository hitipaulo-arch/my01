#!/usr/bin/env python3
"""
Teste de integração com API NVIDIA real para validar chat de IA.
"""
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[0]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("SECRET_KEY", "test-secret")

import app as app_module


class AdminAIChatRealAPITests(unittest.TestCase):
    """Testes que fazem chamadas reais à API NVIDIA."""

    def setUp(self):
        self.client = app_module.app.test_client()
        with self.client.session_transaction() as sess:
            sess["usuario"] = "admin"
            sess["role"] = "admin"

    def test_admin_ai_with_real_nvidia_api(self):
        """Testa o chat de IA com chamada real à API NVIDIA."""
        # Verificar se a chave está configurada
        api_key = os.getenv("NVIDIA_API_KEY")
        if not api_key:
            self.skipTest("NVIDIA_API_KEY não configurada")

        print("\n✅ NVIDIA_API_KEY encontrada! Fazendo chamada real...")

        # Step 1: GET para renderizar a página e pegar CSRF token
        response_get = self.client.get("/admin/ia")
        self.assertEqual(response_get.status_code, 200)

        # Extrair CSRF token
        import re
        csrf_match = re.search(
            r'name="csrf_token"[^>]*value="([^"]+)"',
            response_get.get_data(as_text=True)
        )
        csrf_token = csrf_match.group(1) if csrf_match else None
        self.assertIsNotNone(csrf_token, "CSRF token não encontrado")

        # Step 2: POST com mensagem de teste
        chat_data = {
            "q": "Responda apenas com uma palavra: OK",
            "action": "send",
            "csrf_token": csrf_token,
        }

        print("Enviando requisição para /admin/ia...")
        response_post = self.client.post(
            "/admin/ia",
            data=chat_data,
            follow_redirects=True
        )

        self.assertEqual(response_post.status_code, 200)
        print(f"Status: {response_post.status_code} ✅")

        # Step 3: Verificar se a resposta contém mensagens de IA
        response_text = response_post.get_data(as_text=True)
        
        # Verificar presença de elementos do chat
        self.assertIn("message", response_text.lower(), "Elemento 'message' não encontrado")
        print("Elemento 'message' encontrado ✅")

        # Step 4: Verificar sessão contém histórico
        with self.client.session_transaction() as sess:
            chat_history = sess.get("admin_ai_history", [])
            print(f"Histórico na sessão: {len(chat_history)} mensagens")
            self.assertGreater(len(chat_history), 0, "Histórico não foi salvo em sessão")

        print("\n" + "="*60)
        print("✅ TESTE COM API NVIDIA REAL: PASSOU")
        print("="*60)


if __name__ == "__main__":
    unittest.main(verbosity=2)
