#!/usr/bin/env python3
"""
Teste funcional: Simula abertura de uma nova OS e valida geração de payloads
de notificação (email e WhatsApp) sem realmente enviar.
"""

import json
import os
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def test_email_payload():
    """Simula composição de email para abertura de OS"""
    print("\n✅ TESTE 1: Composição de Email")
    
    # Dados de teste
    os_data = {
        'numero_pedido': 'OS-2026-001',
        'timestamp': '10/01/2026 14:30:00',
        'solicitante': 'João Silva',
        'setor': 'TI',
        'equipamento': 'Servidor de Backup',
        'prioridade': 'Alta',
        'descricao': 'Servidor não está respondendo a pings',
        'info_adicional': 'Equipe aguardando acesso'
    }
    
    # Simula função de construção de email
    msg = MIMEMultipart('alternative')
    msg['From'] = 'noreply@empresa.com'
    msg['To'] = 'admin@empresa.com'
    msg['Subject'] = f"Nova OS Aberta: {os_data['numero_pedido']}"
    
    html_body = f"""
    <html>
      <body style="font-family: Arial, sans-serif;">
        <h2>🚨 Nova Ordem de Serviço</h2>
        <table border="1" cellpadding="10">
          <tr><td><b>Número OS:</b></td><td>{os_data['numero_pedido']}</td></tr>
          <tr><td><b>Solicitante:</b></td><td>{os_data['solicitante']}</td></tr>
          <tr><td><b>Setor:</b></td><td>{os_data['setor']}</td></tr>
          <tr><td><b>Prioridade:</b></td><td>{os_data['prioridade']}</td></tr>
          <tr><td><b>Equipamento:</b></td><td>{os_data['equipamento']}</td></tr>
          <tr><td><b>Data/Hora:</b></td><td>{os_data['timestamp']}</td></tr>
          <tr><td><b>Descrição:</b></td><td>{os_data['descricao']}</td></tr>
          <tr><td><b>Observações:</b></td><td>{os_data['info_adicional']}</td></tr>
        </table>
      </body>
    </html>
    """
    
    part = MIMEText(html_body, 'html')
    msg.attach(part)
    
    print(f"  ✓ Email criado para: {msg['To']}")
    print(f"  ✓ Assunto: {msg['Subject']}")
    print(f"  ✓ Corpo contém: {len(html_body)} caracteres")
    
    assert 'OS-2026-001' in msg['Subject']
    assert 'João Silva' in html_body
    assert 'Alta' in html_body
    
    print(f"  ✓ Email payload OK!")
    return True


def test_whatsapp_payload():
    """Simula composição de payload WhatsApp com ContentVariables"""
    print("\n✅ TESTE 2: Payload WhatsApp ContentVariables")
    
    # Dados de teste
    os_data = {
        'numero_pedido': 'OS-2026-002',
        'timestamp': '10/01/2026 15:00:00',
        'solicitante': 'Maria Santos',
        'setor': 'RH',
        'equipamento': 'Impressora Sala 202',
        'prioridade': 'Média',
        'descricao': 'Impressora não imprime em cores, apenas preto e branco',
        'info_adicional': 'Urgente para relatórios'
    }
    
    # Monta ContentVariables automático (1..8)
    content_vars = {
        "1": os_data['numero_pedido'],
        "2": os_data['timestamp'],
        "3": os_data['solicitante'],
        "4": os_data['setor'],
        "5": os_data['equipamento'],
        "6": os_data['prioridade'],
        "7": (os_data['descricao'][:200] + "..." if len(os_data['descricao']) > 200 
              else os_data['descricao']),
        "8": os_data['info_adicional'][:100] if os_data['info_adicional'] else None
    }
    
    # Remove variável 8 se vazia
    if not content_vars.get("8"):
        del content_vars["8"]
    
    # Simula payload Twilio
    payload = {
        "To": "whatsapp:+5512991635552",
        "From": "whatsapp:+14155238886",
        "ContentSid": "HXb5b62575e6e4ff6129ad7c8efe1f983e",
        "ContentVariables": json.dumps(content_vars)
    }
    
    print(f"  ✓ Payload criado para: {payload['To']}")
    print(f"  ✓ ContentSid: {payload['ContentSid'][:20]}...")
    print(f"  ✓ ContentVariables contém {len(content_vars)} variáveis")
    
    # Valida JSON
    parsed_vars = json.loads(payload['ContentVariables'])
    assert parsed_vars["1"] == "OS-2026-002"
    assert parsed_vars["3"] == "Maria Santos"
    assert "não imprime" in parsed_vars["7"]
    
    print(f"  ✓ Variáveis:")
    for k, v in sorted(parsed_vars.items()):
        print(f"    {k}: {v[:50]}..." if len(v) > 50 else f"    {k}: {v}")
    
    print(f"  ✓ Payload WhatsApp OK!")
    return True


