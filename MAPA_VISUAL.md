# 📐 MAPA VISUAL - Estrutura do app.py

## Estrutura em Árvore

```
📄 app.py (2098 linhas)
│
├─ 📍 HEADER (1-33)
│  └─ Docstring com mapa de navegação
│
├─ 1️⃣ IMPORTS & CONFIGURAÇÃO (34-188)
│  ├─ Imports (34-51)
│  ├─ Logging Setup (53-61)
│  ├─ Google Sheets Config (65-170)
│  │  ├─ SCOPES definition
│  │  ├─ Credentials loading
│  │  ├─ Sheet connection
│  │  ├─ Tab creation (main, horário, usuários)
│  │  └─ USUARIOS initialization
│  └─ Flask App Init (174-188)
│     ├─ CSRF Protection
│     ├─ Cache Setup
│     └─ Session Config
│
├─ 2️⃣ UTILIDADES & HELPERS (195-890)
│  │
│  ├─ 📧 Notificações (195-303)
│  │  ├─ enviar_notificacao_abertura_os() [195]
│  │  └─ enviar_notificacao_whatsapp_os() [308]
│  │
│  ├─ ✔️ Validação & Classes (385-530)
│  │  ├─ ValidacaoResultado [385]
│  │  ├─ ValidadorOS [432]
│  │  └─ ValidadorUsuario [512]
│  │
│  ├─ 👥 Gerenciamento de Usuários (540-715)
│  │  ├─ carregar_usuarios() [540]
│  │  ├─ salvar_usuarios() [625]
│  │  └─ deletar_usuario_sheets() [685]
│  │
│  ├─ 🔐 Decoradores (720-753)
│  │  ├─ login_required() [720]
│  │  └─ admin_required() [737]
│  │
│  ├─ 🎯 Validação & Sheet Utils (760-823)
│  │  ├─ validar_formulario() [760]
│  │  ├─ obter_proximo_id() [780]
│  │  └─ verificar_sheet_disponivel() [815]
│  │
│  └─ 💾 Cache Management (828-890)
│     ├─ obter_cache() [828]
│     ├─ salvar_cache() [850]
│     └─ limpar_cache() [870]
│
├─ 3️⃣ ROTAS - AUTENTICAÇÃO (900-960)
│  ├─ @app.route('/login') [900]
│  ├─ @app.route('/logout') [925]
│  └─ @app.route('/cadastro') [940]
│
├─ 4️⃣ ROTAS - FORMULÁRIOS & CHAMADOS (965-1320)
│  ├─ @app.route('/') [965]
│  ├─ @app.route('/enviar', POST) [980]
│  ├─ @app.route('/dashboard') [1060]
│  ├─ @app.route('/gerenciar') [1155]
│  ├─ @app.route('/atualizar_chamado', POST) [1245]
│  └─ @app.route('/sucesso') [1310]
│
├─ 5️⃣ ROTAS - ADMIN (710-800, 1320-1333)
│  ├─ @app.route('/usuarios', GET/POST) [710]
│  └─ @app.route('/admin/limpar-cache') [1320]
│
├─ 6️⃣ ROTAS - CONTROLE DE HORÁRIO (1335-1650)
│  ├─ @app.route('/controle-horario', GET/POST) [1335]
│  └─ @app.route('/health') [1640]
│
├─ 7️⃣ ROTAS - RELATÓRIOS & CONSULTAS (1655-2065)
│  ├─ @app.route('/relatorios') [1655]
│  ├─ @app.route('/tempo-por-funcionario') [1790]
│  └─ @app.route('/consultar', GET/POST) [1980]
│
├─ 8️⃣ ROTAS - UTILIDADES (2070-2074)
│  └─ @app.route('/favicon.ico') [2070]
│
└─ 🚀 PONTO DE ENTRADA (2080-2098)
   └─ if __name__ == '__main__': [2080]
```

---

## Fluxo de Execução

```
START: python app.py
  │
  ├─→ Import modules (linhas 1-51)
  ├─→ Setup logging (linhas 53-61)
  ├─→ Load credentials (linhas 65-105)
  ├─→ Connect to Google Sheets (linhas 110-155)
  ├─→ Create missing tabs (linhas 130-155)
  ├─→ Initialize Flask app (linhas 174-188)
  ├─→ Register all routes (linhas 900-2074)
  │
  └─→ app.run(port=5000)
        │
        ├─→ Listen on 0.0.0.0:5000
        ├─→ Print "Running on http://127.0.0.1:5000"
        └─→ Wait for requests...
```

---

## Requisição: GET /

```
Client Request: GET /
  │
  ├─→ @app.route('/') linha 965
  ├─→ homepage() função
  ├─→ render_template('index.html')
  │
  └─→ Response: 200 OK (index.html)
```

---

## Requisição: POST /enviar (Submeter Formulário)

```
Client Request: POST /enviar { formulário data }
  │
  ├─→ @app.route('/enviar', POST) linha 980
  ├─→ receber_requerimento() função
  │
  ├─ Passo 1: validar_formulario() [linha 760]
  │  └─ ValidadorOS.validar_formulario() [linha 432]
  │
  ├─ Passo 2: verificar_sheet_disponivel() [linha 815]
  │
  ├─ Passo 3: obter_proximo_id() [linha 780]
  │
  ├─ Passo 4: sheet.append_row() [salvar no Google Sheets]
  │
  ├─ Passo 5: enviar_notificacao_abertura_os() [linha 195]
  │  └─ Send email via SMTP
  │
  ├─ Passo 6: enviar_notificacao_whatsapp_os() [linha 308]
  │  └─ Send WhatsApp via Twilio
  │
  ├─ Passo 7: limpar_cache('dashboard') [linha 870]
  │
  └─→ Response: redirect('/sucesso')
```

