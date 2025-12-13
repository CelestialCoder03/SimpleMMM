import apiClient from '../client';

// --- Types ---

export interface DimensionLevel {
  name: string;
  column: string | null;
  display_name: string;
  order: number;
}

export interface Dimension {
  name: string;
  display_name: string;
  levels: DimensionLevel[];
}

export interface Metric {
  name: string;
  column: string;
  metric_type?: string;
  aggregation_method?: string;
  weight_column?: string | null;
  derived_formula?: string | null;
}

export interface GranularitySpec {
  name: string;
  dimensions: Record<string, string>;
  filters?: Record<string, unknown[]>;
}

export interface AggregationPreviewRequest {
  granularity: GranularitySpec;
  dimensions: Dimension[];
  metrics: Metric[];
  sample_size?: number;
}

export interface GranularityOption {
  dimension: string;
  display_name: string;
  levels: Array<{
    name: string;
    display_name: string;
    column: string | null;
    available: boolean;
    unique_values?: number;
  }>;
}

// --- API ---

export const granularityApi = {
  getDefaultDimensions: async (projectId: string): Promise<{ dimensions: Dimension[] }> => {
    const response = await apiClient.get(`/projects/${projectId}/dimensions/defaults`);
    return response.data;
  },

  detectDimensions: async (
    projectId: string,
    datasetId: string
  ): Promise<{ columns: string[]; suggestions: Record<string, unknown> }> => {
    const response = await apiClient.get(
      `/projects/${projectId}/datasets/${datasetId}/dimensions/detect`
    );
    return response.data;
  },

  validateGranularity: async (
    projectId: string,
    datasetId: string,
    request: AggregationPreviewRequest
  ): Promise<Record<string, unknown>> => {
    const response = await apiClient.post(
      `/projects/${projectId}/datasets/${datasetId}/granularity/validate`,
      request
    );
    return response.data;
  },

  previewAggregation: async (
    projectId: string,
    datasetId: string,
    request: AggregationPreviewRequest
  ): Promise<Record<string, unknown>> => {
    const response = await apiClient.post(
      `/projects/${projectId}/datasets/${datasetId}/granularity/preview`,
      request
    );
    return response.data;
  },

  aggregateData: async (
    projectId: string,
    datasetId: string,
    request: AggregationPreviewRequest
  ): Promise<{ total_rows: number; columns: string[]; data: Record<string, unknown>[]; warning?: string }> => {
    const response = await apiClient.post(
      `/projects/${projectId}/datasets/${datasetId}/granularity/aggregate`,
      request
    );
    return response.data;
  },

  getDimensionValues: async (
    projectId: string,
    datasetId: string,
    dimension: string,
    level: string,
    parentColumn?: string,
    parentValue?: string
  ): Promise<{ dimension: string; level: string; values: string[]; count: number }> => {
    const params: Record<string, string> = { level };
    if (parentColumn) params.parent_column = parentColumn;
    if (parentValue) params.parent_value = parentValue;
    const response = await apiClient.get(
      `/projects/${projectId}/datasets/${datasetId}/dimensions/${dimension}/values`,
      { params }
    );
    return response.data;
  },

  getGranularityOptions: async (
    projectId: string,
    datasetId: string
  ): Promise<{ options: GranularityOption[] }> => {
    const response = await apiClient.get(
      `/projects/${projectId}/granularity/options`,
      { params: { dataset_id: datasetId } }
    );
    return response.data;
  },
};
