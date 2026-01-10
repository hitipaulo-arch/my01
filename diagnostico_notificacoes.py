#!/usr/bin/env python3
"""
Script de diagnóstico para notificações de OS.
Verifica se as credenciais e configuração estão corretas.
"""

import os
import sys
from pathlib import Path

def check_env_file():
    """Verifica se .env existe"""
    print("\n🔍 VERIFICAÇÃO 1: Arquivo .env")
    print("-" * 60)
    
    if not Path('.env').exists():
        print("❌ Arquivo .env não encontrado!")
        print("   Execute: Copy-Item .env.example .env")
        return False
    
    print("✅ Arquivo .env encontrado")
    return True


def check_env_variables():
    """Verifica se as variáveis estão configuradas"""
    print("\n🔍 VERIFICAÇÃO 2: Variáveis de Ambiente")
    print("-" * 60)
    
    # Carrega .env
    from dotenv import load_dotenv
    load_dotenv()
    
    required_vars = [
        'GOOGLE_SHEET_ID',
        'GOOGLE_SHEET_TAB',
        'SECRET_KEY',
    ]
    
    notification_vars = [
        'NOTIFY_ENABLED',
        'SMTP_USER',
        'SMTP_PASSWORD',
        'SMTP_RECIPIENTS',
        'WHATSAPP_ENABLED',
        'TWILIO_ACCOUNT_SID',
        'TWILIO_AUTH_TOKEN',
        'TWILIO_WHATSAPP_TO',
        'TWILIO_CONTENT_SID',
    ]
    
    all_missing = []
    
    # Verifica variáveis obrigatórias
    print("Variáveis obrigatórias:")
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"  ✅ {var}")
        else:
            print(f"  ❌ {var} - NÃO CONFIGURADO")
            all_missing.append(var)
    
    # Verifica variáveis de notificação
    print("\nVariáveis de notificação:")
    notify_enabled = os.getenv('NOTIFY_ENABLED', 'false').lower() == 'true'
    whatsapp_enabled = os.getenv('WHATSAPP_ENABLED', 'false').lower() == 'true'
    
    print(f"  {'✅' if notify_enabled else '⚠️'} NOTIFY_ENABLED = {notify_enabled}")
    print(f"  {'✅' if whatsapp_enabled else '⚠️'} WHATSAPP_ENABLED = {whatsapp_enabled}")
    
    if notify_enabled:
        for var in ['SMTP_USER', 'SMTP_PASSWORD', 'SMTP_RECIPIENTS']:
            value = os.getenv(var)
            if value:
                masked = value[:3] + '*' * (len(value) - 6) + value[-3:] if len(value) > 6 else '***'
                print(f"  ✅ {var} = {masked}")
            else:
                print(f"  ❌ {var} - NÃO CONFIGURADO")
                all_missing.append(var)
    
    if whatsapp_enabled:
        for var in ['TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN', 'TWILIO_WHATSAPP_TO', 'TWILIO_CONTENT_SID']:
            value = os.getenv(var)
            if value and value.startswith('x') == False:  # Se não for placeholder
                masked = value[:3] + '*' * (len(value) - 6) + value[-3:] if len(value) > 6 else '***'
                print(f"  ✅ {var} = {masked}")
            else:
                print(f"  ❌ {var} - PLACEHOLDER (use valores reais)")
                all_missing.append(var)
    
    return len(all_missing) == 0


def check_smtp_connection():
    """Testa conexão com Gmail SMTP"""
    print("\n🔍 VERIFICAÇÃO 3: Conexão Gmail SMTP")
    print("-" * 60)
    
    from dotenv import load_dotenv
    load_dotenv()
    
    notify_enabled = os.getenv('NOTIFY_ENABLED', 'false').lower() == 'true'
    
    if not notify_enabled:
        print("⚠️  NOTIFY_ENABLED = false (notificações desativadas)")
        return True
    
    import smtplib
    
    smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    smtp_user = os.getenv('SMTP_USER')
    smtp_password = os.getenv('SMTP_PASSWORD')
    
    try:
        print(f"Conectando a {smtp_host}:{smtp_port}...")
        server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
        server.starttls()
        print("✅ Conexão TLS estabelecida")
        
        print(f"Autenticando como {smtp_user}...")
        server.login(smtp_user, smtp_password)
        print("✅ Autenticação bem-sucedida")
        
        server.quit()
        print("✅ Gmail SMTP OK")
        return True
        
    except smtplib.SMTPAuthenticationError:
        print("❌ Erro de autenticação Gmail")
        print("   Verifique:")
        print("   - SMTP_USER está correto?")
        print("   - SMTP_PASSWORD é a senha de APP (não a senha do Gmail)?")
        print("   - 2FA está ativado em myaccount.google.com?")
        return False
    except Exception as e:
        print(f"❌ Erro ao conectar Gmail: {e}")
        return False


