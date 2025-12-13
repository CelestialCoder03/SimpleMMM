import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { projectsApi, datasetsApi, modelsApi } from '@/api/services';
import { Header, PageWrapper } from '@/components/layout';
import { ProjectMembersPanel } from '@/components/features/projects/ProjectMembersPanel';
import { ModelComparisonView } from '@/components/features/models/ModelComparisonView';
import { useAuthStore } from '@/stores/authStore';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import {
  Database,
  LineChart,
  Plus,
  Upload,
  Loader2,
  ArrowRight,
  CheckCircle2,
  Clock,
  AlertCircle,
  Trash2,
  BarChart3,
  Layers,
  Tag,
  RefreshCw,
  GitBranch,
  Target,
} from 'lucide-react';
import { CardSkeleton, MetricCardSkeleton } from '@/components/ui/skeleton';
import type { Dataset, ModelConfig, ModelStatus } from '@/types';

const statusConfig: Record<ModelStatus, { icon: typeof CheckCircle2; color: string; label: string }> = {
  pending: { icon: Clock, color: 'text-muted-foreground', label: 'Pending' },
  training: { icon: Loader2, color: 'text-blue-500', label: 'Training' },
  completed: { icon: CheckCircle2, color: 'text-green-500', label: 'Completed' },
  failed: { icon: AlertCircle, color: 'text-destructive', label: 'Failed' },
};

