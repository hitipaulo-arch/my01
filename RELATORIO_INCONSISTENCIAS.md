# Relatório de Inconsistências — Repositório my01

**Data da análise:** 2026-09-09
**Branch:** `arena/01a08685-my01` (commit `5563522`)
**Escopo:** todos os arquivos versionados (código Python, templates, testes, docs, config, scripts).

## Metodologia

- `py_compile` em todos os `.py` — **sem erros de sintaxe**.
- Import real da aplicação (`python -c "import app"`) — **importa com sucesso**, 40 rotas registradas.
- `pytest tests/` — **8 passaram, 3 falharam**.
- `pyflakes` em app.py/appmodules/testes — acusou imports mortos, redefinições e 1 nome indefinido.
- Análise estática de: variáveis de ambiente (usadas × documentadas), endpoints (rotas × `url_for`/`href`/JS em templates), templates (include/extends/estáticos), documentação × realidade do código, duplicação de arquivos.

---

## Sumário executivo

| # | Achado | Severidade |
|---|--------|-----------|
| 1 | Rate limiting anunciado, mas **nunca ativo** (`Limiter` indefinido + config inválida + lib fora do requirements) | Alta |
| 2 | Refatoração para `appmodules/` **incompleta**: app.py mantém cópias locais que **sombreiam** os imports dos módulos novos; funções "extraídas" têm **zero chamadores** em produção | Alta |
| 3 | **3 testes commitados falham** no checkout limpo (`tests/test_admin_ai_chat.py`) — fluxo de autenticação real × suposição dos testes | Alta |
| 4 | `.env.bak` **commitado** com segredos (webhook token/secret, sheet id) — foge do `.gitignore` e está **desatualizado** vs `.env.example` | Alta (segurança) |
| 5 | **Orquestração de env vars do WhatsApp inconsistente**: `WHATSAPP_ENABLED=true` nunca é lida; gates usam `WHATSAPP_WEB_ENABLED` com **defaults divergentes** entre serviços | Média |
| 6 | `.env.example` omite ~20 variáveis usadas pelo código e contradiz `.env.bak` (cache Redis × SimpleCache) | Média |
| 7 | Arquivos mortos/duplicados versionados: shims na raiz, `report_logic.py` obsoleto, `temp_script.js`, `centrais_preview.txt`, suíte de testes legada na raiz | Média |
| 8 | Documentação desatualizada/contraditória (README cita **Twilio**, docs afirmam "testes 100%", "5 testes") | Média |
| 9 | Inconsistências pontuais: classe (não instância) em `app.config`, TTL fixo duplicado, Bootstrap/Chart.js com versões misturadas, `requirements.txt` com linhas duplicadas | Baixa |

---

## 1. Rate limiting silenciosamente morto (app.py)

- `app.py:110` usa `Limiter(app, **limiter_config)` mas **`Limiter` nunca é importado** — o `pyflakes` acusa `undefined name 'Limiter'` (`app.py:110:15`).
- O `try/except` genérico em volta **engole o `NameError`**, e o app loga `"Flask-Limiter não disponível. Instale 'Flask-Limiter'..."` mesmo quando o pacote está instalado — diagnóstico enganoso.
- `limiter_config = {'min_requests': 5, 'seconds': 60}` (config.py) **não são parâmetros válidos** do construtor do Flask-Limiter (espera `key_func`, `storage_uri`, etc.), então mesmo importando, falharia.
- `flask-limiter` **não está em `requirements.txt`**.

**Efeito:** a proteção contra força bruta em `/login` e `/cadastro` (prevista em `app.py:190-199`) **nunca opera** em nenhum ambiente.

**Correção:** importar `Limiter` (de forma opcional), corrigir a config (`Limiter(app, key_func=..., storage_uri=...)`), adicionar `Flask-Limiter` ao requirements ou remover o código morto e o aviso enganoso.

---

## 2. Refatoração incompleta: cópias locais sombreiam módulos extraídos

`app.py:64-72` importa de `appmodules/utils/validators.py` e `formatters.py`:

```python
from appmodules.utils.validators import (_parse_int_field, _validate_item_form_data, _validate_user_payload)
from appmodules.utils.formatters import (_format_codigo_code, _format_mtc_code, _append_producao_info)
```

