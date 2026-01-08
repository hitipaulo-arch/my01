export interface IProduction {
  id: string;
  name: string;
  description: string;
  machineId: string;
  operatorId: string;
  quantity: number;
  status: 'pending' | 'in_progress' | 'completed' | 'paused';
  startDate: Date;
  endDate?: Date;
  priority: 'low' | 'medium' | 'high';
  createdAt: Date;
  updatedAt: Date;
}

export interface IMachine {
  id: string;
  name: string;
  code: string;
  status: 'active' | 'inactive' | 'maintenance';
  capacity: number;
  createdAt: Date;
  updatedAt: Date;
}

export interface IOperator {
  id: string;
  name: string;
  email: string;
  department: string;
  status: 'active' | 'inactive';
  createdAt: Date;
  updatedAt: Date;
}

export interface IUser {
  id: string;
  name: string;
  email: string;
  password: string;
  role: 'admin' | 'manager' | 'operator';
  createdAt: Date;
  updatedAt: Date;
}

export interface ITask {
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

export interface ITimeTracking {
  id: string;
  taskId: string;
  startTime: Date;
  endTime?: Date;
  duration: number; // em minutos
}

export interface AuthRequest {
  email: string;
  password: string;
}

export interface TokenPayload {
  id: string;
  email: string;
  role: string;
}

// Integração com Sistema de OS (my01)
export interface IOrderService {
  id: string;
  osNumber: string; // Número da OS do sistema externo
  requester: string; // Nome do solicitante
  sector: string; // Setor
  equipment: string; // Equipamento ou local afetado
  priority: 'low' | 'medium' | 'high'; // Nível de prioridade
  description: string; // Descrição do problema
  additionalInfo?: string; // Informações adicionais
  status: 'open' | 'assigned' | 'in_progress' | 'completed' | 'closed';
  externalId?: string; // ID no sistema externo
  externalUrl?: string; // URL da OS no sistema externo
  linkedTaskId?: string; // ID da tarefa sincronizada
  createdAt: Date;
  updatedAt: Date;
}

export interface IIntegrationSync {
  id: string;
  osId: string;
  taskId: string;
  syncedAt: Date;
  syncType: 'os_to_task' | 'task_to_os';
  status: 'success' | 'failed' | 'pending';
  message?: string;
}
