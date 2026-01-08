# Production Management Setup

## 📋 Pré-requisitos

Antes de começar, certifique-se de ter instalado:

- **Node.js** 18.x ou superior ([Download](https://nodejs.org/))
- **npm** 9.x ou superior (vem com Node.js)
- **PostgreSQL** 12+ ou banco de dados compatível (opcional para começar)

## 🚀 Instalação Rápida

### Windows (PowerShell)

```powershell
# 1. Instale o Node.js
# Baixe em: https://nodejs.org/

# 2. Verifique a instalação
node --version
npm --version

# 3. Instale as dependências
npm install

# 4. Configure as variáveis de ambiente
copy .env.example .env

# 5. Inicie o servidor
npm run dev
```

### macOS / Linux

```bash
# 1. Instale o Node.js (via Homebrew no macOS)
brew install node

# 2. Verifique a instalação
node --version
npm --version

# 3. Instale as dependências
npm install

# 4. Configure as variáveis de ambiente
cp .env.example .env

# 5. Inicie o servidor
npm run dev
```

## 📝 Variáveis de Ambiente

Crie um arquivo `.env` na raiz do projeto:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/production_db
JWT_SECRET=sua_chave_secreta_muito_segura_aqui
NODE_ENV=development
PORT=3000
```

## ✅ Verificação de Instalação

```bash
# Compilar TypeScript
npm run build

# Verificar se não há erros
npm run lint

# Iniciar servidor de desenvolvimento
npm run dev
```

O servidor estará disponível em: `http://localhost:3000`

## 🧪 Testando a API

### 1. Registrar usuário

```bash
curl -X POST http://localhost:3000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "João Silva",
    "email": "joao@example.com",
    "password": "senha123",
    "role": "manager"
  }'
```

### 2. Fazer login

```bash
curl -X POST http://localhost:3000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "joao@example.com",
    "password": "senha123"
  }'
```

### 3. Criar produção (use o token obtido)

```bash
curl -X POST http://localhost:3000/api/productions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer SEU_TOKEN_AQUI" \
  -d '{
    "name": "Produção teste",
    "description": "Descrição da produção",
    "machineId": "machine-001",
    "operatorId": "operator-001",
    "quantity": 100,
    "status": "pending",
    "startDate": "2024-01-07T10:00:00Z",
    "priority": "high"
  }'
```

## 📚 Documentação

- [README.md](./README.md) - Documentação principal
- [.github/copilot-instructions.md](./.github/copilot-instructions.md) - Instruções para Copilot
- [package.json](./package.json) - Dependências e scripts

## 🆘 Troubleshooting

### "npm não é reconhecido"
- Reinstale o Node.js de https://nodejs.org/
- Reinicie o terminal após a instalação

### "Porta 3000 já está em uso"
- Mude a porta no arquivo `.env`: `PORT=3001`

### "Erro de conexão com banco de dados"
- Verifique se PostgreSQL está rodando
- Confirme a `DATABASE_URL` no `.env`

## 📞 Suporte

Para dúvidas ou problemas, consulte:
- [Node.js Documentation](https://nodejs.org/docs/)
- [Express.js Guide](https://expressjs.com/)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)
