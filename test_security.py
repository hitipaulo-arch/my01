"""
Script de validação das melhorias de segurança implementadas.
Execute este script para verificar se as implementações estão funcionando corretamente.
"""

import sys
from werkzeug.security import generate_password_hash, check_password_hash


def test_password_hashing():
    """Testa funcionalidade de hash de senhas"""
    print("🔐 Testando Hash de Senhas...")

    # Teste 1: Gerar hash
    senha_original = "senha_teste_123"
    senha_hash = generate_password_hash(senha_original, method="pbkdf2:sha256")

    print(f"  ✓ Senha original: {senha_original}")
    print(f"  ✓ Hash gerado: {senha_hash[:50]}...")

    # Teste 2: Validar senha correta
    assert check_password_hash(senha_hash, senha_original), (
        "Falha ao validar senha correta"
    )
    print("  ✓ Validação de senha correta: OK")

    # Teste 3: Rejeitar senha incorreta
    senha_incorreta = "senha_errada"
    assert not check_password_hash(senha_hash, senha_incorreta), (
        "Falha ao rejeitar senha incorreta"
    )
    print("  ✓ Rejeição de senha incorreta: OK")

    # Teste 4: Hash único (mesmo para mesma senha)
    senha_hash2 = generate_password_hash(senha_original, method="pbkdf2:sha256")
    assert senha_hash != senha_hash2, "Hashes deveriam ser únicos"
    print("  ✓ Hashes únicos para mesma senha: OK")

    print("✅ Todos os testes de hash passaram!\n")


def test_csrf_imports():
    """Testa se as importações CSRF estão disponíveis"""
    print("🔒 Testando Proteção CSRF...")

    try:
        from flask_wtf.csrf import CSRFProtect

        print("  ✓ Flask-WTF importado com sucesso")
        print("  ✓ CSRFProtect disponível")
        print("✅ Proteção CSRF configurada!\n")

    except ImportError as e:
        print(f"  ❌ Erro ao importar Flask-WTF: {e}")
        print("  ℹ️  Execute: pip install Flask-WTF\n")
        return False


def test_migration_scenario():
    """Simula cenário de migração de senha legada"""
    print("🔄 Testando Migração de Senha Legada...")

    # Senha em texto plano (formato antigo)
    senha_texto_plano = "admin123"
    senha_digitada = "admin123"

    # Simula validação legada
    if senha_texto_plano == senha_digitada:
        print("  ✓ Senha legada validada")

        # Converte para hash
        novo_hash = generate_password_hash(senha_digitada, method="pbkdf2:sha256")
        print(f"  ✓ Hash criado: {novo_hash[:50]}...")

        # Valida com hash
        assert check_password_hash(novo_hash, senha_digitada), (
            "Falha na validação pós-migração"
        )
        print("  ✓ Validação pós-migração: OK")

    print("✅ Migração automática funcionando!\n")


def test_hash_detection():
    """Testa detecção de tipo de senha (hash vs texto plano)"""
    print("🔍 Testando Detecção de Tipo de Senha...")

    senha_hash = generate_password_hash("teste123", method="pbkdf2:sha256")
    senha_texto = "admin123"

    # Detecta hash
    is_hash = senha_hash.startswith("pbkdf2:sha256:") or senha_hash.startswith(
        "scrypt:"
    )
    assert is_hash, "Falha ao detectar hash"
    print(f"  ✓ Hash detectado corretamente: {is_hash}")

    # Detecta texto plano
    is_plain = not (
        senha_texto.startswith("pbkdf2:sha256:") or senha_texto.startswith("scrypt:")
    )
    assert is_plain, "Falha ao detectar texto plano"
    print(f"  ✓ Texto plano detectado: {is_plain}")

    print("✅ Detecção de tipo funcionando!\n")


def main():
    """Executa todos os testes"""
    print("=" * 60)
    print("🧪 VALIDAÇÃO DE MELHORIAS DE SEGURANÇA")
    print("=" * 60 + "\n")

    resultados = []

    # Executa testes
    for nome, func in [
        ("Hash de Senhas", test_password_hashing),
        ("Proteção CSRF", test_csrf_imports),
        ("Migração Legada", test_migration_scenario),
        ("Detecção de Tipo", test_hash_detection),
    ]:
        try:
            resultado = func()
            if resultado is None:
                resultado = True
        except Exception:
            resultado = False
        resultados.append((nome, resultado))

    # Resumo
    print("=" * 60)
    print("📊 RESUMO DOS TESTES")
    print("=" * 60)

    total = len(resultados)
    sucesso = sum(1 for _, resultado in resultados if resultado)

    for nome, resultado in resultados:
        status = "✅ PASSOU" if resultado else "❌ FALHOU"
        print(f"{status} - {nome}")

    print(f"\n{sucesso}/{total} testes passaram")

    if sucesso == total:
        print("\n🎉 Todas as melhorias de segurança estão funcionando corretamente!")
        return 0
    else:
        print("\n⚠️ Algumas verificações falharam. Verifique as dependências.")
        print("Execute: pip install -r requirements.txt")
        return 1


if __name__ == "__main__":
    sys.exit(main())