def check_twilio_connection():
    """Testa conexão com Twilio"""
    print("\n🔍 VERIFICAÇÃO 4: Conexão Twilio WhatsApp")
    print("-" * 60)
    
    from dotenv import load_dotenv
    load_dotenv()
    
    whatsapp_enabled = os.getenv('WHATSAPP_ENABLED', 'false').lower() == 'true'
    
    if not whatsapp_enabled:
        print("⚠️  WHATSAPP_ENABLED = false (notificações desativadas)")
        return True
    
    import requests
    
    account_sid = os.getenv('TWILIO_ACCOUNT_SID')
    auth_token = os.getenv('TWILIO_AUTH_TOKEN')
    
    # Remove placeholders
    if 'x' in account_sid.lower() or 'x' in auth_token.lower():
        print("❌ TWILIO_ACCOUNT_SID ou TWILIO_AUTH_TOKEN ainda são placeholders")
        print("   Use suas credenciais reais de twilio.com")
        return False
    
    try:
        print(f"Testando API Twilio ({account_sid[:10]}...)...")
        
        url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
        
        # Testa autenticação (não envia mensagem)
        response = requests.get(
            f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}.json",
            auth=(account_sid, auth_token),
            timeout=10
        )
        
        if response.status_code == 200:
            print("✅ Autenticação Twilio bem-sucedida")
            return True
        elif response.status_code == 401:
            print("❌ Credenciais Twilio inválidas")
            return False
        else:
            print(f"❌ Erro Twilio: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao conectar Twilio: {e}")
        return False


def check_app_functions():
    """Verifica se as funções de notificação estão em app.py"""
    print("\n🔍 VERIFICAÇÃO 5: Funções de Notificação em app.py")
    print("-" * 60)
    
    try:
        with open('app.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        functions = [
            'enviar_notificacao_abertura_os',
            'enviar_notificacao_whatsapp_os',
        ]
        
        for func in functions:
            if f"def {func}" in content:
                print(f"✅ Função {func} encontrada")
            else:
                print(f"❌ Função {func} NÃO encontrada")
                return False
        
        return True
    except Exception as e:
        print(f"❌ Erro ao ler app.py: {e}")
        return False


def main():
    """Executa diagnóstico completo"""
    print("=" * 60)
    print("🔧 DIAGNÓSTICO DE NOTIFICAÇÕES")
    print("=" * 60)
    
    checks = [
        ("Arquivo .env", check_env_file),
        ("Variáveis de Ambiente", check_env_variables),
        ("Conexão Gmail", check_smtp_connection),
        ("Conexão Twilio", check_twilio_connection),
        ("Funções em app.py", check_app_functions),
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ Erro em {name}: {e}")
            results.append((name, False))
    
    # Resumo
    print("\n" + "=" * 60)
    print("📊 RESUMO")
    print("=" * 60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {name}")
    
    print(f"\n{passed}/{total} verificações passaram")
    
    if passed == total:
        print("\n✨ Tudo OK! Sistema pronto para enviar notificações.")
        print("\nPróximos passos:")
        print("1. Inicie o servidor: python app.py")
        print("2. Crie uma nova OS")
        print("3. Verifique email e WhatsApp")
        return 0
    else:
        print(f"\n⚠️  {total - passed} problema(s) encontrado(s)")
        print("Corrija os itens marcados com ❌ acima")
        return 1


if __name__ == "__main__":
    try:
        exit(main())
    except Exception as e:
        print(f"\n❌ Erro fatal: {e}")
        exit(1)
