import { Router } from 'express';
import { IntegrationController } from '../controllers/integration.controller';
import { authMiddleware, roleMiddleware } from '../middleware/auth';

const router = Router();
const controller = new IntegrationController();

// GET - Estatísticas de OS (sem autenticação para dashboard)
router.get('/stats', controller.getStats.bind(controller));

// Todas as outras rotas requerem autenticação
router.use(authMiddleware);

// ===== Gerenciamento de OS =====
// GET - Listar todas as OS
router.get('/os', controller.listAllOS.bind(controller));

// GET - Buscar OS por ID
router.get('/os/:id', controller.getOSById.bind(controller));

// POST - Criar nova OS (admin/manager)
router.post('/os', roleMiddleware(['admin', 'manager']), controller.createOS.bind(controller));

// PUT - Atualizar OS (admin/manager)
router.put(
  '/os/:id',
  roleMiddleware(['admin', 'manager']),
  controller.updateOS.bind(controller)
);

// ===== Sincronização =====
// POST - Sincronizar OS para Tarefa
router.post(
  '/sync/os-to-task',
  roleMiddleware(['admin', 'manager']),
  controller.syncOSToTask.bind(controller)
);

// POST - Sincronizar Tarefa para OS
router.post(
  '/sync/task-to-os',
  roleMiddleware(['admin', 'manager']),
  controller.syncTaskToOS.bind(controller)
);

// POST - Sincronizar todas as OS pendentes
router.post(
  '/sync/all-pending',
  roleMiddleware(['admin', 'manager']),
  controller.syncAllPendingOS.bind(controller)
);

// ===== Logs de Sincronização =====
// GET - Todos os logs
router.get('/sync-logs', controller.getSyncLogs.bind(controller));

// GET - Logs de uma OS específica
router.get('/sync-logs/os/:osId', controller.getSyncLogsByOS.bind(controller));

// GET - Logs de uma tarefa específica
router.get('/sync-logs/task/:taskId', controller.getSyncLogsByTask.bind(controller));

// ===== Status =====
// GET - Status geral de integração
router.get('/status', controller.getIntegrationStatus.bind(controller));

export default router;
