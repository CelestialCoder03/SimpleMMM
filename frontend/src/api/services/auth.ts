import apiClient from '../client';
import type { LoginRequest, LoginResponse, RegisterRequest, User } from '@/types';

export const authApi = {
  login: async (data: LoginRequest): Promise<LoginResponse> => {
    const formData = new URLSearchParams();
    formData.append('username', data.email);
    formData.append('password', data.password);
    
    const response = await apiClient.post<LoginResponse>('/auth/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
    return response.data;
  },

  register: async (data: RegisterRequest): Promise<User> => {
    const response = await apiClient.post<User>('/auth/register', data);
    return response.data;
  },

  getMe: async (): Promise<User> => {
    const response = await apiClient.get<User>('/auth/me');
    return response.data;
  },

  refresh: async (refreshToken: string): Promise<LoginResponse> => {
    const response = await apiClient.post<LoginResponse>('/auth/refresh', {
      refresh_token: refreshToken,
    });
    return response.data;
  },

  requestPasswordReset: async (email: string): Promise<void> => {
    await apiClient.post('/auth/password-reset/request', { email });
  },

  validateResetToken: async (token: string): Promise<{ valid: boolean }> => {
    const response = await apiClient.post<{ valid: boolean }>('/auth/password-reset/validate', null, {
      params: { token },
    });
    return response.data;
  },

  confirmPasswordReset: async (token: string, newPassword: string): Promise<void> => {
    await apiClient.post('/auth/password-reset/confirm', {
      token,
      new_password: newPassword,
    });
  },
};
