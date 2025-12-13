import { apiClient } from '../client';
import type {
  ProjectMember,
  ProjectMemberListResponse,
  AddMemberRequest,
  UpdateMemberRequest,
} from '@/types';

export const projectMembersApi = {
  list: async (projectId: string): Promise<ProjectMemberListResponse> => {
    const response = await apiClient.get<ProjectMemberListResponse>(
      `/projects/${projectId}/members`
    );
    return response.data;
  },

  add: async (projectId: string, data: AddMemberRequest): Promise<ProjectMember> => {
    const response = await apiClient.post<ProjectMember>(
      `/projects/${projectId}/members`,
      data
    );
    return response.data;
  },

  update: async (
    projectId: string,
    memberId: string,
    data: UpdateMemberRequest
  ): Promise<ProjectMember> => {
    const response = await apiClient.patch<ProjectMember>(
      `/projects/${projectId}/members/${memberId}`,
      data
    );
    return response.data;
  },

  remove: async (projectId: string, memberId: string): Promise<void> => {
    await apiClient.delete(`/projects/${projectId}/members/${memberId}`);
  },
};