Porém `app.py` **redefine os mesmos nomes** logo adiante, então os imports **nunca são usados** (o pyflakes confirma: `redefinition of unused '_...' from line 64/69`):

- `app.py:485` `_parse_int_field`
- `app.py:657` `_format_codigo_code` / `app.py:686` `_format_mtc_code` / `app.py:692` `_append_producao_info`
- `app.py:706` `_validate_item_form_data` / `app.py:748` `_validate_user_payload`

Agravante: as versões **divergiram de comportamento**:

| Função | Versão em `appmodules/utils` | Versão viva em `app.py` |
|---|---|---|
| `append_producao_info` | recebe **dict** e enriquece com "Percentual Produção" | recebe **2 strings** e concatena (`existing/nova`) |
| `validate_user_payload` | recebe **dict** `{username,email,role}` | recebe `(username, senha, role)` e **agrega todas** as mensagens de erro |
| `validate_item_form_data` | retorna **1º erro** apenas | agrega múltiplos erros numa mensagem só |

Além disso, **nenhum código em produção chama as versões de `appmodules/utils`** (grep confirmou zero chamadores fora de app.py/testes). Ou seja: os módulos "extraídos" são código morto, sem testes, com semântica própria — e os testes commitados (`tests/test_backend_validations.py`) cobrem exatamente as cópias locais de app.py (assinatura `username, senha, role`), não as dos módulos.

**Efeito:** manutenção dupla; correção num dos lugares não propaga; risco de alguém "consertar" o módulo e nada mudar.

**Correção:** escolher uma fonte única (ideal: `appmodules/utils`), remover as defs locais de app.py e ajustar os testes/imports.

---

## 3. Testes commitados que falham no checkout limpo

`python -m pytest tests/ -q` → **3 failed, 8 passed**:

```
FAILED tests/test_admin_ai_chat.py::AdminAIChatTests::test_admin_ai_page_renders
FAILED tests/test_admin_ai_chat.py::AdminAIChatTests::test_admin_ai_keeps_chat_history_in_session
FAILED tests/test_admin_ai_chat.py::AdminAIChatTests::test_admin_ai_summary_action_uses_default_prompt
```

**Causa raiz:** os testes setam apenas `session["usuario"]="admin"` / `session["role"]="admin"` e esperam `200`. Mas `/admin/ia` usa `@admin_required` (appmodules/utils/decorators.py), que **consulta o Google Sheets** (`user_service.get_usuario("admin")`). Sem `credentials.json`/planilha configurada, `get_usuario` retorna `None` e a rota redireciona (`302`) para `/`.

Ou seja: **o teste assume autenticação só por sessão; a aplicação exige que o usuário exista na aba "Usuários" da planilha**. É uma divergência de contrato entre a suíte e o comportamento real, e os testes não rodam sem credenciais externas.

Relacionado (mesmo modelo híbrido de auth, comportamento inconsistente entre rotas):
- `app.py:775-796` `_get_current_user_role()` — quando o usuário da sessão não é encontrado no service, **`session.clear()`** (derruba o usuário sem aviso).
- Rotas com `@login_required` apenas (`/producao`, `/itens`) tratam papel como *read-only* consultando a planilha a cada request; rotas com `@admin_required` (`/admin/ia`, `/relatorios`, `/ferramentas`, `/centrais`, `/usuarios`) redirecionam para a home.
- Com `sheets_service` indisponível, `/os-abertas` devolve **503**, enquanto `/producao` renderiza a página em modo somente-leitura — comportamentos de falha diferentes para a mesma condição.

**Correção:** decidir um modelo único de autorização (sessão × planilha), tratar usuário inexistente sem derrubar a sessão silenciosamente e fazer os testes injetarem um `user_service` fake (ou marcar os 3 testes como `skip` quando não há credenciais).

---

## 4. `.env.bak` commitado com segredos e desatualizado

- `.env.bak` está no **git tracking** (e em qualquer histórico anterior), embora o `.gitignore` ignore `.env` e `credentials.json`. Backup de ambiente não é segredo versionável.
- Contém valores com cara de produção: `WHATSAPP_WEBHOOK_TOKEN`, `WHATSAPP_WEBHOOK_SECRET` e `GOOGLE_SHEET_ID` idênticos aos do `.env.example` (que deveria conter só placeholders — o próprio cabeçalho do `.env.example` diz "NÃO COMITAR suas chaves reais").
- **Recomendação:** remover `.env.bak` do repositório (`git rm --cached`), substituir segredos reais por placeholders no `.env.example` e **rotacionar token/secret** se já circularam.
- `.env.bak` está **defasado**: `CACHE_TYPE=SimpleCache` e sem as chaves Redis/`WHATSAPP_WEB_*` que o `.env.example` documenta — duas "fontes da verdade" divergentes para configuração.

