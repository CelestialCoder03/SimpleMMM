import apiClient from '../client';
import type { Project, CreateProjectRequest, PaginatedResponse, ProjectSettings } from '@/types';

export const projectsApi = {
  list: async (page = 1, limit = 20): Promise<PaginatedResponse<Project>> => {
    const response = await apiClient.get<PaginatedResponse<Project>>('/projects', {
      params: { page, limit },
    });
    return response.data;
  },

  get: async (id: string): Promise<Project> => {
    const response = await apiClient.get<Project>(`/projects/${id}`);
    return response.data;
  },

  create: async (data: CreateProjectRequest): Promise<Project> => {
    const response = await apiClient.post<Project>('/projects', data);
    return response.data;
  },

  update: async (id: string, data: Partial<CreateProjectRequest>): Promise<Project> => {
    const response = await apiClient.patch<Project>(`/projects/${id}`, data);
    return response.data;
  },

  delete: async (id: string): Promise<void> => {
    await apiClient.delete(`/projects/${id}`);
  },

  // Settings
  getSettings: async (id: string): Promise<ProjectSettings> => {
    const response = await apiClient.get<ProjectSettings>(`/projects/${id}/settings`);
    return response.data;
  },

  updateSettings: async (id: string, settings: Partial<ProjectSettings>): Promise<ProjectSettings> => {
    const response = await apiClient.patch<ProjectSettings>(`/projects/${id}/settings`, settings);
    return response.data;
  },
};
