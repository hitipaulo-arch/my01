import { ITask, ITimeTracking } from '../types';

// Mock database com dados de exemplo
const tasks: ITask[] = [
  {
    id: '1',
    name: 'Configurar máquina',
    description: 'Configurar parâmetros da máquina para nova produção',
    productionId: '1',
    operatorId: 'OP001',
    status: 'completed',
    estimatedTime: 30,
    actualTime: 25,
    startTime: new Date('2026-01-07T08:00:00'),
    endTime: new Date('2026-01-07T08:25:00'),
    createdAt: new Date('2026-01-07T07:30:00'),
    updatedAt: new Date('2026-01-07T08:25:00'),
  },
  {
    id: '2',
    name: 'Monitorar produção',
    description: 'Monitorar linha de produção A',
    productionId: '1',
    operatorId: 'OP001',
    status: 'in_progress',
    estimatedTime: 180,
    actualTime: 120,
    startTime: new Date('2026-01-07T08:30:00'),
    createdAt: new Date('2026-01-07T08:25:00'),
    updatedAt: new Date('2026-01-07T14:30:00'),
  },
  {
    id: '3',
    name: 'Preparar material',
    description: 'Separar materiais',
    productionId: '4',
    operatorId: 'OP001',
    status: 'pending',
    estimatedTime: 40,
    createdAt: new Date('2026-01-07T07:00:00'),
    updatedAt: new Date('2026-01-07T07:00:00'),
  },
  {
    id: '4',
    name: 'Inspeção qualidade',
    description: 'Verificar qualidade dos produtos',
    productionId: '2',
    operatorId: 'OP002',
    status: 'completed',
    estimatedTime: 60,
    actualTime: 55,
    startTime: new Date('2026-01-06T16:00:00'),
    endTime: new Date('2026-01-06T16:55:00'),
    createdAt: new Date('2026-01-06T15:30:00'),
    updatedAt: new Date('2026-01-06T16:55:00'),
  },
  {
    id: '5',
    name: 'Trocar ferramenta',
    description: 'Substituir ferramenta desgastada',
    productionId: '3',
    operatorId: 'OP003',
    status: 'paused',
    estimatedTime: 45,
    actualTime: 20,
    startTime: new Date('2026-01-07T11:00:00'),
    createdAt: new Date('2026-01-07T10:50:00'),
    updatedAt: new Date('2026-01-07T11:20:00'),
  },
];
const timeTrackings: ITimeTracking[] = [];

export class TaskService {
  async getAllTasks(): Promise<ITask[]> {
    return tasks;
  }

  async getTaskById(id: string): Promise<ITask | null> {
    return tasks.find((t) => t.id === id) || null;
  }

  async createTask(
    data: Omit<ITask, 'id' | 'actualTime' | 'createdAt' | 'updatedAt'>
  ): Promise<ITask> {
    const task: ITask = {
      id: Date.now().toString(),
      ...data,
      actualTime: 0,
      createdAt: new Date(),
      updatedAt: new Date(),
    };
    tasks.push(task);
    return task;
  }

  async updateTask(id: string, data: Partial<ITask>): Promise<ITask | null> {
    const index = tasks.findIndex((t) => t.id === id);
    if (index === -1) return null;

    const updated = {
      ...tasks[index],
      ...data,
      updatedAt: new Date(),
    };
    tasks[index] = updated;
    return updated;
  }

  async deleteTask(id: string): Promise<boolean> {
    const index = tasks.findIndex((t) => t.id === id);
    if (index === -1) return false;

    tasks.splice(index, 1);
    // Deletar rastreamentos associados
    const trackingIndices = timeTrackings
      .map((t, i) => (t.taskId === id ? i : -1))
      .filter((i) => i !== -1);
    for (let i = trackingIndices.length - 1; i >= 0; i--) {
      timeTrackings.splice(trackingIndices[i], 1);
    }
    return true;
  }

  async getTasksByProduction(productionId: string): Promise<ITask[]> {
    return tasks.filter((t) => t.productionId === productionId);
  }

  async getTasksByOperator(operatorId: string): Promise<ITask[]> {
    return tasks.filter((t) => t.operatorId === operatorId);
  }

  async getTasksByStatus(status: string): Promise<ITask[]> {
    return tasks.filter((t) => t.status === status);
  }

  // Gerenciamento de tempo
  async startTask(taskId: string): Promise<ITask | null> {
    const task = await this.getTaskById(taskId);
    if (!task) return null;

    const updated = await this.updateTask(taskId, {
      status: 'in_progress',
      startTime: new Date(),
    });

    // Criar rastreamento de tempo
    if (updated) {
      const tracking: ITimeTracking = {
        id: Date.now().toString(),
        taskId,
        startTime: new Date(),
        duration: 0,
      };
      timeTrackings.push(tracking);
    }

    return updated;
  }

  async pauseTask(taskId: string): Promise<ITask | null> {
    const task = await this.getTaskById(taskId);
    if (!task) return null;

    // Fechar rastreamento ativo
    const activeTracking = timeTrackings.find(
      (t) => t.taskId === taskId && !t.endTime
    );
    if (activeTracking) {
      activeTracking.endTime = new Date();
      const duration =
        (activeTracking.endTime.getTime() - activeTracking.startTime.getTime()) /
        (1000 * 60); // em minutos
      activeTracking.duration = Math.round(duration);
    }

    return this.updateTask(taskId, { status: 'paused' });
  }

  async resumeTask(taskId: string): Promise<ITask | null> {
    const task = await this.getTaskById(taskId);
    if (!task) return null;

    const updated = await this.updateTask(taskId, {
      status: 'in_progress',
    });

    // Criar novo rastreamento
    if (updated) {
      const tracking: ITimeTracking = {
        id: Date.now().toString(),
        taskId,
        startTime: new Date(),
        duration: 0,
      };
      timeTrackings.push(tracking);
    }

    return updated;
  }

  async completeTask(taskId: string): Promise<ITask | null> {
    const task = await this.getTaskById(taskId);
    if (!task) return null;

    // Fechar rastreamento ativo
    const activeTracking = timeTrackings.find(
      (t) => t.taskId === taskId && !t.endTime
    );
    if (activeTracking) {
      activeTracking.endTime = new Date();
      const duration =
        (activeTracking.endTime.getTime() - activeTracking.startTime.getTime()) /
        (1000 * 60);
      activeTracking.duration = Math.round(duration);
    }

    // Calcular tempo total
    const taskTrackings = timeTrackings.filter((t) => t.taskId === taskId);
    const totalTime = taskTrackings.reduce((sum, t) => sum + t.duration, 0);

    const endTime = new Date();
    return this.updateTask(taskId, {
      status: 'completed',
      actualTime: totalTime,
      endTime,
    });
  }

  async getTaskTimeTrackings(taskId: string): Promise<ITimeTracking[]> {
    return timeTrackings.filter((t) => t.taskId === taskId);
  }

  async getTaskTimeReport(taskId: string): Promise<{
    taskId: string;
    totalTime: number;
    trackings: ITimeTracking[];
  }> {
    const taskTrackings = await this.getTaskTimeTrackings(taskId);
    const totalTime = taskTrackings.reduce((sum, t) => sum + t.duration, 0);

    return {
      taskId,
      totalTime,
      trackings: taskTrackings,
    };
  }
}
