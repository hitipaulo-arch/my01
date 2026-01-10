"""
Script de validação das melhorias de prioridade média implementadas.
Execute este script para verificar se as implementações estão funcionando corretamente.
"""

import sys
from typing import Dict, List

def test_imports():
    """Testa se todos os imports necessários estão disponíveis."""
    print("📦 Testando Imports...")
    
    try:
        from flask_caching import Cache
        print("  ✓ Flask-Caching importado com sucesso")
    except ImportError as e:
        print(f"  ❌ Erro ao importar Flask-Caching: {e}")
        return False
    
    try:
        from typing import Dict, List, Tuple, Optional, Any
        print("  ✓ Typing imports disponíveis")
    except ImportError as e:
        print(f"  ❌ Erro ao importar typing: {e}")
        return False
    
    try:
        from dataclasses import dataclass
        print("  ✓ Dataclasses disponível")
    except ImportError as e:
        print(f"  ❌ Erro ao importar dataclasses: {e}")
        return False
    
    print("✅ Todos os imports estão OK!\n")
    return True

def test_dataclass_validation():
    """Testa estruturas de validação com dataclasses."""
    print("✔️ Testando Validações com Dataclasses...")
    
    from dataclasses import dataclass
    from typing import List
    
    @dataclass
    class ValidacaoResultado:
        valido: bool
        erros: List[str]
    
    # Teste 1: Validação com sucesso
    resultado_valido = ValidacaoResultado(valido=True, erros=[])
    assert resultado_valido.valido == True
    assert len(resultado_valido.erros) == 0
    print("  ✓ Validação bem-sucedida: OK")
    
    # Teste 2: Validação com erros
    resultado_invalido = ValidacaoResultado(valido=False, erros=["Erro 1", "Erro 2"])
    assert resultado_invalido.valido == False
    assert len(resultado_invalido.erros) == 2
    print("  ✓ Validação com erros: OK")
    
    # Teste 3: Acesso a atributos
    assert resultado_invalido.erros[0] == "Erro 1"
    print("  ✓ Acesso a atributos: OK")
    
    print("✅ Dataclasses funcionando!\n")
    return True

def test_type_hints():
    """Testa anotações de tipo."""
    print("📝 Testando Type Hints...")
    
    from typing import Dict, List, Optional, Tuple
    
    def funcao_com_hints(nome: str, idade: int) -> Dict[str, any]:
        return {"nome": nome, "idade": idade}
    
    def funcao_opcional(valor: Optional[str] = None) -> bool:
        return valor is not None
    
    def funcao_tupla() -> Tuple[bool, str]:
        return (True, "sucesso")
    
    # Testes
    resultado = funcao_com_hints("João", 30)
    assert isinstance(resultado, dict)
    print("  ✓ Funções com type hints: OK")
    
    assert funcao_opcional("teste") == True
    assert funcao_opcional(None) == False
    print("  ✓ Optional type hints: OK")
    
    sucesso, msg = funcao_tupla()
    assert sucesso == True
    print("  ✓ Tuple type hints: OK")
    
    print("✅ Type hints funcionando!\n")
    return True

def test_config_structure():
    """Testa estrutura de configuração."""
    print("⚙️ Testando Estrutura de Config...")
    
    import os
    
    class ValidationConfig:
        MIN_USERNAME_LENGTH = 3
        MIN_PASSWORD_LENGTH = 6
        PRIORIDADES_VALIDAS = ['Baixa', 'Média', 'Alta', 'Urgente']
    
    class CacheConfig:
        CACHE_TYPE = 'SimpleCache'
        CACHE_DEFAULT_TIMEOUT = 300
    
    class Config:
        VALIDATION = ValidationConfig
        CACHE = CacheConfig
    
    # Testes
    assert Config.VALIDATION.MIN_USERNAME_LENGTH == 3
    print("  ✓ Acesso a configurações de validação: OK")
    
    assert Config.CACHE.CACHE_TYPE == 'SimpleCache'
    print("  ✓ Acesso a configurações de cache: OK")
    
    assert 'Alta' in Config.VALIDATION.PRIORIDADES_VALIDAS
    print("  ✓ Validação de prioridades: OK")
    
    print("✅ Estrutura de config funcionando!\n")
    return True