---

## 5. Flags de WhatsApp inconsistentes (código × `.env.example`)

- `WHATSAPP_ENABLED=true` (`.env.example:64` e `.env.bak:43`) — **nenhum código lê essa variável** (grep confirmou). É a única chave documentada e não usada.
- Os gates reais usam `WHATSAPP_WEB_ENABLED`, mas com **defaults divergentes**:
  - `whatsapp_web_service.py:47` → default **`false`**;
  - `whatsapp_click_to_chat.py:27` → default **`true`**;
  - `notification_service.py` (`notificar_finalizacao_os`) → default **`true`**.
- Efeito: ambiente **sem** `.env` liga o Click-to-Chat (que abre navegador) e desliga o WhatsApp Web; ambiente **com** `.env.example` faz o contrário (`WHATSAPP_WEB_ENABLED=false` desliga o Click-to-Chat também, e `WHATSAPP_ENABLED=true` não liga nada).
- `WhatsAppClickToChatService` usa `WHATSAPP_WEB_TO` e `WHATSAPP_WEB_DELAY_SECONDS` (variáveis do "Web") e envia para o **número fixo** interno, não para o solicitante — semântica de variável sobreposta entre mecanismos diferentes.
- O Click-to-Chat chama `os.startfile`/`webbrowser.open` a cada OS nova (whatsapp_click_to_chat.py:60-71) — coerente com uso local em PC Windows (run_server.bat/ngrok), **inadequado para o deploy no Render** citado no README/Procfile. É uma ambiguidade de arquitetura não documentada (qual é o ambiente alvo?).

**Correção:** unificar em `WHATSAPP_ENABLED` (documentada) + flags específicas por mecanismo com defaults explícitos e consistentes; documentar o ambiente-alvo (desktop local × servidor).

---

## 6. Variáveis de ambiente: documentação × código

Comparação `os.getenv(...)` em todo o código × chaves do `.env.example`:

- **Usadas no código, ausentes no `.env.example` (~20):** `APP_ENV`, `FLASK_ENV`, `CACHE_KEY_PREFIX`, `GOOGLE_SHEET_PRODUCAO_TAB`, `GOOGLE_SHEET_CENTRAIS_TAB`, `GOOGLE_SHEET_FERRAMENTAS_TAB`, `GOOGLE_SHEET_HISTORICO_FERRAMENTAS_TAB`, `ITEM_ALERT_THRESHOLD`, `LOG_LEVEL`, `LOCAL_ADMIN_USER`, `LOCAL_ADMIN_PASSWORD`, `LOCAL_ADMIN_ROLE`, `ALLOW_LOCAL_ADMIN_FALLBACK`, `NVIDIA_API_KEY`, `SMTP_RECIPIENTS`, `NOTIFICATION_MAX_WORKERS`, `SHEETS_MAX_RETRIES`, `SHEETS_RETRY_INITIAL_DELAY`, `SHEETS_RETRY_BACKOFF`, `WHATSAPP_FROM`, `WHATSAPP_WEB_DELAY_SECONDS`, `WHATSAPP_MAX_PAYLOAD_BYTES`.
- **Documentadas e não usadas:** `WHATSAPP_ENABLED` (ver seção 5).
- `Config.CACHE` (config.py) **auto-detecta** Redis (`CACHE_TYPE` vazio → vira `RedisCache` se `REDIS_URL`/`REDIS_HOST` existir), mas o `.env.example` fixa `CACHE_TYPE=RedisCache` + `REDIS_URL=redis://localhost:6379/0` — em deploy Render **sem Redis**, isso aponta para `localhost:6379` e toda operação de cache pode falhar/atrasar (as chamadas são resilientes com try/except, mas degradam).
- `.env.bak` (SimpleCache) representa o que provavelmente roda de fato — outra contradição com o `.env.example`.

---