export function ProjectDetailPage() {
  const { t } = useTranslation();
  const { projectId } = useParams<{ projectId: string }>();
  const { user } = useAuthStore();

  const { data: project, isLoading: projectLoading } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => projectsApi.get(projectId!),
    enabled: !!projectId,
  });

  const { data: datasets = [], isLoading: datasetsLoading } = useQuery({
    queryKey: ['datasets', projectId],
    queryFn: () => datasetsApi.list(projectId!),
    enabled: !!projectId,
  });

  const { data: models = [], isLoading: modelsLoading } = useQuery({
    queryKey: ['models', projectId],
    queryFn: () => modelsApi.list(projectId!),
    enabled: !!projectId,
  });

  const isLoading = projectLoading || datasetsLoading || modelsLoading;

  return (
    <PageWrapper className="flex flex-col">
      <Header
        title={project?.name || t('projects.title')}
        actions={
          <div className="flex gap-2">
            <Button variant="outline" asChild>
              <Link to={`/projects/${projectId}/explore`}>
                <BarChart3 className="mr-2 h-4 w-4" />
                {t('exploration.title')}
              </Link>
            </Button>
            <Button variant="outline" asChild>
              <Link to={`/projects/${projectId}/datasets/upload`}>
                <Upload className="mr-2 h-4 w-4" />
                {t('datasets.upload')}
              </Link>
            </Button>
            <Button variant="gradient" asChild>
              <Link to={`/projects/${projectId}/models/new`}>
                <Plus className="mr-2 h-4 w-4" />
                {t('models.newModel')}
              </Link>
            </Button>
          </div>
        }
      />

      {isLoading ? (
        <div className="p-6 space-y-6">
          {/* Quick Actions Skeleton */}
          <div className="grid gap-4 md:grid-cols-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <CardSkeleton key={i} />
            ))}
          </div>
          {/* Overview Cards Skeleton */}
          <div className="grid gap-4 md:grid-cols-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <MetricCardSkeleton key={i} />
            ))}
          </div>
          {/* Datasets Section Skeleton */}
          <div className="space-y-4">
            <div className="h-6 w-32 bg-muted rounded animate-pulse" />
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {Array.from({ length: 3 }).map((_, i) => (
                <CardSkeleton key={i} />
              ))}
            </div>
          </div>
          {/* Models Section Skeleton */}
          <div className="space-y-4">
            <div className="h-6 w-24 bg-muted rounded animate-pulse" />
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {Array.from({ length: 3 }).map((_, i) => (
                <CardSkeleton key={i} />
              ))}
            </div>
          </div>
        </div>
      ) : (

      <div className="p-6 space-y-8">
        {/* Quick Actions */}
        <div className="grid gap-4 md:grid-cols-3 lg:grid-cols-6">
          <Link to={`/projects/${projectId}/variables`} className="block group">
            <Card variant="glass" hover="lift" className="h-full">
              <CardHeader className="pb-2">
                <div className="flex items-center gap-3">
                  <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-blue-500/10 text-blue-500 group-hover:bg-blue-500/20 transition-colors">
                    <Tag className="h-5 w-5" />
                  </div>
                  <CardTitle className="text-base">{t('variables.title', '变量管理')}</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">
                  {t('variables.quickDesc', '配置变量类型和分组')}
                </p>
              </CardContent>
            </Card>
          </Link>
          <Link to={`/projects/${projectId}/hierarchical/new`} className="block group">
            <Card variant="glass" hover="lift" className="h-full">
              <CardHeader className="pb-2">
                <div className="flex items-center gap-3">
                  <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-purple-500/10 text-purple-500 group-hover:bg-purple-500/20 transition-colors">
                    <Layers className="h-5 w-5" />
                  </div>
                  <CardTitle className="text-base">{t('hierarchical.title', '分层模型')}</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">
                  {t('hierarchical.quickDesc', '按区域/渠道训练子模型')}
                </p>
              </CardContent>
            </Card>
          </Link>
          <Link to={`/projects/${projectId}/explore`} className="block group">
            <Card variant="glass" hover="lift" className="h-full">
              <CardHeader className="pb-2">
                <div className="flex items-center gap-3">
                  <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-green-500/10 text-green-500 group-hover:bg-green-500/20 transition-colors">
                    <BarChart3 className="h-5 w-5" />
                  </div>
                  <CardTitle className="text-base">{t('exploration.title', '数据探索')}</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">
                  {t('exploration.quickDesc', '可视化分析数据')}
                </p>
              </CardContent>
            </Card>
          </Link>
          <Link to={`/projects/${projectId}/models/new`} className="block group">
            <Card variant="glass" hover="lift" className="h-full">
              <CardHeader className="pb-2">
                <div className="flex items-center gap-3">
                  <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-orange-500/10 text-orange-500 group-hover:bg-orange-500/20 transition-colors">
                    <Plus className="h-5 w-5" />
                  </div>
                  <CardTitle className="text-base">{t('models.newModel', '新建模型')}</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">
                  {t('models.newModelDesc', '创建MMM模型')}
                </p>
              </CardContent>
            </Card>
          </Link>
          <Link to={`/projects/${projectId}/scenarios`} className="block group">
            <Card variant="glass" hover="lift" className="h-full">
              <CardHeader className="pb-2">
                <div className="flex items-center gap-3">
                  <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-teal-500/10 text-teal-500 group-hover:bg-teal-500/20 transition-colors">
                    <GitBranch className="h-5 w-5" />
                  </div>
                  <CardTitle className="text-base">{t('scenarios.title', 'Scenarios')}</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">
                  {t('scenarios.quickDesc', 'What-if scenario analysis')}
                </p>
              </CardContent>
            </Card>
          </Link>
          <Link to={`/projects/${projectId}/optimization`} className="block group">
            <Card variant="glass" hover="lift" className="h-full">
              <CardHeader className="pb-2">
                <div className="flex items-center gap-3">
                  <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-red-500/10 text-red-500 group-hover:bg-red-500/20 transition-colors">
                    <Target className="h-5 w-5" />
                  </div>
                  <CardTitle className="text-base">{t('optimization.title', 'Budget Optimization')}</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">
                  {t('optimization.quickDesc', 'Optimize budget allocation')}
                </p>
              </CardContent>
            </Card>
          </Link>
        </div>

        {/* Overview Cards */}
        <div className="grid gap-4 md:grid-cols-3">
          <Card variant="glass">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">{t('datasets.title')}</CardTitle>
              <Database className="h-5 w-5 text-muted-foreground/50" />
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold tracking-tight">{datasets.length}</div>
              <p className="text-sm text-muted-foreground mt-1">
                {datasets.filter((d) => d.status === 'ready').length} {t('datasets.ready').toLowerCase()}
              </p>
            </CardContent>
          </Card>
          <Card variant="glass">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">{t('models.title')}</CardTitle>
              <LineChart className="h-5 w-5 text-muted-foreground/50" />
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold tracking-tight">{models.length}</div>
              <p className="text-sm text-muted-foreground mt-1">
                {models.filter((m) => m.status === 'completed').length} {t('models.status.completed').toLowerCase()}
              </p>
            </CardContent>
          </Card>
          <Card variant="glass">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">{t('projects.status')}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold tracking-tight text-green-500">{t('projects.active')}</div>
              <p className="text-sm text-muted-foreground mt-1">
                {t('projects.lastUpdated')} {project?.updated_at ? new Date(project.updated_at).toLocaleDateString() : 'N/A'}
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Datasets Section */}
        <div>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold tracking-tight">{t('datasets.title')}</h2>
            <Button variant="ghost" size="sm" asChild>
              <Link to={`/projects/${projectId}/datasets/upload`}>
                <Plus className="mr-2 h-4 w-4" />
                {t('datasets.addDataset')}
              </Link>
            </Button>
          </div>
          {datasets.length === 0 ? (
            <Card variant="glass">
              <CardContent className="flex flex-col items-center justify-center py-12">
                <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-muted/50">
                  <Database className="h-7 w-7 text-muted-foreground/50" />
                </div>
                <p className="mt-4 text-sm text-muted-foreground">
                  {t('datasets.noDatasets')}
                </p>
                <Button className="mt-4" variant="outline" asChild>
                  <Link to={`/projects/${projectId}/datasets/upload`}>
                    <Upload className="mr-2 h-4 w-4" />
                    {t('datasets.upload')}
                  </Link>
                </Button>
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {datasets.map((dataset: Dataset) => (
                <DatasetCard key={dataset.id} dataset={dataset} projectId={projectId!} />
              ))}
            </div>
          )}
        </div>

        {/* Models Section */}
        <div>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold tracking-tight">{t('models.title')}</h2>
            <Button variant="ghost" size="sm" asChild>
              <Link to={`/projects/${projectId}/models/new`}>
                <Plus className="mr-2 h-4 w-4" />
                {t('models.createModel')}
              </Link>
            </Button>
          </div>
          {models.length === 0 ? (
            <Card variant="glass">
              <CardContent className="flex flex-col items-center justify-center py-12">
                <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-muted/50">
                  <LineChart className="h-7 w-7 text-muted-foreground/50" />
                </div>
                <p className="mt-4 text-sm text-muted-foreground">
                  {t('models.noModels')}
                </p>
                <Button className="mt-4" variant="outline" asChild disabled={datasets.length === 0}>
                  <Link to={`/projects/${projectId}/models/new`}>
                    <Plus className="mr-2 h-4 w-4" />
                    {t('models.createModel')}
                  </Link>
                </Button>
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {models.map((model: ModelConfig) => (
                <ModelCard key={model.id} model={model} projectId={projectId!} />
              ))}
            </div>
          )}
        </div>

        {/* Model Comparison Section */}
        {models.filter((m: ModelConfig) => m.status === 'completed').length >= 2 && (
          <div>
            <h2 className="text-lg font-semibold tracking-tight mb-4">{t('models.comparison', 'Model Comparison')}</h2>
            <ModelComparisonView projectId={projectId!} models={models} />
          </div>
        )}

        {/* Team Members Section - at bottom */}
        <ProjectMembersPanel
          projectId={projectId!}
          isOwner={project?.owner_id === user?.id}
        />
      </div>
      )}
    </PageWrapper>
  );
}

