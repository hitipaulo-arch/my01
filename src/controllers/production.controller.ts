import { Request, Response } from 'express';
import { ProductionService } from '../services/production.service';
import { IProduction } from '../types';

const service = new ProductionService();

export class ProductionController {
  async listAll(_req: Request, res: Response): Promise<void> {
    try {
      const productions = await service.getAllProductions();
      res.json(productions);
    } catch (error) {
      res.status(500).json({ error: 'Erro ao listar produções' });
    }
  }

  async getById(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const production = await service.getProductionById(id);

      if (!production) {
        res.status(404).json({ error: 'Produção não encontrada' });
        return;
      }

      res.json(production);
    } catch (error) {
      res.status(500).json({ error: 'Erro ao buscar produção' });
    }
  }

  async create(req: Request, res: Response): Promise<void> {
    try {
      const data = req.body as Omit<IProduction, 'id' | 'createdAt' | 'updatedAt'>;

      // Validações
      if (!data.name || !data.machineId || !data.operatorId) {
        res.status(400).json({ error: 'Campos obrigatórios: name, machineId, operatorId' });
        return;
      }

      const production = await service.createProduction(data);
      res.status(201).json(production);
    } catch (error) {
      res.status(500).json({ error: 'Erro ao criar produção' });
    }
  }

  async update(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const data = req.body as Partial<IProduction>;

      const production = await service.updateProduction(id, data);

      if (!production) {
        res.status(404).json({ error: 'Produção não encontrada' });
        return;
      }

      res.json(production);
    } catch (error) {
      res.status(500).json({ error: 'Erro ao atualizar produção' });
    }
  }

  async delete(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const deleted = await service.deleteProduction(id);

      if (!deleted) {
        res.status(404).json({ error: 'Produção não encontrada' });
        return;
      }

      res.status(204).send();
    } catch (error) {
      res.status(500).json({ error: 'Erro ao deletar produção' });
    }
  }

  async getByStatus(req: Request, res: Response): Promise<void> {
    try {
      const { status } = req.params;
      const productions = await service.getProductionsByStatus(status);
      res.json(productions);
    } catch (error) {
      res.status(500).json({ error: 'Erro ao buscar produções por status' });
    }
  }

  async getByMachine(req: Request, res: Response): Promise<void> {
    try {
      const { machineId } = req.params;
      const productions = await service.getProductionsByMachine(machineId);
      res.json(productions);
    } catch (error) {
      res.status(500).json({ error: 'Erro ao buscar produções por máquina' });
    }
  }

  async getStats(_req: Request, res: Response): Promise<void> {
    try {
      const productions = await service.getAllProductions();
      const stats = {
        total: productions.length,
        inProgress: productions.filter(p => p.status === 'in_progress').length,
        completed: productions.filter(p => p.status === 'completed').length,
        paused: productions.filter(p => p.status === 'paused').length,
        pending: productions.filter(p => p.status === 'pending').length,
        recent: productions.slice(-5).reverse()
      };
      res.json(stats);
    } catch (error) {
      res.status(500).json({ error: 'Erro ao obter estatísticas' });
    }
  }
}
