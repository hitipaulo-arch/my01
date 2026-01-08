# Task Management - Gerenciamento de Tempo por Tarefa

## Visão Geral

O módulo de gerenciamento de tarefas permite rastrear o tempo gasto em cada tarefa durante a produção. Cada tarefa pode ser:

- Criada, editada e deletada
- Iniciada, pausada, retomada e concluída
- Rastreada com histórico de tempo
- Filtrada por produção, operador ou status

## Endpoints de Tarefas

### Listar Todas as Tarefas
```
GET /api/tasks
Authorization: Bearer <token>

Response:
[
  {
    "id": "task-001",
    "name": "Montagem de componentes",
    "description": "Descrição da tarefa",
    "productionId": "prod-001",
    "operatorId": "operator-001",
    "status": "completed",
    "estimatedTime": 120,
    "actualTime": 135,
    "startTime": "2024-01-07T10:00:00Z",
    "endTime": "2024-01-07T12:15:00Z",
    "createdAt": "2024-01-07T10:00:00Z",
    "updatedAt": "2024-01-07T12:15:00Z"
  }
]
```

### Buscar Tarefa por ID
```
GET /api/tasks/:id
Authorization: Bearer <token>

Response:
{
  "id": "task-001",
  "name": "Montagem de componentes",
  ...
}
```

### Criar Nova Tarefa
```
POST /api/tasks
Authorization: Bearer <token> (admin/manager)
Content-Type: application/json

Request:
{
  "name": "Nova tarefa",
  "description": "Descrição",
  "productionId": "prod-001",
  "operatorId": "operator-001",
  "status": "pending",
  "estimatedTime": 120
}

Response: (201 Created)
{
  "id": "task-new",
  "name": "Nova tarefa",
  "actualTime": 0,
  ...
}
```

### Atualizar Tarefa
```
PUT /api/tasks/:id
Authorization: Bearer <token> (admin/manager)
Content-Type: application/json

Request:
{
  "name": "Tarefa atualizada",
  "estimatedTime": 150
}

Response:
{
  "id": "task-001",
  "name": "Tarefa atualizada",
  ...
}
```

### Deletar Tarefa
```
DELETE /api/tasks/:id
Authorization: Bearer <token> (admin)

Response: (204 No Content)
```

### Buscar Tarefas por Produção
```
GET /api/tasks/production/:productionId
Authorization: Bearer <token>

Response: Array de tarefas da produção
```

### Buscar Tarefas por Operador
```
GET /api/tasks/operator/:operatorId
Authorization: Bearer <token>

Response: Array de tarefas do operador
```

### Buscar Tarefas por Status
```
GET /api/tasks/status/:status
Authorization: Bearer <token>

Status values: pending, in_progress, completed, paused

Response: Array de tarefas com status especificado
```

## Gerenciamento de Tempo

### Iniciar Tarefa
```
POST /api/tasks/:id/start
Authorization: Bearer <token>

Response:
{
  "message": "Tarefa iniciada",
  "task": {
    "id": "task-001",
    "status": "in_progress",
    "startTime": "2024-01-07T14:30:00Z",
    ...
  }
}
```

### Pausar Tarefa
```
POST /api/tasks/:id/pause
Authorization: Bearer <token>

Response:
{
  "message": "Tarefa pausada",
  "task": {
    "id": "task-001",
    "status": "paused",
    ...
  }
}
```

### Retomar Tarefa
```
POST /api/tasks/:id/resume
Authorization: Bearer <token>

Response:
{
  "message": "Tarefa retomada",
  "task": {
    "id": "task-001",
    "status": "in_progress",
    ...
  }
}
```

### Completar Tarefa
```
POST /api/tasks/:id/complete
Authorization: Bearer <token>

Response:
{
  "message": "Tarefa concluída",
  "task": {
    "id": "task-001",
    "status": "completed",
    "endTime": "2024-01-07T16:45:00Z",
    "actualTime": 135
  }
}
```

## Rastreamento de Tempo

### Buscar Rastreamentos de Tempo
```
GET /api/tasks/:id/time-trackings
Authorization: Bearer <token>

Response:
[
  {
    "id": "tracking-001",
    "taskId": "task-001",
    "startTime": "2024-01-07T14:30:00Z",
    "endTime": "2024-01-07T15:30:00Z",
    "duration": 60
  },
  {
    "id": "tracking-002",
    "taskId": "task-001",
    "startTime": "2024-01-07T15:45:00Z",
    "endTime": "2024-01-07T16:45:00Z",
    "duration": 60
  }
]
```

### Gerar Relatório de Tempo
```
GET /api/tasks/:id/time-report
Authorization: Bearer <token>

Response:
{
  "taskId": "task-001",
  "totalTime": 120,
  "trackings": [
    {
      "id": "tracking-001",
      "taskId": "task-001",
      "startTime": "2024-01-07T14:30:00Z",
      "endTime": "2024-01-07T15:30:00Z",
      "duration": 60
    },
    ...
  ]
}
```

## Estrutura de Dados

### ITask
```typescript
{
  id: string;
  name: string;
  description?: string;
  productionId: string;
  operatorId: string;
  status: 'pending' | 'in_progress' | 'completed' | 'paused';
  estimatedTime: number; // em minutos
  actualTime?: number; // em minutos
  startTime?: Date;
  endTime?: Date;
  createdAt: Date;
  updatedAt: Date;
}
```

### ITimeTracking
```typescript
{
  id: string;
  taskId: string;
  startTime: Date;
  endTime?: Date;
  duration: number; // em minutos
}
```

## Casos de Uso

### Criar e Rastrear uma Tarefa
```bash
# 1. Criar tarefa
curl -X POST http://localhost:3000/api/tasks \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Montagem",
    "productionId": "prod-1",
    "operatorId": "op-1",
    "estimatedTime": 120,
    "status": "pending"
  }'

# 2. Iniciar tarefa
curl -X POST http://localhost:3000/api/tasks/task-id/start \
  -H "Authorization: Bearer TOKEN"

# 3. Pausar (se necessário)
curl -X POST http://localhost:3000/api/tasks/task-id/pause \
  -H "Authorization: Bearer TOKEN"

# 4. Retomar
curl -X POST http://localhost:3000/api/tasks/task-id/resume \
  -H "Authorization: Bearer TOKEN"

# 5. Completar
curl -X POST http://localhost:3000/api/tasks/task-id/complete \
  -H "Authorization: Bearer TOKEN"

# 6. Ver relatório
curl -X GET http://localhost:3000/api/tasks/task-id/time-report \
  -H "Authorization: Bearer TOKEN"
```

## Permissões

| Ação | Admin | Manager | Operator |
|------|-------|---------|----------|
| Listar tarefas | ✓ | ✓ | ✓ |
| Criar tarefa | ✓ | ✓ | ✗ |
| Atualizar tarefa | ✓ | ✓ | ✗ |
| Deletar tarefa | ✓ | ✗ | ✗ |
| Iniciar tarefa | ✓ | ✓ | ✓ |
| Pausar tarefa | ✓ | ✓ | ✓ |
| Retomar tarefa | ✓ | ✓ | ✓ |
| Completar tarefa | ✓ | ✓ | ✓ |
| Ver rastreamento | ✓ | ✓ | ✓ |
| Ver relatório | ✓ | ✓ | ✓ |
