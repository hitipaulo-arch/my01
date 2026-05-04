#!/usr/bin/env python3
"""
Testes para WhatsApp Webhook Service
"""

import json
from appmodules.services.whatsapp_webhook_service import WhatsAppWebhookService


def test_extrair_comando_status():
    """Testa extração de comando status"""
    print("\n✅ TESTE 1: Extrair Comando Status")
    
    service = WhatsAppWebhookService()
    
    testes = [
        ("status OS-2026-001", {"tipo": "status", "numero_os": "OS-2026-001"}),
        ("STATUS OS-2026-001", {"tipo": "status", "numero_os": "OS-2026-001"}),
        ("Status os-2026-001", {"tipo": "status", "numero_os": "OS-2026-001"}),
    ]
    
    for mensagem, esperado in testes:
        resultado = service.extrair_comando(mensagem)
        assert resultado == esperado, f"Falhou para '{mensagem}': {resultado} != {esperado}"
        print(f"  ✓ '{mensagem}' -> {resultado}")
    
    return True


def test_extrair_comando_concluir():
    """Testa extração de comando concluir"""
    print("\n✅ TESTE 2: Extrair Comando Concluir")
    
    service = WhatsAppWebhookService()
    
    testes = [
        ("concluir OS-2026-001", {"tipo": "concluir", "numero_os": "OS-2026-001"}),
        ("concluído OS-2026-001", {"tipo": "concluir", "numero_os": "OS-2026-001"}),
        ("done OS-2026-001", {"tipo": "concluir", "numero_os": "OS-2026-001"}),
        ("finalizar OS-2026-001", {"tipo": "concluir", "numero_os": "OS-2026-001"}),
    ]
    
    for mensagem, esperado in testes:
        resultado = service.extrair_comando(mensagem)
        assert resultado == esperado, f"Falhou para '{mensagem}': {resultado} != {esperado}"
        print(f"  ✓ '{mensagem}' -> {resultado}")
    
    return True


def test_extrair_comando_chegada():
    """Testa extração de comando chegada"""
    print("\n✅ TESTE 3: Extrair Comando Chegada")
    
    service = WhatsAppWebhookService()
    
    testes = [
        ("cheguei OS-2026-001", {"tipo": "chegada", "numero_os": "OS-2026-001"}),
        ("chegada OS-2026-001", {"tipo": "chegada", "numero_os": "OS-2026-001"}),
        ("arrived OS-2026-001", {"tipo": "chegada", "numero_os": "OS-2026-001"}),
    ]
    
    for mensagem, esperado in testes:
        resultado = service.extrair_comando(mensagem)
        assert resultado == esperado, f"Falhou para '{mensagem}': {resultado} != {esperado}"
        print(f"  ✓ '{mensagem}' -> {resultado}")
    
    return True


def test_extrair_comando_pausa():
    """Testa extração de comando pausa"""
    print("\n✅ TESTE 4: Extrair Comando Pausa")
    
    service = WhatsAppWebhookService()
    
    testes = [
        ("pausa OS-2026-001", {"tipo": "pausa", "numero_os": "OS-2026-001"}),
        ("pause OS-2026-001", {"tipo": "pausa", "numero_os": "OS-2026-001"}),
    ]
    
    for mensagem, esperado in testes:
        resultado = service.extrair_comando(mensagem)
        assert resultado == esperado, f"Falhou para '{mensagem}': {resultado} != {esperado}"
        print(f"  ✓ '{mensagem}' -> {resultado}")
    
    return True


def test_extrair_comando_ajuda():
    """Testa extração de comando ajuda"""
    print("\n✅ TESTE 5: Extrair Comando Ajuda")
    
    service = WhatsAppWebhookService()
    
    testes = [
        ("ajuda", {"tipo": "ajuda", "numero_os": None}),
        ("help", {"tipo": "ajuda", "numero_os": None}),
        ("?", {"tipo": "ajuda", "numero_os": None}),
    ]
    
    for mensagem, esperado in testes:
        resultado = service.extrair_comando(mensagem)
        assert resultado == esperado, f"Falhou para '{mensagem}': {resultado} != {esperado}"
        print(f"  ✓ '{mensagem}' -> {resultado}")
    
    return True


def test_extrair_numero_whatsapp():
    """Testa extração de número de WhatsApp"""
    print("\n✅ TESTE 6: Extrair Número WhatsApp")
    
    service = WhatsAppWebhookService()
    
    testes = [
        ("+55 12 98220-0009", "5512982200009"),
        ("55 12 98220-0009", "5512982200009"),
        ("12 98220-0009", "12982200009"),  # Sem DDD 55, apenas remove caracteres
        ("5512982200009", "5512982200009"),
        ("whatsapp:+5512982200009", "5512982200009"),
    ]
    
    for numero, esperado in testes:
        resultado = service.extrair_numero_whatsapp(numero)
        assert resultado == esperado, f"Falhou para '{numero}': {resultado} != {esperado}"
        print(f"  ✓ '{numero}' -> {resultado}")
    
    return True


