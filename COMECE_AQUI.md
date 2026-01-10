# 🚀 GUIA RÁPIDO - COMEÇAR A USAR NOTIFICAÇÕES

## 5 Passos para Ativar Notificações

### Passo 1: Clonar ou Copiar Arquivo .env

```powershell
# Acesse a pasta do projeto
cd c:\Users\Automação\Documents\GitHub\my01

# Copie o arquivo de exemplo
Copy-Item .env.example .env
```

### Passo 2: Configurar Variáveis Twilio

Edite o arquivo `.env` e preencha com suas credenciais:

```bash
# Credenciais Twilio (preencha com suas)
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
TWILIO_WHATSAPP_TO=whatsapp:+seu_numero
TWILIO_CONTENT_SID=HXxxxxxxxxxxxxxxxxxxxxxxx

# Opcional: Mapeamento customizado
# TWILIO_CONTENT_MAP=1=numero_pedido,2=timestamp,3=solicitante,4=setor,5=equipamento,6=prioridade,7=descricao,8=info
```

### Passo 3: Configurar Email (Gmail)

Para obter **SMTP_PASSWORD**, siga:

1. **Ative 2FA em sua conta Google:** https://myaccount.google.com/security
2. **Crie "App Password":**
   - Vá para: https://myaccount.google.com/apppasswords
   - Selecione: Aplicativo: Mail | Dispositivo: Windows PC
   - Copie a senha gerada (16 caracteres)

Adicione a `.env`:

```bash
SMTP_USER=seu_email@gmail.com
SMTP_PASSWORD=xxxxxxxxxxxxxxxx  # Senhas de aplicativo Google (16 chars)
SMTP_RECIPIENTS=admin@empresa.com,manager@empresa.com
```

### Passo 4: Instalar Dependências

```powershell
pip install -r requirements.txt
```

### Passo 5: Testar

#### A. Verificar Sintaxe

```powershell
python -m py_compile app.py
# Deve retornar sem erros
```

#### B. Executar Testes Automatizados

```powershell
# Teste de mapeamento
python test_twilio_mapping.py

# Teste de integração
python test_integration.py

# Teste funcional
python test_functional.py

# Todos os testes de uma vez
python run_all_tests.py
```

#### C. Iniciar Servidor

```powershell
# Em desenvolvimento
python app.py

# Acesse: http://localhost:5000
# Usuário: admin
# Senha: admin
```

#### D. Criar uma OS de Teste

1. Abra http://localhost:5000
2. Faça login (admin/admin)
3. Vá em **"Nova OS"** (ou similar)
4. Preencha os dados:
   - **Solicitante:** Seu Nome
   - **Setor:** TI
   - **Equipamento:** Computador
   - **Prioridade:** Alta
   - **Descrição:** Teste de notificação
   - **Informações Adicionais:** (deixe em branco ou preencha)
5. Clique em **"Enviar"** ou **"Criar OS"**

#### E. Verificar Notificações

- **Email:** Verifique sua caixa de entrada (SMTP_RECIPIENTS)
- **WhatsApp:** Verifique a mensagem em TWILIO_WHATSAPP_TO

---

## ✅ Checklist de Funcionamento

Após completar os 5 passos, verifique:

- [ ] Arquivo `.env` criado com credenciais
- [ ] `test_twilio_mapping.py` retorna "6/6 testes passaram"
- [ ] `test_integration.py` retorna "8/8 testes passaram"
- [ ] `test_functional.py` retorna "6/6 testes passaram"
- [ ] `app.py` compila sem erros
- [ ] Servidor inicia com `python app.py`
- [ ] Email recebido após criar OS
- [ ] WhatsApp recebido após criar OS

---

## 🔧 Troubleshooting

### Email não é recebido

**Problema:** SMTP_PASSWORD incorreto ou 2FA não ativado

**Solução:**
```powershell
# Verifique .env
type .env | Select-String "SMTP"

# Confirme que:
# 1. SMTP_USER = seu_email@gmail.com (com @gmail.com)
# 2. SMTP_PASSWORD = 16 caracteres (gerado em apppasswords)
# 3. 2FA está ativado na conta Google
```

