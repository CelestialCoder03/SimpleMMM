import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { datasetsApi, projectsApi } from '@/api/services';
import { Header } from '@/components/layout';
import { Button } from '@/components/ui/button';
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
  Database,
  Rows3,
  Columns3,
  Calendar,
  Hash,
  Type,
  Trash2,
} from 'lucide-react';
import { PageHeaderSkeleton, MetricCardSkeleton, TableSkeleton } from '@/components/ui/skeleton';
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
import type { ColumnMetadata } from '@/types';

export function DatasetDetailPage() {
  const { t } = useTranslation();
  const { projectId, datasetId } = useParams<{ projectId: string; datasetId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const deleteMutation = useMutation({
    mutationFn: () => datasetsApi.delete(projectId!, datasetId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['datasets', projectId] });
      navigate(`/projects/${projectId}`);
    },
  });

  const { data: dataset, isLoading } = useQuery({
    queryKey: ['dataset', projectId, datasetId],
    queryFn: () => datasetsApi.get(projectId!, datasetId!),
    enabled: !!projectId && !!datasetId,
  });

  const { data: project } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => projectsApi.get(projectId!),
    enabled: !!projectId,
  });

  const { data: preview, isLoading: previewLoading } = useQuery({
    queryKey: ['dataset-preview', projectId, datasetId],
    queryFn: () => datasetsApi.getPreview(projectId!, datasetId!, 50),
    enabled: !!projectId && !!datasetId,
  });

  if (isLoading) {
    return (
      <div className="flex flex-col">
        <Header title={t('datasets.title')} />
        <main className="flex-1 p-6 space-y-6">
          <PageHeaderSkeleton />
          <div className="grid gap-4 md:grid-cols-4">
            <MetricCardSkeleton />
            <MetricCardSkeleton />
            <MetricCardSkeleton />
            <MetricCardSkeleton />
          </div>
          <TableSkeleton rows={8} columns={5} />
        </main>
      </div>
    );
  }

  if (!dataset) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-muted-foreground">Dataset not found</p>
      </div>
    );
  }

  const getColumnIcon = (col: ColumnMetadata) => {
    if (col.column_type === 'datetime' || col.dtype.includes('date') || col.dtype.includes('datetime')) {
      return <Calendar className="h-4 w-4" />;
    }
    if (col.dtype.includes('int') || col.dtype.includes('float')) {
      return <Hash className="h-4 w-4" />;
    }
    return <Type className="h-4 w-4" />;
  };

  return (
    <div className="flex flex-col min-h-screen bg-app-gradient">
      <Header
        title={dataset.name}
        projectName={project?.name}
        actions={
          <div className="flex gap-2">
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button variant="destructive" size="sm">
                  <Trash2 className="mr-2 h-4 w-4" />
                  {t('common.delete')}
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
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
            <Button variant="ghost" onClick={() => navigate(`/projects/${projectId}`)}>
              <ArrowLeft className="mr-2 h-4 w-4" />
              {t('common.back')}
            </Button>
          </div>
        }
      />

      <div className="p-6 space-y-6">
        {/* Overview Cards */}
        <div className="grid gap-4 md:grid-cols-4">
          <Card variant="glass" hover="lift">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">{t('datasets.status')}</CardTitle>
              <div className={`flex h-8 w-8 items-center justify-center rounded-lg ${dataset.status === 'ready' ? 'bg-emerald-500/10 text-emerald-600' : 'bg-yellow-500/10 text-yellow-600'}`}>
                <Database className="h-4 w-4" />
              </div>
            </CardHeader>
            <CardContent>
              <div className={`text-2xl font-bold capitalize ${
                dataset.status === 'ready' ? 'text-emerald-600 dark:text-emerald-400' : 'text-yellow-600 dark:text-yellow-400'
              }`}>
                {dataset.status}
              </div>
            </CardContent>
          </Card>
          <Card variant="glass" hover="lift">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">{t('datasets.rows')}</CardTitle>
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <Rows3 className="h-4 w-4" />
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {dataset.row_count !== undefined && dataset.row_count !== null
                  ? dataset.row_count.toLocaleString()
                  : '-'}
              </div>
            </CardContent>
          </Card>
          <Card variant="glass" hover="lift">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">{t('datasets.columns')}</CardTitle>
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-purple-500/10 text-purple-600 dark:text-purple-400">
                <Columns3 className="h-4 w-4" />
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{dataset.column_count ?? '-'}</div>
            </CardContent>
          </Card>
          <Card variant="glass" hover="lift">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">{t('projects.created')}</CardTitle>
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-500/10 text-blue-600 dark:text-blue-400">
                <Calendar className="h-4 w-4" />
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-lg font-bold">
                {new Date(dataset.created_at).toLocaleDateString()}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Columns */}
        <Card variant="glass">
          <CardHeader>
            <CardTitle>{t('datasets.columns')}</CardTitle>
            <CardDescription>
              {t('datasets.columnsOverview')}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="rounded-xl overflow-hidden">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-[var(--glass-border)] glass-sm">
                    <th className="px-4 py-3.5 text-left text-sm font-medium text-muted-foreground">Name</th>
                    <th className="px-4 py-3.5 text-left text-sm font-medium text-muted-foreground">Type</th>
                    <th className="px-4 py-3.5 text-left text-sm font-medium text-muted-foreground">Column Type</th>
                    <th className="px-4 py-3.5 text-right text-sm font-medium text-muted-foreground">Unique</th>
                    <th className="px-4 py-3.5 text-right text-sm font-medium text-muted-foreground">Nulls</th>
                  </tr>
                </thead>
                <tbody>
                  {dataset.columns?.map((col: ColumnMetadata, index: number) => (
                    <tr key={col.name} className={`transition-colors hover:bg-white/50 dark:hover:bg-white/5 ${index % 2 === 0 ? '' : 'bg-muted/10'}`}>
                      <td className="px-4 py-3.5">
                        <div className="flex items-center gap-2">
                          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary/10 text-primary">
                            {getColumnIcon(col)}
                          </div>
                          <span className="font-medium">{col.name}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3.5 text-sm text-muted-foreground">
                        {col.dtype}
                      </td>
                      <td className="px-4 py-3.5">
                        <span className="inline-flex rounded-lg glass-sm px-2.5 py-1 text-xs font-medium">
                          {col.column_type}
                        </span>
                      </td>
                      <td className="px-4 py-3.5 text-right text-sm font-medium">
                        {col.unique_count.toLocaleString()}
                      </td>
                      <td className="px-4 py-3.5 text-right text-sm">
                        {col.null_count > 0 ? (
                          <span className="inline-flex items-center rounded-lg bg-red-500/10 px-2 py-0.5 text-red-600 dark:text-red-400">{col.null_count}</span>
                        ) : (
                          <span className="inline-flex items-center rounded-lg bg-emerald-500/10 px-2 py-0.5 text-emerald-600 dark:text-emerald-400">0</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>

        {/* Data Preview */}
        <Card variant="glass">
          <CardHeader>
            <CardTitle>{t('datasets.dataPreview')}</CardTitle>
            <CardDescription>{t('datasets.firstRows')}</CardDescription>
          </CardHeader>
          <CardContent>
            {previewLoading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : preview ? (
              <div className="overflow-x-auto rounded-xl">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-[var(--glass-border)] glass-sm">
                      {preview.columns.map((col: string) => (
                        <th key={col} className="whitespace-nowrap px-4 py-3 text-left font-medium text-muted-foreground">
                          {col}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {preview.data.slice(0, 50).map((row: Record<string, unknown>, rowIndex: number) => (
                      <tr key={rowIndex} className={`transition-colors hover:bg-white/50 dark:hover:bg-white/5 ${rowIndex % 2 === 0 ? '' : 'bg-muted/10'}`}>
                        {preview.columns.map((col: string, cellIndex: number) => {
                          const cell = (row as Record<string, unknown>)[col];
                          return (
                            <td key={cellIndex} className="whitespace-nowrap px-4 py-2.5">
                              {cell === null || cell === undefined ? (
                                <span className="text-muted-foreground">-</span>
                              ) : (
                                String(cell)
                              )}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-center text-muted-foreground py-8">
                {t('datasets.previewNotAvailable')}
              </p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
