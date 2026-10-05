# Limpeza Contextual de Mojibake

Para corrigir encoding no frontend, compare sequências reais de mojibake por code point e preserve acentos legítimos; não substitua globalmente toda ocorrência de `Ã`.

## What Happened
Na tarefa encoding-cleanup de my01, templates e JavaScript tinham UTF-8 interpretado como Latin-1 em textos, chaves Jinja, status e ícones. As chaves foram alinhadas ao contrato existente do backend, e a busca final usou leitura UTF-8 direta com `String.Contains` para evitar falsos positivos do console do PowerShell.

## Takeaway
Use entidades HTML para ícones em markup e escapes Unicode em `textContent`; valide compilação, testes, renderização HTTP e uma busca literal final excluindo ambientes, caches e logs.

## History
- 2026-09-28 (my01/encoding-cleanup): inicial
