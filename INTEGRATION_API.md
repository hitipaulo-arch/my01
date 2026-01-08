# Integração com Sistema de Ordens de Serviço (OS)

## Visão Geral

Este módulo integra o **Sistema de Gerenciamento de Produção** com o **Sistema de Ordens de Serviço (my01)**, permitindo sincronização bidirecional entre OS e Tarefas de Produção.

### Fluxo de Integração

```
Sistema my01 (OS)
    ↓
API Bridge (Integration)
    ↓
Sistema de Produção (Tarefas)
```

**Sincronização:**
- OS → Tarefa de Produção (com rastreamento de tempo)
- Status da Tarefa → Status da OS
- Histórico de tempo da Tarefa → Tempo gasto na OS

---

## Tipos de Dados

### IOrderService (OS)
```typescript
{
  id: string;
  osNumber: string;           // Número da OS
  requester: string;          // Solicitante
  sector: string;             // Setor
  equipment: string;          // Equipamento/Local
  priority: 'low' | 'medium' | 'high';
  description: string;        // Descrição
  additionalInfo?: string;
  status: 'open' | 'assigned' | 'in_progress' | 'completed' | 'closed';
  linkedTaskId?: string;      // ID da tarefa sincronizada
  externalId?: string;        // ID no sistema externo
  externalUrl?: string;
  createdAt: Date;
  updatedAt: Date;
}
```

### IIntegrationSync (Log de Sincronização)
```typescript
{
  id: string;
  osId: string;
  taskId: string;
  syncedAt: Date;
  syncType: 'os_to_task' | 'task_to_os';
  status: 'success' | 'failed' | 'pending';
  message?: string;
}
```

---

## Endpoints de Integração

### Gerenciamento de OS

#### Listar Todas as OS
```
GET /api/integration/os
Authorization: Bearer <token>

Response:
[
  {
    "id": "1",
    "osNumber": "OS-2024-001",
    "requester": "João Silva",
    "sector": "Produção",
    "equipment": "Máquina CNC-01",
    "priority": "high",
    "description": "Falha no motor da máquina",
    "status": "open",
    "linkedTaskId": null,
    "createdAt": "2024-01-07T10:00:00Z",
    "updatedAt": "2024-01-07T10:00:00Z"
  }
]
```

#### Buscar OS por ID
```
GET /api/integration/os/:id
Authorization: Bearer <token>

Response: Objeto IOrderService
```

#### Criar OS
```
POST /api/integration/os
Authorization: Bearer <token> (admin/manager)
Content-Type: application/json

Request:
{
  "osNumber": "OS-2024-001",
  "requester": "João Silva",
  "sector": "Produção",
  "equipment": "Máquina CNC-01",
  "priority": "high",
  "description": "Falha no motor da máquina",
  "status": "open",
  "additionalInfo": "Fazer inspeção completa"
}

Response: (201 Created)
{
  "id": "1",
  "osNumber": "OS-2024-001",
  ...
}
```

#### Atualizar OS
```
PUT /api/integration/os/:id
Authorization: Bearer <token> (admin/manager)
Content-Type: application/json

Request:
{
  "status": "assigned",
  "priority": "medium"
}

Response: Objeto IOrderService atualizado
```

---

## Sincronização

### Sincronizar OS para Tarefa
```
POST /api/integration/sync/os-to-task
Authorization: Bearer <token> (admin/manager)
Content-Type: application/json

Request:
{
  "osId": "1",
  "productionId": "prod-001",
  "operatorId": "operator-001"
}

Response:
{
  "message": "OS sincronizada com sucesso",
  "data": {
    "os": {
      "id": "1",
      "linkedTaskId": "task-123",
      "status": "assigned",
      ...
    },
    "task": {
      "id": "task-123",
      "name": "OS-2024-001: Falha no motor da máquina",
      "status": "pending",
      "estimatedTime": 240,
      ...
    },
    "syncLog": {
      "id": "sync-1",
      "osId": "1",
      "taskId": "task-123",
      "syncType": "os_to_task",
      "status": "success",
      "syncedAt": "2024-01-07T10:30:00Z"
    }
  }
}
```

### Sincronizar Tarefa para OS
```
POST /api/integration/sync/task-to-os
Authorization: Bearer <token> (admin/manager)
Content-Type: application/json

Request:
{
  "taskId": "task-123"
}

Response:
{
  "message": "Tarefa sincronizada com sucesso",
  "data": {
    "task": { ... },
    "os": {
      "id": "1",
      "status": "in_progress",
      ...
    },
    "syncLog": { ... }
  }
}
```

