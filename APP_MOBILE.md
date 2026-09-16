# 📱 App Mobile (PWA) — Gestão OS

O sistema agora pode ser usado como **aplicativo instalável no celular**, com a
mesma aparência, os mesmos dados, as mesmas regras de negócio e o mesmo login da
versão web. Não existe um segundo backend: o app é o **mesmo Flask**, exposto sob
o prefixo `/m`.

| | Versão web | App mobile |
|---|---|---|
| Endereço | `https://SEU-HOST/` | `https://SEU-HOST/m/` |
| Layout | Tabelas e menus largos | Cartões, abas no rodapé, bottom sheets |
| Visual | `static/unified.css` | `unified.css` + `static/mobile/mobile.css` |
| Dados/regras | rotas Flask | **as mesmas rotas Flask** |
| Sessão/CSRF | cookie de sessão | o mesmo cookie |
| Instalável | — | sim (ícone, splash, offline) |

---

## 🚀 Como usar

0. Na página inicial da versão web há um **QR Code “Use o sistema como aplicativo”**
   (e um botão **📱 App** no topo): aponte a câmera do celular para abrir direto no app.
1. Ou abra no celular: `https://SEU-HOST/m/`
2. Faça login com o mesmo usuário/senha do sistema web (ou use as telas públicas:
   abrir OS, consultar status, OS abertas).
3. Para instalar:
   * **Android/Chrome**: menu `⋮` → *Instalar aplicativo*.
   * **iPhone/Safari**: *Compartilhar* → *Adicionar à Tela de Início*.
   * **Desktop/Chrome·Edge**: ícone de instalação na barra de endereços.
   * Dentro do app: **Mais → 📲 Instalar app** (também em `/m/instalar`).

> ℹ️ A instalação (e o funcionamento offline) exigem **HTTPS**. Em `http://localhost`
> o Chrome também permite testar.

---

## 🗂️ O que tem no app

Todas as telas do sistema, otimizadas para o dedo:

| Módulo | Rota no app | Observações |
|---|---|---|
| Início (hub) | `/m/` | Cartões de acesso rápido + status online/offline |
| Abertura de OS | `/m/nova-os` | Formulário completo, ditar descrição por voz, compartilhar link |
| OS Abertas | `/m/os-abertas` | KPIs de conclusão/tempo médio, filtro instantâneo |
| Consultar OS | `/m/consultar` | Consulta por número do pedido (atualiza a cada 30s) |
| Enviar Arquivo | `/m/upload-documento` | Anexos direto da câmera/arquivos |
| Gerenciar OS | `/m/gerenciar` | Cartões, filtro, edição em bottom sheet, link `wa.me` |
| Produção | `/m/producao` | Cadastro, atualização (AJAX) e exclusão, barra de avanço |
| OPs Abertas | `/m/producao-abertas` | Itens fora de concluído/bloqueado |
| Dashboard | `/m/dashboard-producao` | Gráficos Chart.js consumindo `/producao/dados` |
| Itens / Compras | `/m/itens` | Alerta de reposição, edição e exclusão |
| Centrais | `/m/centrais` | Cadastro, status/obra e **matriz de programação tocável** |
| Ferramentas | `/m/ferramentas` | Cadastro, status e histórico de eventos |
| Relatórios | `/m/relatorios` | Indicadores e gráficos de auditoria |
| Tempo por Funcionário | `/m/tempo-por-funcionario` | Filtros, gráficos, paginação e exportação CSV/XLSX |
| Editar Item | `/m/itens/<id>/editar` | Nome, código, MTC, estoque (com botões −/＋) e observação |
| Usuários | `/m/usuarios` | Criar/atualizar/excluir usuários (admin) |
| IA Admin | `/m/admin/ia` | Chat com resumo do dia e histórico em sessão |
| Login / Cadastro | `/m/login`, `/m/cadastro` | Mesa sessão e mesmas regras de senha |
| Sem conexão | `/m/offline` | Servida pelo service worker |
| Instalação | `/m/instalar` | Passo a passo por sistema operacional |

O menu respeita o papel do usuário exatamente como o topo da versão web
(`admin`, `operador`, `visualizador`, público).

---

## 🏗️ Arquitetura (por que não há código duplicado)

```
appmodules/mobile/
├── middleware.py   # move o prefixo /m para SCRIPT_NAME  → url_for já sai com /m
├── context.py      # render_page(): escolhe mobile/<tela> quando está em /m
├── routes.py       # rotas exclusivas do app (manifest, SW, offline, instalar, menu)
└── __init__.py     # instala o middleware, registra o blueprint e os helpers
static/mobile/
├── mobile.css          # camada visual do app (usa as variáveis do unified.css)
├── app.js              # SW, offline, instalação, máscaras, filtros
├── manifest.json       # PWA (nome, ícones, atalhos, cores)
├── service-worker.js   # cache do shell + fallback offline
└── icons/              # 192, 512, maskable e apple-touch-icon
templates/mobile/       # uma tela mobile para cada template existente
tests/test_mobile_app.py
```

