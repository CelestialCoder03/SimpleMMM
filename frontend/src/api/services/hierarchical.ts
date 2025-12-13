import apiClient from '../client';

export interface HierarchicalModelCreate {
  name: string;
  parent_model_id?: string;
  dataset_id: string;
  dimension_columns: string[];
  granularity_type: string;
  model_type: string;
  target_variable: string;
  date_column?: string;
  features?: Array<{
    column: string;
    enabled: boolean;
    adstock?: { enabled: boolean; decay: number; max_lag: number };
    saturation?: { enabled: boolean; type: string; half_saturation?: number };
  }>;
  inherit_constraints: boolean;
  constraint_relaxation: number;
  inherit_priors: boolean;
  prior_weight: number;
  min_observations: number;
}

export interface SubModel {
  id: string;
  dimension_values: Record<string, string>;
  status: 'pending' | 'training' | 'completed' | 'failed' | 'skipped';
  error_message?: string;
  observation_count?: number;
  r_squared?: number;
  rmse?: number;
  training_duration_seconds?: number;
  model_config_id?: string;
  created_at: string;
  updated_at: string;
}

export interface HierarchicalModel {
  id: string;
  project_id: string;
  name: string;
  parent_model_id?: string;
  dataset_id: string;
  dimension_columns: string[];
  granularity_type: string;
  model_type: string;
  target_variable: string;
  date_column?: string;
  features?: Array<Record<string, unknown>>;
  inherit_constraints: boolean;
  constraint_relaxation: number;
  inherit_priors: boolean;
  prior_weight: number;
  min_observations: number;
  status: string;
  task_id?: string;
  sub_models: SubModel[];
  created_at: string;
  updated_at: string;
}

export interface HierarchicalModelListItem {
  id: string;
  name: string;
  granularity_type: string;
  model_type: string;
  status: string;
  sub_model_count: number;
  completed_count: number;
  created_at: string;
}

export interface TrainingProgress {
  total: number;
  completed: number;
  failed: number;
  in_progress: number;
  pending: number;
}

export interface TrainingStatus {
  status: string;
  progress: TrainingProgress;
  sub_models: SubModel[];
}

export interface DimensionCombination {
  values: Record<string, string>;
  observation_count: number;
}

export interface DimensionAnalysis {
  dimension_columns: string[];
  combinations: DimensionCombination[];
  total_combinations: number;
}

export interface ResultsSummary {
  id: string;
  name: string;
  total_sub_models: number;
  completed_sub_models: number;
  avg_r_squared?: number;
  min_r_squared?: number;
  max_r_squared?: number;
  coefficient_comparisons: Array<{
    variable: string;
    national_estimate?: number;
    national_ci_lower?: number;
    national_ci_upper?: number;
    sub_model_estimates: Record<string, number>;
  }>;
}

export const hierarchicalApi = {
  list: async (projectId: string): Promise<HierarchicalModelListItem[]> => {
    const response = await apiClient.get<HierarchicalModelListItem[]>(
      `/projects/${projectId}/hierarchical-models`
    );
    return response.data;
  },

  create: async (projectId: string, data: HierarchicalModelCreate): Promise<HierarchicalModel> => {
    const response = await apiClient.post<HierarchicalModel>(
      `/projects/${projectId}/hierarchical-models`,
      data
    );
    return response.data;
  },

  get: async (projectId: string, configId: string): Promise<HierarchicalModel> => {
    const response = await apiClient.get<HierarchicalModel>(
      `/projects/${projectId}/hierarchical-models/${configId}`
    );
    return response.data;
  },

  delete: async (projectId: string, configId: string): Promise<void> => {
    await apiClient.delete(`/projects/${projectId}/hierarchical-models/${configId}`);
  },

  analyzeDimensions: async (projectId: string, configId: string): Promise<DimensionAnalysis> => {
    const response = await apiClient.get<DimensionAnalysis>(
      `/projects/${projectId}/hierarchical-models/${configId}/dimensions`
    );
    return response.data;
  },

  startTraining: async (projectId: string, configId: string): Promise<{ status: string; task_id: string }> => {
    const response = await apiClient.post<{ status: string; task_id: string }>(
      `/projects/${projectId}/hierarchical-models/${configId}/train`
    );
    return response.data;
  },

  getStatus: async (projectId: string, configId: string): Promise<TrainingStatus> => {
    const response = await apiClient.get<TrainingStatus>(
      `/projects/${projectId}/hierarchical-models/${configId}/status`
    );
    return response.data;
  },

  cancelTraining: async (projectId: string, configId: string): Promise<{ status: string }> => {
    const response = await apiClient.post<{ status: string }>(
      `/projects/${projectId}/hierarchical-models/${configId}/cancel`
    );
    return response.data;
  },

  getResults: async (projectId: string, configId: string): Promise<ResultsSummary> => {
    const response = await apiClient.get<ResultsSummary>(
      `/projects/${projectId}/hierarchical-models/${configId}/results`
    );
    return response.data;
  },
};
