# Comparação: Repositório Local × GitHub (hitipaulo-arch/my01)

**Data:** 2026-09-09
**Remote:** `https://github.com/hitipaulo-arch/my01.git` — **repositório PÚBLICO**
**GitHub (main):** commit `5563522` ("feat: atualizar chat administrativo e organizar modulos")
**Local (branch da sessão `arena/01a08685-my01`):** commit `e8e36da` (= `5563522` + **2 commits de correção**)

> Os arquivos anexados pelo usuário correspondem ao estado **do GitHub** (`5563522`):
> estão lá `temp_script.js`, `centrais_preview.txt`, os `.md` de resumo e o
> `README.md` com a seção Twilio — tudo que foi removido/corrigido localmente.

---

## 1. Situação geral

| | GitHub `origin/main` | Local `arena/...` |
|---|---|---|
| Último commit | `5563522` | `e8e36da` (`5563522` + 2 commits) |
| Contém as correções da análise? | ❌ Não | ✅ Sim |
| Contém `.env.bak` com segredos? | ⚠️ **Sim, no tree** | ✅ Removido do tracking |
| `tests/` passa? | ❌ 3 falhas | ✅ 21 passed + 28 E2E |
| Rate limiting ativo? | ❌ Morto (`Limiter` indefinido) | ✅ Ativo |
| `requirements.txt` | Duplicado, sem Flask-Limiter | ✅ Limpo |
| Repo visível publicamente | ⚠️ **Público** | — |

**Resumo:** o GitHub está exatamente no estado pré-correção. Nada do que foi
corrigido localmente chegou lá (2 commits locais não publicados).

---

## 2. 🚨 Segurança — segredos expostos no repositório PÚBLICO

O arquivo **`.env.bak` está commitado no `origin/main`** do repositório
**público** e contém valores reais (verificados via `git show origin/main:.env.bak`):

| Chave | Valor no GitHub | Risco |
|---|---|---|
| `GOOGLE_SHEET_ID` | `1qs3cxlklTnzCp4RpQGhxIrEF4CbeUvid1S0Cp2tC3Xg` (real) | Expõe o ID da planilha (dá pra tentar acesso p/ qualquer um) |
| `WHATSAPP_WEBHOOK_SECRET` | `QBxQW3lFFcMqGvezQEZJvkVhA-VkPMeUVJqJi9ECn9I` (real) | Assinatura HMAC do webhook comprometida |
| `WHATSAPP_WEBHOOK_FROM` | `5512982200009` (número real) | Número autorizado do webhook exposto |
| `SECRET_KEY` / `WHATSAPP_WEBHOOK_TOKEN` | placeholders (`SUBSTITU...`, `gere_um_...`) | OK (placeholder) |

Como o repo é **público**, esses valores estão acessíveis a qualquer pessoa na
internet, inclusive no **histórico** de commits (remover o arquivo do tree não
apaga do histórico).

**Recomendações imediatas:**
1. Rotacionar `WHATSAPP_WEBHOOK_SECRET` e o número/credenciais associadas ao
   webhook e ao Google Sheets (service account) se usarem o mesmo sheet ID.
2. Remover `.env.bak` do tree do GitHub (o commit local `2b18db6` já faz isso —
   falta publicar).
3. Para remover do **histórico**: `git filter-repo`/BFG + `git push --force`
   (avaliar custo x benefício; o ideal é rotacionar os segredos de qualquer forma).
4. Considere tornar o repo **privado**.

> Nota: o `credentials.json` anexado pelo usuário **não está** no GitHub
> (só `credentials.json.example` com placeholders) — bom sinal. Mantenha-o fora
> do git (o `.gitignore` já cobre `*.json`).

---

## 3. O que mudou localmente e ainda não está no GitHub