Como funciona o reaproveitamento:

1. O middleware converte `/m/gerenciar` em `/gerenciar` **dentro** do Flask e
   guarda `/m` em `SCRIPT_NAME`. Resultado: `url_for` passa a gerar `/m/...`
   automaticamente, então o usuário nunca “escapa” para a versão desktop.
2. As rotas existentes trocaram `render_template(...)` por `render_page(...)`.
   Esse helper é um drop-in: ele escolhe `templates/mobile/<arquivo>` quando a
   requisição está em `/m` e cai no template original em qualquer outro caso.
3. Nenhuma validação, cálculo, cache ou integração foi reescrita — as telas
   mobile postam nos **mesmos endpoints** (`/enviar`, `/atualizar_chamado`,
   `/producao/atualizar/<id>`, `/centrais/programacao/<id>`, …), usando o
   mesmo CSRF e a mesma sessão.
4. Como o prefixo é movido para `SCRIPT_NAME`, `request.path` é igual nos dois
   modos. Por isso as páginas com cache usam `cache_key_by_mode(...)`, que
   separa a chave do app da chave da web (sem isso, o app receberia o HTML
   cacheado da versão desktop).

### Como adicionar uma nova tela ao app

1. Crie `templates/mobile/<nome>.html` estendendo `mobile/_base.html`.
2. Pronto — a rota correspondente já a entregará quando acessada via `/m`.
   Se preferir um item no menu, acrescente-o em `APP_MENU`/`APP_TABS`
   (`appmodules/mobile/context.py`).

---

## 📲 Recursos de app incluídos

* **Instalação real** — manifest com `display: standalone`, ícones (inclusive
  *maskable* para Android), splash, tema `#5d6bd6` e atalhos de toque longo
  (Nova OS, OS abertas, Produção).
* **Service worker** — cache do shell e dos assets do app (inclusive CDNs
  versionadas) e tela `/m/offline`; respostas dinâmicas do Sheets nunca são
  cacheadas (evita dado desatualizado).
* **Banner de instalação** (dispensável, com memória local) e página `/m/instalar`
  com o passo a passo por SO. No iOS, onde o navegador não emite
  `beforeinstallprompt`, o convite aparece com as instruções do Safari.
* **Indicador de conexão** e botão “Tentar novamente”.
* **Sessão expirada** — quando uma chamada AJAX é desviada para o login, o app
  avisa e retorna para `/m/login?next=<tela atual>`, sem “erro ao atualizar” solto.
* **Filtros por status em um toque** (OS Abertas e Gerenciar) e contador de itens
  exibidos, além da busca livre por qualquer campo.
* **Atualização rápida de produção (−1 / ＋1)** no cartão do item, usando o mesmo
  endpoint `/producao/atualizar/<id>` — o chão de fábrica atualiza sem abrir formulário.
* **Ergonomia de celular**: campos com 16px (sem zoom no iOS), alvos de toque
  ≥ 44px, abas fixas com `safe-area-inset`, bottom sheets, filtro instantâneo,
  máscaras de código (`##-##-#####`) e MTC, links `wa.me`.
* **Ditado por voz** na descrição da OS (Web Speech API, quando suportado).

---

## 🧪 Testes

```bash
pytest tests/test_mobile_app.py -v
```

Cobrem o middleware de prefixo, os assets de PWA, o menu por papel do usuário,
os filtros/atalhos do app, o isolamento do cache entre app e web e a renderização
de **todas** as telas no modo app (com serviços simulados), garantindo que a
versão web permaneça intacta.

As travas que evitam regressões silenciosas:

* **Cobertura de telas** — varre todo `render_page("*.html")` do projeto e exige
  um template mobile equivalente; sem isso uma tela nova volta ao layout desktop
  dentro do app sem ninguém perceber.
* **Manifesto versionado** — confere que `static/mobile/manifest.json` não caiu no
  `*.json` do `.gitignore` (o app deixa de ser instalável sem ele), que as chaves
  obrigatórias do PWA existem e que cada ícone declarado tem o tamanho correto.
* **Sintaxe do JavaScript** — roda `node --check` nos arquivos do app e em todo
  `<script>` inline dos templates mobile, pegando erro que quebra a tela no
  celular mas não aparece em teste de renderização.
* **Service worker** — confere a versão do cache (incremente ao mexer nos assets),
  o precache dos arquivos do app, a limpeza de caches antigos, o fallback offline
  e a regra de nunca cachear dados dinâmicos.
* **Base das telas** — todas as telas do app precisam estender `mobile/_base.html`
  e as meta tags de instalação (iOS/Android, `viewport-fit=cover`) precisam existir.

> O manifesto PWA é a única exceção ao `*.json` do `.gitignore`
> (`!static/mobile/manifest.json`), porque é código do projeto, não credencial.

---

## 🔧 Sem novas variáveis de ambiente

O app usa exatamente as variáveis já documentadas no `README.md`
(`SECRET_KEY`, `GOOGLE_SHEET_ID`, cache, notificações, …).
