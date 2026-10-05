# Fase 3 — Blueprints de produção e compras

## Summary
Extraídas as rotas de produção e compras para `producao_bp` e `compras_bp`, com URLs públicas e métodos preservados, endpoints qualificados nos templates e registro na factory.

## Upstream Artifacts Consumed
- `/memories/session/plan.md` — escopo e contratos de compatibilidade.
- `.github/modernize/rearchitecture/artifacts/phase1-modernize-rearchitecture-worker.md` — factory e extensões existentes.
- `.github/modernize/rearchitecture/artifacts/phase2-admin-worker.md` — aliases/monkeypatches de IA preservados.
- `.github/modernize/rearchitecture/learnings/modernize-rearchitecture-worker/admin-blueprint-endpoint-compat.md` — uso de endpoints qualificados.

## Evidence Mapping
- `plan.md#20-21` -> `appmodules/routes/producao_routes.py`, `appmodules/routes/compras_routes.py`.
- `plan.md#47-50` -> compileall e suíte focada executados.
- `plan.md#53-57` -> adapters de validação e helpers de IA mantidos em `app.py`.

## Route Inventory
- Produção: 5 regras (`/producao`, atualização, dados, abertas e dashboard).
- Compras: 5 regras (`/itens`, `/compras`, edição e os dois aliases de exclusão).
- Total no escopo: 10 regras, sem duplicação; endpoints nomeados `producao.*` e `compras.*`.

## Test Results
- Command: `python -m compileall app.py appmodules`
- Passed: compilação concluída
- Failed: 0
- Skipped: 0
- Command: `python -m pytest -q tests/test_backend_validations.py tests/test_item_routes.py tests/test_admin_ai_chat.py`
- Passed: 14
- Failed: 0
- Skipped: 0
- Warning: Flask-Limiter usa armazenamento em memória quando nenhum backend é configurado.

## Residual Risk
- O `app.py` foi reduzido ao entrypoint, compatibilidade de IA/validação, webhook e endpoints legados mínimos de ferramentas durante a recuperação do arquivo após um patch parcial. A lógica detalhada de ferramentas deve ser conferida na próxima fase antes de extrair `ferramentas_routes.py`.
