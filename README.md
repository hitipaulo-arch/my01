# Sistema de Ordem de Serviço (OS)

Sistema web para gerenciamento de Ordens de Serviço integrado com Google Sheets.

## 🚀 Funcionalidades

- ✅ Abertura de OS via formulário web
- 🔧 Gerenciamento e edição de chamados
- 🔍 Consulta pública de status
- 💾 Cache inteligente (5 minutos TTL)
- 📝 Logging estruturado
- ✨ Validação de formulários
- 🔐 Tratamento seguro de credenciais
- 🛡️ **Hash de senhas com PBKDF2** (segurança aprimorada)
- 🔒 **Proteção CSRF** em todos os formulários
- 🔄 Migração automática de senhas legadas
- ⚡ **Flask-Caching** para melhor performance
- 🚨 **Error handlers globais** para tratamento robusto de erros
- ✔️ **Validações centralizadas** com dataclasses
- 📝 **Type hints** para código mais seguro

## 📋 Pré-requisitos

- Python 3.8+
- Conta Google Cloud com API Sheets habilitada
- Service Account do Google Cloud

## 🔧 Instalação

1. Clone o repositório:
```bash
git clone <seu-repositorio>
cd projeto_flask
```

2. Instale as dependências:
```bash
pip install -r requirements.txt
```

