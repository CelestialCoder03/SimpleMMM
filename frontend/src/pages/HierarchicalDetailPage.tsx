import { useParams, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { hierarchicalApi } from '@/api/services';
import type { SubModel } from '@/api/services/hierarchical';
import { Header } from '@/components/layout';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  ArrowLeft,
  Play,
  Square,
  CheckCircle2,
  XCircle,
  Clock,
  Loader2,
  AlertCircle,
  SkipForward,
} from 'lucide-react';

export function HierarchicalDetailPage() {
  const { t } = useTranslation();
  const { projectId, configId } = useParams<{ projectId: string; configId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  // Fetch hierarchical model
  const { data: config, isLoading } = useQuery({
    queryKey: ['hierarchical-model', projectId, configId],
    queryFn: () => hierarchicalApi.get(projectId!, configId!),
    enabled: !!projectId && !!configId,
  });

  const isPolling = config?.status === 'training';

  // Fetch status (polling when training)
  const { data: status } = useQuery({
    queryKey: ['hierarchical-status', projectId, configId],
    queryFn: () => hierarchicalApi.getStatus(projectId!, configId!),
    enabled: !!projectId && !!configId && isPolling,
    refetchInterval: isPolling ? 2000 : false,
  });

  // Start training mutation
  const startMutation = useMutation({
    mutationFn: () => hierarchicalApi.startTraining(projectId!, configId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['hierarchical-model', projectId, configId] });
    },
  });

  // Cancel training mutation
  const cancelMutation = useMutation({
    mutationFn: () => hierarchicalApi.cancelTraining(projectId!, configId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['hierarchical-model', projectId, configId] });
    },
  });

  const getStatusIcon = (subStatus: string) => {
    switch (subStatus) {
      case 'completed':
        return <CheckCircle2 className="h-4 w-4 text-green-500" />;
      case 'failed':
        return <XCircle className="h-4 w-4 text-red-500" />;
      case 'training':
        return <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />;
      case 'skipped':
        return <SkipForward className="h-4 w-4 text-yellow-500" />;
      default:
        return <Clock className="h-4 w-4 text-muted-foreground" />;
    }
  };

  const getStatusBadge = (subStatus: string) => {
    switch (subStatus) {
      case 'completed':
        return <Badge variant="default" className="bg-green-500">{t('common.completed', '完成')}</Badge>;
      case 'failed':
        return <Badge variant="destructive">{t('common.failed', '失败')}</Badge>;
      case 'training':
        return <Badge variant="default" className="bg-blue-500">{t('common.training', '训练中')}</Badge>;
      case 'skipped':
        return <Badge variant="secondary">{t('common.skipped', '跳过')}</Badge>;
      default:
        return <Badge variant="outline">{t('common.pending', '等待中')}</Badge>;
    }
  };

  const getDimensionKey = (values: Record<string, string>) => {
    return Object.values(values).join(' / ');
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    );
  }

  if (!config) {
    return (
      <div className="p-6">
        <p>{t('common.notFound', '未找到')}</p>
      </div>
    );
  }

  const progress = status?.progress;
  const progressPercent = progress ? (progress.completed / progress.total) * 100 : 0;
  const subModels = status?.sub_models || config.sub_models || [];

  return (
    <div className="flex flex-col">
      <Header title={config.name} />

      <div className="p-6 space-y-6">
        {/* Back button */}
        <Button variant="ghost" onClick={() => navigate(`/projects/${projectId}`)}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          {t('common.back')}
        </Button>

        {/* Status Card */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>{t('hierarchical.trainingStatus', '训练状态')}</CardTitle>
                <CardDescription>
                  {config.granularity_type} / {config.model_type}
                </CardDescription>
              </div>
              <div className="flex gap-2">
                {config.status === 'pending' && (
                  <Button onClick={() => startMutation.mutate()} disabled={startMutation.isPending}>
                    {startMutation.isPending ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <Play className="mr-2 h-4 w-4" />
                    )}
                    {t('hierarchical.startTraining', '开始训练')}
                  </Button>
                )}
                {config.status === 'training' && (
                  <Button variant="destructive" onClick={() => cancelMutation.mutate()} disabled={cancelMutation.isPending}>
                    <Square className="mr-2 h-4 w-4" />
                    {t('hierarchical.cancelTraining', '取消训练')}
                  </Button>
                )}
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {progress && (
              <div className="space-y-4">
                <div className="flex items-center justify-between text-sm">
                  <span>{t('hierarchical.progress', '进度')}</span>
                  <span>{progress.completed} / {progress.total}</span>
                </div>
                <Progress value={progressPercent} />
                <div className="flex gap-4 text-sm">
                  <span className="flex items-center gap-1">
                    <CheckCircle2 className="h-4 w-4 text-green-500" />
                    {t('common.completed', '完成')}: {progress.completed}
                  </span>
                  <span className="flex items-center gap-1">
                    <Loader2 className="h-4 w-4 text-blue-500" />
                    {t('common.inProgress', '进行中')}: {progress.in_progress}
                  </span>
                  <span className="flex items-center gap-1">
                    <XCircle className="h-4 w-4 text-red-500" />
                    {t('common.failed', '失败')}: {progress.failed}
                  </span>
                  <span className="flex items-center gap-1">
                    <Clock className="h-4 w-4 text-muted-foreground" />
                    {t('common.pending', '等待')}: {progress.pending}
                  </span>
                </div>
              </div>
            )}

            {!progress && config.status === 'pending' && (
              <div className="flex items-center gap-2 text-muted-foreground">
                <AlertCircle className="h-4 w-4" />
                {t('hierarchical.notStarted', '训练尚未开始')}
              </div>
            )}

            {config.status === 'completed' && (
              <div className="flex items-center gap-2 text-green-600">
                <CheckCircle2 className="h-5 w-5" />
                {t('hierarchical.trainingCompleted', '训练已完成')}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Sub-models Table */}
        {subModels.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle>{t('hierarchical.subModels', '子模型')}</CardTitle>
              <CardDescription>
                {t('hierarchical.subModelsDesc', '每个维度值对应一个子模型')}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>{t('hierarchical.dimension', '维度')}</TableHead>
                    <TableHead>{t('common.status', '状态')}</TableHead>
                    <TableHead>{t('hierarchical.observations', '观测数')}</TableHead>
                    <TableHead>R²</TableHead>
                    <TableHead>RMSE</TableHead>
                    <TableHead>{t('hierarchical.duration', '用时')}</TableHead>
                    <TableHead></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {subModels.map((sub: SubModel) => (
                    <TableRow key={sub.id}>
                      <TableCell className="font-medium">
                        <div className="flex items-center gap-2">
                          {getStatusIcon(sub.status)}
                          {getDimensionKey(sub.dimension_values)}
                        </div>
                      </TableCell>
                      <TableCell>{getStatusBadge(sub.status)}</TableCell>
                      <TableCell>{sub.observation_count ?? '-'}</TableCell>
                      <TableCell>
                        {sub.r_squared != null ? (sub.r_squared * 100).toFixed(1) + '%' : '-'}
                      </TableCell>
                      <TableCell>
                        {sub.rmse != null ? sub.rmse.toFixed(2) : '-'}
                      </TableCell>
                      <TableCell>
                        {sub.training_duration_seconds != null
                          ? sub.training_duration_seconds.toFixed(1) + 's'
                          : '-'}
                      </TableCell>
                      <TableCell>
                        {sub.model_config_id && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => navigate(`/projects/${projectId}/models/${sub.model_config_id}/results`)}
                          >
                            {t('common.viewResults', '查看结果')}
                          </Button>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}

export default HierarchicalDetailPage;
