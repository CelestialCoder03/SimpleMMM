// Auth types
export interface User {
  id: string;
  email: string;
  full_name: string;
  created_at: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in?: number;
}

export interface RegisterRequest {
  email: string;
  password: string;
  full_name: string;
}

// Project types
export interface ProjectSettings {
  default_model_type?: string;
  default_hyperparameters?: Record<string, unknown>;
  date_format?: string;
  currency?: string;
  chart_theme?: string;
  decimal_places?: number;
  export_format?: string;
  include_raw_data?: boolean;
}

export interface Project {
  id: string;
  name: string;
  description?: string;
  owner_id: string;
  settings?: ProjectSettings;
  created_at: string;
  updated_at: string;
}

export interface CreateProjectRequest {
  name: string;
  description?: string;
  settings?: ProjectSettings;
}

// Dataset types
export type ColumnType =
  | "numeric"
  | "categorical"
  | "datetime"
  | "text"
  | "boolean";
export type DatasetStatus = "pending" | "processing" | "ready" | "failed";

export interface ColumnMetadata {
  name: string;
  dtype: string;
  column_type: ColumnType;
  non_null_count: number;
  null_count: number;
  unique_count: number;
  min?: number;
  max?: number;
  mean?: number;
  std?: number;
  median?: number;
  top_values?: Array<{ value: string; count: number }>;
}

export interface ColumnStats {
  min?: number;
  max?: number;
  mean?: number;
  std?: number;
  median?: number;
}

export interface Dataset {
  id: string;
  project_id: string;
  name: string;
  description?: string;
  status: DatasetStatus;
  file_name?: string;
  file_size?: number;
  row_count?: number;
  column_count?: number;
  columns?: ColumnMetadata[];
  created_at: string;
  updated_at: string;
  version?: number;
  parent_id?: string | null;
  is_latest?: boolean;
}

// Model types
export type ModelType = "ols" | "ridge" | "elasticnet" | "bayesian";
export type ModelStatus = "pending" | "training" | "completed" | "failed";

export interface AdstockConfig {
  type: "geometric" | "weibull";
  decay: number | "auto";
  max_lag: number;
  shape?: number;
  scale?: number;
  enabled?: boolean;
}

export interface SaturationConfig {
  type: "hill" | "logistic";
  k: number | "auto";
  s: number | "auto";
  enabled?: boolean;
}

export interface FeatureConfig {
  column: string;
  transformations?: {
    adstock?: AdstockConfig;
    saturation?: SaturationConfig;
  };
  enabled?: boolean;
}

export interface ConstraintConfig {
  variable: string;
  sign?: "positive" | "negative";
  min?: number;
  max?: number;
}

export interface PriorConfig {
  distribution: "normal" | "truncated_normal" | "half_normal";
  mean?: number;
  std?: number;
  lower?: number;
  upper?: number;
}

export interface ModelConfig {
  id: string;
  project_id: string;
  dataset_id: string;
  name: string;
  model_type: ModelType;
  status: ModelStatus;
  target_variable: string;
  date_column: string;
  features: FeatureConfig[];
  granularity?: Record<string, unknown> | null;
  constraints?: Record<string, unknown> | null;
  priors?: Record<string, unknown> | null;
  hyperparameters?: Record<string, unknown> | null;
  seasonality?: {
    enabled: boolean;
    method: "calendar" | "fourier" | "both";
    calendar?: {
      include_weekend: boolean;
      include_month: boolean;
      include_quarter: boolean;
      include_day_of_week: boolean;
    };
    fourier?: {
      periods: number[];
      n_terms: number;
    };
  } | null;
  task_id?: string | null;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
}

export interface CreateModelRequest {
  dataset_id: string;
  name: string;
  model_type: ModelType;
  target_variable: string;
  date_column: string;
  features: FeatureConfig[];
  granularity?: Record<string, unknown> | null;
  constraints?: Record<string, unknown> | null;
  priors?: Record<string, unknown> | null;
  hyperparameters?: Record<string, unknown> | null;
  seasonality?: {
    enabled: boolean;
    method: "calendar" | "fourier" | "both";
    calendar?: {
      include_weekend: boolean;
      include_month: boolean;
      include_quarter: boolean;
      include_day_of_week: boolean;
    };
    fourier?: {
      periods: number[];
      n_terms: number;
    };
  } | null;
}

// Training types
export type TrainingStatusType =
  | "pending"
  | "training"
  | "completed"
  | "failed";

export interface TrainingStatus {
  model_id: string;
  status: TrainingStatusType;
  progress: number;
  current_step: string | null;
  estimated_remaining_seconds?: number | null;
}

// Results types
export interface ModelMetrics {
  r_squared: number;
  adj_r_squared: number;
  rmse: number;
  mape: number;
  aic?: number;
  bic?: number;
  durbin_watson?: number;
}

export interface CoefficientResult {
  variable: string;
  coefficient: number;
  std_error: number;
  t_statistic: number;
  p_value: number;
  significant: boolean;
  ci_lower: number;
  ci_upper: number;
}

export interface ContributionResult {
  variable: string;
  contribution: number;
  contribution_pct: number;
  roi?: number;
}

export interface DecompositionPoint {
  date: string;
  actual: number;
  predicted: number;
  base: number;
  [channel: string]: string | number;
}

export interface ResponseCurve {
  variable: string;
  spend_levels: number[];
  response_values: number[];
  current_spend: number;
  current_response: number;
  marginal_roi: number[];
}

export interface ModelResult {
  model_id: string;
  metrics: ModelMetrics;
  coefficients: CoefficientResult[];
  contributions: ContributionResult[];
  decomposition: DecompositionPoint[];
  response_curves: Record<string, ResponseCurve>;
}

// Project Member types
export type ProjectRole = "owner" | "editor" | "viewer";

export interface ProjectMemberUser {
  id: string;
  email: string;
  full_name: string;
}

export interface ProjectMember {
  id: string;
  project_id: string;
  user_id: string;
  role: ProjectRole;
  created_at: string;
  user: ProjectMemberUser;
}

export interface AddMemberRequest {
  email: string;
  role: ProjectRole;
}

export interface UpdateMemberRequest {
  role: ProjectRole;
}

export interface ProjectMemberListResponse {
  members: ProjectMember[];
  total: number;
}

// API response wrapper
export interface ApiResponse<T> {
  data: T;
  message?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

// Chart data types for visualization endpoints
export interface DecompositionChartData {
  dates: string[];
  actual: number[];
  predicted: number[];
  base: number[];
  channels: Record<string, number[]>;
}

export interface ContributionChartData {
  variables: string[];
  contributions: number[];
  contributions_pct: number[];
  colors?: string[];
}

export interface ResponseCurveChartData {
  variable: string;
  spend_levels: number[];
  response_values: number[];
  current_spend: number;
  current_response: number;
  optimal_spend?: number;
  optimal_response?: number;
}

export interface WaterfallChartData {
  categories: string[];
  values: number[];
  cumulative: number[];
  colors?: string[];
}

export interface DiagnosticsChartData {
  residuals: number[];
  fitted_values: number[];
  qq_theoretical: number[];
  qq_sample: number[];
  autocorrelation: number[];
  lags: number[];
}

export type ChartData =
  | DecompositionChartData
  | ContributionChartData
  | ResponseCurveChartData
  | WaterfallChartData
  | DiagnosticsChartData;