## 7. Arquivos mortos, duplicados ou "lixo" versionado

| Arquivo | Problema |
|---|---|
| `centrais_repository.py` (raiz) | shim de compatibilidade — **ninguém importa** (app.py usa `appmodules.repositories`) |
| `report_logic.py` (raiz) | **cópia antiga/obsoleta** (~230+ linhas divergentes) do `appmodules/logic/report_logic.py` — ninguém importa (app.py:57 usa o módulo) |
| `temp_script.js` (14 KB) | sem nenhuma referência em templates/código — sobra de sessão de desenvolvimento |
| `centrais_preview.txt` | idem, sem referências |
| `test_*.py` na raiz (8 arquivos) | suíte **legada sobreposta** a `tests/` (3 arquivos): `test_functional.py`, `test_integration.py`, `test_medium_priority.py` são scripts de verificação com `print`/asserts soltos; `test_api_chat*.py` e `test_nvidia_real_api.py` exigem **servidor vivo/API real**; alguns citam **Twilio**, que não existe mais no código |
| Docs `.md` na raiz (16+ arquivos) | vários resumos da mesma entrega com **estágios diferentes** (ver seção 8) |

`requirements.txt` também tem **linhas duplicadas** (`python-dateutil`, `Werkzeug`, `requests`, `qrcode[pil]`, `pywhatkit` aparecem 2×).

---

## 8. Documentação contraditória

- `CHECKLIST_FINAL.md:198` → "Testes passando: **100%**"; `VALIDATION_POST_CLEANUP.md:57,86` → "**5 testes** localizados" — realidade no checkout: **11 arquivos de teste, 3 falhando**.
- `README.md` (seção "WhatsApp (Twilio API)", com `ContentSid`/templates Twilio) descreve uma integração **que não existe no código** — o `.env.example` e os guias novos dizem "(sem Twilio)". Também há 2 guias WhatsApp na raiz citando Twilio.
- `CLEANUP_SUMMARY.md` afirma que scripts obsoletos foram removidos ("usar pytest ao invés") — mas os `test_*.py` da raiz continuam versionados.
- `app.py` (1696 linhas) mantém toda a lógica de producao/itens/ferramentas/usuários/IA, apesar da organização em `appmodules/` — o próprio docstring em `app.py:430` diz que a lógica de relatórios "foi movida para appmodules", mas os utilitários continuam duplicados (seção 2).
- `app.py:123` faz `app.config["notification_service"] = NotificationService` — guarda **a classe**, não uma instância; o único consumidor real (`os_routes.py`) importa a classe diretamente. Config morta/enganosa.
- `@cache.cached(timeout=300)` fixo em `app.py:430` duplica a constante `CACHE_TTL_SECONDS`/`CACHE_DEFAULT_TIMEOUT` da config — drift quando um mudar sem o outro.

## 9. Inconsistências cosméticas (templates)

- **Bootstrap misturado:** `login.html` e `cadastro.html` usam **5.1.3**; as demais 20 páginas usam **5.3.3** (CSS e JS bundle) — comportamento/estilos podem diferir entre páginas de auth e o resto.
- **Chart.js:** `relatorios.html` e `tempo_por_funcionario.html` usam `chart.js` (última versão via CDN); `dashboard_producao.html` usa **4.4.1 pinado**.
- `centrais_bp` registra `template_folder="../../templates"` (appmodules/routes/centrais_routes.py:17-18) desnecessariamente — os demais blueprints não fazem isso e o app já resolve os templates pela raiz. Inofensivo, mas revela padrões divergentes.

---

## Pontos que se mostraram consistentes (para contexto)

- Todos os `.py` compilam; o app importa e registra 40 rotas sem erro.
- Todos os endpoints referenciados em templates via `url_for`, `href` e JS (`/producao/dados`, `/atualizar_chamado`, `/enviar`, etc.) **existem** no mapa de rotas.
- Todos os `{% include %}` apontam para `_top_nav.html`, que existe.
- Não há referência a templates inexistentes; `static/unified.css` é referenciado de forma uniforme.
- Webhook do WhatsApp exige `WHATSAPP_WEBHOOK_SECRET` em produção e desliga-se sem token — tratamento de segurança coerente.
- `atexit` registra o shutdown do executor de notificações corretamente.

---

## Recomendações priorizadas

