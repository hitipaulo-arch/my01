import { Request, Response } from 'express';
import { TaskService } from '../services/task.service';
import { ITask } from '../types';

const service = new TaskService();

export class TaskController {
  async listAll(_req: Request, res: Response): Promise<void> {
    try {
      const tasks = await service.getAllTasks();
      res.json(tasks);
    } catch (error) {
      res.status(500).json({ error: 'Erro ao listar tarefas' });
    }
  }

  async getById(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const task = await service.getTaskById(id);

      if (!task) {
        res.status(404).json({ error: 'Tarefa não encontrada' });
        return;
      }

      res.json(task);
    } catch (error) {
      res.status(500).json({ error: 'Erro ao buscar tarefa' });
    }
  }

  async create(req: Request, res: Response): Promise<void> {
    try {
      const data = req.body as Omit<
        ITask,
        'id' | 'actualTime' | 'createdAt' | 'updatedAt'
      >;

      // Validações
      if (!data.name || !data.productionId || !data.operatorId) {
        res
          .status(400)
          .json({
            error:
              'Campos obrigatórios: name, productionId, operatorId, estimatedTime',
          });
        return;
      }

      const task = await service.createTask(data);
      res.status(201).json(task);
    } catch (error) {
      res.status(500).json({ error: 'Erro ao criar tarefa' });
    }
  }

  async update(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const data = req.body as Partial<ITask>;

      const task = await service.updateTask(id, data);

      if (!task) {
        res.status(404).json({ error: 'Tarefa não encontrada' });
        return;
      }

      res.json(task);
    } catch (error) {
      res.status(500).json({ error: 'Erro ao atualizar tarefa' });
    }
  }

  async delete(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const deleted = await service.deleteTask(id);

      if (!deleted) {
        res.status(404).json({ error: 'Tarefa não encontrada' });
        return;
      }

      res.status(204).send();
    } catch (error) {
      res.status(500).json({ error: 'Erro ao deletar tarefa' });
    }
  }

  // Gerenciamento de tempo
  async startTask(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const task = await service.startTask(id);

      if (!task) {
        res.status(404).json({ error: 'Tarefa não encontrada' });
        return;
      }

      res.json({
        message: 'Tarefa iniciada',
        task,
      });
    } catch (error) {
      res.status(500).json({ error: 'Erro ao iniciar tarefa' });
    }
  }

  async pauseTask(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const task = await service.pauseTask(id);

      if (!task) {
        res.status(404).json({ error: 'Tarefa não encontrada' });
        return;
      }

      res.json({
        message: 'Tarefa pausada',
        task,
      });
    } catch (error) {
      res.status(500).json({ error: 'Erro ao pausar tarefa' });
    }
  }

  async resumeTask(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const task = await service.resumeTask(id);

      if (!task) {
        res.status(404).json({ error: 'Tarefa não encontrada' });
        return;
      }

      res.json({
        message: 'Tarefa retomada',
        task,
      });
    } catch (error) {
      res.status(500).json({ error: 'Erro ao retomar tarefa' });
    }
  }

  async completeTask(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const task = await service.completeTask(id);

      if (!task) {
        res.status(404).json({ error: 'Tarefa não encontrada' });
        return;
      }

      res.json({
        message: 'Tarefa concluída',
        task,
      });
    } catch (error) {
      res.status(500).json({ error: 'Erro ao completar tarefa' });
    }
  }

  async getTimeTrackings(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const trackings = await service.getTaskTimeTrackings(id);
      res.json(trackings);
    } catch (error) {
      res.status(500).json({ error: 'Erro ao buscar rastreamentos' });
    }
  }

  async getTimeReport(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const report = await service.getTaskTimeReport(id);
      res.json(report);
    } catch (error) {
      res.status(500).json({ error: 'Erro ao gerar relatório de tempo' });
    }
  }

  async getByProduction(req: Request, res: Response): Promise<void> {
    try {
      const { productionId } = req.params;
      const tasks = await service.getTasksByProduction(productionId);
      res.json(tasks);
    } catch (error) {
      res.status(500).json({ error: 'Erro ao buscar tarefas da produção' });
    }
  }

  async getByOperator(req: Request, res: Response): Promise<void> {
    try {
      const { operatorId } = req.params;
      const tasks = await service.getTasksByOperator(operatorId);
      res.json(tasks);
    } catch (error) {
      res.status(500).json({ error: 'Erro ao buscar tarefas do operador' });
    }
  }

  async getByStatus(req: Request, res: Response): Promise<void> {
    try {
      const { status } = req.params;
      const tasks = await service.getTasksByStatus(status);
      res.json(tasks);
    } catch (error) {
      res.status(500).json({ error: 'Erro ao buscar tarefas por status' });
    }
  }

  async getStats(_req: Request, res: Response): Promise<void> {
    try {
      const tasks = await service.getAllTasks();
      const stats = {
        total: tasks.length,
        pending: tasks.filter(t => t.status === 'pending').length,
        inProgress: tasks.filter(t => t.status === 'in_progress').length,
        paused: tasks.filter(t => t.status === 'paused').length,
        completed: tasks.filter(t => t.status === 'completed').length,
        active: tasks.filter(t => ['in_progress', 'paused'].includes(t.status)).slice(-5).reverse()
      };
      res.json(stats);
    } catch (error) {
      res.status(500).json({ error: 'Erro ao obter estatísticas' });
    }
  }
}
