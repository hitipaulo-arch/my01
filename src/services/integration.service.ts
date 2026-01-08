import { IOrderService, IIntegrationSync, ITask } from '../types';
import { TaskService } from './task.service';

// Mock database com dados de exemplo
const orderServices: IOrderService[] = [
  {
    id: '1',
    osNumber: 'OS-2026-001',
    requester: 'João Silva',
    sector: 'Produção',
    equipment: 'Máquina CNC 01',
    priority: 'high',
    description: 'Manutenção preventiva',
    status: 'in_progress',
    linkedTaskId: '2',
    externalId: 'ext-001',
    createdAt: new Date('2026-01-07T08:00:00'),
    updatedAt: new Date('2026-01-07T08:30:00'),
  },
  {
    id: '2',
    osNumber: 'OS-2026-002',
    requester: 'Maria Santos',
    sector: 'Manutenção',
    equipment: 'Esteira Linha B',
    priority: 'medium',
    description: 'Ajuste de velocidade',
    status: 'completed',
    linkedTaskId: '3',
    externalId: 'ext-002',
    createdAt: new Date('2026-01-06T09:00:00'),
    updatedAt: new Date('2026-01-06T17:00:00'),
  },
  {
    id: '3',
    osNumber: 'OS-2026-003',
    requester: 'Carlos Oliveira',
    sector: 'Qualidade',
    equipment: 'Sistema de Medição',
    priority: 'low',
    description: 'Calibração',
    status: 'open',
    externalId: 'ext-003',
    createdAt: new Date('2026-01-07T07:00:00'),
    updatedAt: new Date('2026-01-07T07:00:00'),
  },
];
const syncLogs: IIntegrationSync[] = [];

const taskService = new TaskService();

export class IntegrationService {
  // ===== Gerenciamento de OS =====
  async getAllOrderServices(): Promise<IOrderService[]> {
    return orderServices;
  }

  async getOrderServiceById(id: string): Promise<IOrderService | null> {
    return orderServices.find((os) => os.id === id) || null;
  }

  async createOrderService(
    data: Omit<IOrderService, 'id' | 'createdAt' | 'updatedAt'>
  ): Promise<IOrderService> {
    const os: IOrderService = {
      id: Date.now().toString(),
      ...data,
      createdAt: new Date(),
      updatedAt: new Date(),
    };
    orderServices.push(os);
    return os;
  }

  async updateOrderService(
    id: string,
    data: Partial<IOrderService>
  ): Promise<IOrderService | null> {
    const index = orderServices.findIndex((os) => os.id === id);
    if (index === -1) return null;

    const updated = {
      ...orderServices[index],
      ...data,
      updatedAt: new Date(),
    };
    orderServices[index] = updated;
    return updated;
  }

  // ===== Sincronização OS <-> Task =====

  /**
   * Sincroniza OS recebida do sistema externo para Tarefa
   */
  async syncOSToTask(osData: IOrderService, productionId: string, operatorId: string): Promise<{
    os: IOrderService;
    task: ITask;
    syncLog: IIntegrationSync;
  }> {
    try {
      // Criar tarefa a partir da OS
      const task = await taskService.createTask({
        name: `OS-${osData.osNumber}: ${osData.description}`,
        description: `Setor: ${osData.sector} | Equipamento: ${osData.equipment} | ${osData.additionalInfo || ''}`,
        productionId,
        operatorId,
        status: 'pending',
        estimatedTime: this.estimateTimeByPriority(osData.priority),
      });

      // Atualizar OS com referência da tarefa
      const updatedOS = await this.updateOrderService(osData.id, {
        linkedTaskId: task.id,
        status: 'assigned',
      });

      // Registrar sincronização
      const syncLog: IIntegrationSync = {
        id: Date.now().toString(),
        osId: osData.id,
        taskId: task.id,
        syncedAt: new Date(),
        syncType: 'os_to_task',
        status: 'success',
        message: 'OS sincronizada para tarefa com sucesso',
      };
      syncLogs.push(syncLog);

      return {
        os: updatedOS || osData,
        task,
        syncLog,
      };
    } catch (error) {
      const syncLog: IIntegrationSync = {
        id: Date.now().toString(),
        osId: osData.id,
        taskId: '',
        syncedAt: new Date(),
        syncType: 'os_to_task',
        status: 'failed',
        message: `Erro ao sincronizar OS: ${error instanceof Error ? error.message : 'Erro desconhecido'}`,
      };
      syncLogs.push(syncLog);
      throw error;
    }
  }