3. Configure as credenciais:
   - Acesse [Google Cloud Console](https://console.cloud.google.com/)
   - Crie um novo projeto ou selecione um existente
   - Ative a API do Google Sheets
   - Crie um Service Account em "IAM & Admin" > "Service Accounts"
   - Gere uma chave JSON para o Service Account
   - Copie o arquivo `credentials.json.example` para `credentials.json`
   - Substitua os valores de exemplo pelos dados do seu Service Account
   - **IMPORTANTE**: Compartilhe sua planilha Google Sheets com o email do Service Account (permissão de editor)

4. Configure variáveis de ambiente (opcional):
```bash
# .env
GOOGLE_SHEET_ID=seu_id_da_planilha
SECRET_KEY=sua_chave_secreta_aqui
CACHE_TTL_SECONDS=300
FLASK_DEBUG=false
```

### Gravar a chave de produção localmente

Garanta que o arquivo `.env` esteja em `.gitignore` e copie `.env.example` para `.env` preenchendo os valores reais.

Não inclua chaves reais no repositório. Use `.env` local (gitignored) ou variáveis de ambiente do sistema.

### Agente no VS Code

O workspace inclui um prompt invocável do Continue em [.continue/prompts/nvidia-local-agent.md](.continue/prompts/nvidia-local-agent.md).

Use `/nvidia` no Continue para abrir o fluxo do agente com suporte a streaming e leitura segura de `NVIDIA_API_KEY` pelo ambiente.


```

## ▶️ Executar

**Desenvolvimento:**
```bash
python app.py
```

Se for usar o túnel público com ngrok, prefira a versão oficial instalada a partir de https://ngrok.com/download. A distribuição da Microsoft Store/MSIX pode falhar com o erro `disabled updater should never run`.

**Produção (com Gunicorn):**
```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

Acesse: http://localhost:5000

## 📁 Estrutura

```
projeto_flask/
├── app.py                 # Aplicação principal
├── templates/             # Templates HTML
│   ├── index.html        # Formulário de abertura
│   ├── gerenciar.html    # Gerenciamento de OS
│   ├── consultar.html    # Consulta pública
│   ├── sucesso.html      # Confirmação
│   └── erro.html         # Página de erro
├── requirements.txt       # Dependências Python
├── credentials.json       # Credenciais Google (não commitar!)
└── .gitignore            # Arquivos ignorados

```

## 🌐 Deploy no Render

1. Crie conta no Render.com
2. Conecte seu repositório GitHub
3. Configure Secret Files:
   - Nome: `credentials.json`
   - Conteúdo: JSON do Service Account
4. Configure Environment Variables:
   - `GOOGLE_SHEET_ID`
   - `SECRET_KEY`
5. **Recomendado para produção:** provisione um **Redis** no Render (Add-ons → Redis) e defina:
   - `REDIS_URL` → use a *Internal Redis URL* (começa com `redis://red-...`)
   - `CACHE_TYPE=RedisCache` (opcional — auto-detectado quando `REDIS_URL` está setado)
6. Deploy automático!

## 🔑 Variáveis de Ambiente

| Variável | Descrição | Padrão |
|----------|-----------|--------|
| `GOOGLE_SHEET_ID` | ID da planilha Google | - |
| `GOOGLE_SHEET_TAB` | Nome da aba | "Respostas ao formulário 3" |
| `SECRET_KEY` | Chave secreta Flask | "dev-secret-key..." |
| `CACHE_TTL_SECONDS` | Tempo de cache padrão (segundos) | 300 |
| `CACHE_TYPE` | Backend do cache (`RedisCache` ou `SimpleCache`) | Auto-detectado via `REDIS_URL` |
| `OS_CACHE_TTL_SECONDS` | TTL do cache de OS no SheetsService (segundos) | 120 |
| `PRODUCAO_CACHE_TTL_SECONDS` | TTL do cache de produção (segundos) | 30 |
| `USUARIOS_CACHE_TTL_SECONDS` | TTL do cache de usuários (segundos) | 300 |
| `REDIS_URL` | URL completa do Redis (ex.: `redis://:senha@host:6379/0`) | - |
| `REDIS_HOST` | Host do Redis (se `REDIS_URL` não definido) | localhost |
| `REDIS_PORT` | Porta do Redis | 6379 |
| `REDIS_DB` | Número do database Redis | 0 |
| `REDIS_PASSWORD` | Senha do Redis (vazio se sem senha) | - |
| `FLASK_DEBUG` | Modo debug | false |
| `PORT` | Porta do servidor | 5000 |


Também existe um endpoint administrativo para teste direto no Flask:

```bash
POST /admin/nvidia/stream
Content-Type: application/json

{"prompt":"Explique em uma frase como validar uma integracao de API com streaming."}
```

O endpoint exige autenticação de administrador e retorna o texto em streaming.

### 🔔 Notificação ao abrir OS

Quando habilitado, o sistema envia notificações automaticamente ao **criar uma nova OS** (rota `/enviar`).

#### 📧 E-mail (SMTP)

| Variável | Descrição | Padrão |
|----------|-----------|--------|
| `NOTIFY_ENABLED` | Ativa notificação por e-mail (`true`/`false`) | `false` |
| `NOTIFY_TO` | Destinatários (separados por vírgula) | - |
| `NOTIFY_FROM` | Remetente do e-mail | `SMTP_USER` ou `no-reply@localhost` |
| `SMTP_HOST` | Host do servidor SMTP | - |
| `SMTP_PORT` | Porta do servidor SMTP | `587` |
| `SMTP_USER` | Usuário do SMTP (se necessário) | - |
| `SMTP_PASSWORD` | Senha do SMTP (se necessário) | - |
| `SMTP_USE_TLS` | Usa STARTTLS (`true`/`false`) | `true` |
| `SMTP_USE_SSL` | Usa SMTP SSL (`true`/`false`) | `false` |
| `SMTP_TIMEOUT_SECONDS` | Timeout de conexão (segundos) | `10` |

**Exemplo de configuração para Gmail:**

```bash
# .env
NOTIFY_ENABLED=true
NOTIFY_TO=seuemail@gmail.com,outro@empresa.com
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=seuemail@gmail.com
SMTP_PASSWORD=sua_senha_de_app_aqui
SMTP_USE_TLS=true
```

**⚠️ Importante para Gmail:**
1. Ative a verificação em 2 etapas na sua conta Google
2. Gere uma **Senha de App** em [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
3. Use a senha de app gerada (16 caracteres) no `SMTP_PASSWORD`, não sua senha normal

#### 📱 WhatsApp (Click-to-Chat, WhatsApp Web e Webhook)

> **Nota (atualizado em 2026-09-09):** a integração antiga via **Twilio API** foi substituída por
> mecanismos nativos — links **wa.me (Click-to-Chat)**, **WhatsApp Web (pywhatkit)** e o
> **webhook** para técnicos enviarem comandos. Não existem mais variáveis `TWILIO_*` no código.

| Variável | Descrição | Padrão |
|----------|-----------|--------|
| `WHATSAPP_ENABLED` | Liga o serviço **Click-to-Chat** (abre link `wa.me` no navegador da máquina que roda o app) | `false` |
| `WHATSAPP_WEB_ENABLED` | Liga o envio automático via **WhatsApp Web/pywhatkit** (exige navegador logado em `WHATSAPP_FROM`) | `false` |
| `WHATSAPP_WEB_TO` | Número interno que recebe notificações de nova OS (dígitos com DDI, ex.: `5511999999999`) | - |
| `WHATSAPP_WEB_DELAY_SECONDS` | Atraso (s) antes do envio via pywhatkit | `15` |
| `WHATSAPP_WEBHOOK_ENABLED` | Liga o webhook que recebe comandos dos técnicos | `false` |
| `WHATSAPP_WEBHOOK_TOKEN` | Token de autenticação do webhook (Bearer) | - |
| `WHATSAPP_WEBHOOK_SECRET` | Segredo para validar a assinatura HMAC (obrigatório em produção) | - |
| `WHATSAPP_WEBHOOK_FROM` | Número autorizado a enviar comandos via webhook | - |

**Exemplo de configuração (máquina desktop local):**

```bash
# .env
WHATSAPP_ENABLED=true
WHATSAPP_WEB_ENABLED=false        # opcional: envio automático via pywhatkit
WHATSAPP_WEB_TO=5511999999999     # número que recebe as notificações
```

> ⚠️ O Click-to-Chat **abre o navegador** na máquina que executa o app — use
> `WHATSAPP_ENABLED=true` apenas em máquina local/desktop; em servidores
> (ex.: Render) mantenha `false`.

**Webhook (técnicos enviam status via WhatsApp):** configure
`WHATSAPP_WEBHOOK_ENABLED=true` + `WHATSAPP_WEBHOOK_TOKEN` e, em produção,
`WHATSAPP_WEBHOOK_SECRET`. O endpoint é `/webhook/whatsapp`.


## 📊 Cache

O sistema implementa cache inteligente com **Flask-Caching**, suportando dois backends:

### Backends suportados

| Backend | Quando usar | Como ativar |
|---------|-------------|-------------|
| `SimpleCache` (padrão em dev) | Single-worker / desenvolvimento | Não definir `REDIS_URL` |
| `RedisCache` (recomendado em produção) | Multi-worker com gunicorn | Definir `REDIS_URL` ou `CACHE_TYPE=RedisCache` |

> 💡 **Auto-detecção**: se `REDIS_URL` estiver definido, o sistema usa `RedisCache` automaticamente, mesmo sem `CACHE_TYPE`.

### Por que Redis em produção?

O `SimpleCache` armazena dados **na memória de cada processo**. Com `gunicorn -w 4`, cada worker tem seu próprio cache isolado, causando:

- ❌ **Race conditions**: dois workers podem ler dados desatualizados simultaneamente
- ❌ **Inconsistência**: usuário criado no worker 1 não aparece no worker 2 até o TTL expirar
- ❌ **Cache miss duplicado**: cada worker faz sua própria consulta ao Google Sheets

O **Redis** resolve isso compartilhando o cache entre todos os workers via rede.

### Instalação do Redis

**🐧 Linux (Ubuntu/Debian):**
```bash
sudo apt-get update
sudo apt-get install redis-server
sudo systemctl enable redis-server
sudo systemctl start redis-server
```

**🍎 macOS (Homebrew):**
```bash
brew install redis
brew services start redis
```

**🪟 Windows:**
- Baixe o instalador em [github.com/microsoftarchive/redis/releases](https://github.com/microsoftarchive/redis/releases)
- Ou use WSL2 com Ubuntu (recomendado)
- Ou use Docker: `docker run -d -p 6379:6379 --name redis redis:alpine`

**🐳 Docker (qualquer SO):**
```bash
docker run -d -p 6379:6379 --name redis redis:alpine
```

### Configuração no `.env`

```bash
# Tipo de cache (auto-detectado se REDIS_URL estiver definido)
CACHE_TYPE=RedisCache

# URL completa do Redis (tem prioridade sobre as variáveis individuais)
REDIS_URL=redis://localhost:6379/0

# OU configuração individual (usada se REDIS_URL não estiver definido)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# TTLs específicos por tipo de dado (em segundos)
CACHE_TTL_SECONDS=300          # TTL padrão
OS_CACHE_TTL_SECONDS=120       # Cache de ordens de serviço
PRODUCAO_CACHE_TTL_SECONDS=30  # Cache de produção
USUARIOS_CACHE_TTL_SECONDS=300 # Cache de usuários
```

### Funcionalidades do cache

- **TTL**: configurável por tipo de dado (padrão 5 minutos)
- **Rotas cacheadas**: Gerenciar
- **Invalidação**: automática após criar/atualizar/deletar OS ou usuários
- **Limpeza manual**: `/admin/limpar-cache`
- **Fallback automático**: se Redis cair, o sistema usa cache local em memória (degradação graceful)

### Deploy no Render com Redis

1. Crie um **Redis instance** no Render (plano free disponível)
2. Copie a **Internal Redis URL** fornecida pelo Render
3. Defina `REDIS_URL=<internal_url>` nas variáveis de ambiente do Web Service
4. Pronto! O sistema detecta e usa Redis automaticamente

### Verificando o cache

```bash
# Conectar ao Redis CLI
redis-cli

# Listar todas as chaves do app
KEYS my01_*

# Ver TTL de uma chave
TTL my01_sheets:os:all

# Ver valor (cuidado: pode ser grande)
GET my01_sheets:os:all

# Limpar todo o cache do app
FLUSHDB
```

## 🛡️ Segurança

- ✅ **Hash de senhas PBKDF2** (600.000 iterações)
- ✅ **Proteção CSRF** com Flask-WTF
- ✅ Migração automática de senhas legadas
- ✅ Validação de entrada
- ✅ Sanitização de dados
- ✅ Credenciais não expostas
- ✅ Secret key configurável
- ✅ Session cookies com HttpOnly e SameSite
- ✅ HTTPS recomendado em produção

**📖 Veja [SECURITY_IMPROVEMENTS.md](SECURITY_IMPROVEMENTS.md) para detalhes das melhorias implementadas.**

## ⚡ Performance & Código

- ✅ **Flask-Caching** com RedisCache (produção multi-worker) ou SimpleCache (dev) — auto-detectado via `REDIS_URL`
- ✅ **Error Handlers Globais** (404, 500, Exception)
- ✅ **Validações Centralizadas** com dataclasses
- ✅ **Type Hints** em funções principais
- ✅ **Configurações Centralizadas** em config.py

**📖 Veja [MEDIUM_PRIORITY_IMPROVEMENTS.md](MEDIUM_PRIORITY_IMPROVEMENTS.md) para detalhes das melhorias de código.**

## 📝 Logs

Logs estruturados com níveis:
```
2025-11-17 21:47:10 - __main__ - INFO - Credenciais carregadas com sucesso
2025-11-17 21:47:12 - __main__ - INFO - Conectado à planilha
2025-11-17 21:47:15 - __main__ - INFO - Nova OS (Pedido #123) adicionada
```

## 🤝 Contribuindo

1. Fork o projeto
2. Crie uma branch (`git checkout -b feature/nova-funcionalidade`)
3. Commit suas mudanças (`git commit -m 'Adiciona nova funcionalidade'`)
4. Push para a branch (`git push origin feature/nova-funcionalidade`)
5. Abra um Pull Request

## 📄 Licença

Este projeto é de código aberto.

## 👨‍💻 Autor

Sistema desenvolvido para gerenciamento de Ordens de Serviço.
