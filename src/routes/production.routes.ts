import { Router } from 'express';
import { ProductionController } from '../controllers/production.controller';
import { authMiddleware, roleMiddleware } from '../middleware/auth';

const router = Router();
const controller = new ProductionController();

// GET - Estatísticas gerais (sem autenticação para dashboard)
router.get('/stats', controller.getStats.bind(controller));

// Todas as outras rotas requerem autenticação
router.use(authMiddleware);

// GET - Listar todas as produções
router.get('/', controller.listAll.bind(controller));

// GET - Buscar produção por ID
router.get('/:id', controller.getById.bind(controller));

// GET - Buscar produções por status
router.get('/status/:status', controller.getByStatus.bind(controller));

// GET - Buscar produções por máquina
router.get('/machine/:machineId', controller.getByMachine.bind(controller));

// POST - Criar nova produção (apenas admin e manager)
router.post('/', roleMiddleware(['admin', 'manager']), controller.create.bind(controller));

// PUT - Atualizar produção (apenas admin e manager)
router.put('/:id', roleMiddleware(['admin', 'manager']), controller.update.bind(controller));

// DELETE - Deletar produção (apenas admin)
router.delete('/:id', roleMiddleware(['admin']), controller.delete.bind(controller));

export default router;