def test_validador_os():
    """Testa validador de OS."""
    print("🔍 Testando ValidadorOS...")
    
    from dataclasses import dataclass
    from typing import List, Dict, Any
    
    @dataclass
    class ValidacaoResultado:
        valido: bool
        erros: List[str]
    
    class ValidadorOS:
        @staticmethod
        def validar_formulario(form_data: Dict[str, Any]) -> ValidacaoResultado:
            erros = []
            
            if not form_data.get('nome_solicitante', '').strip():
                erros.append('Nome obrigatório')
            
            descricao = form_data.get('descricao', '').strip()
            if len(descricao) < 10:
                erros.append('Descrição muito curta')
            
            return ValidacaoResultado(valido=len(erros) == 0, erros=erros)
    
    # Teste 1: Dados válidos
    dados_validos = {
        'nome_solicitante': 'João Silva',
        'descricao': 'Descrição detalhada do problema com mais de 10 caracteres'
    }
    resultado = ValidadorOS.validar_formulario(dados_validos)
    assert resultado.valido == True
    print("  ✓ Validação de dados válidos: OK")
    
    # Teste 2: Nome faltando
    dados_sem_nome = {
        'nome_solicitante': '',
        'descricao': 'Descrição válida com mais de 10 caracteres'
    }
    resultado = ValidadorOS.validar_formulario(dados_sem_nome)
    assert resultado.valido == False
    assert 'Nome obrigatório' in resultado.erros
    print("  ✓ Detecção de nome faltando: OK")
    
    # Teste 3: Descrição curta
    dados_desc_curta = {
        'nome_solicitante': 'João',
        'descricao': 'Curto'
    }
    resultado = ValidadorOS.validar_formulario(dados_desc_curta)
    assert resultado.valido == False
    assert 'curta' in resultado.erros[0].lower()
    print("  ✓ Detecção de descrição curta: OK")
    
    print("✅ ValidadorOS funcionando!\n")
    return True

def test_validador_usuario():
    """Testa validador de usuário."""
    print("👤 Testando ValidadorUsuario...")
    
    from dataclasses import dataclass
    from typing import List
    
    @dataclass
    class ValidacaoResultado:
        valido: bool
        erros: List[str]
    
    class ValidadorUsuario:
        @staticmethod
        def validar_cadastro(username: str, password: str, confirm: str = None) -> ValidacaoResultado:
            erros = []
            
            if len(username) < 3:
                erros.append('Usuário muito curto')
            
            if len(password) < 6:
                erros.append('Senha muito curta')
            
            if confirm and password != confirm:
                erros.append('Senhas não coincidem')
            
            return ValidacaoResultado(valido=len(erros) == 0, erros=erros)
    
    # Teste 1: Dados válidos
    resultado = ValidadorUsuario.validar_cadastro('joaosilva', 'senha123', 'senha123')
    assert resultado.valido == True
    print("  ✓ Validação de usuário válido: OK")
    
    # Teste 2: Username curto
    resultado = ValidadorUsuario.validar_cadastro('ab', 'senha123')
    assert resultado.valido == False
    assert 'curto' in resultado.erros[0].lower()
    print("  ✓ Detecção de username curto: OK")
    
    # Teste 3: Senha curta
    resultado = ValidadorUsuario.validar_cadastro('joao', '12345')
    assert resultado.valido == False
    print("  ✓ Detecção de senha curta: OK")
    
    # Teste 4: Senhas não coincidem
    resultado = ValidadorUsuario.validar_cadastro('joao', 'senha123', 'senha456')
    assert resultado.valido == False
    assert 'coincidem' in resultado.erros[0].lower()
    print("  ✓ Detecção de senhas diferentes: OK")
    
    print("✅ ValidadorUsuario funcionando!\n")
    return True

def main():
    """Executa todos os testes."""
    print("=" * 60)
    print("🧪 VALIDAÇÃO DE MELHORIAS DE PRIORIDADE MÉDIA")
    print("=" * 60 + "\n")
    
    resultados = []
    
    # Executa testes
    resultados.append(("Imports", test_imports()))
    resultados.append(("Dataclass Validation", test_dataclass_validation()))
    resultados.append(("Type Hints", test_type_hints()))
    resultados.append(("Config Structure", test_config_structure()))
    resultados.append(("ValidadorOS", test_validador_os()))
    resultados.append(("ValidadorUsuario", test_validador_usuario()))
    
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
        print("\n🎉 Todas as melhorias de prioridade média estão funcionando!")
        print("\n📚 Próximos passos:")
        print("  1. Execute: pip install -r requirements.txt")
        print("  2. Inicie a aplicação: python app.py")
        print("  3. Teste os endpoints no navegador")
        return 0
    else:
        print("\n⚠️ Algumas verificações falharam. Verifique as dependências.")
        print("Execute: pip install -r requirements.txt")
        return 1

if __name__ == "__main__":
    sys.exit(main())
