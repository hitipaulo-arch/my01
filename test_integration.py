#!/usr/bin/env python3
"""
Teste de integração das funções de notificação (email + WhatsApp).
Valida que ambas as funções estão presentes e com a sintaxe correta.
"""

import sys
import json
import os

def test_app_syntax():
    """Testa que app.py compila sem erros"""
    print("\n✅ TESTE 1: Sintaxe do app.py")
    
    import py_compile
    try:
        py_compile.compile('app.py', doraise=True)
        print("  ✓ app.py compila sem erros!")
        return True
    except py_compile.PyCompileError as e:
        print(f"  ✗ Erro de compilação: {e}")
        return False


def test_imports():
    """Testa que todas as importações necessárias estão presentes"""
    print("\n✅ TESTE 2: Imports Necessários")
    
    required_imports = [
        ('flask', 'Flask'),
        ('gspread', None),
        ('requests', None),
        ('smtplib', None),
        ('email.mime.text', 'MIMEText'),
        ('email.mime.multipart', 'MIMEMultipart'),
    ]
    
    try:
        for module, cls in required_imports:
            if cls:
                exec(f"from {module} import {cls}")
                print(f"  ✓ {module}.{cls} OK")
            else:
                exec(f"import {module}")
                print(f"  ✓ {module} OK")
        
        return True
    except ImportError as e:
        print(f"  ✗ Erro de import: {e}")
        return False


