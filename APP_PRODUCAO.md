# 🏭 App de Produção — controle por setor

Aplicativo **independente** do sistema de OS, feito para o chão de fábrica acompanhar
cada ordem de produção (OP) pelos setores:

**Corte → Dobra → Montagem Primária → Solda → Acabamento → Silicone e Limpeza → Embalagem**

Cada setor entra com o **seu próprio PIN**, vê a fila dele e marca o seu status
(Não iniciado / Em andamento / Concluído) com **data/hora automática**. A gestão
vê o painel geral, cadastra OPs e define os PINs.

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
| **Correção** | Dá para voltar um setor para *Não iniciado* (limpa os carimbos e registra a correção no histórico). |

**Status da OP** é sempre calculado dos setores — não é digitado:

* ninguém começou → **Aguardando**
* algum começou → **Em andamento**
* todos concluíram → **Concluída**

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
| `GOOGLE_APPLICATION_CREDENTIALS` | Caminho do `credentials.json` | `./credentials.json` |

`/healthz` responde o estado do app e do armazenamento (útil para monitoração).

---

## 🧪 Testes

```bash
pytest tests/test_producao_web.py -v
```

75 testes cobrem o fluxo de setores (ordem, status calculado, progresso), o
armazenamento local, o login por setor, as permissões (cada setor só mexe no
próprio status), o cadastro/edição/exclusão de OP, o painel, o histórico, a
instalação (manifest, service worker, ícones) e o **isolamento** — há teste que
falha se algum arquivo do sistema de OS importar o app de produção ou se os
templates vazarem de um para o outro.

---

## 🗂️ Arquivos

```
producao_app.py                     ponto de entrada (gunicorn producao_app:app)
appmodules/producao_web/
  setores.py                        fluxo de setores e regras de status
  storage.py                        planilha dedicada + backend local
  auth.py                           login por setor (PIN, permissões)
  routes.py                         telas e ações
  config.py                         variáveis de ambiente do app
templates/producao/                 10 telas (login, fila, ficha da OP, painel, acessos…)
static/producao/                    app.css, app.js, service worker, manifest, ícones
scripts/gerar_icones_producao.py    regera os ícones do app
scripts/verificar_planilha_producao.py  confere/configura a planilha
tests/test_producao_web.py          75 testes
```

### Mudar o fluxo de setores

Acrescentar, renomear ou reordenar setores é editar **uma tupla** em
`appmodules/producao_web/setores.py`:

```python
SETORES = (
    Setor("corte", "Corte", "🪚"),
    Setor("dobra", "Dobra", "📐"),
    ...
)
```

O armazenamento, as telas, o painel, o login e os testes leem tudo daí. OPs já
existentes ganham a linha do setor novo automaticamente na próxima leitura (a
OP aparece com ele como *Não iniciado*).

---

## 🔜 O que sai do sistema antigo

Quando você aprovar, a limpeza é uma etapa à parte e envolve:

* remover do sistema de OS (web **e** app em `/m`) as telas de Controle de
  Produção: `🏭 Produção`, `OPs Abertas` e `Dashboard de Produção`;
* manter **Itens/Compras**, que hoje moram na mesma aba da planilha — é preciso
  separar as linhas de estoque das de fabricação antes de mexer;
* decidir sobre a IA Admin e o resumo do dia, que hoje leem a produção.

Diga "pode remover" e eu executo essa parte com os testes cobrindo a migração.
