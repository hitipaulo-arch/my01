# 📊 Gerenciamento de Produção - TypeScript

Sistema completo de gerenciamento de produção desenvolvido em **TypeScript** com **Express.js**, API REST, autenticação JWT e banco de dados.

## 🎯 Funcionalidades

- ✅ Autenticação de usuários (JWT)
- ✅ Controle de acesso por roles (admin, manager, operator)
- ✅ Gerenciamento de produções
- ✅ Rastreamento de máquinas
- ✅ Controle de operadores
- ✅ API REST completa
- ✅ Validação de entrada
- ✅ Tratamento de erros robusto

## 🛠️ Tecnologias

- **TypeScript 5.x** - Linguagem com tipagem estática
- **Express.js 4.x** - Framework web
- **Prisma** - ORM para banco de dados
- **JWT** - Autenticação segura
- **BCrypt** - Hash de senhas
- **Cors/Helmet** - Segurança
- **Node.js 18+** - Runtime

## 📁 Estrutura do Projeto

```
src/
├── controllers/      # Controladores da API
├── services/         # Lógica de negócio
├── routes/          # Definição de rotas
├── middleware/      # Middleware customizado
├── models/          # Modelos de dados (Prisma)
├── types/           # Tipos TypeScript
├── config/          # Configurações
└── index.ts         # Arquivo principal
```

## 🚀 Como Começar

### Pré-requisitos
- Node.js 18+
- npm ou yarn
- PostgreSQL (ou outro banco configurado)

### Instalação

1. **Clone e entre na pasta:**
   ```bash
   cd production-management
   ```

2. **Instale as dependências:**
   ```bash
   npm install
   ```

3. **Configure as variáveis de ambiente:**
   ```bash
   cp .env.example .env
   ```
   Edite o arquivo `.env` com seus valores.

4. **Inicie o servidor de desenvolvimento:**
   ```bash
   npm run dev
   ```

O servidor será iniciado em `http://localhost:3000`

## 📚 API Endpoints

### Autenticação

```
POST   /api/auth/register    # Registrar novo usuário
POST   /api/auth/login       # Fazer login
GET    /api/auth/profile     # Obter perfil (requer token)
```

### Produções

```
GET    /api/productions              # Listar todas
GET    /api/productions/:id          # Buscar por ID
GET    /api/productions/status/:status  # Buscar por status
GET    /api/productions/machine/:machineId # Buscar por máquina
POST   /api/productions              # Criar (admin/manager)
PUT    /api/productions/:id          # Atualizar (admin/manager)
DELETE /api/productions/:id          # Deletar (admin)
```

## 🔐 Autenticação

Todos os endpoints de produção requerem um token JWT no header:

```bash
Authorization: Bearer <seu_token>
```

### Roles
- **admin** - Acesso total
- **manager** - Criar e atualizar produções
- **operator** - Apenas visualizar

## 🧪 Testes

```bash
npm run test
```

## 🏗️ Build

```bash
npm run build
npm start
```

## 📝 Scripts Disponíveis

| Comando | Descrição |
|---------|-----------|
| `npm run dev` | Inicia servidor em desenvolvimento |
| `npm run build` | Compila TypeScript para JavaScript |
| `npm start` | Inicia servidor em produção |
| `npm run migrate` | Executa migrações do Prisma |
| `npm run test` | Executa testes |
| `npm run lint` | Valida código com ESLint |

## 🛡️ Segurança

- Senhas criptografadas com bcrypt
- Tokens JWT com expiração
- Validação de entrada em todas as rotas
- Middleware de autenticação
- Helmet.js para headers de segurança
- CORS configurado

## 📖 Próximos Passos

1. Implementar banco de dados com Prisma
2. Adicionar testes unitários e de integração
3. Configurar Docker para contêinerização
4. Implementar logging completo
5. Adicionar documentação Swagger/OpenAPI

## 👤 Autor

Sistema de Gerenciamento de Produção

## 📄 Licença

MIT
