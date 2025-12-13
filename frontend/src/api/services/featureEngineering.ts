// TODO: Backend endpoints for feature engineering (adstock-preview, dummy-variables, adstock-presets)
// are not implemented yet. This file is currently orphaned and not exported from index.ts.
// Once backend endpoints are created, export this module and wire it into the UI.
import apiClient from '../client';

// Adstock Types
export interface AdstockPreviewRequest {
  dataset_id: string;
  variable_name: string;
  adstock_type: 'geometric' | 'weibull';
  decay?: number;     // For Geometric
  shape?: number;     // For Weibull
  scale?: number;     // For Weibull
  max_lag: number;
}

export interface AdstockPreviewResponse {
  original_values: number[];
  transformed_values: number[];
  dates: string[];
  metrics: {
    avg_lag: number;
    cumulative_multiplier: number;
    decay_90_pct: number; // Time to 90% decay
  };
}

export interface AdstockPreset {
  id: string;
  name: string;
  variable_name: string;
  adstock_type: 'geometric' | 'weibull';
  decay?: number;
  shape?: number;
  scale?: number;
  max_lag: number;
}

// Dummy Variable Types
export type DummyType = 'calendar' | 'custom' | 'regional' | 'outlier';

export interface DummyVariable {
  id: string;
  name: string;
  dummy_type: DummyType;
  
  // Calendar
  calendar_event?: string;
  lead_periods?: number;
  lag_periods?: number;
  
  // Custom/Outlier
  start_date?: string;
  end_date?: string;
  
  // Regional
  geography_column?: string;
  geography_values?: string[];
  
  // Stats
  affected_rows?: number;
  affected_pct?: number;
}

export interface CreateDummyRequest {
  dataset_id: string;
  name: string;
  dummy_type: DummyType;
  calendar_event?: string;
  lead_periods?: number;
  lag_periods?: number;
  start_date?: string;
  end_date?: string;
  geography_column?: string;
  geography_values?: string[];
}

export const featureEngineeringApi = {
  // Adstock Preview
  previewAdstock: async (projectId: string, datasetId: string, data: Omit<AdstockPreviewRequest, 'dataset_id'>): Promise<AdstockPreviewResponse> => {
    const response = await apiClient.post<AdstockPreviewResponse>(
      `/projects/${projectId}/datasets/${datasetId}/adstock-preview`,
      data
    );
    return response.data;
  },

  // Adstock Presets
  listAdstockPresets: async (projectId: string, datasetId: string): Promise<AdstockPreset[]> => {
    const response = await apiClient.get<AdstockPreset[]>(
      `/projects/${projectId}/datasets/${datasetId}/adstock-presets`
    );
    return response.data;
  },

  saveAdstockPreset: async (projectId: string, datasetId: string, data: Omit<AdstockPreset, 'id'>): Promise<AdstockPreset> => {
    const response = await apiClient.post<AdstockPreset>(
      `/projects/${projectId}/datasets/${datasetId}/adstock-presets`,
      data
    );
    return response.data;
  },

  deleteAdstockPreset: async (projectId: string, datasetId: string, presetId: string): Promise<void> => {
    await apiClient.delete(
      `/projects/${projectId}/datasets/${datasetId}/adstock-presets/${presetId}`
    );
  },

  // Dummy Variables
  listDummyVariables: async (projectId: string, datasetId: string): Promise<DummyVariable[]> => {
    const response = await apiClient.get<DummyVariable[]>(
      `/projects/${projectId}/datasets/${datasetId}/dummy-variables`
    );
    return response.data;
  },

  createDummyVariable: async (projectId: string, datasetId: string, data: CreateDummyRequest): Promise<DummyVariable> => {
    const response = await apiClient.post<DummyVariable>(
      `/projects/${projectId}/datasets/${datasetId}/dummy-variables`,
      data
    );
    return response.data;
  },

  updateDummyVariable: async (projectId: string, datasetId: string, dummyId: string, data: Partial<CreateDummyRequest>): Promise<DummyVariable> => {
    const response = await apiClient.put<DummyVariable>(
      `/projects/${projectId}/datasets/${datasetId}/dummy-variables/${dummyId}`,
      data
    );
    return response.data;
  },

  deleteDummyVariable: async (projectId: string, datasetId: string, dummyId: string): Promise<void> => {
    await apiClient.delete(
      `/projects/${projectId}/datasets/${datasetId}/dummy-variables/${dummyId}`
    );
  },

  getCalendarEvents: async (): Promise<{ value: string; label: string }[]> => {
    // This might be a static list or fetched from backend
    return [
      { value: 'chinese_new_year', label: 'Chinese New Year' },
      { value: 'national_day', label: 'National Day (China)' },
      { value: 'mid_autumn', label: 'Mid-Autumn Festival' },
      { value: 'singles_day', label: 'Singles Day (11.11)' },
      { value: 'labor_day', label: 'Labor Day' },
      { value: 'christmas', label: 'Christmas' },
      { value: 'new_year', label: 'New Year' },
    ];
  }
};
