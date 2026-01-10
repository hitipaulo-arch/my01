#!/usr/bin/env python3
"""
Teste de mapeamento automático de ContentVariables para templates Twilio.
Valida que as variáveis são montadas corretamente a partir dos dados da OS.
"""

import json
import os
from datetime import datetime

# Simular função de mapeamento (extraído do app.py)
def build_content_variables(
    numero_pedido: str,
    timestamp: str,
    solicitante: str,
    setor: str,
    equipamento: str,
    prioridade: str,
    descricao: str,
    info_adicional: str = '',
    content_map: str = ''
) -> dict:
    """
    Monta ContentVariables para template Twilio.
    
    Args:
        numero_pedido: Número da OS
        timestamp: Data/hora de criação
        solicitante: Nome do solicitante
        setor: Setor
        equipamento: Equipamento/local
        prioridade: Prioridade
        descricao: Descrição
        info_adicional: Info adicional (opcional)
        content_map: Mapeamento customizado (ex: "1=numero_pedido,2=prioridade")
    
    Returns:
        Dict com as variáveis mapeadas
    """
    
    # Prepara os valores dos campos
    field_values = {
        'numero_pedido': str(numero_pedido or ''),
        'timestamp': str(timestamp or ''),
        'solicitante': str(solicitante or ''),
        'setor': str(setor or ''),
        'equipamento': str(equipamento or ''),
        'prioridade': str(prioridade or ''),
        'descricao': (str(descricao or '')[:200] + ("..." if len(str(descricao or '')) > 200 else '')),
        'info': (info_adicional.strip()[:100] if info_adicional and info_adicional.strip() else '')
    }

    auto_vars = {}
    
    if content_map:
        # Usa mapeamento customizado
        pairs = [p.strip() for p in content_map.split(',') if p.strip()]
        for pair in pairs:
            try:
                key, field = [x.strip() for x in pair.split('=', 1)]
                if key and field and field in field_values:
                    auto_vars[str(key)] = field_values[field]
            except Exception:
                continue
    else:
        # Usa mapeamento padrão 1..8
        auto_vars = {
            "1": field_values['numero_pedido'],
            "2": field_values['timestamp'],
            "3": field_values['solicitante'],
            "4": field_values['setor'],
            "5": field_values['equipamento'],
            "6": field_values['prioridade'],
            "7": field_values['descricao']
        }
        # Só adiciona 8 se houver conteúdo
        if field_values['info']:
            auto_vars["8"] = field_values['info']
    
    return auto_vars


# ==================== TESTES ====================

def test_mapeamento_padrao():
    """Testa mapeamento padrão 1..8"""
    print("\n✅ TESTE 1: Mapeamento Padrão (1..8)")
    
    vars = build_content_variables(
        numero_pedido="123",
        timestamp="10/01/2026 14:30:00",
        solicitante="João Silva",
        setor="TI",
        equipamento="Notebook sala 201",
        prioridade="Alta",
        descricao="Notebook não liga, suspeita de problema na fonte",
        info_adicional="Urgente para apresentação"
    )
    
    print(f"  Variáveis geradas:")
    for k, v in sorted(vars.items()):
        print(f"    {k}: {v[:50]}..." if len(v) > 50 else f"    {k}: {v}")
    
    # Validações
    assert vars["1"] == "123", "Variável 1 deve ser número da OS"
    assert "2026" in vars["2"], "Variável 2 deve conter timestamp"
    assert vars["3"] == "João Silva", "Variável 3 deve ser solicitante"
    assert vars["4"] == "TI", "Variável 4 deve ser setor"
    assert "Notebook" in vars["5"], "Variável 5 deve ser equipamento"
    assert vars["6"] == "Alta", "Variável 6 deve ser prioridade"
    assert "Notebook não liga" in vars["7"], "Variável 7 deve ser descrição"
    assert vars["8"] == "Urgente para apresentação", "Variável 8 deve ser info adicional"
    
    print("  ✓ Mapeamento padrão OK!")
    return True


def test_sem_info_adicional():
    """Testa que variável 8 não aparece se info_adicional vazio"""
    print("\n✅ TESTE 2: Sem Info Adicional (variável 8 ausente)")
    
    vars = build_content_variables(
        numero_pedido="124",
        timestamp="10/01/2026 15:00:00",
        solicitante="Maria Santos",
        setor="RH",
        equipamento="Impressora",
        prioridade="Média",
        descricao="Impressora não imprime",
        info_adicional=""  # Vazio!
    )
    
    print(f"  Variáveis geradas: {sorted(vars.keys())}")
    
    assert "8" not in vars, "Variável 8 não deve existir quando info_adicional vazio"
    assert len(vars) == 7, "Devem existir apenas 7 variáveis"
    
    print("  ✓ Info adicional opcional OK!")
    return True


