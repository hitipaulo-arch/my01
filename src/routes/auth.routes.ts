import { Router } from 'express';
import { AuthController } from '../controllers/auth.controller';
import { authMiddleware } from '../middleware/auth';

const router = Router();
const controller = new AuthController();

// POST - Registrar novo usuário
router.post('/register', controller.register.bind(controller));

// POST - Login
router.post('/login', controller.login.bind(controller));

// GET - Obter perfil do usuário autenticado
router.get('/profile', authMiddleware, controller.getProfile.bind(controller));

export default router;
