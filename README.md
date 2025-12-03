# Sistema de Ordem de Serviço (OS)

Sistema web para gerenciamento de Ordens de Serviço integrado com Google Sheets.

## 🚀 Funcionalidades

- ✅ Abertura de OS via formulário web
- 📊 Dashboard com gráficos de análise
- 🔧 Gerenciamento e edição de chamados
- 🔍 Consulta pública de status
- 💾 Cache inteligente (5 minutos TTL)
- 📝 Logging estruturado
- ✨ Validação de formulários
- 🔐 Tratamento seguro de credenciais

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

## ▶️ Executar

**Desenvolvimento:**
```bash
python app.py
```

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
│   ├── dashboard.html    # Dashboard com gráficos
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
5. Deploy automático!

## 🔑 Variáveis de Ambiente

| Variável | Descrição | Padrão |
|----------|-----------|--------|
| `GOOGLE_SHEET_ID` | ID da planilha Google | - |
| `GOOGLE_SHEET_TAB` | Nome da aba | "Respostas ao formulário 3" |
| `SECRET_KEY` | Chave secreta Flask | "dev-secret-key..." |
| `CACHE_TTL_SECONDS` | Tempo de cache (segundos) | 300 |
| `FLASK_DEBUG` | Modo debug | false |
| `PORT` | Porta do servidor | 5000 |

## 📊 Cache

O sistema implementa cache inteligente:
- **TTL**: 5 minutos configurável
- **Rotas cacheadas**: Dashboard, Gerenciar
- **Invalidação**: Automática após criar/atualizar OS
- **Limpeza manual**: `/admin/limpar-cache`

## 🛡️ Segurança

- ✅ Validação de entrada
- ✅ Sanitização de dados
- ✅ Credenciais não expostas
- ✅ Secret key configurável
- ✅ HTTPS recomendado em produção

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