def test_descricao_truncada():
    """Testa truncamento de descrição > 200 chars"""
    print("\n✅ TESTE 3: Descrição Truncada (>200 caracteres)")
    
    descricao_longa = "A" * 250
    vars = build_content_variables(
        numero_pedido="125",
        timestamp="10/01/2026 15:30:00",
        solicitante="Pedro Costa",
        setor="Suporte",
        equipamento="Servidor",
        prioridade="Urgente",
        descricao=descricao_longa,
        info_adicional=""
    )
    
    print(f"  Descrição original: {len(descricao_longa)} chars")
    print(f"  Descrição truncada: {len(vars['7'])} chars")
    
    assert len(vars["7"]) == 203, "Descrição deve ter 200 chars + '...'"
    assert vars["7"].endswith("..."), "Descrição longa deve terminar com '...'"
    
    print("  ✓ Truncamento OK!")
    return True


def test_mapeamento_customizado():
    """Testa TWILIO_CONTENT_MAP customizado"""
    print("\n✅ TESTE 4: Mapeamento Customizado (TWILIO_CONTENT_MAP)")
    
    # Inverte ordem: 1=prioridade, 2=numero_pedido, 3=solicitante
    vars = build_content_variables(
        numero_pedido="126",
        timestamp="10/01/2026 16:00:00",
        solicitante="Ana Clara",
        setor="Financeiro",
        equipamento="Monitor",
        prioridade="Baixa",
        descricao="Monitor piscando",
        info_adicional="Não urgente",
        content_map="1=prioridade,2=numero_pedido,3=solicitante,4=setor,5=equipamento,6=timestamp,7=descricao,8=info"
    )
    
    print(f"  Mapeamento: 1=prioridade, 2=numero_pedido, 3=solicitante, etc.")
    print(f"  Resultado:")
    for k, v in sorted(vars.items()):
        print(f"    {k}: {v[:50]}..." if len(v) > 50 else f"    {k}: {v}")
    
    assert vars["1"] == "Baixa", "Variável 1 deve ser prioridade"
    assert vars["2"] == "126", "Variável 2 deve ser número da OS"
    assert vars["3"] == "Ana Clara", "Variável 3 deve ser solicitante"
    assert vars["4"] == "Financeiro", "Variável 4 deve ser setor"
    
    print("  ✓ Mapeamento customizado OK!")
    return True


def test_json_serializable():
    """Testa que resultado é JSON serializável"""
    print("\n✅ TESTE 5: JSON Serializável")
    
    vars = build_content_variables(
        numero_pedido="127",
        timestamp="10/01/2026 16:30:00",
        solicitante="Roberto",
        setor="Operações",
        equipamento="Ar condicionado",
        prioridade="Média",
        descricao="Ar condicionado da sala não funciona",
        info_adicional="Muito quente"
    )
    
    # Tenta serializar para JSON
    try:
        json_str = json.dumps(vars, ensure_ascii=False)
        print(f"  JSON gerado: {json_str[:80]}...")
        
        # Tenta desserializar
        parsed = json.loads(json_str)
        assert parsed == vars, "JSON deve ser reversível"
        
        print("  ✓ JSON Serializável OK!")
        return True
    except Exception as e:
        print(f"  ✗ Erro ao serializar JSON: {e}")
        return False


def test_campos_especiais():
    """Testa campos com caracteres especiais e Unicode"""
    print("\n✅ TESTE 6: Caracteres Especiais e Unicode")
    
    vars = build_content_variables(
        numero_pedido="128",
        timestamp="10/01/2026 17:00:00",
        solicitante="José da Silva",
        setor="Administrativo",
        equipamento="Computador/Desktop",
        prioridade="Alta",
        descricao="Não consegue acessar a rede (VPN) - \"erro conexão\"",
        info_adicional="Atenção: caracteres especiais & acentos"
    )
    
    print(f"  Solicitante com acento: {vars['3']}")
    print(f"  Descrição com caracteres especiais: {vars['7'][:60]}...")
    print(f"  Info com símbolos: {vars['8']}")
    
    assert "José" in vars["3"], "Acentos devem ser preservados"
    assert "&" in vars["8"], "Símbolos devem ser preservados"
    assert "\"" in vars["7"], "Aspas devem ser preservadas"
    
    print("  ✓ Caracteres especiais OK!")
    return True


def main():
    """Executa todos os testes"""
    print("=" * 70)
    print("🧪 TESTES DE MAPEAMENTO TWILIO CONTENT VARIABLES")
    print("=" * 70)
    
    tests = [
        test_mapeamento_padrao,
        test_sem_info_adicional,
        test_descricao_truncada,
        test_mapeamento_customizado,
        test_json_serializable,
        test_campos_especiais,
    ]
    
    resultados = []
    for test_func in tests:
        try:
            resultado = test_func()
            resultados.append((test_func.__name__, resultado))
        except AssertionError as e:
            print(f"  ✗ Falha: {e}")
            resultados.append((test_func.__name__, False))
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
    
    if passou == total:
        print("\n🎉 Todos os testes passaram! Mapeamento Twilio ContentVariables funcionando!")
        return 0
    else:
        print(f"\n⚠️  {total - passou} teste(s) falharam.")
        return 1


if __name__ == "__main__":
    exit(main())
