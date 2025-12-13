import apiClient from '../client';
import type { ModelConfig, CreateModelRequest, TrainingStatus, ModelResult } from '@/types';

interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export const modelsApi = {
  list: async (projectId: string): Promise<ModelConfig[]> => {
    const response = await apiClient.get<PaginatedResponse<ModelConfig>>(`/projects/${projectId}/models`);
    return response.data.items;
  },

  get: async (projectId: string, modelId: string): Promise<ModelConfig> => {
    const response = await apiClient.get<ModelConfig>(`/projects/${projectId}/models/${modelId}`);
    return response.data;
  },

  create: async (projectId: string, data: CreateModelRequest): Promise<ModelConfig> => {
    const response = await apiClient.post<ModelConfig>(`/projects/${projectId}/models`, data);
    return response.data;
  },

  update: async (
    projectId: string,
    modelId: string,
    data: Partial<CreateModelRequest>
  ): Promise<ModelConfig> => {
    const response = await apiClient.put<ModelConfig>(
      `/projects/${projectId}/models/${modelId}`,
      data
    );
    return response.data;
  },

  delete: async (projectId: string, modelId: string): Promise<void> => {
    await apiClient.delete(`/projects/${projectId}/models/${modelId}`);
  },

  // Training
  train: async (projectId: string, modelId: string): Promise<ModelConfig> => {
    const response = await apiClient.post<ModelConfig>(`/projects/${projectId}/models/${modelId}/train`);
    return response.data;
  },

  getTrainingStatus: async (projectId: string, modelId: string): Promise<TrainingStatus> => {
    const response = await apiClient.get<TrainingStatus>(
      `/projects/${projectId}/models/${modelId}/status`
    );
    return response.data;
  },

  cancelTraining: async (projectId: string, modelId: string): Promise<void> => {
    await apiClient.post(`/projects/${projectId}/models/${modelId}/cancel`);
  },

  // Results
  getResults: async (projectId: string, modelId: string): Promise<ModelResult> => {
    const response = await apiClient.get<ModelResult>(
      `/projects/${projectId}/models/${modelId}/results/summary`
    );
    return response.data;
  },

  getDecompositionChart: async (projectId: string, modelId: string) => {
    const response = await apiClient.get(
      `/projects/${projectId}/models/${modelId}/results/charts/decomposition`
    );
    return response.data;
  },

  getContributionChart: async (projectId: string, modelId: string, type = 'pie') => {
    const response = await apiClient.get(
      `/projects/${projectId}/models/${modelId}/results/charts/contributions`,
      { params: { chart_type: type } }
    );
    return response.data;
  },

  getResponseCurvesChart: async (projectId: string, modelId: string) => {
    const response = await apiClient.get(
      `/projects/${projectId}/models/${modelId}/results/charts/response-curves`
    );
    return response.data;
  },

  getWaterfallChart: async (projectId: string, modelId: string) => {
    const response = await apiClient.get(
      `/projects/${projectId}/models/${modelId}/results/charts/waterfall`
    );
    return response.data;
  },

  // Export
  exportCsv: async (projectId: string, modelId: string): Promise<Blob> => {
    const response = await apiClient.get(
      `/projects/${projectId}/models/${modelId}/results/export/csv`,
      { responseType: 'blob' }
    );
    return response.data;
  },

  exportExcel: async (projectId: string, modelId: string, language: string = 'en'): Promise<Blob> => {
    const response = await apiClient.get(
      `/projects/${projectId}/models/${modelId}/results/export/excel`,
      { params: { language }, responseType: 'blob' }
    );
    return response.data;
  },

  exportPdf: async (projectId: string, modelId: string): Promise<Blob> => {
    const response = await apiClient.get(
      `/projects/${projectId}/models/${modelId}/results/export/pdf`,
      { responseType: 'blob' }
    );
    return response.data;
  },

  exportPptx: async (projectId: string, modelId: string): Promise<Blob> => {
    const response = await apiClient.get(
      `/projects/${projectId}/models/${modelId}/results/export/pptx`,
      { responseType: 'blob' }
    );
    return response.data;
  },

  exportJson: async (projectId: string, modelId: string): Promise<Blob> => {
    const response = await apiClient.get(
      `/projects/${projectId}/models/${modelId}/results/export/json`,
      { responseType: 'blob' }
    );
    return response.data;
  },

  exportHtml: async (projectId: string, modelId: string): Promise<Blob> => {
    const response = await apiClient.get(
      `/projects/${projectId}/models/${modelId}/results/export/html`,
      { responseType: 'blob' }
    );
    return response.data;
  },

  compareModels: async (
    projectId: string,
    primaryModelId: string,
    compareWithIds: string[]
  ) => {
    const params = compareWithIds.map(id => `compare_with=${id}`).join('&');
    const response = await apiClient.post(
      `/projects/${projectId}/models/${primaryModelId}/results/compare?${params}`
    );
    return response.data;
  },

  // Constraint validation
  validateConstraints: async (
    projectId: string,
    constraints: {
      coefficient_constraints?: Array<{
        variable: string;
        sign?: string;
        min?: number;
        max?: number;
      }>;
      contribution_constraints?: Array<{
        variable: string;
        min_contribution_pct?: number;
        max_contribution_pct?: number;
      }>;
      group_constraints?: Array<{
        name: string;
        variables: string[];
        min_contribution_pct?: number;
        max_contribution_pct?: number;
      }>;
    }
  ): Promise<{
    valid: boolean;
    conflicts: Array<{
      type: 'error' | 'warning' | 'info';
      code: string;
      message: string;
      affected_variables: string[];
      affected_groups: string[];
      suggestion: string | null;
    }>;
    warnings_count: number;
    errors_count: number;
  }> => {
    const response = await apiClient.post(
      `/projects/${projectId}/models/validate-constraints`,
      constraints
    );
    return response.data;
  },

  // Apply config to different dataset
  applyToDataset: async (
    projectId: string,
    modelId: string,
    targetDatasetId: string,
    newName?: string
  ): Promise<ModelConfig> => {
    const params: Record<string, string> = { target_dataset_id: targetDatasetId };
    if (newName) {
      params.new_name = newName;
    }
    const response = await apiClient.post<ModelConfig>(
      `/projects/${projectId}/models/${modelId}/apply-to-dataset`,
      undefined,
      { params }
    );
    return response.data;
  },
};
