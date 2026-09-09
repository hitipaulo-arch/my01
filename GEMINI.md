# Diretrizes do Projeto

Este arquivo contém as diretrizes e convenções para o desenvolvimento neste projeto. Por favor, siga estas instruções para garantir consistência, qualidade e facilidade de manutenção.

## 1. Linguagem e Frameworks Principais

*   **Linguagem:** Python
*   **Framework Web:** FastAPI
*   **Validação de Dados:** Pydantic
*   **Banco de Dados/ORM:** (Preencher se houver um ORM específico como SQLAlchemy)

## 2. Estrutura de Projeto

O projeto segue uma estrutura modular, com responsabilidades bem definidas:

*   `app.py`: Ponto de entrada principal da aplicação.
*   `appmodules/routes/`: Contém os roteadores da API (endpoints).
*   `appmodules/services/`: Contém a lógica de negócios e orquestração.
*   `appmodules/repositories/`: Contém a lógica de acesso a dados (interação com o DB).
*   `appmodules/models/`: Contém os modelos de dados (Pydantic, SQLAlchemy models, etc.).
*   `appmodules/utils/`: Contém funções utilitárias e helpers.
*   `templates/`: Contém os templates HTML (se houver).
*   `static/`: Contém arquivos estáticos (CSS, JS, imagens).
*   `tests/`: Contém todos os testes do projeto.

## 3. Estilo de Código e Qualidade

*   **Formatação:** Use `black` para formatar o código Python. Certifique-se de que o código esteja formatado antes de cada commit.
*   **Linters/Qualidade:** Use `ruff` (ou `flake8`/similar) para verificar a qualidade do código e identificar problemas.
*   **Nomenclatura:**
    *   Variáveis e funções: `snake_case`.
    *   Classes: `PascalCase`.
    *   Constantes: `UPPER_SNAKE_CASE`.
*   **Comentários:** Adicione comentários quando a lógica não for autoexplicativa. Comente *por que* algo foi feito, não *o que* foi feito.
*   **Typing:** Use type hints sempre que possível para melhorar a legibilidade e a detecção de erros.

## 4. Testes

*   **Framework de Testes:** Utilize `pytest` para todos os testes.
*   **Localização:** Testes devem ser colocados no diretório `tests/`, espelhando a estrutura do `appmodules/`.
*   **Convenção de Nomenclatura:** Arquivos de teste devem começar com `test_` (ex: `test_auth_routes.py`) e funções de teste devem começar com `test_` (ex: `test_login_success`).
*   **Cobertura:** Busque uma boa cobertura de testes para garantir a robustez do código.

## 5. Ambiente de Desenvolvimento

*   **Virtual Environment:** Sempre use um ambiente virtual (`.venv`) para gerenciar as dependências do projeto.
    *   Ativar: `.\.venv\Scripts\activate` (Windows) ou `source .venv/bin/activate` (Linux/macOS).
    *   Instalar dependências: `pip install -r requirements.txt`.

## 6. Commits

*   **Mensagens:** Utilize mensagens de commit claras e descritivas. Pense em usar o padrão Conventional Commits (feat, fix, chore, docs, style, refactor, test, build, ci).
*   **Escopo:** Mantenha os commits focados em uma única alteração lógica.

## 7. Interação com o Assistente (Gemini CLI Agent)

*   **Comunicação:** Prefira a comunicação em **Português**.
*   **Instruções:** Seja o mais específico possível ao me dar instruções. Forneça o contexto necessário (caminhos de arquivo, nomes de funções) para que eu possa atuar de forma eficiente e precisa.
*   **Otimização de Tokens:** Siga as dicas para otimizar o uso de tokens (especificidade, quebrar tarefas, otimizar saída de comandos).
