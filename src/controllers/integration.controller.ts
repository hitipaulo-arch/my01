import { Request, Response } from 'express';
import { IntegrationService } from '../services/integration.service';
import { IOrderService } from '../types';

const service = new IntegrationService();

export class IntegrationController {
  // ===== Gerenciamento de OS =====
  async listAllOS(_req: Request, res: Response): Promise<void> {
    try {
      const os = await service.getAllOrderServices();
      res.json(os);
    } catch (error) {
      res.status(500).json({ error: 'Erro ao listar OS' });
    }
  }

  async getOSById(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const os = await service.getOrderServiceById(id);

      if (!os) {
        res.status(404).json({ error: 'OS não encontrada' });
        return;
      }

      res.json(os);
    } catch (error) {
      res.status(500).json({ error: 'Erro ao buscar OS' });
    }
  }

  async createOS(req: Request, res: Response): Promise<void> {
    try {
      const data = req.body as Omit<IOrderService, 'id' | 'createdAt' | 'updatedAt'>;

      // Validações
      if (!data.osNumber || !data.requester || !data.sector) {
        res
          .status(400)
          .json({
            error: 'Campos obrigatórios: osNumber, requester, sector, description, priority',
          });
        return;
      }

      const os = await service.createOrderService(data);
      res.status(201).json(os);
    } catch (error) {
      res.status(500).json({ error: 'Erro ao criar OS' });
    }
  }

  async updateOS(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const data = req.body as Partial<IOrderService>;

      const os = await service.updateOrderService(id, data);

      if (!os) {
        res.status(404).json({ error: 'OS não encontrada' });
        return;
      }

      res.json(os);
    } catch (error) {
      res.status(500).json({ error: 'Erro ao atualizar OS' });
    }
  }

  // ===== Sincronização =====
  async syncOSToTask(req: Request, res: Response): Promise<void> {
    try {
      const { osId, productionId, operatorId } = req.body;

      if (!osId || !productionId || !operatorId) {
        res
          .status(400)
          .json({
            error: 'Campos obrigatórios: osId, productionId, operatorId',
          });
        return;
      }

      const os = await service.getOrderServiceById(osId);
      if (!os) {
        res.status(404).json({ error: 'OS não encontrada' });
        return;
      }

      const result = await service.syncOSToTask(os, productionId, operatorId);

      res.status(201).json({
        message: 'OS sincronizada com sucesso',
        data: result,
      });
    } catch (error) {
      res.status(500).json({
        error: 'Erro ao sincronizar OS',
        details: error instanceof Error ? error.message : 'Erro desconhecido',
      });
    }
  }

  async syncTaskToOS(req: Request, res: Response): Promise<void> {
    try {
      const { taskId } = req.body;

      if (!taskId) {
        res.status(400).json({ error: 'Campo obrigatório: taskId' });
        return;
      }

      const result = await service.syncTaskToOS(taskId);

      res.json({
        message: 'Tarefa sincronizada com sucesso',
        data: result,
      });
    } catch (error) {
      res.status(500).json({
        error: 'Erro ao sincronizar tarefa',
        details: error instanceof Error ? error.message : 'Erro desconhecido',
      });
    }
  }

  async syncAllPendingOS(_req: Request, res: Response): Promise<void> {
    try {
      const results = await service.syncAllPendingOS();

      res.json({
        message: `${results.length} OS sincronizadas com sucesso`,
        results,
      });
    } catch (error) {
      res.status(500).json({
        error: 'Erro ao sincronizar OS pendentes',
        details: error instanceof Error ? error.message : 'Erro desconhecido',
      });
    }
  }

  // ===== Logs de Sincronização =====
  async getSyncLogs(_req: Request, res: Response): Promise<void> {
    try {
      const logs = await service.getSyncLogs();
      res.json(logs);
    } catch (error) {
      res.status(500).json({ error: 'Erro ao buscar logs' });
    }
  }

  async getSyncLogsByOS(req: Request, res: Response): Promise<void> {
    try {
      const { osId } = req.params;
      const logs = await service.getSyncLogsByOS(osId);
      res.json(logs);
    } catch (error) {
      res.status(500).json({ error: 'Erro ao buscar logs da OS' });
    }
  }

  async getSyncLogsByTask(req: Request, res: Response): Promise<void> {
    try {
      const { taskId } = req.params;
      const logs = await service.getSyncLogsByTask(taskId);
      res.json(logs);
    } catch (error) {
      res.status(500).json({ error: 'Erro ao buscar logs da tarefa' });
    }
  }

  // ===== Status de Integração =====
  async getIntegrationStatus(_req: Request, res: Response): Promise<void> {
    try {
      const status = await service.getIntegrationStatus();
      res.json(status);
    } catch (error) {
      res.status(500).json({ error: 'Erro ao buscar status de integração' });
    }
  }
  async getStats(_req: Request, res: Response): Promise<void> {
    try {
      const allOS = await service.getAllOrderServices();
      const stats = {
        total: allOS.length,
        synced: allOS.filter((os: IOrderService) => !!os.linkedTaskId).length,
        pending: allOS.filter((os: IOrderService) => !os.linkedTaskId && os.status !== 'closed').length,
        open: allOS.filter((os: IOrderService) => os.status === 'open').length,
        inProgress: allOS.filter((os: IOrderService) => os.status === 'in_progress').length,
        completed: allOS.filter((os: IOrderService) => os.status === 'completed').length,
        recent: allOS.slice(-5).reverse()
      };
      res.json(stats);
    } catch (error) {
      res.status(500).json({ error: 'Erro ao obter estatísticas' });
    }
  }
}
