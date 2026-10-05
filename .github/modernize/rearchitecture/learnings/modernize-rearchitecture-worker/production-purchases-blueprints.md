# Production Purchases Blueprints

Endpoints extraídos devem manter os caminhos públicos, mas templates e redirects internos devem usar nomes qualificados do blueprint.

## What Happened
Na fase 3 de my01, produção e compras foram movidas para `producao.*` e `compras.*`; os aliases de URL foram mantidos apenas como decorators dentro do blueprint (`/itens` e `/compras`, `/excluir` e `/deletar`).

## Takeaway
Depois de qualificar todos os `url_for`, não registre aliases adicionais na factory: isso duplica regras e mascara regressões de endpoint.

## History
- 2026-09-28 (my01/phase3-production-purchases): initial