```
D  .env.bak                        → removido do tracking (segredos fora do git)
D  centrais_preview.txt            → lixo removido
D  centrais_repository.py (raiz)   → shim sem uso removido
D  report_logic.py (raiz)          → cópia obsoleta removida
D  temp_script.js                  → sobra de dev removida
M  app.py                          → −298 linhas líquidas: rate limit OK, utils
                                     centralizados, /tempo-por-funcionario real
M  appmodules/utils/{validators,formatters}.py → fonte única (código vivo movido p/ cá)
M  appmodules/services/*           → TTLs centralizados, flags WhatsApp coerentes,
                                     MetricsService exportado + funcional
M  config.py                       → TTLs por tipo em Config.CACHE; limiter_config removido
M  requirements.txt                → sem duplicatas + Flask-Limiter
M  README.md                       → seção Twilio (inexistente no código) removida
M  .env.example                    → sanitizado (placeholders) + ~20 chaves que faltavam
M  .gitignore                      → + .env.bak
M  templates/{login,cadastro,relatorios,tempo_por_funcionario}.html → CDNs pinadas 5.3.3/4.4.1
M  CHECKLIST_FINAL.md / CLEANUP_SUMMARY.md / VALIDATION_POST_CLEANUP.md → aviso de marco histórico
A  RELATORIO_INCONSISTENCIAS.md    → relatório da análise
A  tests/test_tempo_funcionario.py → 10 testes unitários + 4 de rota (novos)
A  tests/e2e_live_smoke.py         → smoke E2E contra servidor vivo (28 checks)
M  tests/test_admin_ai_chat.py     → user_service fake (3 testes voltaram a passar)
```

### Arquivos que continuam iguais (sem divergência)
`runtime.txt`, `Procfile`, `config.py` (parcial), templates restantes,
`appmodules/routes/*`, `appmodules/models/*`, `appmodules/repositories/*`,
`appmodules/logic/*`, `static/unified.css`, `tests/` antigos, `.github/`,
`credentials.json.example`, scripts `.bat/.ps1`, docs restantes.

---

## 4. Divergências GitHub → local (detalhe por arquivo de configuração)

### requirements.txt
- **GitHub:** linhas duplicadas (`python-dateutil`, `Werkzeug`, `requests`,
  `qrcode[pil]`, `pywhatkit` 2×) e **sem Flask-Limiter**.
- **Local:** deduplicado e com `Flask-Limiter>=3.5,<4.0.0`.

### .env.example
- **GitHub:** `GOOGLE_SHEET_ID` real + `WHATSAPP_WEBHOOK_SECRET` real (não é
  exemplo!), `CACHE_TYPE=RedisCache` fixo com `REDIS_URL` apontando p/ localhost,
  sem ~20 chaves usadas pelo código, sem abas de Produção/Centrais/Ferramentas.
- **Local:** placeholders em todos os segredos, `CACHE_TYPE=` vazio (auto-detect),
  Redis comentado, chaves de Sheets/WhatsApp/IA/fallback local documentadas.

---

## 5. Diferença de comportamento (o que o GitHub ainda tem de errado)

| Bug | GitHub | Local |
|---|---|---|
| `Limiter` usado sem import → rate limit nunca ativa | ❌ presente | ✅ corrigido |
| `login`/`cadastro` sem proteção contra brute-force | ❌ | ✅ 5/min e 3/min em POST |
| `app.py` importa utils e redefine tudo (sombra) | ❌ presente | ✅ fonte única |
| `tests/test_admin_ai_chat.py` (3 testes) | ❌ falham | ✅ passam (fake user_service) |
| `GET /tempo-por-funcionario` p/ admin logado | ❌ **500** | ✅ 200 (página funcional + CSV/XLSX) |
| Click-to-Chat ligado por padrão + número fixo hardcoded | ❌ | ✅ desligado por padrão, sem número fixo |
| TTLs de cache espalhados (timeout fixo + env) | ❌ | ✅ centralizados em Config.CACHE |
| `.env.bak` + segredos no repo público | ❌ presente | ✅ removido do tracking |

---

## 6. Recomendações / próximos passos

1. **Segurança primeiro:** rotacionar `WHATSAPP_WEBHOOK_SECRET` e validar o
   acesso da service account à planilha `1qs3...` (se a planilha for privada, o
   ID exposto sozinho não permite acesso — a service account precisa estar
   compartilhada com ela). Tornar o repo privado se for caso.
2. **Publicar as correções:** `git push origin arena/01a08685-my01` + PR para
   `main` (2 commits: `2b18db6`, `e8e36da`). É o único caminho para o GitHub
   sair do estado com bugs.
3. **Opcional:** purgar `.env.bak` do histórico (BFG/filter-repo) se desejar
   que os segredos não fiquem acessíveis no histórico público.
4. **Rodar com dados reais:** com o `credentials.json` em mãos, é possível
   subir o app conectado à planilha e exercitar fluxos reais (criar OS, produção,
   relatórios). Isso escreveria na planilha — recomendo uma planilha de teste
   (basta apontar `GOOGLE_SHEET_ID`) antes de usar a de produção.
