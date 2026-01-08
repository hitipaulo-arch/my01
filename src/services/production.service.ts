import { IProduction } from '../types';

// Mock database com dados de exemplo
const productions: IProduction[] = [
  {
    id: '1',
    name: 'Produção Linha A',
    description: 'Produção de peças metálicas',
    machineId: 'M001',
    operatorId: 'OP001',
    status: 'in_progress',
    quantity: 650,
    priority: 'high',
    startDate: new Date('2026-01-07T08:00:00'),
    createdAt: new Date('2026-01-07T08:00:00'),
    updatedAt: new Date('2026-01-07T14:30:00'),
  },
  {
    id: '2',
    name: 'Produção Linha B',
    description: 'Montagem de componentes',
    machineId: 'M002',
    operatorId: 'OP002',
    status: 'completed',
    quantity: 520,
    priority: 'medium',
    startDate: new Date('2026-01-06T09:00:00'),
    endDate: new Date('2026-01-06T17:00:00'),
    createdAt: new Date('2026-01-06T09:00:00'),
    updatedAt: new Date('2026-01-06T17:00:00'),
  },
  {
    id: '3',
    name: 'Produção Linha C',
    description: 'Fabricação de chassis',
    machineId: 'M003',
    operatorId: 'OP003',
    status: 'paused',
    quantity: 300,
    priority: 'medium',
    startDate: new Date('2026-01-07T10:00:00'),
    createdAt: new Date('2026-01-07T10:00:00'),
    updatedAt: new Date('2026-01-07T12:00:00'),
  },
  {
    id: '4',
    name: 'Produção Linha D',
    description: 'Usinagem de precisão',
    machineId: 'M004',
    operatorId: 'OP001',
    status: 'pending',
    quantity: 0,
    priority: 'low',
    startDate: new Date('2026-01-07T15:00:00'),
    createdAt: new Date('2026-01-07T07:00:00'),
    updatedAt: new Date('2026-01-07T07:00:00'),
  },
];

export class ProductionService {
  async getAllProductions(): Promise<IProduction[]> {
    return productions;
  }

  async getProductionById(id: string): Promise<IProduction | null> {
    return productions.find((p) => p.id === id) || null;
  }

  async createProduction(data: Omit<IProduction, 'id' | 'createdAt' | 'updatedAt'>): Promise<IProduction> {
    const production: IProduction = {
      id: Date.now().toString(),
      ...data,
      createdAt: new Date(),
      updatedAt: new Date(),
    };
    productions.push(production);
    return production;
  }

  async updateProduction(id: string, data: Partial<IProduction>): Promise<IProduction | null> {
    const index = productions.findIndex((p) => p.id === id);
    if (index === -1) return null;

    const updated = {
      ...productions[index],
      ...data,
      updatedAt: new Date(),
    };
    productions[index] = updated;
    return updated;
  }

  async deleteProduction(id: string): Promise<boolean> {
    const index = productions.findIndex((p) => p.id === id);
    if (index === -1) return false;

    productions.splice(index, 1);
    return true;
  }

  async getProductionsByStatus(status: string): Promise<IProduction[]> {
    return productions.filter((p) => p.status === status);
  }

  async getProductionsByMachine(machineId: string): Promise<IProduction[]> {
    return productions.filter((p) => p.machineId === machineId);
  }
}
