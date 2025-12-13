import apiClient from '../client';

export interface VariableTypeOption {
  value: string;
  label: string;
  description: string;
}

export interface VariableMetadata {
  id: string;
  project_id: string;
  dataset_id?: string;
  variable_name: string;
  display_name?: string;
  variable_type: string;
  unit?: string;
  related_spending_variable?: string;
  cost_per_unit?: number;
  group_id?: string;
  description?: string;
  created_at: string;
  updated_at: string;
}

export interface VariableSummary {
  name: string;
  dtype?: string;
  metadata?: VariableMetadata;
  group_name?: string;
  group_color?: string;
}

export interface VariableMetadataCreate {
  variable_name: string;
  dataset_id?: string;
  display_name?: string;
  variable_type?: string;
  unit?: string;
  related_spending_variable?: string;
  cost_per_unit?: number;
  group_id?: string;
  description?: string;
}

export interface VariableMetadataUpdate {
  display_name?: string;
  variable_type?: string;
  unit?: string;
  related_spending_variable?: string;
  cost_per_unit?: number;
  group_id?: string;
  description?: string;
}

export const variableMetadataApi = {
  getTypes: async (projectId: string): Promise<VariableTypeOption[]> => {
    const response = await apiClient.get<VariableTypeOption[]>(`/projects/${projectId}/variables/types`);
    return response.data;
  },

  list: async (projectId: string, datasetId?: string): Promise<VariableSummary[]> => {
    const params = datasetId ? { dataset_id: datasetId } : {};
    const response = await apiClient.get<VariableSummary[]>(
      `/projects/${projectId}/variables`,
      { params }
    );
    return response.data;
  },

  create: async (projectId: string, data: VariableMetadataCreate): Promise<VariableMetadata> => {
    const response = await apiClient.post<VariableMetadata>(
      `/projects/${projectId}/variables`,
      data
    );
    return response.data;
  },

  update: async (projectId: string, variableName: string, data: VariableMetadataUpdate): Promise<VariableMetadata> => {
    const response = await apiClient.put<VariableMetadata>(
      `/projects/${projectId}/variables/${encodeURIComponent(variableName)}`,
      data
    );
    return response.data;
  },

  bulkUpdate: async (projectId: string, variables: VariableMetadataCreate[]): Promise<VariableMetadata[]> => {
    const response = await apiClient.post<VariableMetadata[]>(
      `/projects/${projectId}/variables/bulk`,
      { variables }
    );
    return response.data;
  },

  delete: async (projectId: string, variableName: string): Promise<void> => {
    await apiClient.delete(`/projects/${projectId}/variables/${encodeURIComponent(variableName)}`);
  },

  getSpendingOptions: async (projectId: string): Promise<string[]> => {
    const response = await apiClient.get<string[]>(
      `/projects/${projectId}/variables/spending-options`
    );
    return response.data;
  },
};

// Variable type constants for frontend use
export const VARIABLE_TYPES = [
  { value: 'target', label: '目标变量', labelEn: 'Target', description: '销售额、收入等需要预测的目标' },
  { value: 'spending', label: '花费/投资', labelEn: 'Spending', description: '媒体投放花费、广告支出等' },
  { value: 'support', label: '支持指标', labelEn: 'Support', description: 'GRP、曝光次数、点击量等非花费类指标' },
  { value: 'dimension', label: '维度', labelEn: 'Dimension', description: '地区、渠道、日期等分类字段' },
  { value: 'control', label: '控制变量', labelEn: 'Control', description: '价格、铺货率、季节性等控制因素' },
  { value: 'other', label: '其他', labelEn: 'Other', description: '未分类的变量' },
];

export const getVariableTypeLabel = (type: string, lang: string = 'zh'): string => {
  const found = VARIABLE_TYPES.find(t => t.value === type);
  if (!found) return type;
  return lang.startsWith('zh') ? found.label : found.labelEn;
};

export const getVariableTypeColor = (type: string): string => {
  switch (type) {
    case 'target': return 'bg-purple-500';
    case 'spending': return 'bg-green-500';
    case 'support': return 'bg-blue-500';
    case 'dimension': return 'bg-orange-500';
    case 'control': return 'bg-gray-500';
    default: return 'bg-slate-400';
  }
};
