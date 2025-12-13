import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { modelsApi, projectsApi } from '@/api/services';
import { Header } from '@/components/layout';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  ArrowLeft,
  Loader2,
  Play,
  Square,
  CheckCircle2,
  AlertCircle,
  Clock,
} from 'lucide-react';
import type { TrainingStatusType } from '@/types';

const statusConfig: Record<TrainingStatusType, { icon: typeof CheckCircle2; color: string; bgColor: string }> = {
  pending: { icon: Clock, color: 'text-muted-foreground', bgColor: 'bg-muted' },
  training: { icon: Loader2, color: 'text-blue-500', bgColor: 'bg-blue-50' },
  completed: { icon: CheckCircle2, color: 'text-green-500', bgColor: 'bg-green-50' },
  failed: { icon: AlertCircle, color: 'text-destructive', bgColor: 'bg-destructive/10' },
};

export function ModelTrainingPage() {
  const { t } = useTranslation();
  const { projectId, modelId } = useParams<{ projectId: string; modelId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data: model } = useQuery({
    queryKey: ['model', projectId, modelId],
    queryFn: () => modelsApi.get(projectId!, modelId!),
    enabled: !!projectId && !!modelId,
  });

  const { data: trainingStatus, refetch } = useQuery({
    queryKey: ['training-status', projectId, modelId],
    queryFn: () => modelsApi.getTrainingStatus(projectId!, modelId!),
    enabled: !!projectId && !!modelId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === 'training' || status === 'pending' ? 2000 : false;
    },
  });

  const { data: project } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => projectsApi.get(projectId!),
    enabled: !!projectId,
  });

  const trainMutation = useMutation({
    mutationFn: () => modelsApi.train(projectId!, modelId!),
    onSuccess: () => {
      refetch();
    },
    onError: (error: Error) => {
      console.error('Training error:', error);
      alert(`Training failed: ${error.message}`);
    },
  });

  const cancelMutation = useMutation({
    mutationFn: () => modelsApi.cancelTraining(projectId!, modelId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['training-status', projectId, modelId] });
    },
  });

  // Auto-navigate to results when completed
  useEffect(() => {
    if (trainingStatus?.status === 'completed') {
      const timer = setTimeout(() => {
        navigate(`/projects/${projectId}/models/${modelId}/results`);
      }, 2000);
      return () => clearTimeout(timer);
    }
  }, [trainingStatus?.status, navigate, projectId, modelId]);

  const status = trainingStatus?.status || 'pending';
  const StatusIcon = statusConfig[status]?.icon || Clock;
  const statusColor = statusConfig[status]?.color || 'text-muted-foreground';
  const statusBgColor = statusConfig[status]?.bgColor || 'bg-muted';

  return (
    <div className="flex flex-col min-h-screen bg-app-gradient">
      <Header
        title={`${t('training.title')}: ${model?.name || t('models.model')}`}
        projectName={project?.name}
        actions={
          <Button variant="ghost" onClick={() => navigate(`/projects/${projectId}`)}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            {t('training.backToProject')}
          </Button>
        }
      />

      <div className="mx-auto w-full max-w-2xl p-6 space-y-6">
        {/* Status Card */}
        <Card variant="glass" className="animate-in-slow">
          <CardHeader>
            <CardTitle>{t('training.status')}</CardTitle>
            <CardDescription>
              {t('training.monitorProgress')}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Status Badge */}
            <div className={`flex items-center gap-3 rounded-xl glass-sm p-4 border border-[var(--glass-border)]`}>
              <div className={`flex h-12 w-12 items-center justify-center rounded-xl ${statusBgColor}`}>
                <StatusIcon className={`h-6 w-6 ${statusColor} ${status === 'training' ? 'animate-spin' : ''}`} />
              </div>
              <div>
                <p className={`font-semibold capitalize ${statusColor}`}>
                  {status}
                </p>
                <p className="text-sm text-muted-foreground">
                  {trainingStatus?.current_step || t('training.waitingToStart')}
                </p>
              </div>
            </div>

            {/* Progress Bar */}
            {(status === 'training' || status === 'pending') && (
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span>{t('training.progress')}</span>
                  <span>{trainingStatus?.progress || 0}%</span>
                </div>
                <Progress value={trainingStatus?.progress || 0} />
              </div>
            )}

            {/* Success Message */}
            {status === 'completed' && (
              <div className="rounded-xl glass-sm border border-emerald-500/30 bg-emerald-500/10 p-6 text-center">
                <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-gradient-to-br from-emerald-400 to-teal-500 shadow-lg">
                  <CheckCircle2 className="h-7 w-7 text-white" />
                </div>
                <p className="mt-3 font-semibold text-emerald-700 dark:text-emerald-300">{t('training.complete')}</p>
                <p className="text-sm text-emerald-600 dark:text-emerald-400">{t('training.redirecting')}</p>
              </div>
            )}

            {/* Actions */}
            <div className="flex gap-3">
              {status === 'pending' && (
                <Button
                  variant="gradient"
                  className="flex-1"
                  onClick={() => trainMutation.mutate()}
                  disabled={trainMutation.isPending}
                >
                  {trainMutation.isPending ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <Play className="mr-2 h-4 w-4" />
                  )}
                  {t('training.startTraining')}
                </Button>
              )}
              
              {status === 'training' && (
                <Button
                  variant="destructive"
                  className="flex-1"
                  onClick={() => cancelMutation.mutate()}
                  disabled={cancelMutation.isPending}
                >
                  <Square className="mr-2 h-4 w-4" />
                  {t('training.cancelTraining')}
                </Button>
              )}

              {status === 'completed' && (
                <Button
                  variant="gradient"
                  className="flex-1"
                  onClick={() => navigate(`/projects/${projectId}/models/${modelId}/results`)}
                >
                  {t('training.viewResults')}
                </Button>
              )}

              {status === 'failed' && (
                <Button
                  className="flex-1"
                  onClick={() => trainMutation.mutate()}
                  disabled={trainMutation.isPending}
                >
                  <Play className="mr-2 h-4 w-4" />
                  {t('training.retryTraining')}
                </Button>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Model Info */}
        <Card variant="glass-subtle">
          <CardHeader>
            <CardTitle className="text-base">{t('training.modelConfiguration')}</CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <dt className="text-muted-foreground">{t('models.modelType')}</dt>
                <dd className="font-medium capitalize">{model?.model_type}</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">{t('models.targetVariable')}</dt>
                <dd className="font-medium">{model?.target_variable}</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">{t('models.features')}</dt>
                <dd className="font-medium">
                  {model?.features ? model.features.length : 0} {t('training.variables')}
                </dd>
              </div>
              <div>
                <dt className="text-muted-foreground">{t('common.created')}</dt>
                <dd className="font-medium">
                  {model?.created_at ? new Date(model.created_at).toLocaleDateString() : '-'}
                </dd>
              </div>
            </dl>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
