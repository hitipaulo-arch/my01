import { Router } from 'express';
import { TaskController } from '../controllers/task.controller';
import { authMiddleware, roleMiddleware } from '../middleware/auth';

const router = Router();
const controller = new TaskController();

// GET - Estatísticas de tarefas (sem autenticação para dashboard)
router.get('/stats', controller.getStats.bind(controller));

// Todas as outras rotas requerem autenticação
router.use(authMiddleware);

// GET - Listar todas as tarefas
router.get('/', controller.listAll.bind(controller));

// GET - Buscar tarefa por ID
router.get('/:id', controller.getById.bind(controller));

// GET - Buscar tarefas por produção
router.get('/production/:productionId', controller.getByProduction.bind(controller));

// GET - Buscar tarefas por operador
router.get('/operator/:operatorId', controller.getByOperator.bind(controller));

// GET - Buscar tarefas por status
router.get('/status/:status', controller.getByStatus.bind(controller));

// GET - Rastreamentos de tempo de uma tarefa
router.get('/:id/time-trackings', controller.getTimeTrackings.bind(controller));

// GET - Relatório de tempo de uma tarefa
router.get('/:id/time-report', controller.getTimeReport.bind(controller));

// POST - Criar nova tarefa (apenas admin e manager)
router.post('/', roleMiddleware(['admin', 'manager']), controller.create.bind(controller));

// PUT - Atualizar tarefa (apenas admin e manager)
router.put('/:id', roleMiddleware(['admin', 'manager']), controller.update.bind(controller));

// DELETE - Deletar tarefa (apenas admin)
router.delete('/:id', roleMiddleware(['admin']), controller.delete.bind(controller));

// Gerenciamento de tempo
// POST - Iniciar tarefa (todos os roles autenticados)
router.post('/:id/start', controller.startTask.bind(controller));

// POST - Pausar tarefa (todos os roles autenticados)
router.post('/:id/pause', controller.pauseTask.bind(controller));

// POST - Retomar tarefa (todos os roles autenticados)
router.post('/:id/resume', controller.resumeTask.bind(controller));

// POST - Completar tarefa (todos os roles autenticados)
router.post('/:id/complete', controller.completeTask.bind(controller));

export default router;