  /**
   * Sincroniza status de Tarefa para OS
   */
  async syncTaskToOS(taskId: string): Promise<{
    task: ITask | null;
    os: IOrderService | null;
    syncLog: IIntegrationSync;
  }> {
    try {
      const task = await taskService.getTaskById(taskId);
      if (!task) throw new Error('Tarefa não encontrada');

      // Encontrar OS vinculada
      const os = orderServices.find((o) => o.linkedTaskId === taskId);
      if (!os) throw new Error('OS vinculada não encontrada');

      // Mapear status da tarefa para OS
      const osStatus = this.mapTaskStatusToOSStatus(task.status);
      const updatedOS = await this.updateOrderService(os.id, {
        status: osStatus,
      });

      // Registrar sincronização
      const syncLog: IIntegrationSync = {
        id: Date.now().toString(),
        osId: os.id,
        taskId: taskId,
        syncedAt: new Date(),
        syncType: 'task_to_os',
        status: 'success',
        message: `Status da tarefa sincronizado para OS: ${osStatus}`,
      };
      syncLogs.push(syncLog);

      return {
        task,
        os: updatedOS,
        syncLog,
      };
    } catch (error) {
      const syncLog: IIntegrationSync = {
        id: Date.now().toString(),
        osId: '',
        taskId,
        syncedAt: new Date(),
        syncType: 'task_to_os',
        status: 'failed',
        message: `Erro ao sincronizar tarefa: ${error instanceof Error ? error.message : 'Erro desconhecido'}`,
      };
      syncLogs.push(syncLog);
      throw error;
    }
  }

  /**
   * Busca OS do sistema externo (mock para demonstração)
   */
  async fetchExternalOrderServices(): Promise<IOrderService[]> {
    try {
      // Em produção, isso faria uma requisição real ao sistema externo
      // const response = await axios.get(`${this.externalApiUrl}/os`);
      // return response.data;

      // Mock de dados
      return orderServices;
    } catch (error) {
      console.error('Erro ao buscar OS do sistema externo:', error);
      return [];
    }
  }

  /**
   * Sincroniza todas as OS pendentes
   */
  async syncAllPendingOS(): Promise<Array<{ os: IOrderService; task: ITask; syncLog: IIntegrationSync }>> {
    const results: Array<{ os: IOrderService; task: ITask; syncLog: IIntegrationSync }> = [];

    const pendingOS = orderServices.filter(
      (os) => os.status === 'open' && !os.linkedTaskId
    );

    for (const os of pendingOS) {
      try {
        const result = await this.syncOSToTask(os, 'default-production', 'default-operator');
        results.push(result);
      } catch (error) {
        console.error(`Erro ao sincronizar OS ${os.id}:`, error);
      }
    }

    return results;
  }

  // ===== Logs de Sincronização =====
  async getSyncLogs(): Promise<IIntegrationSync[]> {
    return syncLogs;
  }

  async getSyncLogsByOS(osId: string): Promise<IIntegrationSync[]> {
    return syncLogs.filter((log) => log.osId === osId);
  }

  async getSyncLogsByTask(taskId: string): Promise<IIntegrationSync[]> {
    return syncLogs.filter((log) => log.taskId === taskId);
  }

  // ===== Utilitários =====
  private estimateTimeByPriority(priority: 'low' | 'medium' | 'high'): number {
    const estimates: Record<string, number> = {
      low: 120, // 2 horas
      medium: 180, // 3 horas
      high: 240, // 4 horas
    };
    return estimates[priority] || 120;
  }

  private mapTaskStatusToOSStatus(
    taskStatus: string
  ): 'open' | 'assigned' | 'in_progress' | 'completed' | 'closed' {
    const statusMap: Record<string, 'open' | 'assigned' | 'in_progress' | 'completed' | 'closed'> = {
      pending: 'open',
      in_progress: 'in_progress',
      completed: 'completed',
      paused: 'assigned',
    };
    return statusMap[taskStatus] || 'open';
  }

  async getIntegrationStatus(): Promise<{
    totalOS: number;
    totalTasks: number;
    syncedOS: number;
    syncLogs: number;
    lastSync?: Date;
  }> {
    const syncedOS = orderServices.filter((os) => os.linkedTaskId).length;
    const lastSync = syncLogs.length > 0 ? syncLogs[syncLogs.length - 1].syncedAt : undefined;

    return {
      totalOS: orderServices.length,
      totalTasks: (await taskService.getAllTasks()).length,
      syncedOS,
      syncLogs: syncLogs.length,
      lastSync,
    };
  }
}