### WhatsApp não é recebido

**Problema:** Credenciais Twilio incorretas ou número não validado

**Solução:**
```powershell
# Verifique .env
type .env | Select-String "TWILIO"

# Confirme que:
# 1. TWILIO_ACCOUNT_SID começa com AC...
# 2. TWILIO_AUTH_TOKEN tem 32 caracteres
# 3. TWILIO_WHATSAPP_TO tem formato: whatsapp:+55...
# 4. Número está validado no sandbox Twilio
```

### Python não encontra módulos

```powershell
# Instale dependências novamente
pip install -r requirements.txt --force-reinstall

# Verifique versão
python --version  # Deve ser 3.8+
```

### Port 5000 já está em uso

```powershell
# Mude a porta em app.py (última linha)
# Mude: app.run(debug=True, port=5000)
# Para: app.run(debug=True, port=5001)
```

---

## 📊 Variáveis de Mapeamento (ContentVariables)

Quando uma OS é criada, esses campos são mapeados automaticamente:

| Slot | Campo | Exemplo |
|------|-------|---------|
| 1 | numero_pedido | OS-2026-001 |
| 2 | timestamp | 10/01/2026 14:30:00 |
| 3 | solicitante | João Silva |
| 4 | setor | TI |
| 5 | equipamento | Notebook sala 201 |
| 6 | prioridade | Alta |
| 7 | descricao | Notebook não liga (max 200 chars) |
| 8 | info_adicional | Urgente (max 100 chars, opcional) |

**Customizar:** Adicione a `.env`:
```bash
TWILIO_CONTENT_MAP=1=numero_pedido,2=prioridade,3=solicitante,4=setor,5=equipamento,6=timestamp,7=descricao,8=info
```

---

## 🎯 Exemplos de Notificações

### Email Recebido

```
De: noreply@seu-app.com
Para: admin@empresa.com
Assunto: Nova OS Aberta: OS-2026-001

┌─────────────────────────────────┐
│ 🚨 Nova Ordem de Serviço        │
├─────────────────────────────────┤
│ Número OS:      OS-2026-001     │
│ Solicitante:    João Silva      │
│ Setor:          TI              │
│ Prioridade:     Alta            │
│ Equipamento:    Notebook        │
│ Data/Hora:      10/01/2026 14:30│
│ Descrição:      Notebook não... │
│ Observações:    Urgente         │
└─────────────────────────────────┘
```

### WhatsApp Recebido

```
[14:30] Sistema de Notificações

🚨 Nova OS: OS-2026-001
📋 Solicitante: João Silva
🔧 Setor: TI
📱 Equipamento: Notebook sala 201
⚡ Prioridade: Alta
📝 Descrição: Notebook não liga...
ℹ️ Info: Urgente para apresentação
```

---

## 💡 Dicas

1. **Teste primeiro em sandbox:** Twilio fornece um número sandbox (+14155238886) para testes gratuitos
2. **Múltiplos destinatários:** Use `whatsapp:+551199999999,whatsapp:+551188888888` em TWILIO_WHATSAPP_TO
3. **Modo desenvolvimento:** Deixe `TWILIO_ENABLED=true` para ativar/desativar testes sem enviar
4. **Logs detalhados:** Erros aparecem em stderr durante desenvolvimento

---

## 📖 Documentação Completa

Para mais detalhes, consulte:

- [README.md](README.md) - Visão geral do sistema
- [GUIA_NOTIFICACOES.md](GUIA_NOTIFICACOES.md) - Guia passo-a-passo completo
- [RELATORIO_TESTES.md](RELATORIO_TESTES.md) - Detalhes de testes
- [TESTE_COMPLETO_SUMMARY.md](TESTE_COMPLETO_SUMMARY.md) - Sumário executivo

---

## 🚀 Deploy em Render.com

Após testar localmente, para publicar:

1. Faça push para GitHub
2. Conecte repo em https://render.com
3. Adicione variáveis de ambiente no dashboard Render
4. Deploy automático acontece ao fazer push

---

**Último update:** 10/01/2026  
**Status:** ✅ Pronto para usar
