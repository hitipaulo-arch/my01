# Aliases de endpoint administrativo

Blueprints Flask prefixam endpoints com o nome do blueprint; aliases explícitos preservam templates legados.

## What Happened
Na extração administrativa de my01, os caminhos permaneceram iguais, mas `url_for('relatorios')` passou a exigir `admin.relatorios`. A factory registrou aliases com os métodos HTTP originais, apontando para as mesmas view functions.

## Takeaway
Ao extrair rotas sem atualizar templates nesta fase, registre aliases na factory e informe `methods` explicitamente; `add_url_rule` não herda automaticamente todos os métodos da regra original.

## History
- 2026-09-28 (my01/phase2-admin): initial
