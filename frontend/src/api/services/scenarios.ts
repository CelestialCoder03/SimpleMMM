import apiClient from '../client';

export interface VariableAdjustment {
  variable: string;
  type: 'percentage' | 'absolute' | 'multiplier';
  value: number;
}

export interface Scenario {
  id: string;
  name: string;
  description: string | null;
  project_id: string;
  model_id: string;
  status: 'draft' | 'calculating' | 'ready' | 'failed';
  adjustments: Record<string, { type: string; value: number }>;
  start_date: string | null;
  end_date: string | null;
  baseline_total: number | null;
  scenario_total: number | null;
  lift_percentage: number | null;
  created_at: string;
  updated_at: string;
}

export interface ScenarioResults {
  scenario_id: string;
  dates: string[];
  baseline: number[];
  scenario: number[];
  baseline_contributions: Record<string, number[]>;
  scenario_contributions: Record<string, number[]>;
  summary: Record<string, unknown>;
}

export interface CreateScenarioRequest {
  name: string;
  description?: string;
  model_id: string;
  adjustments: VariableAdjustment[];
  start_date?: string;
  end_date?: string;
}

export interface UpdateScenarioRequest {
  name?: string;
  description?: string;
  adjustments?: VariableAdjustment[];
  start_date?: string;
  end_date?: string;
}

export const scenariosApi = {
  list: async (projectId: string, page = 1, limit = 20) => {
    const response = await apiClient.get(`/projects/${projectId}/scenarios`, {
      params: { page, limit },
    });
    return response.data;
  },

  get: async (projectId: string, scenarioId: string): Promise<Scenario> => {
    const response = await apiClient.get<Scenario>(
      `/projects/${projectId}/scenarios/${scenarioId}`
    );
    return response.data;
  },

  create: async (projectId: string, data: CreateScenarioRequest): Promise<Scenario> => {
    const response = await apiClient.post<Scenario>(
      `/projects/${projectId}/scenarios`,
      data
    );
    return response.data;
  },

  update: async (
    projectId: string,
    scenarioId: string,
    data: UpdateScenarioRequest
  ): Promise<Scenario> => {
    const response = await apiClient.patch<Scenario>(
      `/projects/${projectId}/scenarios/${scenarioId}`,
      data
    );
    return response.data;
  },

  delete: async (projectId: string, scenarioId: string): Promise<void> => {
    await apiClient.delete(`/projects/${projectId}/scenarios/${scenarioId}`);
  },

  calculate: async (projectId: string, scenarioId: string): Promise<ScenarioResults> => {
    const response = await apiClient.post<ScenarioResults>(
      `/projects/${projectId}/scenarios/${scenarioId}/calculate`
    );
    return response.data;
  },

  getResults: async (projectId: string, scenarioId: string): Promise<ScenarioResults> => {
    const response = await apiClient.get<ScenarioResults>(
      `/projects/${projectId}/scenarios/${scenarioId}/results`
    );
    return response.data;
  },

  compare: async (projectId: string, scenarioIds: string[]) => {
    const response = await apiClient.post(`/projects/${projectId}/scenarios/compare`, {
      scenario_ids: scenarioIds,
    });
    return response.data;
  },
};