---

## Requisição: POST /login

```
Client Request: POST /login { username, password }
  │
  ├─→ @app.route('/login', POST) linha 900
  ├─→ login() função
  │
  ├─ Passo 1: carregar_usuarios() [linha 540]
  │  └─ Get users from Google Sheets
  │
  ├─ Passo 2: check_password_hash(stored_pwd, input_pwd)
  │
  ├─ Passo 3: session['usuario'] = username
  ├─ Passo 4: session['role'] = user_role
  │
  └─→ Response: redirect('/dashboard')
```

---

## Estrutura de Dados

### Sheet Principal (SHEET_TAB_NAME)
```
Coluna A    B          C      D       E        ...
─────────────────────────────────────────────────
ID          Timestamp  Name   Sector Date     ...
────────────────────────────────────────────────
1           2026-01-01 João   TI     2026-01-01
2           2026-01-02 Maria  HR     2026-01-02
3           2026-01-03 Pedro  Sales  2026-01-03
```

### Sheet Usuários (SHEET_USUARIOS_TAB)
```
Username    Senha       Role
────────────────────────────
admin       admin123    admin
gestor      gestor123   admin
operador    op123       user
```

### Sheet Horário (SHEET_HORARIO_TAB)
```
Data       Funcionário  Pedido/OS  Tipo    Horário     Observação
─────────────────────────────────────────────────────────────────
2026-01-01 João         OS#1       Entrada 08:00:00    -
2026-01-01 João         OS#1       Saída   18:00:00    -
```

---

## Configuração de Ambiente

```
.env (gitignored)
├─ GOOGLE_SHEET_ID = "1qs3cxlklTnzCp4RpQGhxIrEF4CbeUvid1S0Cp2tC3Xg"
├─ GOOGLE_SHEET_TAB = "Respostas ao formulário 3"
├─ GOOGLE_SHEET_HORARIO_TAB = "Controle de Horário"
├─ GOOGLE_SHEET_USUARIOS_TAB = "Usuários"
├─ NOTIFY_ENABLED = "true"
├─ SMTP_SERVER = "smtp.gmail.com"
├─ SMTP_PORT = "587"
├─ SMTP_EMAIL = "seu_email@gmail.com"
├─ SMTP_PASSWORD = "sua_senha_app"
├─ SMTP_RECIPIENTS = "notificacoes@empresa.com"
├─ TWILIO_ACCOUNT_SID = "..."
├─ TWILIO_AUTH_TOKEN = "..."
├─ TWILIO_CONTENT_SID = "..."
└─ CACHE_TTL_SECONDS = "300"

credentials.json (gitignored)
└─ { JSON da Google Service Account }
```

---

## Fluxo de Erro

```
Erro na inicialização:
  │
  ├─ credentials.json não encontrado
  │  └─ logger.error() [linha 84]
  │  └─ sheet_error = "Arquivo não encontrado"
  │  └─ sheet = None
  │
  ├─ Credentials inválidas
  │  └─ logger.error() [linha 91]
  │  └─ sheet_error = "Erro ao carregar: ..."
  │  └─ sheet = None
  │
  └─ Sheet não encontrada
     └─ logger.error() [linha 105]
     └─ sheet_error = "Erro ao conectar: ..."
     └─ sheet = None
  
  ⚠️ Aplicação continua funcionando!
     └─ Renderiza templates mesmo sem sheet
     └─ Cache still works
     └─ Usuários carregados sob demanda (com fallback)
```

---

## Comandos Úteis no VS Code

| Atalho | Função | Exemplo |
|--------|--------|---------|
| `Ctrl+G` | Ir para linha | Ctrl+G → 195 (vai para notificações) |
| `Ctrl+F` | Buscar | Ctrl+F → @app.route (/dashboard) |
| `Ctrl+Shift+O` | Outline (structure view) | Ver todas as funções |
| `Ctrl+Shift+P` | Command palette | `Go to Line` |
| `Ctrl+H` | Find & Replace | Buscar + substituir |
| `Alt+Up/Down` | Mover linha | Reorganizar código |

---

## Convenções de Nomenclatura

```
Funções de notificação:
  enviar_notificacao_*()

Funções de cache:
  [obter|salvar|limpar]_cache()

Funções de usuário:
  [carregar|salvar|deletar]_usuario*()

Decoradores:
  @*_required()

Rotas:
  @app.route('/rota-nome', methods=[...])

Classes de validação:
  Validador*()
```

---

## Performance Notes

- Cache TTL: 300 segundos (configurável)
- Sheet requests são cached quando possível
- Notificações rodam em paralelo (não bloqueiam)
- Conexão com Google Sheets é feita uma vez na inicialização
- Usuários carregados sob demanda (não no startup)

---

## Segurança

- ✅ CSRF Protection ativada (WTF_CSRF_ENABLED = True)
- ✅ Session cookies seguros (HTTPONLY + SAMESITE)
- ✅ Senhas hasheadas com werkzeug.security
- ✅ Credentials em credentials.json (gitignored)
- ✅ Env vars em .env (gitignored)
- ✅ Login required no @decorador

---

**Última Atualização:** 2026-01-10
**Versão:** 2.0 (Reorganizada)
