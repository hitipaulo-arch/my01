# Instruções para Copilot - Gerenciamento de Produção

## Visão Geral do Projeto

Este é um sistema TypeScript de gerenciamento de produção com Express.js, JWT, e padrões SOLID.

## Arquitetura

- **Controllers** - Manipulam requisições HTTP e respostas
- **Services** - Contêm a lógica de negócio
- **Routes** - Definem endpoints da API
- **Middleware** - Autenticação e autorização
- **Types** - Interfaces TypeScript compartilhadas
- **Config** - Variáveis de ambiente e configurações

## Padrões e Convenções

### Tipagem TypeScript
- Sempre use interfaces para estruturas de dados
- Tipos genéricos para reutilização
- Strict mode ativado
- No implicit any

### Controllers
- Herdar de classe base ou seguir padrão de métodos
- Sempre validar entrada do usuário
- Retornar respostas estruturadas (JSON)
- Usar status HTTP corretos

### Services
- Lógica de negócio isolada
- Métodos assincronizados para operações de BD
- Tratamento de erro no controlador
- Sem dependência direta de Express

### Rotas
- Usar router pattern do Express
- Aplicar middleware de autenticação/autorização
- Nomes descritivos para rotas

### Middleware
- Reutilizável e composável
- Validar tokens JWT
- Verificar roles/permissões
- Passar dados via req.user

## Segurança

- JWT secret em variável de ambiente
- Hash de senhas com bcrypt
- CORS configurado
- Helmet.js para headers
- Validação de entrada

## Banco de Dados (Prisma)

Quando implementar Prisma:
1. Executar `npx prisma init`
2. Criar schema.prisma com modelos
3. Executar migrações
4. Gerar cliente Prisma
5. Usar em services

## Como Adicionar Novas Features

1. **Criar tipos** em `src/types/`
2. **Criar service** com lógica em `src/services/`
3. **Criar controller** para requisições em `src/controllers/`
4. **Criar rotas** em `src/routes/`
5. **Registrar rotas** em `src/index.ts`
6. **Adicionar validações** apropriadas

## Exemplo de Nova Rota

```typescript
// 1. Types
export interface INewFeature {
  id: string;
  // ...
}

// 2. Service
export class NewFeatureService {
  async getAll(): Promise<INewFeature[]> { }
}

// 3. Controller
export class NewFeatureController {
  async list(req: Request, res: Response): Promise<void> { }
}

// 4. Routes
router.get('/', controller.list.bind(controller));

// 5. Register in index.ts
app.use('/api/new-feature', newFeatureRoutes);
```

## Testes

- Adicionar testes em `src/tests/`
- Usar Jest e ts-jest
- Testar services isoladamente
- Testar rotas com supertest

## Dependências Principais

- express - Web framework
- typescript - Tipagem
- jsonwebtoken - JWT
- bcryptjs - Hash de senhas
- prisma - ORM (quando implementar BD)
- helmet - Segurança
- cors - CORS

## Variáveis de Ambiente

Verificar `.env.example` para todas as variáveis necessárias:
- DATABASE_URL
- JWT_SECRET
- NODE_ENV
- PORT

## Performance

- Implementar caching quando necessário
- Usar indexes no banco de dados
- Validar queries do Prisma
- Manter serviços simples e reutilizáveis

## Coding Style

- Use async/await
- Nomes descritivos em inglês
- Comentários para lógica complexa
- Consistent formatting (prettier)

---

Para dúvidas ou sugestões, consulte a documentação oficial das dependências.
