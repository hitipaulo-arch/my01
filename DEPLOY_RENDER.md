# Deploy no Render - Guia Completo

## 📦 Pré-requisitos

- Conta no [Render.com](https://render.com) (gratuita)
- Repositório GitHub configurado
- Arquivo `credentials.json` do Google Service Account

## 🚀 Passo a Passo

### 1. Preparar Repositório

Certifique-se que os arquivos estão commitados:
```bash
git add .
git commit -m "Preparar para deploy no Render"
git push origin main
```

### 2. Criar Web Service no Render

1. Acesse [Render Dashboard](https://dashboard.render.com)
2. Clique em **"New +"** → **"Web Service"**
3. Conecte seu repositório GitHub
4. Configure:
   - **Name**: `projeto-flask-os` (ou nome de sua escolha)
   - **Region**: escolha a mais próxima
   - **Branch**: `main`
   - **Root Directory**: (deixe vazio)
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Instance Type**: `Free`

### 3. Configurar Variáveis de Ambiente

Na seção **"Environment"**, adicione:

| Key | Value |
|-----|-------|
| `GOOGLE_SHEET_ID` | `1qs3cxlklTnzCp4RpQGhxIrEF4CbeUvid1S0Cp2tC3Xg` |
| `GOOGLE_SHEET_TAB` | `Respostas ao formulário 3` |
| `SECRET_KEY` | Gere uma chave aleatória segura |
| `CACHE_TTL_SECONDS` | `300` |
| `PYTHON_VERSION` | `3.11.0` |

**Para gerar SECRET_KEY segura:**
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 4. Configurar Secret File (credentials.json)

⚠️ **IMPORTANTE**: Nunca faça commit do `credentials.json` no GitHub!

1. No Render Dashboard, vá em **"Environment"**
2. Role até **"Secret Files"**
3. Clique em **"Add Secret File"**
4. Configure:
   - **Filename**: `credentials.json`
   - **Contents**: Cole todo o conteúdo do seu arquivo JSON do Google Service Account

Exemplo de estrutura do credentials.json:
```json
{
  "type": "service_account",
  "project_id": "seu-projeto-id",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "seu-service-account@projeto.iam.gserviceaccount.com",
  "client_id": "...",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "..."
}
```

### 5. Configurar Google Sheets

1. Abra sua planilha no Google Sheets
2. Clique em **"Compartilhar"**
3. Adicione o email do Service Account (está no credentials.json como `client_email`)
4. Dê permissão de **"Editor"**

### 6. Deploy

1. Clique em **"Create Web Service"**
2. Aguarde o build completar (2-5 minutos)
3. Acesse a URL fornecida: `https://projeto-flask-os.onrender.com`

## 🔍 Verificar Logs

Após deploy, verifique os logs:
- Deve aparecer: `INFO - Credenciais carregadas com sucesso`
- Deve aparecer: `INFO - Conectado com sucesso à planilha`

Se houver erro:
- ✅ Verifique se o Secret File está configurado
- ✅ Verifique se a planilha está compartilhada com o Service Account
- ✅ Verifique se todas as variáveis de ambiente estão corretas

## 🔄 Atualizações Futuras

Toda vez que fizer push para o repositório:
```bash
git add .
git commit -m "Descrição das mudanças"
git push origin main
```

O Render fará deploy automático!

## ⚡ Performance

Com cache ativado:
- **Primeira requisição**: 2-5s (carrega da planilha)
- **Requisições seguintes**: ~200ms (cache)
- **TTL do cache**: 5 minutos

## 🐛 Troubleshooting

### Erro: "Credenciais não encontradas"
- Verifique se o Secret File `credentials.json` foi adicionado corretamente
- Path deve ser exatamente: `credentials.json`

### Erro: "Erro ao conectar na planilha"
- Verifique se compartilhou a planilha com o `client_email`
- Verifique se o `GOOGLE_SHEET_ID` está correto

### Erro: "Application failed to start"
- Verifique os logs do Render
- Confirme que `requirements.txt` está correto
- Confirme que `Procfile` existe

### Cache não funciona
- Verifique variável `CACHE_TTL_SECONDS`
- Verifique logs: deve aparecer "Cache HIT" ou "Cache MISS"

## 📊 Monitoramento

Acesse `/admin/limpar-cache` para forçar atualização dos dados.

## 🔒 Segurança

- ✅ `credentials.json` não está no repositório
- ✅ Secret key configurada
- ✅ Debug mode desativado em produção
- ✅ HTTPS automático no Render

## 💰 Plano Free Render

Limitações:
- Sleep após 15min de inatividade
- 750h/mês de uptime
- Primeira requisição pode demorar ~30s (cold start)

Para produção 24/7: considere plano pago ($7/mês)
