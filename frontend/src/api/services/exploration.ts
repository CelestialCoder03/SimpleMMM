import apiClient from '../client';

export interface ColumnSummary {
  name: string;
  dtype: string;
  count: number;
  missing: number;
  missing_pct: number;
  unique: number;
  mean?: number;
  std?: number;
  min?: number;
  q25?: number;
  median?: number;
  q75?: number;
  max?: number;
  skewness?: number;
  kurtosis?: number;
  top_values?: { value: string; count: number; pct: number }[];
}

export interface DataSummary {
  n_rows: number;
  n_columns: number;
  memory_mb: number;
  total_missing: number;
  total_missing_pct: number;
  numeric_columns: string[];
  categorical_columns: string[];
  datetime_columns: string[];
  columns: ColumnSummary[];
}

export interface DistributionResult {
  column: string;
  dtype: string;
  histogram?: {
    counts: number[];
    bin_edges: number[];
    bins: number[];
  };
  kde?: {
    x: number[];
    y: number[];
  };
  normality_test?: {
    test: string;
    statistic: number;
    p_value: number;
    is_normal: boolean;
  };
  outliers?: {
    count: number;
    pct: number;
    lower_bound: number;
    upper_bound: number;
    lower_outliers: number;
    upper_outliers: number;
  };
  value_counts?: { value: string; count: number; pct: number }[];
}

export interface CorrelationResult {
  method: string;
  columns: string[];
  matrix: number[][];
  significant_pairs: {
    var1: string;
    var2: string;
    correlation: number;
    strength: string;
  }[];
}

export interface MissingValueResult {
  total_rows: number;
  total_cells: number;
  total_missing: number;
  total_missing_pct: number;
  complete_rows: number;
  complete_rows_pct: number;
  columns: {
    column: string;
    missing: number;
    missing_pct: number;
    dtype: string;
  }[];
  patterns: {
    missing_columns: string[];
    count: number;
    pct: number;
  }[];
}

export interface TimeSeriesResult {
  date_column: string;
  value_column: string;
  frequency: string;
  n_periods: number;
  date_range: [string, string];
  dates: string[];
  values: number[];
  trend?: number[];
  seasonality?: Record<string, number>;
  mean: number;
  std: number;
  cv: number;
  autocorrelation?: number[];
}

export const explorationApi = {
  getSummary: async (projectId: string, datasetId: string): Promise<DataSummary> => {
    const response = await apiClient.get<DataSummary>(
      `/projects/${projectId}/datasets/${datasetId}/explore/summary`
    );
    return response.data;
  },

  getDistribution: async (
    projectId: string,
    datasetId: string,
    column: string,
    nBins = 30,
    includeKde = true
  ): Promise<DistributionResult> => {
    const response = await apiClient.get<DistributionResult>(
      `/projects/${projectId}/datasets/${datasetId}/explore/distribution/${column}`,
      { params: { n_bins: nBins, include_kde: includeKde } }
    );
    return response.data;
  },

  getCorrelations: async (
    projectId: string,
    datasetId: string,
    columns?: string[],
    method: 'pearson' | 'spearman' | 'kendall' = 'pearson',
    threshold = 0.5
  ): Promise<CorrelationResult> => {
    const response = await apiClient.get<CorrelationResult>(
      `/projects/${projectId}/datasets/${datasetId}/explore/correlations`,
      { params: { columns: columns?.join(','), method, threshold } }
    );
    return response.data;
  },

  getMissingAnalysis: async (
    projectId: string,
    datasetId: string
  ): Promise<MissingValueResult> => {
    const response = await apiClient.get<MissingValueResult>(
      `/projects/${projectId}/datasets/${datasetId}/explore/missing`
    );
    return response.data;
  },

  getTimeSeries: async (
    projectId: string,
    datasetId: string,
    dateColumn: string,
    valueColumn: string,
    freq?: string
  ): Promise<TimeSeriesResult> => {
    const response = await apiClient.get<TimeSeriesResult>(
      `/projects/${projectId}/datasets/${datasetId}/explore/time-series`,
      { params: { date_column: dateColumn, value_column: valueColumn, freq } }
    );
    return response.data;
  },

  getChartData: async (
    projectId: string,
    datasetId: string,
    xColumn: string,
    yColumns: string[],
    groupBy?: string,
    aggregation: 'sum' | 'mean' | 'count' | 'min' | 'max' = 'sum'
  ): Promise<ChartDataResult> => {
    const response = await apiClient.post<ChartDataResult>(
      `/projects/${projectId}/datasets/${datasetId}/explore/chart-data`,
      null,
      { 
        params: { 
          x_column: xColumn, 
          y_columns: yColumns.join(','), 
          group_by: groupBy,
          aggregation 
        } 
      }
    );
    return response.data;
  },
};

export interface ChartDataResult {
  x_axis: string[];
  series: { name: string; data: number[] }[];
  aggregation: string;
  x_column: string;
  y_columns: string[];
  group_by?: string;
}
