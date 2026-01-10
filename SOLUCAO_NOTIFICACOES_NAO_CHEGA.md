# 🔧 COMO ATIVAR NOTIFICAÇÕES - GUIA DE SOLUÇÃO

## ⚠️ Problemas Detectados

O diagnóstico encontrou 3 problemas:

1. **❌ SMTP_PASSWORD incorreta** - Senha Gmail não está certa
2. **❌ TWILIO_AUTH_TOKEN vazio** - Token Twilio não foi preenchido
3. **❌ Variáveis ainda com placeholders** - Alguns valores ainda são exemplos

---

## ✅ Solução Passo a Passo

### PASSO 1: Obter Senha de App do Gmail

**O problema:** Você colocou sua senha do Gmail no `.env`, mas Gmail não permite isso por segurança.

**A solução:** Use uma "Senha de Aplicativo" especial:

1. Vá para: https://myaccount.google.com/apppasswords
2. Faça login com sua conta Google
3. Se não vir "App passwords", é porque **2FA não está ativado**:
   - Primeiro, ative 2FA: https://myaccount.google.com/security
   - Escolha: Telefone
   - Depois volta em https://myaccount.google.com/apppasswords

4. Em "App passwords":
   - **Selecione:** Mail
   - **Selecione:** Windows PC
   - Clique em **Gerar**

5. Copie a **senha de 16 caracteres** que aparecer

6. Cole em `.env`:
   ```
   SMTP_PASSWORD=xxxx xxxx xxxx xxxx
   ```

**Exemplo:**
```
SMTP_PASSWORD=abcd efgh ijkl mnop
```

---

### PASSO 2: Obter Credenciais Twilio

Você tem a conta Twilio? Se sim, siga:

1. Vá para: https://www.twilio.com/console
2. Você verá:
   - **Account SID** (começa com AC...)
   - **Auth Token** (token longo)

3. Copie e cole em `.env`:
   ```
   TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxx
   TWILIO_AUTH_TOKEN=seu_auth_token_aqui
   ```

**Se não tiver conta Twilio:**
- Crie em: https://www.twilio.com/try-twilio
- Verifique o celular
- No dashboard verá as credenciais

---

### PASSO 3: Editar o Arquivo .env

Abra `.env` com editor de texto e altere:

```bash
# ❌ ANTES (incorreto):
SMTP_PASSWORD=minha_senha_gmail
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx

# ✅ DEPOIS (correto):
SMTP_PASSWORD=abcd efgh ijkl mnop
TWILIO_ACCOUNT_SID=ACsua_conta_real_aqui
TWILIO_AUTH_TOKEN=seu_token_real_aqui
```

---

### PASSO 4: Verificar Outras Variáveis

Certifique-se que também tem:

```bash
# Email
NOTIFY_ENABLED=true
SMTP_USER=seu_email@gmail.com
SMTP_RECIPIENTS=seu_email@gmail.com,outro@empresa.com

# WhatsApp
WHATSAPP_ENABLED=true
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
TWILIO_WHATSAPP_TO=whatsapp:+5512991635552
TWILIO_CONTENT_SID=HXxxxxxxxxxxxxxxxxxxxxxxxx
```

---

### PASSO 5: Testar o Diagnóstico Novamente

Depois de configurar, rode:

```powershell
python diagnostico_notificacoes.py
```

Deve aparecer:
```
✅ Arquivo .env
✅ Variáveis de Ambiente
✅ Conexão Gmail
✅ Conexão Twilio
✅ Funções em app.py

5/5 verificações passaram ✨
```

---

## 🧪 Testar Manualmente

Depois que o diagnóstico passar, teste:

```powershell
# Inicie o servidor
python app.py

# Acesse: http://localhost:5000
# Faça login: admin / admin
# Crie uma OS nova
# Verifique email + WhatsApp
```

---

## 🆘 Se Ainda Não Funcionar

### Email não chega:
- ✅ SMTP_PASSWORD é a senha de app (não a senha do Gmail)?
- ✅ 2FA está ativado em sua conta Google?
- ✅ SMTP_USER = seu_email@gmail.com exatamente?
- ✅ SMTP_RECIPIENTS está preenchido?

### WhatsApp não chega:
- ✅ TWILIO_ACCOUNT_SID começa com "AC"?
- ✅ TWILIO_AUTH_TOKEN tem caracteres válidos?
- ✅ TWILIO_WHATSAPP_TO tem seu número (ex: whatsapp:+5512991635552)?
- ✅ Seu número foi validado no Twilio sandbox?

### Ambos não funcionam:
- Rode novamente: `python diagnostico_notificacoes.py`
- Verifique as mensagens de erro
- Compare com este guia

---

## 📖 Referência Rápida

| Problema | Solução |
|----------|---------|
| SMTP_PASSWORD não funciona | Use senha de app (myaccount.google.com/apppasswords) |
| TWILIO_AUTH_TOKEN vazio | Copie de twilio.com/console |
| Email chega, WhatsApp não | Verifique TWILIO_ACCOUNT_SID e TWILIO_AUTH_TOKEN |
| Nenhum chega | Rode `python diagnostico_notificacoes.py` |

---

## 📞 Links Úteis

- **Gmail:** https://myaccount.google.com/apppasswords
- **Twilio:** https://www.twilio.com/console
- **2FA Google:** https://myaccount.google.com/security

---

**Pronto!** Depois de configurar, seu sistema enviará notificações automaticamente quando uma nova OS for criada. 🎉
