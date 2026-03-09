# Sistema Completo de Notificações WhatsApp

Este documento descreve a implementação de 3 métodos diferentes para enviar notificações via WhatsApp quando uma nova ordem de serviço (OS) é criada.

## 🚀 Métodos Implementados

### 1. **Click-to-Chat WhatsApp** (Recomendado - UNIVERSAL ✅)

**O que é:**
- Gera links `wa.me/` que abrem WhatsApp com a mensagem pré-preenchida
- Funciona em qualquer dispositivo: Windows, Mac, Linux, Android, iOS
- Não requer configuração especial de credenciais

**Como funciona:**
1. Sistema gera link wa.me com mensagem codificada
2. Abre automaticamente o WhatsApp (ou navegador com link)
3. Usuário vê as informações pré-preenchidas
4. Usuário clica "Enviar" para confirmar

**Vantagens:**
- ✅ Universal (funciona em qualquer OS)
- ✅ Nenhuma credencial necessária
- ✅ Não requer autenticação
- ✅ Sempre funciona como fallback

**Desvantagens:**
- Requer ação manual do usuário (clic em enviar)

**Configuração:**
```.env
WHATSAPP_WEB_ENABLED=true
WHATSAPP_WEB_TO=5512982200009
WHATSAPP_WEB_DELAY_SECONDS=0
```

---

### 2. **WhatsApp Web Automático** (pywhatkit)

**O que é:**
- Automação de WhatsApp Web usando pywhatkit
- Abre navegador e envia mensagem automaticamente
- Requer WhatsApp Web logado

**Como funciona:**
1. pywhatkit detecta navegador instalado
2. Abre WhatsApp Web em abas do navegador
3. Envia mensagem automaticamente

**Vantagens:**
- ✅ Automático (sem intervenção do usuário)
- ✅ Funciona em Windows, Mac, Linux

**Desvantagens:**
- ❌ Requer WhatsApp Web logado continuamente
- ❌ Requer número específico (+5512991635552)
- ⚠️ Timing sensível (requer 30+ segundos por mensagem)
- ❌ Pode falhar se navegador não está disponível

**Configuração:**
```.env
WHATSAPP_WEB_ENABLED=true
WHATSAPP_WEB_TO=5512982200009
WHATSAPP_WEB_DELAY_SECONDS=35
```

**Instalação:**
```bash
pip install pywhatkit
```

---

### 3. **Twilio API** (Sandbox Mode)

**O que é:**
- Integracao com API Twilio para enviar WhatsApp
- Funciona via Twilio sandbox (número de teste)
- Não requer WhatsApp Web aberto

**Como funciona:**
1. Sistema chama API REST Twilio
2. Twilio envia mensagem para número configurado
3. Mensagem entregue diretamente via WhatsApp

**Vantagens:**
- ✅ Automático
- ✅ Não requer WhatsApp Web
- ✅ Funciona em modo server/background

**Desvantagens:**
- ❌ Requer credenciais Twilio (Account SID, Auth Token)
- ❌ Sandbox requer validação de número (não llega mensagem sem setup)
- ❌ Requer assinatura paga para produção
- ⚠️ Requer muita configuração

**Configuração:**
```.env
WHATSAPP_ENABLED=true
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
TWILIO_WHATSAPP_TO=whatsapp:+5512982200009
```

---

## 📊 Comparação

| Feature | Click-to-Chat | WebAutomático | Twilio |
|---------|--------------|---------------|--------|
| Universal | ✅ Sim | ⚠️ Limits | ✅ Sim |
| Automático | ❌ Não | ✅ Sim | ✅ Sim |
| Credenciais | ❌ Não | ❌ Não | ✅ Sim |
| Setup | ✅ Fácil | ⚠️ Médio | ❌ Complexo |
| Confiabilidade | ✅ Alta | ⚠️ Média | ✅ Alta |
| Custo | ✅ Free | ✅ Free | ❌ Pago |

---

## 🔧 Integração com Sistema

Quando uma nova OS é criada, o sistema automaticamente:
1. ✅ Envia Email (se configurado)
2. ✅ Envia via Twilio WhatsApp (se configurado)
3. ✅ Envia via WhatsApp Web (se configurado e logado)
4. ✅ Gera link Click-to-Chat (sempre disponível)

Resultado retornado contém status de cada método:
```python
{
    'email': True/False,
    'whatsapp_twilio': True/False,
    'whatsapp_web': True/False,
    'whatsapp_click_to_chat': True/False
}
```

---

## 🧪 Testes

### Testar Click-to-Chat
```bash
python test_click_to_chat.py
# Deve abrir WhatsApp com link wa.me e generar bot message
```

### Testar Fluxo Completo
```bash
python test_fluxo_completo.py
# Simula criação de OS e testa todos os 3 métodos
```

### Testar Diagnóstico
```bash
python diagnostic_whatsapp.py
# Valida credenciais, conectividade e dispositivo info
```

---

## ⚙️ Arquivo de Configuracão (.env)

Exemplo completo:
```ini
# ----- Email Notifications -----
NOTIFY_ENABLED=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=seu_email@gmail.com
SMTP_PASSWORD=sua_senha_app
NOTIFY_FROM=seu_email@gmail.com
SMTP_RECIPIENTS=destinatario@email.com

# ----- WhatsApp Web (pywhatkit) -----
WHATSAPP_WEB_ENABLED=true
WHATSAPP_WEB_TO=5512982200009
WHATSAPP_WEB_DELAY_SECONDS=35

# ----- Twilio WhatsApp -----
WHATSAPP_ENABLED=true
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
TWILIO_WHATSAPP_TO=whatsapp:+5512982200009
TWILIO_CONTENT_SID=your_content_sid (opcional)
TWILIO_CONTENT_MAP=1=numero_pedido,2=timestamp,3=solicitante (opcional)
```

---

## 📋 Troubleshooting

### "Browser não abre WhatsApp"
- Solução: Click-to-Chat é fallback automático, gera link para abrir manualmente
- Verifique se WhatsApp Web está acessível em seu browser
- Teste webbrowser.open com URL comum primeiro

### "Twilio mensagem não chegando"
- Razão: Sandbox requer unirse a WhatsApp template
- Solução: Envie "+5514155238886" o texto "join blue-pigeon"
- Ou use Click-to-Chat e Web Automático como alternativas

### "Pywhatkit timeout"
- Razão: WHATSAPP_WEB_DELAY_SECONDS muito baixo
- Solução: Aumente para 35+ segundos
- Mensagens requerem tempo para browser carregar e digitar

## 🎯 Recomendação

Para produção:
1. **Primary**: Click-to-Chat (sempre funciona)
2. **Secondary**: WhatsApp Web (automático, mas sensível)
3. **Tertiary**: Twilio (confiável mas requer setup e custo)

Sistema tenta os 3 em paralelo - primeira que funciona é entregue!