### Sincronizar Todas as OS Pendentes
```
POST /api/integration/sync/all-pending
Authorization: Bearer <token> (admin/manager)

Response:
{
  "message": "5 OS sincronizadas com sucesso",
  "results": [
    {
      "os": { ... },
      "task": { ... },
      "syncLog": { ... }
    },
    ...
  ]
}
```

---

## Logs de Sincronização

### Listar Todos os Logs
```
GET /api/integration/sync-logs
Authorization: Bearer <token>

Response: Array de IIntegrationSync
```

### Logs de uma OS
```
GET /api/integration/sync-logs/os/:osId
Authorization: Bearer <token>

Response: Logs associados à OS
```

### Logs de uma Tarefa
```
GET /api/integration/sync-logs/task/:taskId
Authorization: Bearer <token>

Response: Logs associados à tarefa
```

---

## Status de Integração

### Ver Status Geral
```
GET /api/integration/status
Authorization: Bearer <token>

Response:
{
  "totalOS": 25,
  "totalTasks": 30,
  "syncedOS": 20,
  "syncLogs": 150,
  "lastSync": "2024-01-07T14:30:00Z"
}
```

---

## Mapeamento de Status

### Task → OS Status

| Task Status | OS Status |
|------------|-----------|
| pending | open |
| in_progress | in_progress |
| paused | assigned |
| completed | completed |

### Estimativa de Tempo por Prioridade

| Prioridade | Tempo Estimado |
|-----------|----------------|
| low | 120 min (2h) |
| medium | 180 min (3h) |
| high | 240 min (4h) |

---

## Casos de Uso

### 1. Criar OS e Sincronizar
```bash
# 1. Criar OS
curl -X POST http://localhost:3000/api/integration/os \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "osNumber": "OS-2024-002",
    "requester": "Maria Santos",
    "sector": "Manutenção",
    "equipment": "Ar Condicionado",
    "priority": "medium",
    "description": "Limpeza de filtros"
  }'

# 2. Sincronizar para Tarefa
curl -X POST http://localhost:3000/api/integration/sync/os-to-task \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "osId": "1",
    "productionId": "prod-001",
    "operatorId": "operator-002"
  }'

# 3. Iniciar Tarefa
curl -X POST http://localhost:3000/api/tasks/task-123/start \
  -H "Authorization: Bearer TOKEN"

# 4. Completar Tarefa
curl -X POST http://localhost:3000/api/tasks/task-123/complete \
  -H "Authorization: Bearer TOKEN"

# 5. Sincronizar Status para OS
curl -X POST http://localhost:3000/api/integration/sync/task-to-os \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{ "taskId": "task-123" }'
```

### 2. Sincronizar Lote de OS Pendentes
```bash
curl -X POST http://localhost:3000/api/integration/sync/all-pending \
  -H "Authorization: Bearer TOKEN"
```

### 3. Monitora Integração
```bash
# Ver status geral
curl -X GET http://localhost:3000/api/integration/status \
  -H "Authorization: Bearer TOKEN"

# Ver logs de sincronização
curl -X GET http://localhost:3000/api/integration/sync-logs \
  -H "Authorization: Bearer TOKEN"
```

---

## Configuração Futura

Para conectar ao sistema **my01** real (my01-yzj7.onrender.com):

1. **Obter Credenciais API** do sistema my01
2. **Configurar Webhook** para receber notificações de novas OS
3. **Implementar Autenticação** entre sistemas
4. **Testar Sincronização** em ambiente de staging

### Próximas Etapas

```typescript
// Em production, substituir:
private externalApiUrl = 'https://my01-yzj7.onrender.com/api';

// E implementar:
async fetchExternalOrderServices(): Promise<IOrderService[]> {
  const response = await axios.get(`${this.externalApiUrl}/os`, {
    headers: { Authorization: `Bearer ${process.env.MY01_API_TOKEN}` }
  });
  return response.data;
}
```

---

## Permissões

| Ação | Admin | Manager | Operator |
|------|-------|---------|----------|
| Listar OS | ✓ | ✓ | ✓ |
| Criar OS | ✓ | ✓ | ✗ |
| Atualizar OS | ✓ | ✓ | ✗ |
| Sincronizar | ✓ | ✓ | ✗ |
| Ver Logs | ✓ | ✓ | ✓ |
| Ver Status | ✓ | ✓ | ✓ |
