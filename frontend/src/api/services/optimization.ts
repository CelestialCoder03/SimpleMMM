import apiClient from '../client';

export interface ChannelConstraint {
  channel: string;
  min_budget?: number;
  max_budget?: number;
  min_share?: number;
  max_share?: number;
}

export interface OptimizationRequest {
  model_id: string;
  total_budget: number;
  objective: 'maximize_response' | 'maximize_roi' | 'minimize_cost';
  constraints: ChannelConstraint[];
}

export interface ChannelChange {
  current: number;
  optimized: number;
  change: number;
  change_pct: number;
}

export interface OptimizationResult {
  success: boolean;
  message: string;
  objective: string;
  total_budget: number;
  current_allocation: Record<string, number>;
  current_response: number;
  current_roi: number;
  optimized_allocation: Record<string, number>;
  optimized_response: number;
  optimized_roi: number;
  response_lift: number;
  response_lift_pct: number;
  roi_improvement: number;
  channel_changes: Record<string, ChannelChange>;
}

export interface ChannelInfo {
  name: string;
  coefficient: number;
  average_contribution: number;
  total_contribution: number;
  share_pct: number;
}

export interface ChannelsResponse {
  model_id: string;
  channels: ChannelInfo[];
  total_contribution: number;
}

export const optimizationApi = {
  optimize: async (projectId: string, request: OptimizationRequest): Promise<OptimizationResult> => {
    const response = await apiClient.post<OptimizationResult>(
      `/projects/${projectId}/optimize/budget`,
      request
    );
    return response.data;
  },

  getChannels: async (projectId: string, modelId: string): Promise<ChannelsResponse> => {
    const response = await apiClient.get<ChannelsResponse>(
      `/projects/${projectId}/optimize/channels`,
      { params: { model_id: modelId } }
    );
    return response.data;
  },
};
