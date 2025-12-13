import { apiClient } from '../client';

export interface VariableGroup {
  id: string;
  name: string;
  description: string | null;
  variables: string[];
  color: string | null;
  created_at: string;
  updated_at: string;
}

export interface VariableGroupCreate {
  name: string;
  description?: string | null;
  variables: string[];
  color?: string | null;
}

export interface VariableGroupUpdate {
  name?: string;
  description?: string | null;
  variables?: string[];
  color?: string | null;
}

export interface VariableGroupList {
  items: VariableGroup[];
  total: number;
}

export interface OverlapCheck {
  has_overlaps: boolean;
  overlaps: Record<string, string[]>;
}

export const variableGroupsApi = {
  list: async (projectId: string): Promise<VariableGroup[]> => {
    const response = await apiClient.get<VariableGroupList>(
      `/projects/${projectId}/variable-groups`
    );
    return response.data.items;
  },

  get: async (projectId: string, groupId: string): Promise<VariableGroup> => {
    const response = await apiClient.get<VariableGroup>(
      `/projects/${projectId}/variable-groups/${groupId}`
    );
    return response.data;
  },

  create: async (projectId: string, data: VariableGroupCreate): Promise<VariableGroup> => {
    const response = await apiClient.post<VariableGroup>(
      `/projects/${projectId}/variable-groups`,
      data
    );
    return response.data;
  },

  update: async (
    projectId: string,
    groupId: string,
    data: VariableGroupUpdate
  ): Promise<VariableGroup> => {
    const response = await apiClient.put<VariableGroup>(
      `/projects/${projectId}/variable-groups/${groupId}`,
      data
    );
    return response.data;
  },

  delete: async (projectId: string, groupId: string): Promise<void> => {
    await apiClient.delete(`/projects/${projectId}/variable-groups/${groupId}`);
  },

  checkOverlap: async (projectId: string): Promise<OverlapCheck> => {
    const response = await apiClient.get<OverlapCheck>(
      `/projects/${projectId}/variable-groups/check-overlap`
    );
    return response.data;
  },
};
