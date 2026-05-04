# 📱 Guia de Webhook WhatsApp - Recebimento de Mensagens

## 📌 Visão Geral

O sistema agora suporta **receber mensagens via WhatsApp** para permitir que técnicos enviem atualizações de status das OS diretamente pelo WhatsApp.

**Exemplos de comandos que técnicos podem enviar:**
- `status OS-2026-001` - Verificar status da OS
- `cheguei OS-2026-001` - Indicar que chegou no local
- `concluído OS-2026-001` - Marcar OS como concluída
- `pausa OS-2026-001` - Pausar OS
- `ajuda` - Ver lista de comandos

## ⚙️ Configuração

### 1. Variáveis de Ambiente

Adicione ao seu `.env`:

```env
# Webhook WhatsApp
WHATSAPP_WEBHOOK_ENABLED=true
WHATSAPP_WEBHOOK_TOKEN=seu_token_muito_seguro_aqui
WHATSAPP_WEBHOOK_FROM=5512982200009  # Número do técnico autorizado
```

**Explicação:**
- `WHATSAPP_WEBHOOK_ENABLED`: Habilita o webhook (true/false)
- `WHATSAPP_WEBHOOK_TOKEN`: Token de segurança (use algo aleatório forte)
- `WHATSAPP_WEBHOOK_FROM`: Número do WhatsApp autorizado a enviar (apenas este receberá comandos)

### 2. Integração com API WhatsApp

O webhook está disponível em: `POST /webhook/whatsapp`

**Estrutura da requisição:**
```json
{
  "entry": [
    {
      "changes": [
        {
          "value": {
            "messages": [
              {
                "from": "55129988887777",
                "type": "text",
                "text": {
                  "body": "status OS-2026-001"
                },
                "timestamp": "1643650000"
              }
            ]
          }
        }
      ]
    }
  ]
}
```

### 3. Configurar Webhook em Provedor (Ex: Twilio/WhatsApp Cloud API)

Se usar um provedor de WhatsApp:

**Webhook URL:**
```
https://seu-dominio.com/webhook/whatsapp
```

**Webhook Token:** Use o valor de `WHATSAPP_WEBHOOK_TOKEN`

**Verificação GET (Handshake):**
O sistema responde automaticamente ao teste de validação do provedor.

## 🎯 Comandos Disponíveis

| Comando | Exemplo | Ação |
|---------|---------|------|
| **Status** | `status OS-2026-001` | Retorna status atual da OS |
| **Concluir** | `concluído OS-2026-001` | Marca OS como Concluída |
| **Chegada** | `cheguei OS-2026-001` | Marca como Em Andamento (chegou) |
| **Pausa** | `pausa OS-2026-001` | Pausa a OS |
| **Retomar** | `retomar OS-2026-001` | Retoma OS pausada |
| **Ajuda** | `ajuda` | Mostra lista de comandos |

**Variações aceitas:**
- `concluído`, `concluir`, `done`, `finalizar` → Concluir
- `cheguei`, `chegada`, `arrived` → Chegada
- `pausa`, `pause` → Pausa
- `retomar`, `resume` → Retomar
- `?`, `help` → Ajuda

## 🔐 Segurança

### Validação de Remetente

Apenas o número configurado em `WHATSAPP_WEBHOOK_FROM` pode enviar comandos.

```python
# No .env
WHATSAPP_WEBHOOK_FROM=5512982200009
```

Mensagens de outros números:
- ✅ São registradas
- ❌ Não executam comandos
- 📤 Recebem aviso de não autorizado

### Validação de Token

A requisição POST **precisa incluir o token** no header ou query:

```bash
curl -X POST https://seu-dominio.com/webhook/whatsapp \
  -H "Authorization: Bearer seu_token_aqui" \
  -H "Content-Type: application/json" \
  -d '{...}'
```

## 📊 Resposta do Webhook

A resposta do webhook é um JSON com resultado do processamento:

```json
{
  "OK": true,
  "resultado": {
    "sucesso": true,
    "tipo": "concluir",
    "numero_os": "OS-2026-001",
    "atualizado": true,
    "resposta": "✅ OS OS-2026-001 marcada como concluída!"
  }
}
```

## 🧪 Testes

Teste o webhook localmente:

```bash
python test_whatsapp_webhook.py
```

**Resultado esperado:** Todos os 10 testes devem passar ✅

## 📝 Exemplo de Fluxo Completo

### 1. Técnico envia mensagem
```
Técnico: "cheguei OS-2026-001"
```

### 2. Sistema processa
```
[INFO] Mensagem recebida: cheguei OS-2026-001
[INFO] Comando detectado: chegada
[INFO] OS-2026-001 atualizada para 'Em Andamento'
```

### 3. Bot responde
```
🤖 Bot: "👨‍🔧 Técnico chegou na OS OS-2026-001!"
```

### 4. OS é atualizada no Google Sheets
Status: **Em Andamento**
Timestamp: Atualizado automaticamente

## 🚀 Próximos Passos (Opcional)

1. **Respostas Automáticas**: Integrar com API do provedor para enviar respostas
2. **Histórico**: Armazenar conversas em coluna "Histórico Técnico" do Sheets
3. **Notificações**: Avisar gerente quando OS é concluída via WhatsApp
4. **Múltiplos Técnicos**: Expandir `WHATSAPP_WEBHOOK_FROM` para aceitar lista de números
5. **Autenticação 2FA**: Adicionar PIN ou validação adicional para aceitar comandos

## ❓ Troubleshooting

### Webhook não está recebendo mensagens
- ✅ Verificar se `WHATSAPP_WEBHOOK_ENABLED=true`
- ✅ Verificar se webhook está registrado no provedor
- ✅ Validar URL pública está acessível

### Mensagens não são processadas
- ✅ Verificar `WHATSAPP_WEBHOOK_TOKEN` está correto
- ✅ Verificar `WHATSAPP_WEBHOOK_FROM` contém número do técnico

### OS não está sendo atualizada
- ✅ Verificar se `sheets_service` está inicializado
- ✅ Verificar se número da OS existe no Sheets
- ✅ Verificar credenciais do Google Sheets estão válidas

## 📚 Referências

- [Arquivo de Serviço](../appmodules/services/whatsapp_webhook_service.py)
- [Rota Webhook](../app.py)
- [Testes](../test_whatsapp_webhook.py)