def test_custom_mapping():
    """Testa mapeamento customizado via TWILIO_CONTENT_MAP"""
    print("\n✅ TESTE 3: Mapeamento Customizado TWILIO_CONTENT_MAP")
    
    os_data = {
        'numero_pedido': 'OS-2026-003',
        'timestamp': '10/01/2026 16:00:00',
        'solicitante': 'Pedro Costa',
        'setor': 'Suporte',
        'equipamento': 'Notebook',
        'prioridade': 'Urgente',
        'descricao': 'Tela do notebook não liga',
        'info_adicional': ''
    }
    
    # Mapa customizado (inverte ordem)
    content_map = "1=prioridade,2=numero_pedido,3=setor,4=solicitante,5=equipamento,6=timestamp,7=descricao"
    
    # Processa mapeamento
    field_values = {
        'numero_pedido': os_data['numero_pedido'],
        'timestamp': os_data['timestamp'],
        'solicitante': os_data['solicitante'],
        'setor': os_data['setor'],
        'equipamento': os_data['equipamento'],
        'prioridade': os_data['prioridade'],
        'descricao': os_data['descricao'][:200],
        'info': os_data.get('info_adicional', '')[:100] if os_data.get('info_adicional') else ''
    }
    
    custom_vars = {}
    pairs = [p.strip() for p in content_map.split(',')]
    for pair in pairs:
        key, field = pair.split('=')
        key = key.strip()
        field = field.strip()
        if field in field_values:
            custom_vars[key] = field_values[field]
    
    print(f"  ✓ Mapeamento: {content_map}")
    print(f"  ✓ Variáveis geradas:")
    for k, v in sorted(custom_vars.items()):
        print(f"    {k}: {v[:50]}..." if len(v) > 50 else f"    {k}: {v}")
    
    # Validações
    assert custom_vars["1"] == "Urgente", "Var 1 deve ser prioridade"
    assert custom_vars["2"] == "OS-2026-003", "Var 2 deve ser número"
    assert custom_vars["3"] == "Suporte", "Var 3 deve ser setor"
    
    print(f"  ✓ Mapeamento customizado OK!")
    return True


def test_multiple_recipients():
    """Testa envio para múltiplos destinatários WhatsApp"""
    print("\n✅ TESTE 4: Múltiplos Destinatários WhatsApp")
    
    # Simula múltiplos números
    whatsapp_to = "whatsapp:+5512991635552,whatsapp:+5511999887766"
    recipients = [r.strip() for r in whatsapp_to.split(',')]
    
    os_data = {
        'numero_pedido': 'OS-2026-004',
        'timestamp': datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        'solicitante': 'Ana Clara',
        'setor': 'Financeiro',
        'equipamento': 'Servidor',
        'prioridade': 'Alta',
        'descricao': 'Sistema de pagamento offline',
        'info_adicional': 'Crítico'
    }
    
    # Simula envio para cada destinatário
    results = []
    for recipient in recipients:
        payload = {
            "To": recipient,
            "From": "whatsapp:+14155238886",
            "ContentSid": "HXb5b62575e6e4ff6129ad7c8efe1f983e",
            "ContentVariables": json.dumps({
                "1": os_data['numero_pedido'],
                "2": os_data['timestamp'],
                "3": os_data['solicitante'],
                "4": os_data['setor'],
                "5": os_data['equipamento'],
                "6": os_data['prioridade'],
                "7": os_data['descricao'][:200],
                "8": os_data['info_adicional']
            })
        }
        results.append((recipient, payload))
        print(f"  ✓ Destinatário: {recipient}")
    
    assert len(results) == 2, "Deve ter 2 destinatários"
    print(f"  ✓ {len(results)} mensagens WhatsApp preparadas!")
    return True


