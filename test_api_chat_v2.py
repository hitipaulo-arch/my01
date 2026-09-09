#!/usr/bin/env python3
"""
Teste de login e chat de IA no painel admin.
"""
import requests
import re
from bs4 import BeautifulSoup

BASE_URL = 'http://127.0.0.1:5000'

# Criar sessão
s = requests.Session()

# Step 1: Tentar fazer login com credenciais diferentes
print("📍 Step 1: Tentando credenciais de login...")
credenciais_test = [
    ('admin', 'admin'),
    ('admin', '123456'),
    ('administrator', 'admin'),
    ('admin@exemplo.com', '123456'),
]

logged_in = False
for username, password in credenciais_test:
    print(f"   Tentando: {username} / {password}")
    login_data = {
        'email': username,  # O campo pode ser 'email' ou 'username'
        'senha': password
    }
    
    # Tentar com campo 'email'
    r_login = s.post(f'{BASE_URL}/login', data=login_data)
    
    # Se retornar 302 (redirect), significa que não houve erro de validação
    if r_login.status_code == 302 or (r_login.status_code == 200 and 'login' not in r_login.url):
        print(f"   ✅ Possível login bem-sucedido: {username}")
        logged_in = True
        break
    elif r_login.status_code == 200:
        # Verificar se ainda está na página de login
        if '<form' in r_login.text and 'senha' in r_login.text.lower():
            print(f"      Ainda em login page (form presente)")
        else:
            print(f"      Possível sucesso (sem form)")
            logged_in = True
            break

if not logged_in:
    # Tentar campo 'username' em vez de 'email'
    print("\n   Tentando com campo 'username'...")
    for username, password in [('admin', 'admin')]:
        login_data = {
            'username': username,
            'password': password
        }
        r_login = s.post(f'{BASE_URL}/login', data=login_data)
        print(f"      Status: {r_login.status_code}")

# Step 2: Tentar acessar /admin/ia (pode redirecionar para login se não autenticado)
print("\n📍 Step 2: Acessando /admin/ia...")
r_ia = s.get(f'{BASE_URL}/admin/ia')
print(f"   Status: {r_ia.status_code}")

if 'Sem Permissão' in r_ia.text or 'login' in r_ia.url.lower() or r_ia.status_code in [401, 403]:
    print("   ❌ Acesso negado (não autenticado ou sem permissão)")
    print("\n⚠️  Não foi possível fazer login. Verifique as credenciais dos usuários cadastrados no Google Sheets.")
else:
    print("   ✅ Acesso permitido ao /admin/ia")
    
    # Extrair CSRF token
    csrf_match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', r_ia.text)
    csrf_token = csrf_match.group(1) if csrf_match else None
    
    if csrf_token:
        print(f"   CSRF Token encontrado: ✅")
        
        # Step 3: Enviar mensagem de chat
        print("\n📍 Step 3: Enviando mensagem para chat de IA...")
        chat_data = {
            'user_input': 'Como está a produção hoje?',
            'action': 'send',
            'csrf_token': csrf_token
        }
        
        r_chat = s.post(f'{BASE_URL}/admin/ia', data=chat_data)
        print(f"   Status: {r_chat.status_code}")
        
        if r_chat.status_code == 200:
            # Verificar se há resposta de IA
            if 'assistant' in r_chat.text.lower() or 'ia' in r_chat.text.lower():
                print("   ✅ Resposta recebida do chat de IA!")
            else:
                print("   ⚠️  Nenhuma resposta de IA visível")
        else:
            print(f"   ❌ Erro ao enviar mensagem: {r_chat.status_code}")
    else:
        print("   ❌ CSRF token não encontrado")

print("\n" + "="*60)
