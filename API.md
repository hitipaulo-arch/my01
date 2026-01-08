# API Endpoints Reference

## Base URL
```
http://localhost:3000/api
```

## Authentication Endpoints

### Register (Registrar novo usuário)
```
POST /auth/register
Content-Type: application/json

Request:
{
  "name": "João Silva",
  "email": "joao@example.com",
  "password": "senha123",
  "role": "operator" // opcional: admin, manager, operator
}

Response:
{
  "message": "Usuário registrado com sucesso",
  "user": {
    "id": "123",
    "name": "João Silva",
    "email": "joao@example.com",
    "role": "operator"
  }
}
```

### Login
```
POST /auth/login
Content-Type: application/json

Request:
{
  "email": "joao@example.com",
  "password": "senha123"
}

Response:
{
  "token": "eyJhbGciOiJIUzI1NiIs...",
  "user": {
    "id": "123",
    "name": "João Silva",
    "email": "joao@example.com",
    "role": "operator"
  }
}
```

### Get Profile
```
GET /auth/profile
Authorization: Bearer <token>

Response:
{
  "id": "123",
  "name": "João Silva",
  "email": "joao@example.com",
  "role": "operator"
}
```

## Production Endpoints

### List All Productions
```
GET /productions
Authorization: Bearer <token>

Response:
[
  {
    "id": "prod-001",
    "name": "Produção A",
    "description": "Descrição",
    "machineId": "machine-001",
    "operatorId": "operator-001",
    "quantity": 100,
    "status": "in_progress",
    "priority": "high",
    "startDate": "2024-01-07T10:00:00Z",
    "endDate": null,
    "createdAt": "2024-01-07T10:00:00Z",
    "updatedAt": "2024-01-07T10:00:00Z"
  }
]
```

### Get Production by ID
```
GET /productions/:id
Authorization: Bearer <token>

Response:
{
  "id": "prod-001",
  "name": "Produção A",
  ...
}
```

### Get Productions by Status
```
GET /productions/status/:status
Authorization: Bearer <token>

Status values: pending, in_progress, completed, paused

Response: Array of productions with specified status
```

### Get Productions by Machine
```
GET /productions/machine/:machineId
Authorization: Bearer <token>

Response: Array of productions for the specified machine
```

### Create Production (admin/manager only)
```
POST /productions
Authorization: Bearer <token>
Content-Type: application/json

Request:
{
  "name": "Nova Produção",
  "description": "Descrição",
  "machineId": "machine-001",
  "operatorId": "operator-001",
  "quantity": 50,
  "status": "pending",
  "priority": "medium",
  "startDate": "2024-01-08T10:00:00Z"
}

Response: (201 Created)
{
  "id": "prod-new",
  "name": "Nova Produção",
  ...
}
```

### Update Production (admin/manager only)
```
PUT /productions/:id
Authorization: Bearer <token>
Content-Type: application/json

Request:
{
  "status": "in_progress",
  "quantity": 75
}

Response:
{
  "id": "prod-001",
  "status": "in_progress",
  "quantity": 75,
  ...
}
```

### Delete Production (admin only)
```
DELETE /productions/:id
Authorization: Bearer <token>

Response: (204 No Content)
```

## Health Check

### Server Status
```
GET /health

Response:
{
  "status": "OK",
  "timestamp": "2024-01-07T10:00:00.000Z"
}
```

## Error Responses

### 400 Bad Request
```json
{
  "error": "Campos obrigatórios: name, machineId, operatorId"
}
```

### 401 Unauthorized
```json
{
  "error": "Token não fornecido"
}
```

### 403 Forbidden
```json
{
  "error": "Acesso negado"
}
```

### 404 Not Found
```json
{
  "error": "Produção não encontrada"
}
```

### 500 Internal Server Error
```json
{
  "error": "Erro interno do servidor"
}
```
