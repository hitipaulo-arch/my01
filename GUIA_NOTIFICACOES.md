# 🔔 Guia Rápido de Configuração de Notificações

## 📧 Configuração de E-mail (Gmail)

### Passo 1: Ativar Verificação em 2 Etapas
1. Acesse [myaccount.google.com/security](https://myaccount.google.com/security)
2. Clique em "Verificação em duas etapas"
3. Siga as instruções para ativar

### Passo 2: Gerar Senha de App
1. Acesse [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
2. Selecione "E-mail" e "Outro (nome personalizado)"
3. Digite "Sistema OS" ou qualquer nome
4. Copie a senha gerada (16 caracteres)

### Passo 3: Configurar Variáveis de Ambiente
```bash
NOTIFY_ENABLED=true
NOTIFY_TO=seuemail@gmail.com
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=seuemail@gmail.com
SMTP_PASSWORD=abcd efgh ijkl mnop  # Senha de app gerada (sem espaços)
SMTP_USE_TLS=true
```

---

## 📱 Configuração de WhatsApp (Twilio)

### Passo 1: Criar Conta Twilio
1. Acesse [twilio.com/try-twilio](https://www.twilio.com/try-twilio)
2. Crie sua conta gratuita (recebe $15 de crédito)
3. Confirme seu e-mail e telefone

### Passo 2: Obter Credenciais
1. Acesse o [Console Twilio](https://console.twilio.com/)
2. Copie seu **Account SID** (começa com AC)
3. Copie seu **Auth Token** (clique no ícone de olho)

### Passo 3: Ativar WhatsApp Sandbox (para testes)
1. No console, vá em **Messaging** > **Try it out** > **Send a WhatsApp message**
2. Você verá um número (ex: +1 415 523 8886)
3. Abra seu WhatsApp e adicione esse número nos contatos
4. Envie a mensagem que aparece na tela (ex: "join [seu-código]")
5. Você receberá confirmação de ativação

### Passo 4: Configurar Variáveis de Ambiente
```bash
WHATSAPP_ENABLED=true
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=seu_auth_token_aqui
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
TWILIO_WHATSAPP_TO=whatsapp:+5511999999999  # Seu número com código do país
```

### (Opcional) Usar Templates (ContentSid) com Variáveis

Você pode enviar mensagens usando **templates do Twilio**. Basta definir o `TWILIO_CONTENT_SID`. Se `TWILIO_CONTENT_VARIABLES_JSON` não for definido, o sistema monta automaticamente as variáveis a partir dos dados da OS com o seguinte mapeamento padrão:

| Chave | Valor |
|------:|-------|
| `"1"` | Número da OS |
| `"2"` | Timestamp (data/hora) |
| `"3"` | Solicitante |
| `"4"` | Setor |
| `"5"` | Equipamento/Local |
| `"6"` | Prioridade |
| `"7"` | Descrição (até 200 caracteres) |
| `"8"` | Info adicional (até 100 caracteres, opcional) |

Exemplo (PowerShell):

```powershell
$env:WHATSAPP_ENABLED = "true"
$env:TWILIO_ACCOUNT_SID = "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
$env:TWILIO_AUTH_TOKEN = "seu_auth_token"
$env:TWILIO_WHATSAPP_FROM = "whatsapp:+14155238886"
$env:TWILIO_WHATSAPP_TO = "whatsapp:+5512991635552"
$env:TWILIO_CONTENT_SID = "HXb5b62575e6e4ff6129ad7c8efe1f983e"

# Opcional: Forçar variáveis específicas do template
# $env:TWILIO_CONTENT_VARIABLES_JSON = '{"1":"12/1","2":"3pm"}'
```

#### (Opcional) Mapeamento Personalizado (TWILIO_CONTENT_MAP)

Você pode escolher quais campos da OS entram em cada variável do template usando `TWILIO_CONTENT_MAP`:

Campos disponíveis: `numero_pedido`, `timestamp`, `solicitante`, `setor`, `equipamento`, `prioridade`, `descricao`, `info`

Exemplo (PowerShell):

```powershell
$env:TWILIO_CONTENT_MAP = "1=numero_pedido,2=prioridade,3=solicitante,4=setor,5=equipamento,6=timestamp,7=descricao,8=info"
```

Se `TWILIO_CONTENT_VARIABLES_JSON` estiver definido, ele prevalece; se não estiver, o sistema usa `TWILIO_CONTENT_MAP`. Se nenhum dos dois estiver definido, usa o mapeamento padrão 1..8.

> Observação: Garanta que seu template no Twilio usa as chaves compatíveis (`{{1}}`, `{{2}}`, etc.). Caso a estrutura seja diferente, defina `TWILIO_CONTENT_VARIABLES_JSON` manualmente.

**⚠️ Importante:** 
- Formato do número: `whatsapp:+[código_país][DDD][número]`
- Exemplo Brasil: `whatsapp:+5511987654321`
- SEM espaços, traços ou parênteses!

### Passo 5 (OPCIONAL): Usar Número Próprio em Produção
1. No console Twilio, vá em **Messaging** > **Senders** > **WhatsApp senders**
2. Clique em "Request Access" para WhatsApp Business
3. Aguarde aprovação da Twilio (pode levar alguns dias)
4. Depois de aprovado, use seu número próprio como `TWILIO_WHATSAPP_FROM`

---

## 🧪 Testar Notificações

### Teste Local (com .env):
1. Copie `.env.example` para `.env`
2. Configure as variáveis conforme os passos acima
3. Execute: `python app.py`
4. Crie uma OS de teste pela interface
5. Verifique e-mail e WhatsApp

### Teste no Render (produção):
1. Acesse seu projeto no Render
2. Vá em **Environment** > **Environment Variables**
3. Adicione cada variável manualmente:
   - `NOTIFY_ENABLED` = `true`
   - `SMTP_HOST` = `smtp.gmail.com`
   - etc.
4. Salve e aguarde o redeploy automático
5. Teste criando uma OS

---

## 🔍 Solução de Problemas

### E-mail não chega:
- ✅ Verificou spam/lixeira?
- ✅ Senha de app está correta? (sem espaços)
- ✅ `SMTP_USE_TLS=true` está configurado?
- ✅ `NOTIFY_ENABLED=true` está ativo?

### WhatsApp não chega:
- ✅ Enviou a mensagem "join [código]" para o número sandbox?
- ✅ Formato do número está correto? `whatsapp:+5511999999999`
- ✅ Account SID e Auth Token estão corretos?
- ✅ `WHATSAPP_ENABLED=true` está ativo?

### Ver logs de erro:
```bash
# Ver últimas 100 linhas do log
tail -n 100 app.log

# Ou verificar no terminal ao executar:
python app.py
```

---

## 💡 Dicas Importantes

1. **Ambas notificações são independentes**: você pode ativar só e-mail, só WhatsApp, ou ambos!

2. **Múltiplos destinatários**: separe por vírgula
   ```bash
   NOTIFY_TO=admin@empresa.com,gerente@empresa.com
   TWILIO_WHATSAPP_TO=whatsapp:+5511999999999,whatsapp:+5511888888888
   ```

3. **Custos Twilio**:
   - Sandbox: GRATUITO para testes
   - Produção: ~$0.005 por mensagem (cheque preços atuais)
   - Crédito inicial: $15 (suficiente para ~3000 mensagens)

4. **Gmail limits**:
   - Máximo 500 e-mails/dia para contas gratuitas
   - Use conta Google Workspace para limites maiores

---

## 📚 Links Úteis

- [Senha de App Google](https://myaccount.google.com/apppasswords)
- [Console Twilio](https://console.twilio.com/)
- [Documentação Twilio WhatsApp](https://www.twilio.com/docs/whatsapp)
- [Preços Twilio](https://www.twilio.com/whatsapp/pricing)

---

**✅ Configuração completa! Agora toda vez que uma OS for aberta, você receberá notificação instantânea por e-mail e/ou WhatsApp! 🚀**
