# encoding-cleanup — Correção de mojibake no frontend

## Summary
Corrigidos textos, ícones, pontuação, status e chaves Jinja corrompidos em `templates/compras.html`, `templates/dashboard_producao.html`, `templates/editar_item.html`, `templates/producao.html`, `templates/producao_abertas.html` e `temp_script.js`. Alterações locais preexistentes fora desse escopo foram preservadas.

## Upstream Artifacts Consumed
- none — no dependency artifacts provided

## Evidence Mapping
- none — no dependency artifacts provided

## Test Results
- Command: `c:/Users/Automação/Documents/GitHub/my01/.venv/Scripts/python.exe -m compileall app.py appmodules`
- Passed: 1 command
- Failed: 0
- Skipped: 0
- Command: `c:/Users/Automação/Documents/GitHub/my01/.venv/Scripts/python.exe -m pytest -q --ignore=test_nvidia_real_api.py`
- Passed: 46
- Failed: 0
- Skipped: 0
- Command: test client render of `/producao-abertas` with local fake Sheets service
- Result: HTTP 200; `Ordens de Produção Abertas`, `Código`, `Responsável` and `Observação` present; no `Ã`, `Â`, `ðŸ` or `�`.
- Command: UTF-8 literal scan excluding `.git`, virtual environments, caches and `logs`
- Result: `NO_REAL_MOJIBAKE_FOUND`

## Findings
- Existing unrelated worktree changes were present in `.env.example`, Python modules, other templates and tests; none were reverted or modified for this task.
- One expected warning remains from Flask-Limiter using in-memory storage during tests.
