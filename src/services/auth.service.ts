import bcrypt from 'bcryptjs';
import jwt, { Secret } from 'jsonwebtoken';
import { config } from '../config';
import { IUser, TokenPayload } from '../types';

// Mock database
const users: IUser[] = [];

export class AuthService {
  async register(name: string, email: string, password: string, role: string = 'operator'): Promise<IUser> {
    const hashedPassword = await bcrypt.hash(password, 10);

    const user: IUser = {
      id: Date.now().toString(),
      name,
      email,
      password: hashedPassword,
      role: role as 'admin' | 'manager' | 'operator',
      createdAt: new Date(),
      updatedAt: new Date(),
    };

    users.push(user);
    return user;
  }

  async login(email: string, password: string): Promise<{ token: string; user: Omit<IUser, 'password'> }> {
    const user = users.find((u) => u.email === email);

    if (!user) {
      throw new Error('Usuário não encontrado');
    }

    const isPasswordValid = await bcrypt.compare(password, user.password);

    if (!isPasswordValid) {
      throw new Error('Senha inválida');
    }

    const payload: TokenPayload = {
      id: user.id,
      email: user.email,
      role: user.role,
    };

    const token = jwt.sign(payload, config.jwt.secret as Secret, {
      expiresIn: '24h',
    });

    const { password: _, ...userWithoutPassword } = user;

    return {
      token,
      user: userWithoutPassword,
    };
  }

  async getUserById(id: string): Promise<Omit<IUser, 'password'> | null> {
    const user = users.find((u) => u.id === id);

    if (!user) return null;

    const { password: _, ...userWithoutPassword } = user;
    return userWithoutPassword;
  }
}