def test_processar_mensagem_sem_comando():
    """Testa processamento de mensagem sem comando"""
    print("\n✅ TESTE 7: Processar Mensagem Sem Comando")
    
    service = WhatsAppWebhookService(whatsapp_phone=None)  # Permite todos
    
    resultado = service.processar_mensagem({
        'from': '5512982200009',
        'text': 'Olá tudo bem',  # Não contém palavras-chave de comando
        'timestamp': '2026-01-01T10:00:00'
    })
    
    assert resultado['sucesso'] == True, f"Falha no processamento: {resultado}"
    assert resultado['tipo'] == 'mensagem_livre', f"Tipo incorreto: {resultado.get('tipo')}"
    assert 'ajuda' in resultado['resposta'].lower(), f"Resposta não contém 'ajuda': {resultado['resposta']}"
    print(f"  ✓ Mensagem sem comando processada")
    print(f"  Resposta: {resultado['resposta'][:60]}...")
    
    return True


def test_processar_comando_status():
    """Testa processamento de comando status"""
    print("\n✅ TESTE 8: Processar Comando Status")
    
    service = WhatsAppWebhookService(whatsapp_phone=None)
    
    resultado = service.processar_mensagem({
        'from': '5512982200009',
        'text': 'status OS-2026-001',
        'timestamp': '2026-01-01T10:00:00'
    })
    
    assert resultado['tipo'] == 'status'
    assert resultado['numero_os'] == 'OS-2026-001'
    # Sem sheets service, retorna erro de OS não encontrada
    print(f"  ✓ Comando status processado")
    print(f"  Tipo: {resultado['tipo']}")
    print(f"  OS: {resultado.get('numero_os')}")
    
    return True


def test_validar_remetente_autorizado():
    """Testa validação de remetente autorizado"""
    print("\n✅ TESTE 9: Validar Remetente Autorizado")
    
    service = WhatsAppWebhookService(whatsapp_phone="+55 12 98220-0009")
    
    # Mesmo número em formatos diferentes
    assert service.validar_remetente("+5512982200009") == True
    assert service.validar_remetente("5512982200009") == True
    assert service.validar_remetente("+55 12 98220-0009") == True
    assert service.validar_remetente("12 98220-0009") == False  # Falta DDI
    
    print(f"  ✓ Validação de remetente funcionando")
    
    return True


def test_gerar_mensagem_ajuda():
    """Testa geração de mensagem de ajuda"""
    print("\n✅ TESTE 10: Gerar Mensagem Ajuda")
    
    service = WhatsAppWebhookService()
    
    ajuda = service._gerar_mensagem_ajuda()
    
    assert "status OS-123" in ajuda
    assert "concluir OS-123" in ajuda
    assert "cheguei OS-123" in ajuda
    assert "pausa OS-123" in ajuda
    
    print(f"  ✓ Mensagem de ajuda gerada com sucesso")
    print(f"  Primeiras 100 chars: {ajuda[:100]}...")
    
    return True


def main():
    """Executa todos os testes"""
    print("=" * 70)
    print("🧪 TESTES - WHATSAPP WEBHOOK SERVICE")
    print("=" * 70)
    
    testes = [
        test_extrair_comando_status,
        test_extrair_comando_concluir,
        test_extrair_comando_chegada,
        test_extrair_comando_pausa,
        test_extrair_comando_ajuda,
        test_extrair_numero_whatsapp,
        test_processar_mensagem_sem_comando,
        test_processar_comando_status,
        test_validar_remetente_autorizado,
        test_gerar_mensagem_ajuda,
    ]
    
    resultados = []
    for teste in testes:
        try:
            resultado = teste()
            resultados.append((teste.__name__, resultado))
        except Exception as e:
            print(f"  ✗ Erro: {e}")
            resultados.append((teste.__name__, False))
    
    # Resumo
    print("\n" + "=" * 70)
    print("📊 RESUMO")
    print("=" * 70)
    
    total = len(resultados)
    passou = sum(1 for _, r in resultados if r)
    
    for nome, resultado in resultados:
        status = "✅" if resultado else "❌"
        print(f"{status} {nome}")
    
    print(f"\n{passou}/{total} testes passaram")
    
    if passou == total:
        print("\n🎉 Todos os testes passaram!")
        return 0
    else:
        print(f"\n⚠️ {total - passou} teste(s) falharam")
        return 1


if __name__ == "__main__":
    exit(main())