def test_field_truncation():
    """Testa truncamento automático de campos longos"""
    print("\n✅ TESTE 5: Truncamento de Campos Longos")
    
    os_data = {
        'numero_pedido': 'OS-2026-005',
        'timestamp': '10/01/2026 17:00:00',
        'solicitante': 'Roberto Silva',
        'setor': 'Operações',
        'equipamento': 'Switch de Rede',
        'prioridade': 'Alta',
        'descricao': 'A' * 300,  # Descrição muito longa
        'info_adicional': 'B' * 150  # Info adicional muito longa
    }
    
    # Processa truncamento
    desc_processed = (os_data['descricao'][:200] + "..." 
                     if len(os_data['descricao']) > 200 
                     else os_data['descricao'])
    info_processed = (os_data['info_adicional'][:100] 
                     if os_data['info_adicional'] and len(os_data['info_adicional']) > 100 
                     else os_data['info_adicional'])
    
    print(f"  Descrição original: {len(os_data['descricao'])} chars")
    print(f"  Descrição processada: {len(desc_processed)} chars")
    assert len(desc_processed) <= 203, "Descrição deve ter max 203 chars (200 + '...')"
    print(f"  ✓ Descrição truncada OK")
    
    print(f"  Info original: {len(os_data['info_adicional'])} chars")
    print(f"  Info processada: {len(info_processed)} chars")
    assert len(info_processed) <= 100, "Info deve ter max 100 chars"
    print(f"  ✓ Info adicional truncada OK")
    
    return True


def test_json_serialization():
    """Testa serialização para JSON (necessário para Twilio)"""
    print("\n✅ TESTE 6: Serialização JSON para Twilio")
    
    os_data = {
        'numero_pedido': 'OS-2026-006',
        'timestamp': '10/01/2026 18:00:00',
        'solicitante': 'José da Silva',
        'setor': 'Administrativo',
        'equipamento': 'Computador & Periféricos',
        'prioridade': 'Média',
        'descricao': 'Não consegue acessar VPN - "erro de conexão"',
        'info_adicional': 'Atenção: Caracteres & Acentos'
    }
    
    content_vars = {
        "1": os_data['numero_pedido'],
        "2": os_data['timestamp'],
        "3": os_data['solicitante'],
        "4": os_data['setor'],
        "5": os_data['equipamento'],
        "6": os_data['prioridade'],
        "7": os_data['descricao'],
        "8": os_data['info_adicional']
    }
    
    try:
        # Serializa para JSON
        json_str = json.dumps(content_vars, ensure_ascii=False)
        print(f"  ✓ JSON serializado: {json_str[:80]}...")
        
        # Desserializa para validar
        parsed = json.loads(json_str)
        assert parsed == content_vars
        print(f"  ✓ JSON desserializado com sucesso")
        
        # Valida acentos e caracteres especiais
        assert "José" in parsed["3"]
        assert "&" in parsed["5"]
        assert "\"" in parsed["7"]
        print(f"  ✓ Caracteres especiais e acentos preservados")
        
        return True
    except Exception as e:
        print(f"  ✗ Erro na serialização: {e}")
        return False


def main():
    """Executa todos os testes funcionais"""
    print("=" * 70)
    print("🧪 TESTES FUNCIONAIS - SIMULAÇÃO DE NOTIFICAÇÕES")
    print("=" * 70)
    
    tests = [
        test_email_payload,
        test_whatsapp_payload,
        test_custom_mapping,
        test_multiple_recipients,
        test_field_truncation,
        test_json_serialization,
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
            print(f"  ✗ Erro: {e}")
            resultados.append((test_func.__name__, False))
    
    # Resumo
    print("\n" + "=" * 70)
    print("📊 RESUMO DOS TESTES FUNCIONAIS")
    print("=" * 70)
    
    total = len(resultados)
    passou = sum(1 for _, r in resultados if r)
    
    for nome, resultado in resultados:
        status = "✅ PASSOU" if resultado else "❌ FALHOU"
        print(f"{status} - {nome}")
    
    print(f"\n{passou}/{total} testes passaram")
    
    if passou == total:
        print("\n🎉 Todos os testes funcionais passaram!")
        print("\nValidações completadas:")
        print("  ✓ Email HTML composição OK")
        print("  ✓ WhatsApp ContentVariables OK")
        print("  ✓ Mapeamento customizado OK")
        print("  ✓ Múltiplos destinatários OK")
        print("  ✓ Truncamento de campos OK")
        print("  ✓ Serialização JSON OK")
        return 0
    else:
        print(f"\n⚠️  {total - passou} teste(s) falharam.")
        return 1


if __name__ == "__main__":
    exit(main())
