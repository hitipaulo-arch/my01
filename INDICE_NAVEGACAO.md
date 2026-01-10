# ÍNDICE DE NAVEGAÇÃO - app.py

## 📍 Localização Rápida das Seções

### ⚙️ Configuração & Setup
- **Linhas 1-33**: Docstring de estrutura + Imports
- **Linhas 34-60**: Google Sheets Configuration & Credentials Loading
- **Linhas 67-155**: Sheet Connection & Tab Creation (main, horário, usuários)
- **Linhas 156-188**: Flask App Initialization + Cache + CSRF

---

### 🛠️ Utilidades & Helpers

#### 📧 Notificações
- **Linhas 195-303**: `enviar_notificacao_abertura_os()` - Email sender
- **Linhas 308-380**: `enviar_notificacao_whatsapp_os()` - WhatsApp via Twilio

#### ✔️ Validação & Classes de Domínio
- **Linhas 385-430**: `ValidacaoResultado` dataclass
- **Linhas 432-510**: `ValidadorOS` class - Form validation
- **Linhas 512-530**: `ValidadorUsuario` class - User validation

#### 👥 Gerenciamento de Usuários
- **Linhas 540-620**: `carregar_usuarios()` - Load from Google Sheets
- **Linhas 625-680**: `salvar_usuarios()` - Save to Google Sheets
- **Linhas 685-715**: `deletar_usuario_sheets()` - Delete user

#### 🔐 Decoradores
- **Linhas 720-732**: `login_required()` - Require authentication
- **Linhas 737-753**: `admin_required()` - Require admin role

#### 🎯 Validação & Sheet Utilities
- **Linhas 760-775**: `validar_formulario()` - Validate form data
- **Linhas 780-810**: `obter_proximo_id()` - Get next OS ID
- **Linhas 815-823**: `verificar_sheet_disponivel()` - Check sheet connectivity

#### 💾 Cache Management
- **Linhas 828-845**: `obter_cache()` - Get cached data
- **Linhas 850-865**: `salvar_cache()` - Save to cache
- **Linhas 870-890**: `limpar_cache()` - Clear cache

---

### 🔓 Rotas - Autenticação

- **Linhas 900-920**: `@app.route('/login', methods=['GET', 'POST'])` - Login handler
- **Linhas 925-935**: `@app.route('/logout')` - Logout
- **Linhas 940-960**: `@app.route('/cadastro', methods=['GET', 'POST'])` - User registration

---

### 📋 Rotas - Formulários & Chamados

- **Linhas 965-975**: `@app.route('/')` - Homepage with form
- **Linhas 980-1055**: `@app.route('/enviar', methods=['POST'])` - Form submission (creates OS)
- **Linhas 1060-1150**: `@app.route('/dashboard')` - Dashboard view
- **Linhas 1155-1240**: `@app.route('/gerenciar')` - Manage OS
- **Linhas 1245-1305**: `@app.route('/atualizar_chamado', methods=['POST'])` - Update OS status
- **Linhas 1310-1320**: `@app.route('/sucesso')` - Success page

---

### 👤 Rotas - Admin & Gestão

- **Linhas 710-800**: `@app.route('/usuarios', methods=['GET', 'POST'])` - User management
- **Linhas 1320-1333**: `@app.route('/admin/limpar-cache', methods=['POST', 'GET'])` - Cache clearing

---

### ⏱️ Rotas - Controle de Horário

- **Linhas 1335-1635**: `@app.route('/controle-horario', methods=['GET', 'POST'])` - Time tracking
- **Linhas 1640-1650**: `@app.route('/health')` - Health check endpoint

---

### 📊 Rotas - Relatórios & Consultas

- **Linhas 1655-1785**: `@app.route('/relatorios')` - Reports with charts
- **Linhas 1790-1975**: `@app.route('/tempo-por-funcionario')` - Time analysis by employee
- **Linhas 1980-2065**: `@app.route('/consultar', methods=['GET', 'POST'])` - Query OS

---

### 🔧 Rotas - Utilidades

- **Linhas 2070-2074**: `@app.route('/favicon.ico')` - Browser icon

---

### 🚀 Ponto de Entrada

- **Linhas 2080-2091**: `if __name__ == '__main__':` - App startup

---

## 🔍 Dicas de Busca

Use esses padrões no VS Code (Ctrl+F) para navegação rápida:

| Buscar | Para encontrar |
|--------|---------------|
| `# ════` | Seções principais |
| `@app.route` | Todas as rotas |
| `def enviar_` | Funções de notificação |
| `class Validador` | Classes de validação |
| `def carregar_usuarios` | Carregamento de usuários |
| `@login_required` | Rotas protegidas |
| `@admin_required` | Rotas admin |

---

## 📄 Fluxos Principais

### Fluxo de Submissão de Formulário (New OS)
```
1. Usuário acessa / → index.html
2. Preenche formulário e submete para /enviar (POST)
3. validar_formulario() valida dados
4. obter_proximo_id() obtém novo ID
7. Dados salvos no Google Sheets
8. enviar_notificacao_abertura_os() envia email
9. enviar_notificacao_whatsapp_os() envia WhatsApp
10. Redireciona para /sucesso
```

### Fluxo de Login
```
1. Usuário acessa /login → login.html
2. Submete credenciais (POST)
3. Busca usuário no carregar_usuarios()
4. Valida senha com check_password_hash()
5. Cria session['usuario']
6. Redireciona para /dashboard
```

### Fluxo de Controle de Horas
```
1. Admin acessa /controle-horario
2. Vê registros da aba sheet_horario
3. Pode registrar entrada/saída/pausas
4. Dados salvos em Google Sheets
5. Cache limpo para atualizar dashboard
```

---

## 🎯 Mudanças Recentes

✅ **Reorganização de Headers**
- Substituído comentários simples por headers estruturados (════)
- Adicionado docstring no topo com mapa de arquivo
- Agrupadas funções relacionadas com headers claros
- Rotas organizadas por funcionalidade (Auth, Forms, Admin, Timesheet, Reports)

✅ **Arquivo de Documentação**
- `ESTRUTURA_CODIGO.md` - Guia completo de navegação
- `INDICE_NAVEGACAO.md` - Este arquivo com referências rápidas
- Facilita onboarding de novos desenvolvedores

---

## 📌 Próximos Passos Sugeridos

1. **Verificar se app inicia sem erros**
   ```bash
   python app.py
   ```

2. **Executar testes para validar funcionalidade**
   ```bash
   python run_all_tests.py
   ```

3. **Revisar documentação de notificações**
   - Ler `GUIA_NOTIFICACOES.md` para entender email + WhatsApp

4. **Configurar credenciais reais**
   - Substituir `credentials.json` com JSON real da Google Cloud
   - Preencher variáveis SMTP e Twilio no `.env`
