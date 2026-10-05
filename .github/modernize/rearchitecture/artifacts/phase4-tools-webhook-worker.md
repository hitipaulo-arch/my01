# Fase 4 — Repositories de ferramentas e blueprints de ferramentas/webhook

## Summary
Extraídas as operações de ferramentas para repository, criados os blueprints de ferramentas e webhook, registrada uma fachada fina de produção e removidas regras duplicadas da factory.

## Upstream Artifacts Consumed
- `/memories/session/plan.md` — escopo, contratos e ordem da extração.
- `.github/modernize/rearchitecture/artifacts/phase3-production-purchases-worker.md` — estado da factory e risco residual de ferramentas.
- `.github/modernize/rearchitecture/learnings/modernize-rearchitecture-worker/production-purchases-blueprints.md` — regra de aliases dentro do blueprint.
- `.github/modernize/rearchitecture/learnings/modernize-rearchitecture-worker/admin-blueprint-endpoint-compat.md` — referência de compatibilidade de endpoints; supersedida nesta fase pela exigência explícita de zero URLs duplicadas.

## Evidence Mapping
- `plan.md#22-25` -> `appmodules/repositories/ferramentas_repository.py`, `appmodules/routes/ferramentas_routes.py`, `appmodules/routes/webhook_routes.py` e registro na factory.
- `plan.md#26,53-57` -> exports/aliases públicos em `app.py` e `appmodules/repositories/__init__.py`, sem duplicação de lógica.
- `phase3-production-purchases-worker.md#Residual Risk` -> stubs de ferramentas substituídos pelas implementações do commit-base.

## Route Map Verification
- Command: script Python de inspeção de `app.app.url_map` com métodos por rota e agrupamento por `(path, methods)`.
- Route count: 39.
- Duplicate route keys: 0.
- Confirmadas: `/ferramentas` GET/POST, `/ferramentas/atualizar/<int:row_id>` POST, `/ferramentas/deletar/<int:row_id>` POST, `/ferramentas/historico` GET e `/webhook/whatsapp` GET/POST.
- Favicon preservado em `/favicon.ico`; handlers globais permanecem na factory.

## Test Results
- Command: `python -m compileall app.py appmodules`
- Passed: compilação concluída
- Failed: 0
- Skipped: 0
- Command: `python -m pytest -q`
- Passed: 46
- Failed: 1
- Skipped: 0
- Failure: `test_nvidia_real_api.py::AdminAIChatRealAPITests::test_admin_ai_with_real_nvidia_api`; NVIDIA API/local service recusou conexão (`WinError 10061`), sem relação com os arquivos migrados.
- Command: script Python de compatibilidade de imports públicos
- Result: `PUBLIC_IMPORTS_OK`.

## Compatibility Notes
- `app.py` continua exportando `ferramentas`, `atualizar_ferramenta`, `deletar_ferramenta`, `historico_ferramentas`, `webhook_whatsapp` e as quatro funções de repository por aliases simples.
- Nomes de abas e headers de ferramentas/histórico foram preservados.
- Templates administrativos usam endpoints qualificados (`admin.*` e `ferramentas.*`) para não exigir aliases que criariam regras duplicadas.