1. **Segurança:** `git rm --cached .env.bak`; trocar valores reais por placeholders no `.env.example`; rotacionar `WHATSAPP_WEBHOOK_TOKEN/SECRET` se já expostos em repositório compartilhado.
2. **Rate limiting:** consertar ou remover o bloco `Limiter` (import + config válida + requirements).
3. **Refatoração:** eleger `appmodules/utils/*` como fonte única; apagar as defs duplicadas de app.py; realinhar testes.
4. **Testes:** fazer `tests/test_admin_ai_chat.py` usar um `user_service` fake; unificar suítes em `tests/` e remover os scripts raiz legados; adicionar CI (`pytest`).
5. **Env/flags WhatsApp:** unificar variáveis e defaults; documentar as ~20 variáveis órfãs; reconciliar `.env.example` × `.env.bak` × config.py (Redis auto-detect).
6. **Limpeza:** remover `temp_script.js`, `centrais_preview.txt`, shims e `report_logic.py` da raiz; deduplicar `requirements.txt`; padronizar versões de CDN nos templates.
7. **Docs:** atualizar README (remover Twilio), consolidar os múltiplos `.md` de resumo e corrigir as afirmações de "testes 100%".

---

## ✅ Correções executadas (2026-09-09)

| # | Inconsistência | Ação aplicada | Verificação |
|---|----------------|---------------|-------------|
| 1 | Rate limiting morto | `Limiter` importado corretamente (`flask_limiter.util.get_remote_address`), storage Redis em produção / memória em dev, limites `5/minute` (login) e `3/minute` (cadastro) aplicados **somente a POST**; `Flask-Limiter>=3.5` adicionado ao requirements; `limiter_config` inválido removido do config.py | Boot loga "Flask-Limiter inicializado"; 6º GET não é limitado; limites ativos no endpoint |
| 2 | Duplicação utils × app.py | `appmodules/utils/validators.py` e `formatters.py` viraram **fonte única** com o comportamento que era o vivo no app.py; 7 defs locais removidas de app.py (−118 linhas) | `pyflakes` limpo; app importa; testes passam |
| 3 | Testes admin/IA falhando | `tests/test_admin_ai_chat.py` injeta `user_service` fake no `setUp` (restaura no `tearDown`) | `pytest tests/` → **11 passed** |
| 4 | `.env.bak` commitado | Removido do tracking (`git rm --cached`) e adicionado ao `.gitignore`; valores sensíveis (token/secret/números) trocados por placeholders no `.env.example` | `git status` sem `.env.bak`; arquivo preservado localmente |
| 5 | Flags WhatsApp inconsistentes | Click-to-Chat passa a respeitar `WHATSAPP_ENABLED` (master) com fallback `WHATSAPP_WEB_ENABLED`, default `false`; número fixo `5512982200009` removido do código (destino vem só de env); `notificar_finalizacao_os` com defaults alinhados; docstrings esclarecem uso desktop vs servidor | Smoke test: sem env → `False`; master=true → `True` |
| 6 | TTLs/env duplicados | TTLs de OS/produção/usuários centralizados em `Config.CACHE`; sheets_service/user_service/decorators (`relatorios`, `producao/dados`) usam a constante em vez de `timeout` fixo ou `os.getenv` esparso | App importa; testes passam |
| 7 | Lixo versionado | Removidos `centrais_repository.py` (shim), `report_logic.py` (cópia antiga), `temp_script.js`, `centrais_preview.txt` | `git status` confirma remoção |
| 8 | `.env.example` incompleto/contraditório | Adicionadas ~20 variáveis usadas pelo código; `CACHE_TYPE=` vazio (auto-detect), Redis comentado com instrução; seção WhatsApp reescrita com chaves reais; `WHATSAPP_ENABLED` documentada com papel correto | `comm` env usado × documentado reduzido a poucos casos opcionais |
| 9 | Docs contraditórios | README: seção Twilio substituída pela implementação real (Click-to-Chat / WhatsApp Web / Webhook); CHECKLIST_FINAL/VALIDATION_POST_CLEANUP/CLEANUP_SUMMARY receberam aviso de "marco histórico" apontando para estado vigente | `grep TWILIO_` → só menção na nota de deprecação |
| 10 | CDNs/templates | Bootstrap 5.1.3 → 5.3.3 em `login.html`/`cadastro.html`; Chart.js pinado em `4.4.1` (antes `latest`) em `relatorios.html`/`tempo_por_funcionario.html` | `grep` sem 5.1.3/chart.js solto |
| 11 | requirements duplicado | `requirements.txt` reescrito sem duplicatas (python-dateutil, Werkzeug, requests, qrcode, pywhatkit apareciam 2×) | `sort | uniq` ok |
| 12 | Config enganosa | `app.config["notification_service"] = NotificationService` (classe) removido; import sem uso removido; `current_app` não usado em error_helpers removido; default de `_is_production()` alinhado ao app.py | `pyflakes` limpo |