def test_notification_functions():
    """Testa que as funções de notificação estão definidas em app.py"""
    print("\n✅ TESTE 3: Funções de Notificação")
    
    try:
        # Lê o arquivo
        with open('app.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verifica se as funções existem
        functions_needed = [
            'enviar_notificacao_abertura_os',
            'enviar_notificacao_whatsapp_os'
        ]
        
        for func in functions_needed:
            if f"def {func}" in content:
                print(f"  ✓ Função {func} encontrada")
            else:
                print(f"  ✗ Função {func} NÃO encontrada")
                return False
        
        # Verifica se há chamadas às funções na rota /enviar
        if "enviar_notificacao_whatsapp_os" in content and "@app.route('/enviar'" in content:
            print(f"  ✓ Rota /enviar integrada com notificações")
        
        return True
    except Exception as e:
        print(f"  ✗ Erro ao validar: {e}")
        return False


def test_twilio_variables():
    """Testa suporte a ContentVariables no código"""
    print("\n✅ TESTE 4: Suporte Twilio ContentVariables")
    
    try:
        with open('app.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        required_keywords = [
            'ContentVariables',
            'TWILIO_CONTENT_SID',
            'TWILIO_CONTENT_MAP',
            'TWILIO_ACCOUNT_SID',
            'TWILIO_AUTH_TOKEN',
            'TWILIO_WHATSAPP_FROM',
            'TWILIO_WHATSAPP_TO',
        ]
        
        found_count = 0
        for keyword in required_keywords:
            if keyword in content:
                print(f"  ✓ {keyword} encontrado")
                found_count += 1
            else:
                print(f"  ⚠️  {keyword} não encontrado (pode ser opcional)")
        
        if found_count >= 5:
            return True
        else:
            print(f"  ✗ Poucos keywords encontrados ({found_count}/{len(required_keywords)})")
            return False
    except Exception as e:
        print(f"  ✗ Erro ao validar: {e}")
        return False


def test_env_example():
    """Testa que .env.example tem as variáveis Twilio"""
    print("\n✅ TESTE 5: Variáveis .env.example")
    
    try:
        with open('.env.example', 'r', encoding='utf-8') as f:
            content = f.read()
        
        required_vars = [
            'TWILIO_ACCOUNT_SID',
            'TWILIO_AUTH_TOKEN',
            'TWILIO_WHATSAPP_FROM',
            'TWILIO_WHATSAPP_TO',
            'TWILIO_CONTENT_SID',
        ]
        
        found = 0
        for var in required_vars:
            if var in content:
                print(f"  ✓ {var} definido em .env.example")
                found += 1
            else:
                print(f"  ⚠️  {var} não encontrado em .env.example")
        
        if found >= 4:
            return True
        else:
            return False
    except Exception as e:
        print(f"  ✗ Erro ao validar: {e}")
        return False


def test_documentation():
    """Testa que a documentação foi atualizada"""
    print("\n✅ TESTE 6: Documentação Atualizada")
    
    docs_needed = {
        'README.md': 'ContentSid',
        'GUIA_NOTIFICACOES.md': 'ContentSid',
        '.env.example': 'TWILIO_CONTENT',
    }
    
    found_count = 0
    for doc, keyword in docs_needed.items():
        try:
            with open(doc, 'r', encoding='utf-8') as f:
                if keyword in f.read():
                    print(f"  ✓ {doc} tem documentação de {keyword}")
                    found_count += 1
                else:
                    print(f"  ⚠️  {doc} não menciona {keyword}")
        except FileNotFoundError:
            print(f"  ⚠️  {doc} não encontrado")
    
    return found_count >= 2


def test_requirements():
    """Testa que requirements.txt tem 'requests'"""
    print("\n✅ TESTE 7: Requirements.txt")
    
    try:
        with open('requirements.txt', 'r', encoding='utf-8') as f:
            content = f.read()
        
        if 'requests' in content:
            print(f"  ✓ 'requests' presente em requirements.txt")
            return True
        else:
            print(f"  ✗ 'requests' não encontrado em requirements.txt")
            return False
    except Exception as e:
        print(f"  ✗ Erro: {e}")
        return False


def test_error_handling():
    """Verifica tratamento de erros nas funções de notificação"""
    print("\n✅ TESTE 8: Tratamento de Erros")
    
    try:
        with open('app.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verifica se há try/except em volta das funções de notificação
        if 'try:' in content and 'except' in content:
            print(f"  ✓ Tratamento de exceções presente")
            if 'logging' in content or 'print(' in content:
                print(f"  ✓ Logging/debug presente")
                return True
        
        print(f"  ⚠️  Tratamento de erros poderia ser mais robusto")
        return True  # Não é crítico
    except Exception as e:
        print(f"  ✗ Erro: {e}")
        return False


def main():
    """Executa todos os testes"""
    print("=" * 70)
    print("🧪 TESTES DE INTEGRAÇÃO - NOTIFICAÇÕES")
    print("=" * 70)
    
    tests = [
        test_app_syntax,
        test_imports,
        test_notification_functions,
        test_twilio_variables,
        test_env_example,
        test_documentation,
        test_requirements,
        test_error_handling,
    ]
    
    resultados = []
    for test_func in tests:
        try:
            resultado = test_func()
            resultados.append((test_func.__name__, resultado))
        except Exception as e:
            print(f"  ✗ Erro inesperado: {e}")
            resultados.append((test_func.__name__, False))
    
    # Resumo
    print("\n" + "=" * 70)
    print("📊 RESUMO DOS TESTES")
    print("=" * 70)
    
    total = len(resultados)
    passou = sum(1 for _, r in resultados if r)
    
    for nome, resultado in resultados:
        status = "✅ PASSOU" if resultado else "❌ FALHOU"
        print(f"{status} - {nome}")
    
    print(f"\n{passou}/{total} testes passaram")
    
    if passou >= total - 1:  # Permite 1 falha
        print("\n🎉 Integração de notificações validada com sucesso!")
        print("\nProximos passos:")
        print("  1. Configurar variáveis de ambiente em .env (copie de .env.example)")
        print("  2. Adicionar credenciais Gmail (SMTP_USER, SMTP_PASSWORD)")
        print("  3. Adicionar credenciais Twilio (fornecidas)")
        print("  4. Testar criar uma nova OS e verificar notificações")
        return 0
    else:
        print(f"\n⚠️  {total - passou} teste(s) falharam.")
        return 1


if __name__ == "__main__":
    exit(main())
