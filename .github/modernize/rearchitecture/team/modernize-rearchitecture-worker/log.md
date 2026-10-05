## Fase 1 — application factory Flask
- `appmodules.extensions` mantém `csrf`, `cache` e `limiter` não vinculados; o Flask-Limiter instalado exige `key_func` no construtor.
- `appmodules.create_app` concentra configuração, serviços, disponibilidade do Sheets, segurança do webhook, blueprints existentes e handlers.
- `app.py` continua contendo temporariamente as rotas legadas e expõe adapters dos validators usados pelos testes.
- Validação: `python -m compileall app.py appmodules` passou; pytest focado passou com 14 testes.

## [phase2-admin] Serviço de IA e blueprint administrativo
- Extraí `ai_service.py` mantendo mensagens, candidatos e fallback de cliente; providers configuráveis preservam monkeypatches no módulo `app`.
- `add_url_rule` não herda métodos da regra do blueprint; aliases legados precisam declarar `GET/POST` explicitamente.
- Validação final: `python -m compileall app.py appmodules` e três arquivos de teste passaram com 14 testes.
- Learnings consumed: [modernize-rearchitecture-worker/flask-factory-extensions]

## [phase3-production-purchases] Blueprints de produção e compras
- Extraídas 10 regras públicas para `producao_bp` e `compras_bp`; aliases `/itens`/`/compras` e `/excluir`/`/deletar` permanecem no mesmo blueprint, sem regras duplicadas.
- Templates passaram a usar endpoints qualificados; `app.py` mantém adapters de validação e wrappers públicos de IA para monkeypatch legado.
- Verificação: compileall passou; suíte focada passou com 14 testes.
- Risco: a reconstrução do entrypoint deixou a lógica detalhada de ferramentas para conferência/recuperação na próxima fase.
- Learnings consumed: [modernize-rearchitecture-worker/flask-factory-extensions, modernize-rearchitecture-worker/admin-blueprint-endpoint-compat]

## [phase4-tools-webhook] Extração de ferramentas e webhook
- Codebase/domain discoveries: as implementações completas estavam no commit-base; o app.py local continha stubs 503. A factory tinha aliases administrativos que duplicavam caminhos dos blueprints.
- Wrong assumptions and corrections: preservar aliases via `add_url_rule` não era compatível com a exigência atual de zero rotas duplicadas; templates foram qualificados e imports Python foram mantidos por alias simples.
- Debugging dead-ends and what actually worked: a falha única da suíte veio da API NVIDIA recusando conexão (`WinError 10061`), não da migração.
- Techniques/patterns worth reusing: usar `url_map` agrupado por `(rule, métodos)` para distinguir duplicatas reais; manter repositories como funções compatíveis quando esse é o contrato público.
- Learnings consumed: [modernize-rearchitecture-worker/flask-factory-extensions, modernize-rearchitecture-worker/admin-blueprint-endpoint-compat, modernize-rearchitecture-worker/production-purchases-blueprints]

## [encoding-cleanup] Correção contextual de mojibake em frontend
- Codebase/domain discoveries: as chaves de produção usam `Código`, `Número do projeto MTC`, `Meta de produção`, `Responsável`, `Observação`, `Informações adicionais` e o status `Concluído`.
- Wrong assumptions and corrections: buscar qualquer `Ã` gera falsos positivos em português; a checagem final deve comparar sequências mojibake específicas por code point.
- Técnicas: entidades HTML para ícones em templates e escapes Unicode em `textContent`, sem alterar contratos Jinja ou lógica de negócio.
- Validação: compileall passou, pytest passou com 46 testes, `/producao-abertas` retornou 200 com os quatro marcadores e a busca UTF-8 final não encontrou mojibake.
- Learnings consumed: [modernize-rearchitecture-worker/admin-blueprint-endpoint-compat, modernize-rearchitecture-worker/blueprint-route-deduplication, modernize-rearchitecture-worker/flask-factory-extensions, modernize-rearchitecture-worker/production-purchases-blueprints]