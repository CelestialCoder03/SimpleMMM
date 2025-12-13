import apiClient from '../client';
import type { Dataset } from '@/types';

interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export const datasetsApi = {
  list: async (projectId: string): Promise<Dataset[]> => {
    const response = await apiClient.get<PaginatedResponse<Dataset>>(`/projects/${projectId}/datasets`);
    return response.data.items;
  },

  get: async (projectId: string, datasetId: string): Promise<Dataset> => {
    const response = await apiClient.get<Dataset>(`/projects/${projectId}/datasets/${datasetId}`);
    return response.data;
  },

  upload: async (projectId: string, file: File, name?: string): Promise<Dataset> => {
    const formData = new FormData();
    formData.append('file', file);
    if (name) {
      formData.append('name', name);
    }

    const response = await apiClient.post<Dataset>(
      `/projects/${projectId}/upload/datasets`,
      formData,
      {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 120000, // 2 minutes for large files
      }
    );
    return response.data;
  },

  delete: async (projectId: string, datasetId: string): Promise<void> => {
    await apiClient.delete(`/projects/${projectId}/datasets/${datasetId}`);
  },

  getPreview: async (
    projectId: string,
    datasetId: string,
    limit = 100
  ): Promise<{ dataset_id: string; columns: string[]; data: Array<Record<string, unknown>>; total_rows: number; preview_rows: number }> => {
    const response = await apiClient.get(`/projects/${projectId}/datasets/${datasetId}/preview`, {
      params: { limit },
    });
    return response.data;
  },

  getColumns: async (projectId: string, datasetId: string) => {
    const response = await apiClient.get(`/projects/${projectId}/datasets/${datasetId}/stats`);
    return response.data.columns;
  },

  reprocess: async (projectId: string, datasetId: string): Promise<Dataset> => {
    const response = await apiClient.post<Dataset>(`/projects/${projectId}/datasets/${datasetId}/reprocess`);
    return response.data;
  },

  update: async (
    projectId: string,
    datasetId: string,
    file: File,
    mode: 'new_version' | 'replace' = 'new_version',
    preserveMetadata = true
  ): Promise<Dataset> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('mode', mode);
    formData.append('preserve_metadata', String(preserveMetadata));

    const response = await apiClient.post<Dataset>(
      `/projects/${projectId}/datasets/${datasetId}/update`,
      formData,
      {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 120000,
      }
    );
    return response.data;
  },

  getColumnDiff: async (
    projectId: string,
    datasetId: string,
    compareTo?: string
  ): Promise<{
    dataset_id: string;
    compare_to: string | null;
    added_columns: string[];
    removed_columns: string[];
    unchanged_columns: string[];
  }> => {
    const params = compareTo ? { compare_to: compareTo } : {};
    const response = await apiClient.get(
      `/projects/${projectId}/datasets/${datasetId}/column-diff`,
      { params }
    );
    return response.data;
  },

  getVersionHistory: async (projectId: string, datasetId: string): Promise<Dataset[]> => {
    const response = await apiClient.get<Dataset[]>(
      `/projects/${projectId}/datasets/${datasetId}/versions`
    );
    return response.data;
  },
};
