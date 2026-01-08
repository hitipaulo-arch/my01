import express, { Express, Request, Response } from 'express';
import cors from 'cors';
import helmet from 'helmet';
import path from 'path';
import { config } from './config';
import authRoutes from './routes/auth.routes';
import productionRoutes from './routes/production.routes';
import taskRoutes from './routes/task.routes';
import integrationRoutes from './routes/integration.routes';

const app: Express = express();

// Middleware global
app.use(helmet());
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Arquivos estáticos
app.use(express.static(path.join(__dirname, '../public')));

// Health check
app.get('/health', (_req: Request, res: Response) => {
  res.json({ status: 'OK', timestamp: new Date().toISOString() });
});

// Rotas
app.use('/api/auth', authRoutes);
app.use('/api/productions', productionRoutes);
app.use('/api/tasks', taskRoutes);
app.use('/api/integration', integrationRoutes);

// 404 handler
app.use((_req: Request, res: Response) => {
  res.status(404).json({ error: 'Rota não encontrada' });
});

// Error handler
app.use((err: any, _req: Request, res: Response) => {
  console.error(err);
  res.status(500).json({ error: 'Erro interno do servidor' });
});

const PORT = config.server.port;

app.listen(PORT, () => {
  console.log(`🚀 Servidor iniciado em http://localhost:${PORT}`);
  console.log(`📝 Ambiente: ${config.server.nodeEnv}`);
});

export default app;
