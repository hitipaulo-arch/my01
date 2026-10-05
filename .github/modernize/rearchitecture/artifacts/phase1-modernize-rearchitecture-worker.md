# Fase 1 — Application Factory Flask

## Summary
Implementada a separação inicial do bootstrap Flask sem extrair as rotas legadas de `app.py`.

## Deliverables
- `appmodules/extensions.py`: instâncias desacopladas de CSRF, Cache e Limiter opcional.
- `appmodules/__init__.py`: `create_app(config_object=None)` com configuração, serviços, health check de disponibilidade, segurança do webhook, blueprints existentes, rate limits de autenticação e handlers de erro.
- `app.py`: usa `app = create_app()`, preserva rotas legadas, helpers de IA e adapters de validação importáveis.

## Upstream Artifacts Consumed
- `/memories/session/plan.md` — escopo, ordem da migração e contratos de compatibilidade.
- `/memories/repo/user-management-notes.md` — regras de usuários e convenções dos blueprints.

## Evidence Mapping
- `/memories/session/plan.md#15-17` → `appmodules/extensions.py`, `appmodules/__init__.py` e bootstrap `app.py`.
- `/memories/session/plan.md#47-50` → compilação, pytest focado e criação repetida da factory.

## Test Results
- Command: `python -m compileall app.py appmodules`
- Passed: compilação concluída sem erros.
- Command: `python -m pytest -q tests/test_backend_validations.py tests/test_item_routes.py tests/test_admin_ai_chat.py`
- Passed: 14
- Failed: 0
- Skipped: 0
- Warning: Flask-Limiter usa armazenamento em memória quando nenhum backend é configurado.
- Additional check: duas chamadas de `create_app()` produziram 19 regras cada, sem duplicação dentro das instâncias.

## Notes
- Alterações locais preexistentes em `.env.example`, `config.py`, `requirements.txt`, `appmodules/routes/os_routes.py`, `appmodules/services/sheets_service.py`, `templates/index.html` e `tests/test_admin_ai_chat.py` foram preservadas.