### Verificação final
- `python -m py_compile` (app.py, config.py, appmodules/, tests/) → OK
- `python -m pyflakes app.py config.py appmodules/ tests/` → limpo
- `pytest tests/ -q` → **11 passed**
- Boot real (`import app`) → OK, 40 rotas, Flask-Limiter inicializado

### Pendências (decisão do usuário)
- **Rotacionar** `WHATSAPP_WEBHOOK_TOKEN/SECRET` se já circularam em repositório compartilhado (troquei por placeholders no `.env.example`, mas o valor antigo permanece no histórico git e no `.env.bak` local).
- Documentação de guias (`.md` de WhatsApp/README de rotas) ainda cita o número real `5512982200009` em exemplos — mantive por serem históricos; troque se desejar.
- Suíte legada `test_*.py` na raiz (8 arquivos, alguns exigem servidor/API real) permanece — recomendo mover/excluir num commit separado para não perder histórico de uso.

---

## 🧪 Rodada de testes de funcionamento (2026-09-09)

O app foi executado de verdade (dev server em `0.0.0.0:5000`, admin local via
`ALLOW_LOCAL_ADMIN_FALLBACK`, sem `credentials.json`) e exercitado de ponta a ponta.

### Novo bug funcional encontrado e corrigido

- **`GET /tempo-por-funcionario` retornava 500** para qualquer admin logado: a
  rota era um *stub* que passava `chart_data={}`/nenhuma variável, enquanto o
  template exige `chart_data.bar_labels`, `page`, `per_page`, etc.
- **Correção:** o `MetricsService` (que estava morto/duplicado) ganhou o método
  `calcular_tempo_por_funcionario()` — agrega pares entrada/saída por
  funcionário/OS/dia a partir de `sheets_service.get_time_records()`, enriquece
  com urgência da OS, aplica filtros (funcionário, OS, período), paginação e
  monta os dados dos gráficos. A rota passou a ler filtros, paginar e exportar
  **CSV** (e XLSX quando `openpyxl` existir, com aviso gracioso caso contrário).
- `MetricsService` exportado em `appmodules/services/__init__.py`.

### Resultado dos testes

| Suíte | Qtd | Resultado |
|---|---|---|
| `tests/` (pytest — inclui 10 novos casos de tempo/rota) | 21 | ✅ todos passam |
| Scripts legados raiz (security, webhook, integration, medium_priority, functional) | 32 | ✅ todos passam |
| Smoke E2E contra servidor vivo (`tests/e2e_live_smoke.py`) | 28 | ✅ todos passam |

Smoke E2E cobre: formulário público, login (CSRF presente/ausente, senha
errada/correta), 16 páginas protegidas, exportação CSV, chat IA com erro
gracioso, `/health`, estático, 404, logout e **rate limit (429)**.

### Observações da execução real (ambiente sem Google Sheets)

- `/health` → `{"status": "degraded", "sheets_connected": false}` (esperado sem credenciais).
- Páginas que dependem de Sheets (`/relatorios`, `/ferramentas`, `/centrais`,
  `/dashboard-producao`, `/tempo-por-funcionario`, ...) renderizam **estado
  vazio sem 500**; `/os-abertas` retorna 503 conforme o design atual.
- `POST /producao` sem Sheets: redireciona com mensagem, **sem traceback**.
- `POST /admin/ia` sem `NVIDIA_API_KEY`/`openai`: página 200 com erro amigável.
- Fluxos com dados reais (criação de OS, produção, leitura de planilha, envio
  WhatsApp, exportação com conteúdo) **não puderam ser exercitados** por falta
  de `credentials.json` + planilha — exigem configuração real.