function DatasetCard({ dataset, projectId }: { dataset: Dataset; projectId: string }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const deleteMutation = useMutation({
    mutationFn: () => datasetsApi.delete(projectId, dataset.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['datasets', projectId] });
    },
  });

  const reprocessMutation = useMutation({
    mutationFn: () => datasetsApi.reprocess(projectId, dataset.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['datasets', projectId] });
    },
  });

  return (
    <Card variant="glass" hover="lift">
      <Link to={`/projects/${projectId}/datasets/${dataset.id}`}>
        <CardHeader className="pb-2">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-blue-500/10 text-blue-500">
              <Database className="h-5 w-5" />
            </div>
            <div className="flex-1 min-w-0">
              <CardTitle className="text-base truncate">{dataset.name}</CardTitle>
              <CardDescription className="text-xs">
                {(dataset.row_count ?? 0).toLocaleString()} {t('datasets.rows').toLowerCase()} · {dataset.column_count ?? '-'} {t('datasets.columns').toLowerCase()}
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between text-sm">
            <span className={`capitalize font-medium ${dataset.status === 'ready' ? 'text-green-500' : dataset.status === 'failed' ? 'text-destructive' : 'text-muted-foreground'}`}>
              {dataset.status === 'ready' ? t('datasets.ready') : dataset.status}
            </span>
            <ArrowRight className="h-4 w-4 text-muted-foreground" />
          </div>
        </CardContent>
      </Link>
      <div className="px-6 pb-4 space-y-2">
        {(dataset.status === 'processing' || dataset.status === 'failed' || dataset.status === 'pending') && (
          <Button
            variant="outline"
            size="sm"
            className="w-full"
            onClick={(e) => {
              e.stopPropagation();
              reprocessMutation.mutate();
            }}
            disabled={reprocessMutation.isPending}
          >
            {reprocessMutation.isPending ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : null}
            {t('datasets.reprocess')}
          </Button>
        )}
        {dataset.status === 'ready' && (
          <Link to={`/projects/${projectId}/datasets/${dataset.id}/update`} onClick={(e) => e.stopPropagation()}>
            <Button variant="outline" size="sm" className="w-full">
              <RefreshCw className="mr-2 h-4 w-4" />
              {t('datasets.update', '更新数据')}
            </Button>
          </Link>
        )}
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button
              variant="ghost"
              size="sm"
              className="w-full text-destructive hover:text-destructive hover:bg-destructive/10"
              onClick={(e) => e.stopPropagation()}
            >
              <Trash2 className="mr-2 h-4 w-4" />
              {t('common.delete')}
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent onClick={(e) => e.stopPropagation()}>
            <AlertDialogHeader>
              <AlertDialogTitle>{t('common.confirm')}</AlertDialogTitle>
              <AlertDialogDescription>
                {t('datasets.deleteConfirm', { name: dataset.name })}
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>{t('common.cancel')}</AlertDialogCancel>
              <AlertDialogAction
                onClick={() => deleteMutation.mutate()}
                className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              >
                {t('common.delete')}
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </Card>
  );
}

