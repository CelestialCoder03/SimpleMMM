import { useQuery } from '@tanstack/react-query';
import { modelsApi } from '@/api/services';
import type { TrainingStatus } from '@/types';

interface UseTrainingStatusOptions {
  enabled?: boolean;
  onComplete?: (status: TrainingStatus) => void;
  onError?: (status: TrainingStatus) => void;
}

export function useTrainingStatus(
  projectId: string | undefined,
  modelId: string | undefined,
  options: UseTrainingStatusOptions = {}
) {
  const { enabled = true, onComplete, onError } = options;

  return useQuery({
    queryKey: ['training-status', projectId, modelId],
    queryFn: async () => {
      const status = await modelsApi.getTrainingStatus(projectId!, modelId!);
      
      // Trigger callbacks based on status
      if (status.status === 'completed' && onComplete) {
        onComplete(status);
      } else if (status.status === 'failed' && onError) {
        onError(status);
      }
      
      return status;
    },
    enabled: enabled && !!projectId && !!modelId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      // Poll every 2 seconds while running or pending
      if (status === 'training' || status === 'pending') {
        return 2000;
      }
      return false;
    },
    staleTime: 0, // Always fetch fresh status
  });
}
