# 🏭 App de Produção — controle por setor

Aplicativo **independente** do sistema de OS, feito para o chão de fábrica acompanhar
cada ordem de produção (OP) pelos setores:

**Corte → Corte Painel → CNC → Policorte → Vidros → Portas → Pass-through →
Dobra → Montagem Primária → Solda → Acabamento → Silicone e Limpeza → Embalagem**

Cada setor entra com o **seu próprio PIN**, vê a fila dele e marca o seu status
(**Não iniciado / Em andamento / Concluído / Não se aplica**) com **data/hora
automática**. A gestão vê o painel geral, cadastra OPs e define os PINs.

> **“Não se aplica”** existe para a peça que não passa por um setor (ex.: sem
> vidro). O setor deixa de segurar a OP sem registrar trabalho que não houve, e a
> decisão fica no histórico com quem marcou e quando.

> ⚠️ **Ainda não removi o "Controle de Produção" do sistema antigo.** O app novo
> está pronto e rodando em paralelo (você pediu para não tirar nada antes de
> validar). Quando aprovar, a remoção é uma etapa à parte — veja
> [O que sai do sistema antigo](#-o-que-sai-do-sistema-antigo).

---

## 🚀 Como rodar

### 1. Criar a planilha da produção

O app guarda tudo em **uma planilha própria** (separada da planilha de OS).

1. Crie uma planilha nova no Google Sheets (pode ser vazia, sem cabeçalho nenhum).
2. Compartilhe com o e-mail da conta de serviço (o mesmo `credentials.json` do
   sistema) como **Editor**. O script abaixo mostra qual é esse e-mail.
3. Rode o verificador — ele cria as abas `OPs`, `Setores`, `Histórico` e `Acessos`:

```bash
export PRODUCAO_SPREADSHEET_ID="cole-aqui-o-id-ou-a-url-da-planilha"
python scripts/verificar_planilha_producao.py --pin 123456
```

### 2. Subir o app

```bash
export PRODUCAO_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
export PRODUCAO_SPREADSHEET_ID="..."
export PRODUCAO_ADMIN_PIN="123456"        # primeiro acesso da gestão
gunicorn -w 2 --threads 4 -b 0.0.0.0:5001 producao_app:app
```

O app de OS continua no 5000; o de produção fica no **5001** (porta configurável
em `PRODUCAO_PORT`). São processos distintos: reiniciar um não afeta o outro.

### 3. Entrar e liberar os setores

1. Abra `http://<servidor>:5001`, escolha **Gestão** e use o PIN de primeiro acesso.
2. Cadastre o PIN de cada setor na aba **Acessos** (4 a 8 dígitos).
3. Mostre o **QR code** (tela *Instalar* → `Instalar agora`) para o pessoal instalar
   o app no celular. Android instala direto; no iPhone, use Safari →
   Compartilhar → *Adicionar à Tela de Início*.

---

## 🧭 Como funciona o fluxo

| Etapa | O que acontece |
|---|---|
| **Gestão cria a OP** | Nome do item, código, MTC, quantidade, cliente/OS, prazo, material e observação. O app cria as **7 linhas de setor** automaticamente. |
| **Setor inicia** | Ao marcar *Em andamento*, o app grava `Iniciado em` com data/hora e quem marcou. |
| **Setor conclui** | Grava `Concluído em`; a OP avança para o próximo setor da ordem. |
| **OP completa** | Quando os 7 setores concluem, a OP vira **Concluída** e recebe a data de conclusão. |
| **Setor não se aplica** | Marca *Não se aplica* (ex.: peça sem vidro): sai da fila sem criar carimbo de trabalho e não trava a conclusão da OP. |
| **Correção** | Dá para voltar um setor para *Não iniciado* (limpa os carimbos e registra a correção no histórico). |

**Status da OP** é sempre calculado dos setores — não é digitado:

* ninguém começou → **Aguardando**
* algum começou → **Em andamento**
* todos **resolvidos** (Concluído ou Não se aplica) → **Concluída**

A barra de progresso conta setores resolvidos: com 13 etapas, uma peça que pula
CNC, Vidros e Portas chega a 100% sem essas três etapas "concluídas".

---

## 👥 Quem vê o quê

| Perfil | Vê | Pode |
|---|---|---|
| **Setor** (ex.: Solda) | A fila do próprio setor + todas as OPs | Marcar **somente o seu setor** |
| **Gestão** | Painel com carga por setor, atrasos e todas as OPs | Tudo: criar/editar/excluir OP, marcar qualquer setor, cadastrar PINs |

O PIN fica **criptografado** na planilha (hash Werkzeug). Há freio de tentativas:
6 PINs errados em 5 minutos bloqueiam aquele setor naquele aparelho por alguns
minutos.

---

## 🗄️ Onde ficam os dados

Planilha própria do app, com quatro abas:

| Aba | Conteúdo |
|---|---|
| `OPs` | uma linha por ordem de produção |
| `Setores` | **uma linha por OP por setor** — status, iniciado em, concluído em, última atualização, quem atualizou, observação |
| `Histórico` | cada mudança de status: anterior → novo, data/hora e quem alterou |
| `Acessos` | PIN (criptografado) de cada setor e da gestão |

Como a planilha fica no Google Sheets, dá para filtrar, montar tabela dinâmica
ou dar acesso somente-leitura para quem precisa só olhar.

### Sem Google Sheets (teste)

```bash
export PRODUCAO_STORAGE=local
export PRODUCAO_LOCAL_DB=/tmp/producao.json     # opcional
python producao_app.py
```

Nesse modo os dados vão para um JSON local (começa vazio). Serve para
desenvolvimento — **não use em produção**.

---

## 📲 O que o app tem de app

* **Instalável (PWA)** — manifest, ícones (192/512 + maskable), atalhos de toque
  longo (Minha fila, Nova OP, Painel) e **QR code** na própria tela de instalação.
* **Botões grandes** — alvos de 46px, pensados para uso com luva; campos de 16px
  para o iOS não dar zoom.
* **Ações rápidas na fila** — *Iniciar* e *Concluir* direto no cartão, sem abrir a
  ficha da OP.
* **Busca e filtros** — busca livre (OP, item, código, MTC, cliente) e recortes
  *Minha fila / Em andamento / Aguardando / Concluídas / Todas*.
* **Barra de progresso** por OP e **carga por setor** no painel, com destaque para
  **prazo vencido**.
* **Histórico** de cada alteração (setor, de → para, quem, quando, observação).
* **Offline** — indicador de conexão, tela `/offline` e service worker com cache
  do shell. Os dados de produção **nunca** são cacheados: quem olha a tela vê o
  status real (e a sessão expirada volta para o login, com aviso).
* **Mesma cara do sistema** — Bootstrap 5 + `static/unified.css`, gradiente
  `#5d6bd6 → #7a5bc2` e o rodapé de sempre.

---

## ⚙️ Configuração (variáveis de ambiente)

| Variável | Para quê | Padrão |
|---|---|---|
| `PRODUCAO_SECRET_KEY` | Sessão do app de produção (obrigatória) | — (aceita `SECRET_KEY`) |
| `PRODUCAO_SPREADSHEET_ID` | ID **ou URL** da planilha da produção | — |
| `PRODUCAO_ADMIN_PIN` | PIN de primeiro acesso da gestão, enquanto não houver PIN cadastrado na planilha | — |
| `PRODUCAO_STORAGE` | `sheets` ou `local` | `sheets` |
| `PRODUCAO_LOCAL_DB` | Arquivo do modo local | `instance/producao_local.json` |
| `PRODUCAO_PORT` | Porta do app | `5001` |
| `PRODUCAO_SESSAO_MINUTOS` | Duração da sessão no celular | `720` (12 h) |
| `PRODUCAO_COOKIE_SECURE` | Exige HTTPS no cookie (ligue em produção com HTTPS) | `false` |
| `PRODUCAO_COOKIE_SAMESITE` | `Lax` no servidor do cliente; `None` se o app for aberto dentro de outra página | `Lax` |
| `PRODUCAO_COOKIE_PARTITIONED` | Cookie particionado (`Partitioned`) — necessário em iframe com bloqueio de cookie de terceiros | `false` |
| `GOOGLE_APPLICATION_CREDENTIALS` | Caminho do `credentials.json` | `./credentials.json` |

`/healthz` responde o estado do app e do armazenamento (útil para monitoração).

### Abrir o app dentro de outra página (iframe/preview)

O padrão `SameSite=Lax` é o correto para o servidor do cliente. Se o app for
embutido em outra página (como acontece em pré-visualizações), o navegador **não
envia** o cookie no POST do login e aparece `CSRF session token is missing`.
Nesse caso ligue:

```bash
export PRODUCAO_COOKIE_SAMESITE=None
export PRODUCAO_COOKIE_SECURE=true      # SameSite=None exige HTTPS
export PRODUCAO_COOKIE_PARTITIONED=true # funciona mesmo com cookies de terceiros bloqueados
```

Em produção normal (domínio próprio, acesso direto) deixe tudo no padrão.

---

## 🔗 Atalho no sistema antigo (integração)

O app de produção continua sendo um **programa separado** — login, sessão e
planilha próprios — e agora aparece como **atalho dentro do sistema de OS**,
tanto na versão web quanto no app do celular (`/m`):

| Onde | O que aparecer |
|---|---|
| Menu do sistema (web, gestão e operador) | botão **🏭 Produção por Setor** |
| Telas antigas de produção (web e `/m`) | cartão com o endereço e o botão "Abrir app" |
| Menu **Mais** do app do celular | seção **🏭 App de produção** |

O atalho é só um **link**: abre em outra aba, o usuário faz login lá (PIN do
setor) e nada de dado, sessão ou regra é compartilhado entre os dois programas.
Há teste automático que falha se algum arquivo do sistema de OS importar o app
de produção.

### De onde vem o endereço

O sistema de OS descobre o endereço do app em camadas:

1. **`PRODUCAO_APP_URL`** — endereço completo (tem prioridade). Use quando os
   dois estiverem em endereços diferentes, ex.:
   `PRODUCAO_APP_URL=https://producao.minhaempresa.com`
2. Se não estiver definido, o endereço é **deduzido do próprio acesso**: mesma
   máquina/domínio, na porta `PRODUCAO_APP_PORT` (padrão `5001`). Funciona
   inclusive em publicações com a porta no nome do host
   (`5000-abc.exemplo.com` → `5001-abc.exemplo.com`).
3. **`PRODUCAO_APP_INTEGRADO=0`** esconde o atalho de todas as telas — útil
   enquanto o app ainda não estiver publicado.

| Variável | Para quê | Padrão |
|---|---|---|
| `PRODUCAO_APP_URL` | Endereço completo do app (vence a dedução) | — (deduzido) |
| `PRODUCAO_APP_PORT` | Porta usada quando o endereço não é informado | `5001` |
| `PRODUCAO_APP_INTEGRADO` | `0` esconde o atalho do sistema antigo | `1` |

Os testes aparecem em `tests/test_integracao_producao.py` (23 testes).

---

## 📦 Gerar o pacote independente

Para levar o app para outra máquina (ou entregar pronto para o cliente), use o
empacotador — ele monta a pasta, roda a suíte **dentro** do pacote e compacta:

```bash
python scripts/empacotar_app_producao.py                 # .zip e .tar.gz na pasta pessoal
python scripts/empacotar_app_producao.py --destino /tmp  # escolhe onde gravar
python scripts/empacotar_app_producao.py --pasta         # só monta a pasta, sem compactar
python scripts/empacotar_app_producao.py --sem-testes    # pula a verificação
```

O pacote leva só o que o app de produção precisa (código, telas, PWA, scripts de
migração, testes e um `LEIA-ME.txt` com o passo a passo). O
`appmodules/__init__.py` do pacote é mínimo de propósito: assim o app **não**
carrega a configuração do sistema de OS (que exige `SECRET_KEY` e as planilhas
do gestor). Há teste garantindo isso.

---

## 🧪 Testes

```bash
pytest tests/test_producao_web.py -v          # 102 testes: só o app de produção
pytest tests/ -q                              # 203 testes: sistema + app + mobile
```

102 testes cobrem o fluxo de setores (ordem, status calculado, progresso), o
armazenamento local, o login por setor, as permissões (cada setor só mexe no
próprio status), o cadastro/edição/exclusão de OP, o painel, o histórico, a
instalação (manifest, service worker, ícones) e o **isolamento** — há teste que
falha se algum arquivo do sistema de OS importar o app de produção, se os
templates vazarem de um para o outro e se o pacote passar a exigir a
configuração do gestor (``SECRET_KEY`` etc.).

O atalho dentro do sistema de OS tem testes próprios em
``tests/test_integracao_producao.py`` (27 testes): resolução do endereço,
cada ponto de entrada (menu web, telas antigas, app em ``/m``) e o isolamento
entre os dois programas.

---

## 🗂️ Arquivos

```
producao_app.py                     ponto de entrada (gunicorn producao_app:app)
appmodules/producao_web/
  setores.py                        fluxo de setores e regras de status
  storage.py                        planilha dedicada + backend local
  auth.py                           login por setor (PIN, permissões)
  routes.py                         telas e ações
  formatters.py                     máscaras de código, MTC e prazo
  config.py                         variáveis de ambiente do app
templates/producao/                 10 telas (login, fila, ficha da OP, painel, acessos…)
static/producao/                    app.css, app.js, service worker, manifest, ícones
scripts/gerar_icones_producao.py    regera os ícones do app
scripts/verificar_planilha_producao.py  confere/configura a planilha
scripts/empacotar_app_producao.py    gera o pacote independente (.zip/.tar.gz)
scripts/migrar_setores_producao.py  completa os setores novos nas OPs antigas
tests/test_producao_web.py          100 testes
```

### Mudar o fluxo de setores

Acrescentar, renomear ou reordenar setores é editar **uma tupla** em
`appmodules/producao_web/setores.py`:

```python
SETORES = (
    Setor("corte", "Corte", "🪚"),
    Setor("corte_painel", "Corte Painel", "🪵"),
    Setor("cnc", "CNC", "🤖"),
    Setor("policorte", "Policorte", "⚙️"),
    Setor("vidros", "Vidros", "🪟"),
    Setor("portas", "Portas", "🚪"),
    Setor("pass_through", "Pass-through", "🔁"),
    Setor("dobra", "Dobra", "📐"),
    Setor("montagem_primaria", "Montagem Primária", "🔧"),
    Setor("solda", "Solda", "🔥"),
    Setor("acabamento", "Acabamento", "🎨"),
    Setor("silicone_limpeza", "Silicone e Limpeza", "🧴"),
    Setor("embalagem", "Embalagem", "📦"),
)
```

O armazenamento, as telas, o painel, o login e os testes leem tudo daí — e a
**chave** do setor (`corte_painel`) é o que aparece nas URLs: mantenha-a estável
ao renomear o rótulo.

O **ícone** é só exibição (tela de acesso, fila, ficha da OP e painel) e precisa
ser único entre os setores — há teste garantindo, porque é o que o pessoal
reconhece de relance no celular. Trocar o ícone é editar esse terceiro campo:

| Setor | Ícone |
|---|---|
| Corte | 🪚 |
| Corte Painel | 🪵 |
| CNC | 🤖 |
| Policorte | ⚙️ |
| Vidros | 🪟 |
| Portas | 🚪 |
| Pass-through | 🔁 |
| Dobra | 📐 |
| Montagem Primária | 🔧 |
| Solda | 🔥 |
| Acabamento | 🎨 |
| Silicone e Limpeza | 🧴 |
| Embalagem | 📦 |

#### OPs que já existiam quando o fluxo ganha setor

Uma OP antiga não tem linha para o setor novo. O painel avisa
(⚠️ *“N OP(s) sem os setores novos do fluxo”*) e o comando abaixo completa a
planilha:

```bash
PRODUCAO_SPREADSHEET_ID="..." python scripts/migrar_setores_producao.py
# banco local de desenvolvimento:
python scripts/migrar_setores_producao.py --local
```

Regra da migração, para não reabrir trabalho antigo:

| Situação da OP | Setor novo entra como |
|---|---|
| Em andamento / Aguardando | **Não iniciado** (vai aparecer na fila do setor) |
| Já concluída | **Não se aplica** (continua concluída) |

O comando é idempotente: rodar duas vezes não duplica linha nenhuma. No banco
local o app se completa sozinho na primeira leitura.

---

## 🔜 O que sai do sistema antigo

Quando você aprovar, a limpeza é uma etapa à parte e envolve:

* remover do sistema de OS (web **e** app em `/m`) as telas de Controle de
  Produção: `🏭 Produção`, `OPs Abertas` e `Dashboard de Produção`;
* manter **Itens/Compras**, que hoje moram na mesma aba da planilha — é preciso
  separar as linhas de estoque das de fabricação antes de mexer;
* decidir sobre a IA Admin e o resumo do dia, que hoje leem a produção.

Diga "pode remover" e eu executo essa parte com os testes cobrindo a migração.
