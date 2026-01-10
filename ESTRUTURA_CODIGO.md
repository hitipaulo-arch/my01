# Estrutura do Código - app.py

## Organização por Seções

Guia completo de como o `app.py` está organizado para facilitar navegação e manutenção.

### 1. **IMPORTS & CONFIGURAÇÃO INICIAL** (linhas 1-166)
- **Imports stdlib**: datetime, pathlib, os, logging, smtplib, threading, secrets, functools
- **Imports third-party**: Flask, gspread, pandas, requests, werkzeug, flask_wtf, flask_caching
- **Logging setup**: Configuração de logs
- **Google Sheets**: Carregamento de credenciais, conexão com Google Sheets API
- **Flask app**: Inicialização, segurança (CSRF, session cookies)
- **Cache**: Configuração Flask-Caching e variáveis legadas

---

### 2. **UTILIDADES & HELPERS** (linhas 168-670)
#### 2.1 Notificações (linhas 168-426)
- `enviar_notificacao_abertura_os()`: Envia email de nova OS
- `enviar_notificacao_whatsapp_os()`: Envia WhatsApp via Twilio

#### 2.2 Classes de Domínio (linhas 428-505)
- `ValidacaoResultado`: Dataclass para resultado de validação
- `ValidadorOS`: Valida dados de nova OS
- `ValidadorUsuario`: Valida dados de usuário

#### 2.3 Gerenciamento de Usuários (linhas 507-643)
- `carregar_usuarios()`: Carrega usuários do Google Sheets
- `salvar_usuarios()`: Salva usuários no Google Sheets
- `deletar_usuario_sheets()`: Deleta usuário da planilha

#### 2.4 Decoradores (linhas 644-670)
- `login_required()`: Requer autenticação
- `admin_required()`: Requer role admin

#### 2.5 Validação & Sheet Utilities (linhas 720-823)
- `validar_formulario()`: Valida dados de formulário
- `obter_proximo_id()`: Obtém próximo ID de OS
- `verificar_sheet_disponivel()`: Verifica acesso à planilha
- `obter_cache()` / `salvar_cache()` / `limpar_cache()`: Gerenciamento de cache

---

### 3. **ROTAS - AUTENTICAÇÃO** (linhas 825-922)
- `@app.route('/login')` - Login (GET/POST)
- `@app.route('/logout')` - Logout
- `@app.route('/cadastro')` - Registro de novo usuário (GET/POST)

---

### 4. **ROTAS - FORMULÁRIOS & CHAMADOS** (linhas 924-1253)
- `@app.route('/')` - Página inicial / formulário
- `@app.route('/enviar')` - Submissão de formulário (POST)
- `@app.route('/dashboard')` - Dashboard de chamados
- `@app.route('/gerenciar')` - Gerenciamento de chamados
- `@app.route('/atualizar_chamado')` - Atualizar status de chamado (POST)
- `@app.route('/sucesso')` - Página de sucesso

---

### 5. **ROTAS - ADMIN & GESTÃO** (linhas 1255-1277)
- `@app.route('/usuarios')` - Gerenciamento de usuários
- `@app.route('/admin/limpar-cache')` - Limpar cache (GET/POST)

---

### 6. **ROTAS - CONTROLE DE HORÁRIO** (linhas 1279-1597)
- `@app.route('/controle-horario')` - Controle de horas (GET/POST)
- `@app.route('/health')` - Health check

---

### 7. **ROTAS - RELATÓRIOS & CONSULTAS** (linhas 1599-2021)
- `@app.route('/relatorios')` - Relatórios de OS
- `@app.route('/tempo-por-funcionario')` - Análise de tempo por funcionário
- `@app.route('/consultar')` - Consultar OS (GET/POST)

---

### 8. **ROTAS - UTILIDADES** (linhas 2023-2039)
- `@app.route('/favicon.ico')` - Ícone do navegador

---

## Padrões de Código

### Estrutura de Funções
```python
def funcao_exemplo(param: tipo) -> tipo_retorno:
    """Docstring com:
    - Propósito
    - Parâmetros
    - Retorno
    - Exceções (se relevante)
    """
    try:
        # Lógica
        return resultado
    except Exception as e:
        logger.error(f"Erro em funcao_exemplo: {e}")
        return None
```

### Estrutura de Rotas
```python
@app.route('/rota', methods=['GET', 'POST'])
@login_required  # Se necessário autenticação
def handler_rota():
    """Docstring clara do handler."""
    if request.method == 'POST':
        # Processa POST
        pass
    # Retorna template ou redirect
    return render_template(...)
```

---

## Fluxo de Dados

### Submissão de Formulário
1. Usuário acessa `/` e preenche formulário (`index.html`)
2. Formulário é enviado para `/enviar` (POST)
3. `receber_requerimento()` valida dados com `ValidadorOS`
4. Dados são salvos no Google Sheets (aba 'Respostas ao formulário 3')
5. Email é enviado via `enviar_notificacao_abertura_os()`
6. WhatsApp é enviado via `enviar_notificacao_whatsapp_os()`
7. Usuário é redirecionado para `/sucesso`

### Fluxo de Login
1. Usuário acessa `/login` e insere credenciais
2. Senha é verificada contra usuários do Google Sheets
3. Session é criada e usuário autenticado
4. Decorador `@login_required` garante acesso protegido

---

## Ambiente & Configuração

### Variáveis de Ambiente (.env)
- `GOOGLE_SHEET_ID`: ID da planilha Google
- `GOOGLE_SHEET_TAB`: Nome da aba principal
- `GOOGLE_SHEET_HORARIO_TAB`: Aba de controle de horário
- `GOOGLE_SHEET_USUARIOS_TAB`: Aba de usuários
- `NOTIFY_ENABLED`: Ativar/desativar notificações
- `SMTP_SERVER`: Servidor SMTP (Gmail)
- `SMTP_PORT`: Porta SMTP
- `SMTP_EMAIL`: Email de envio
- `SMTP_PASSWORD`: Senha de app (Gmail)
- `SMTP_RECIPIENTS`: Email(s) para notificação
- `TWILIO_ACCOUNT_SID`: Twilio account
- `TWILIO_AUTH_TOKEN`: Twilio token
- `TWILIO_CONTENT_SID`: Twilio template SID
- `CACHE_TTL_SECONDS`: TTL do cache

### Arquivos Críticos
- `credentials.json`: Credenciais Google Service Account (gitignored)
- `templates/`: HTML templates (Jinja2)
  - `index.html`: Formulário principal
  - `dashboard.html`: Dashboard de OS
  - `login.html`: Login
  - etc.

---

## Tips de Navegação

- Use `Ctrl+F` para buscar `@app.route` e encontrar rotas rapidamente
- Use `Ctrl+F` para buscar `def ` e encontrar funções
- Use `Ctrl+F` para buscar `class ` e encontrar classes
- Use `Ctrl+F` para buscar `# ---` para pular entre seções principais
