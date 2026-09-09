#!/usr/bin/env python3
"""
Teste de ponta-a-ponta do chat de IA no painel admin.
"""
import requests
import re

BASE_URL = 'http://127.0.0.1:5000'

# Criar sessão
s = requests.Session()

# Step 1: Fazer login como admin
print("📍 Step 1: Fazendo login como admin...")
login_data = {
    'email': 'admin@exemplo.com',
    'senha': '123456'
}
r_login = s.post(f'{BASE_URL}/login', data=login_data)
print(f"   Status: {r_login.status_code}")

# Step 2: Acessar a página de IA (GET) para pegar o token CSRF
print("\n📍 Step 2: Acessando página de IA para obter token CSRF...")
r_ia_page = s.get(f'{BASE_URL}/admin/ia')
print(f"   Status: {r_ia_page.status_code}")

# Extrair CSRF token da página
csrf_match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', r_ia_page.text)
csrf_token = csrf_match.group(1) if csrf_match else None
print(f"   CSRF Token encontrado: {bool(csrf_token)}")

# Step 3: Enviar uma mensagem para o chat de IA
print("\n📍 Step 3: Enviando mensagem para o chat de IA...")
chat_data = {
    'user_input': 'Quantos itens de produção estão em aberto hoje?',
    'action': 'send',
    'csrf_token': csrf_token or ''
}
r_chat = s.post(f'{BASE_URL}/admin/ia', data=chat_data)
print(f"   Status: {r_chat.status_code}")

# Step 4: Verificar a resposta
if r_chat.status_code == 200:
    # Procurar por mensagens de IA na resposta
    if '<div class="message assistant' in r_chat.text or '<div class="message' in r_chat.text:
        # Extrair uma parte da resposta
        response_part = r_chat.text[r_chat.text.find('<div class="message'):r_chat.text.find('<div class="message')+500] if '<div class="message' in r_chat.text else ''
        print(f"\n✅ Resposta recebida do chat!")
        print(f"   Previsualizando resposta (primeiros 200 caracteres):")
        # Limpar HTML tags para leitura
        import html
        cleaned = html.unescape(response_part)
        cleaned = re.sub(r'<[^>]+>', '', cleaned)
        print(f"   {cleaned[:200]}...")
    else:
        print(f"\n❌ Nenhuma mensagem de IA encontrada na resposta")
        print(f"   Primeiros 500 caracteres: {r_chat.text[:500]}")
else:
    print(f"\n❌ Erro ao chamar /admin/ia")
    print(f"   Resposta: {r_chat.text[:500]}")

print("\n" + "="*60)
print("✅ Teste completo!")
print("="*60)