function ModelCard({ model, projectId }: { model: ModelConfig; projectId: string }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const status = statusConfig[model.status];
  const StatusIcon = status.icon;

  const deleteMutation = useMutation({
    mutationFn: () => modelsApi.delete(projectId, model.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['models', projectId] });
    },
  });

  return (
    <Card variant="glass" hover="lift">
      <Link to={`/projects/${projectId}/models/${model.id}${model.status === 'completed' ? '/results' : '/training'}`}>
        <CardHeader className="pb-2">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-purple-500/10 text-purple-500">
              <LineChart className="h-5 w-5" />
            </div>
            <div className="flex-1 min-w-0">
              <CardTitle className="text-base truncate">{model.name}</CardTitle>
              <CardDescription className="text-xs capitalize">
                {model.model_type} {t('models.title').toLowerCase()}
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between text-sm">
            <span className={`flex items-center gap-1.5 font-medium ${status.color}`}>
              <StatusIcon className={`h-4 w-4 ${model.status === 'training' ? 'animate-spin' : ''}`} />
              {t(`models.status.${model.status}`)}
            </span>
            <ArrowRight className="h-4 w-4 text-muted-foreground" />
          </div>
        </CardContent>
      </Link>
      <div className="px-6 pb-4">
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button
              variant="ghost"
              size="sm"
              className="w-full text-destructive hover:text-destructive hover:bg-destructive/10"
              onClick={(e) => e.stopPropagation()}
            >
              <Trash2 className="mr-2 h-4 w-4" />
              {t('common.delete')}
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent onClick={(e) => e.stopPropagation()}>
            <AlertDialogHeader>
              <AlertDialogTitle>{t('common.confirm')}</AlertDialogTitle>
              <AlertDialogDescription>
                {t('models.deleteConfirm', { name: model.name })}
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>{t('common.cancel')}</AlertDialogCancel>
              <AlertDialogAction
                onClick={() => deleteMutation.mutate()}
                className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              >
                {deleteMutation.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  t('common.delete')
                )}
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </Card>
  );
}
