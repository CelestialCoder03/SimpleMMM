import { useState, Component } from 'react';
import type { ErrorInfo, ReactNode } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { datasetsApi, explorationApi, projectsApi } from '@/api/services';
import type { Dataset } from '@/types';
import { Header, PageWrapper } from '@/components/layout';
import { Button } from '@/components/ui/button';

// Error Boundary for catching rendering errors
interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error?: Error;
}

class ChartErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Chart rendering error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback || (
        <div className="p-8 text-center border rounded-lg bg-red-50">
          <p className="text-red-600 font-medium">Chart rendering error</p>
          <p className="text-sm text-red-500 mt-1">{this.state.error?.message}</p>
          <Button 
            variant="outline" 
            className="mt-4"
            onClick={() => this.setState({ hasError: false })}
          >
            Try Again
          </Button>
        </div>
      );
    }
    return this.props.children;
  }
}
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import {
  ArrowLeft,
  BarChart3,
  GitBranch,
  AlertTriangle,
  TrendingUp,
  Database,
  LineChart,
  ScatterChart,
} from 'lucide-react';
import { ChartSkeleton, Skeleton, StatsGridSkeleton } from '@/components/ui/skeleton';
import ReactECharts from 'echarts-for-react';

export function DataExplorationPage() {
  const { t } = useTranslation();
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const [selectedDatasetId, setSelectedDatasetId] = useState<string>('');
  const [selectedColumn, setSelectedColumn] = useState<string>('');
  
  // Chart builder state
  const [chartType, setChartType] = useState<'bar' | 'line' | 'scatter'>('line');
  const [chartXAxis, setChartXAxis] = useState<string>('');
  const [chartYColumns, setChartYColumns] = useState<string[]>([]);
  const [chartGroupBy, setChartGroupBy] = useState<string>('');
  const [chartAggregation, setChartAggregation] = useState<'sum' | 'mean' | 'count' | 'min' | 'max'>('sum');
  const [chartGenerated, setChartGenerated] = useState(false);

  // Fetch datasets for the project
  const { data: project } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => projectsApi.get(projectId!),
    enabled: !!projectId,
  });

  const { data: datasets = [], isLoading: datasetsLoading } = useQuery({
    queryKey: ['datasets', projectId],
    queryFn: () => datasetsApi.list(projectId!),
    enabled: !!projectId,
    select: (data) => data.filter((d: Dataset) => d.status === 'ready'),
  });

  // Fetch exploration data when dataset is selected
  const { data: summary, isLoading: summaryLoading, error: summaryError } = useQuery({
    queryKey: ['exploration-summary', projectId, selectedDatasetId],
    queryFn: () => explorationApi.getSummary(projectId!, selectedDatasetId),
    enabled: !!projectId && !!selectedDatasetId,
    retry: 1,
  });

  const { data: correlations, isLoading: correlationsLoading } = useQuery({
    queryKey: ['exploration-correlations', projectId, selectedDatasetId],
    queryFn: () => explorationApi.getCorrelations(projectId!, selectedDatasetId),
    enabled: !!summary && summary.numeric_columns.length >= 2,
    retry: 1,
  });

  const { data: missing, isLoading: missingLoading } = useQuery({
    queryKey: ['exploration-missing', projectId, selectedDatasetId],
    queryFn: () => explorationApi.getMissingAnalysis(projectId!, selectedDatasetId),
    enabled: !!projectId && !!selectedDatasetId && !!summary,
    retry: 1,
  });

  const { data: distribution, isLoading: distributionLoading } = useQuery({
    queryKey: ['exploration-distribution', projectId, selectedDatasetId, selectedColumn],
    queryFn: () => explorationApi.getDistribution(projectId!, selectedDatasetId, selectedColumn),
    enabled: !!selectedDatasetId && !!selectedColumn,
    retry: 1,
  });

  const handleDatasetChange = (datasetId: string) => {
    setSelectedDatasetId(datasetId);
    setSelectedColumn('');
  };

  return (
    <PageWrapper className="flex flex-col">
      <Header
        title={t('exploration.title')}
        projectName={project?.name}
        actions={
          <Button variant="ghost" onClick={() => navigate(`/projects/${projectId}`)}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            {t('common.back')}
          </Button>
        }
      />

      <div className="p-6 space-y-6">
        {/* Dataset Selector */}
        <Card variant="glass">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-primary text-white shadow-md">
                <Database className="h-4 w-4" />
              </div>
              {t('exploration.selectDataset')}
            </CardTitle>
            <CardDescription>{t('exploration.selectDatasetDescription')}</CardDescription>
          </CardHeader>
          <CardContent>
            {datasetsLoading ? (
              <div className="space-y-2">
                <Skeleton className="h-10 w-full md:w-96" />
              </div>
            ) : datasets.length === 0 ? (
              <p className="text-muted-foreground">{t('exploration.noDatasets')}</p>
            ) : (
              <Select value={selectedDatasetId} onValueChange={handleDatasetChange}>
                <SelectTrigger className="w-full md:w-96">
                  <SelectValue placeholder={t('exploration.chooseDataset')} />
                </SelectTrigger>
                <SelectContent>
                  {datasets.map((dataset: Dataset) => (
                    <SelectItem key={dataset.id} value={dataset.id}>
                      <div className="flex items-center gap-2">
                        <span>{dataset.name}</span>
                        <span className="text-xs text-muted-foreground">
                          ({dataset.row_count?.toLocaleString() || '?'} rows)
                        </span>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </CardContent>
        </Card>

        {/* Exploration Content */}
        {selectedDatasetId && (
          <>
            {summaryLoading ? (
              <div className="space-y-4">
                <StatsGridSkeleton count={4} />
                <ChartSkeleton height="h-48" />
              </div>
            ) : summaryError ? (
              <Card>
                <CardContent className="py-12 text-center">
                  <AlertTriangle className="h-10 w-10 mx-auto text-yellow-500 mb-3" />
                  <p className="text-muted-foreground">{t('exploration.loadError')}</p>
                  <p className="text-sm text-muted-foreground mt-1">
                    {(summaryError as Error)?.message || t('common.unknownError')}
                  </p>
                </CardContent>
              </Card>
            ) : summary ? (
              <Card variant="glass">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-accent text-white shadow-md">
                      <BarChart3 className="h-4 w-4" />
                    </div>
                    {t('exploration.dataAnalysis')}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <Tabs defaultValue="overview" className="w-full">
                    <TabsList className="grid w-full grid-cols-5">
                      <TabsTrigger value="overview">{t('exploration.overview')}</TabsTrigger>
                      <TabsTrigger value="charts">{t('exploration.charts') || 'Charts'}</TabsTrigger>
                      <TabsTrigger value="distribution">{t('exploration.distribution')}</TabsTrigger>
                      <TabsTrigger value="correlations">{t('exploration.correlations')}</TabsTrigger>
                      <TabsTrigger value="missing">{t('exploration.missing')}</TabsTrigger>
                    </TabsList>

                    {/* Overview Tab */}
                    <TabsContent value="overview" className="space-y-4 mt-4">
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <div className="p-4 rounded-xl glass-sm">
                          <p className="text-sm text-muted-foreground">{t('datasets.rows')}</p>
                          <p className="text-2xl font-bold">{summary.n_rows.toLocaleString()}</p>
                        </div>
                        <div className="p-4 rounded-xl glass-sm">
                          <p className="text-sm text-muted-foreground">{t('datasets.columns')}</p>
                          <p className="text-2xl font-bold">{summary.n_columns}</p>
                        </div>
                        <div className="p-4 rounded-xl glass-sm">
                          <p className="text-sm text-muted-foreground">{t('exploration.memoryUsage')}</p>
                          <p className="text-2xl font-bold">{summary.memory_mb.toFixed(2)} MB</p>
                        </div>
                        <div className="p-4 rounded-xl glass-sm">
                          <p className="text-sm text-muted-foreground">{t('exploration.missingValues')}</p>
                          <p className="text-2xl font-bold">{summary.total_missing_pct.toFixed(1)}%</p>
                        </div>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div className="p-4 rounded-xl glass-sm">
                          <p className="text-sm font-medium mb-2">{t('exploration.numericColumns')}</p>
                          <div className="flex flex-wrap gap-1">
                            {summary.numeric_columns.length > 0 ? (
                              summary.numeric_columns.map((col) => (
                                <span key={col} className="px-2.5 py-1 text-xs bg-blue-500/10 text-blue-700 dark:text-blue-300 rounded-lg">
                                  {col}
                                </span>
                              ))
                            ) : (
                              <span className="text-muted-foreground text-sm">{t('common.none')}</span>
                            )}
                          </div>
                        </div>
                        <div className="p-4 rounded-xl glass-sm">
                          <p className="text-sm font-medium mb-2">{t('exploration.categoricalColumns')}</p>
                          <div className="flex flex-wrap gap-1">
                            {summary.categorical_columns.length > 0 ? (
                              summary.categorical_columns.map((col) => (
                                <span key={col} className="px-2.5 py-1 text-xs bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 rounded-lg">
                                  {col}
                                </span>
                              ))
                            ) : (
                              <span className="text-muted-foreground text-sm">{t('common.none')}</span>
                            )}
                          </div>
                        </div>
                        <div className="p-4 rounded-xl glass-sm">
                          <p className="text-sm font-medium mb-2">{t('exploration.datetimeColumns')}</p>
                          <div className="flex flex-wrap gap-1">
                            {summary.datetime_columns.length > 0 ? (
                              summary.datetime_columns.map((col) => (
                                <span key={col} className="px-2.5 py-1 text-xs bg-purple-500/10 text-purple-700 dark:text-purple-300 rounded-lg">
                                  {col}
                                </span>
                              ))
                            ) : (
                              <span className="text-muted-foreground text-sm">{t('common.none')}</span>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Column Statistics Table */}
                      <div className="rounded-xl overflow-hidden">
                        <table className="w-full text-sm">
                          <thead className="glass-sm border-b border-[var(--glass-border)]">
                            <tr>
                              <th className="px-4 py-3 text-left font-medium text-muted-foreground">{t('exploration.columnName')}</th>
                              <th className="px-4 py-3 text-left font-medium text-muted-foreground">{t('exploration.dataType')}</th>
                              <th className="px-4 py-3 text-right font-medium text-muted-foreground">{t('exploration.nonNull')}</th>
                              <th className="px-4 py-3 text-right font-medium text-muted-foreground">{t('exploration.unique')}</th>
                              <th className="px-4 py-3 text-right font-medium text-muted-foreground">{t('exploration.missingPct')}</th>
                            </tr>
                          </thead>
                          <tbody>
                            {summary.columns.map((col, i) => (
                              <tr key={col.name} className={`transition-colors hover:bg-white/50 dark:hover:bg-white/5 ${i % 2 === 0 ? '' : 'bg-muted/10'}`}>
                                <td className="px-4 py-2.5 font-medium">{col.name}</td>
                                <td className="px-4 py-2.5 text-muted-foreground">{col.dtype}</td>
                                <td className="px-4 py-2.5 text-right">{col.count.toLocaleString()}</td>
                                <td className="px-4 py-2.5 text-right">{col.unique.toLocaleString()}</td>
                                <td className="px-4 py-2.5 text-right">
                                  {col.missing_pct > 0 ? (
                                    <span className="inline-flex px-2 py-0.5 rounded-lg bg-yellow-500/10 text-yellow-600 dark:text-yellow-400">{col.missing_pct.toFixed(1)}%</span>
                                  ) : (
                                    <span className="inline-flex px-2 py-0.5 rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">0%</span>
                                  )}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </TabsContent>

                    {/* Charts Tab - Interactive Chart Builder */}
                    <TabsContent value="charts" className="space-y-4 mt-4">
                      <ChartErrorBoundary>
                      {summary && summary.columns && summary.columns.length > 0 ? (
                        <>
                          <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4">
                            <div className="space-y-2">
                              <Label className="text-sm font-medium">{t('exploration.chartType') || 'Chart Type'}</Label>
                              <Select value={chartType} onValueChange={(v) => setChartType(v as 'bar' | 'line' | 'scatter')}>
                                <SelectTrigger>
                                  <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                  <SelectItem value="line">
                                    <div className="flex items-center gap-2">
                                      <LineChart className="h-4 w-4" />
                                      {t('exploration.lineChart') || 'Line Chart'}
                                    </div>
                                  </SelectItem>
                                  <SelectItem value="bar">
                                    <div className="flex items-center gap-2">
                                      <BarChart3 className="h-4 w-4" />
                                      {t('exploration.barChart') || 'Bar Chart'}
                                    </div>
                                  </SelectItem>
                                  <SelectItem value="scatter">
                                    <div className="flex items-center gap-2">
                                      <ScatterChart className="h-4 w-4" />
                                      {t('exploration.scatterPlot') || 'Scatter Plot'}
                                    </div>
                                  </SelectItem>
                                </SelectContent>
                              </Select>
                            </div>
                            <div className="space-y-2">
                              <Label className="text-sm font-medium">{t('exploration.xAxis') || 'X-Axis'}</Label>
                              <Select value={chartXAxis} onValueChange={setChartXAxis}>
                                <SelectTrigger>
                                  <SelectValue placeholder={t('exploration.selectVariable') || 'Select...'} />
                                </SelectTrigger>
                                <SelectContent>
                                  {(summary.columns || []).map((col) => (
                                    <SelectItem key={col.name} value={col.name}>
                                      {col.name}
                                    </SelectItem>
                                  ))}
                                </SelectContent>
                              </Select>
                            </div>
                            <div className="space-y-2">
                              <Label className="text-sm font-medium">{t('exploration.yAxis') || 'Y-Axis (multiple)'}</Label>
                              <Select 
                                value={chartYColumns[0] || ''} 
                                onValueChange={(v) => {
                                  if (v && !chartYColumns.includes(v)) {
                                    setChartYColumns([...chartYColumns, v]);
                                  }
                                }}
                              >
                                <SelectTrigger>
                                  <SelectValue placeholder={t('exploration.addVariable') || 'Add variable...'} />
                                </SelectTrigger>
                                <SelectContent>
                                  {(summary.numeric_columns || []).map((col) => (
                                    <SelectItem key={col} value={col} disabled={chartYColumns.includes(col)}>
                                      {col}
                                    </SelectItem>
                                  ))}
                                </SelectContent>
                              </Select>
                              {chartYColumns.length > 0 && (
                                <div className="flex flex-wrap gap-1 mt-1">
                                  {chartYColumns.map((col) => (
                                    <span 
                                      key={col} 
                                      className="px-2 py-0.5 text-xs bg-blue-100 text-blue-800 rounded cursor-pointer hover:bg-red-100 hover:text-red-800"
                                      onClick={() => setChartYColumns(chartYColumns.filter(c => c !== col))}
                                      title={t('common.clickToRemove') || 'Click to remove'}
                                    >
                                      {col} ×
                                    </span>
                                  ))}
                                </div>
                              )}
                            </div>
                            <div className="space-y-2">
                              <Label className="text-sm font-medium">{t('exploration.groupBy') || 'Group By'}</Label>
                              <Select 
                                value={chartGroupBy || '__none__'} 
                                onValueChange={(v) => setChartGroupBy(v === '__none__' ? '' : v)}
                              >
                                <SelectTrigger>
                                  <SelectValue placeholder={t('exploration.none') || 'None'} />
                                </SelectTrigger>
                                <SelectContent>
                                  <SelectItem value="__none__">{t('exploration.none') || 'None'}</SelectItem>
                                  {(summary.categorical_columns || []).map((col) => (
                                    <SelectItem key={col} value={col}>
                                      {col}
                                    </SelectItem>
                                  ))}
                                </SelectContent>
                              </Select>
                            </div>
                            <div className="space-y-2">
                              <Label className="text-sm font-medium">{t('exploration.aggregation') || 'Aggregation'}</Label>
                              <Select value={chartAggregation} onValueChange={(v) => setChartAggregation(v as 'sum' | 'mean' | 'count' | 'min' | 'max')}>
                                <SelectTrigger>
                                  <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                  <SelectItem value="sum">{t('exploration.sum') || 'Sum'}</SelectItem>
                                  <SelectItem value="mean">{t('exploration.mean') || 'Mean'}</SelectItem>
                                  <SelectItem value="count">{t('exploration.count') || 'Count'}</SelectItem>
                                  <SelectItem value="min">{t('exploration.min') || 'Min'}</SelectItem>
                                  <SelectItem value="max">{t('exploration.max') || 'Max'}</SelectItem>
                                </SelectContent>
                              </Select>
                            </div>
                            <div className="flex items-end">
                              <Button 
                                className="w-full"
                                disabled={!chartXAxis || chartYColumns.length === 0}
                                onClick={() => setChartGenerated(true)}
                              >
                                {t('exploration.generateChart') || 'Generate'}
                              </Button>
                            </div>
                          </div>

                          {chartGenerated && chartXAxis && chartYColumns.length > 0 && (
                            <ChartDisplay
                              projectId={projectId!}
                              datasetId={selectedDatasetId}
                              xColumn={chartXAxis}
                              yColumns={chartYColumns}
                              groupBy={chartGroupBy || undefined}
                              aggregation={chartAggregation}
                              chartType={chartType}
                            />
                          )}

                          {(!chartXAxis || chartYColumns.length === 0) && (
                            <div className="p-8 text-center glass-sm rounded-xl">
                              <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-xl bg-primary/10 mb-4">
                                <BarChart3 className="h-7 w-7 text-primary" />
                              </div>
                              <p className="text-muted-foreground">{t('exploration.selectVariablesToChart') || 'Select X-axis and at least one Y variable to generate a chart'}</p>
                            </div>
                          )}
                        </>
                      ) : (
                        <ChartSkeleton height="h-64" />
                      )}
                      </ChartErrorBoundary>
                    </TabsContent>

                    {/* Distribution Tab */}
                    <TabsContent value="distribution" className="space-y-4 mt-4">
                      <div className="flex items-center gap-4">
                        <Select value={selectedColumn} onValueChange={setSelectedColumn}>
                          <SelectTrigger className="w-64">
                            <SelectValue placeholder={t('exploration.selectColumn')} />
                          </SelectTrigger>
                          <SelectContent>
                            {summary.columns.map((col) => (
                              <SelectItem key={col.name} value={col.name}>
                                {col.name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>

                      {distributionLoading && (
                        <div className="space-y-4">
                          <ChartSkeleton height="h-48" />
                          <Skeleton className="h-24 w-full rounded-lg" />
                        </div>
                      )}

                      {distribution && !distributionLoading && (
                        <div className="space-y-4">
                          {/* Histogram using ECharts */}
                          {distribution.histogram && (
                            <div className="p-4 rounded-lg border">
                              <p className="text-sm font-medium mb-2">{t('exploration.histogram')}</p>
                              <ReactECharts
                                option={{
                                  tooltip: { trigger: 'axis' },
                                  xAxis: {
                                    type: 'category',
                                    data: distribution.histogram.bin_edges.slice(0, -1).map((v, i) => 
                                      `${v.toFixed(1)}-${distribution.histogram!.bin_edges[i + 1].toFixed(1)}`
                                    ),
                                    axisLabel: { rotate: 45, fontSize: 10 },
                                  },
                                  yAxis: { type: 'value', name: 'Count' },
                                  series: [{
                                    type: 'bar',
                                    data: distribution.histogram.counts,
                                    itemStyle: { color: '#3b82f6' },
                                  }],
                                }}
                                style={{ height: '250px' }}
                              />
                            </div>
                          )}

                          {/* Box Plot for numeric columns - horizontal layout */}
                          {distribution.histogram && (
                            <div className="p-4 rounded-lg border">
                              <p className="text-sm font-medium mb-2">{t('exploration.boxPlot') || 'Box Plot'}</p>
                              <ReactECharts
                                option={{
                                  tooltip: { 
                                    trigger: 'item',
                                    formatter: (params: { data: number[] }) => {
                                      const d = params.data;
                                      return `Min: ${d[0]?.toFixed(2)}<br/>Q1: ${d[1]?.toFixed(2)}<br/>Median: ${d[2]?.toFixed(2)}<br/>Q3: ${d[3]?.toFixed(2)}<br/>Max: ${d[4]?.toFixed(2)}`;
                                    }
                                  },
                                  grid: { left: '10%', right: '10%', top: '15%', bottom: '15%' },
                                  xAxis: { 
                                    type: 'value',
                                    name: selectedColumn,
                                    nameLocation: 'middle',
                                    nameGap: 25,
                                  },
                                  yAxis: { 
                                    type: 'category', 
                                    data: [''],
                                    axisTick: { show: false },
                                    axisLine: { show: false },
                                  },
                                  series: [{
                                    type: 'boxplot',
                                    data: [[
                                      distribution.histogram.bin_edges[0],
                                      distribution.histogram.bin_edges[Math.floor(distribution.histogram.bin_edges.length * 0.25)],
                                      distribution.histogram.bin_edges[Math.floor(distribution.histogram.bin_edges.length * 0.5)],
                                      distribution.histogram.bin_edges[Math.floor(distribution.histogram.bin_edges.length * 0.75)],
                                      distribution.histogram.bin_edges[distribution.histogram.bin_edges.length - 1],
                                    ]],
                                    itemStyle: { color: '#3b82f6', borderColor: '#1e40af' },
                                  }],
                                }}
                                style={{ height: '120px' }}
                              />
                            </div>
                          )}

                          {distribution.outliers && (
                            <div className="p-4 rounded-lg border">
                              <p className="text-sm font-medium mb-2 flex items-center gap-2">
                                <AlertTriangle className="h-4 w-4 text-yellow-500" />
                                {t('exploration.outliers')}
                              </p>
                              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                                <div>
                                  <p className="text-muted-foreground">{t('exploration.count')}</p>
                                  <p className="font-medium">{distribution.outliers.count}</p>
                                </div>
                                <div>
                                  <p className="text-muted-foreground">{t('exploration.percentage')}</p>
                                  <p className="font-medium">{distribution.outliers.pct.toFixed(2)}%</p>
                                </div>
                                <div>
                                  <p className="text-muted-foreground">{t('exploration.lowerBound')}</p>
                                  <p className="font-medium">{distribution.outliers.lower_bound.toFixed(2)}</p>
                                </div>
                                <div>
                                  <p className="text-muted-foreground">{t('exploration.upperBound')}</p>
                                  <p className="font-medium">{distribution.outliers.upper_bound.toFixed(2)}</p>
                                </div>
                              </div>
                            </div>
                          )}

                          {distribution.value_counts && (
                            <div className="p-4 rounded-lg border">
                              <p className="text-sm font-medium mb-2">{t('exploration.valueCounts')}</p>
                              <ReactECharts
                                option={{
                                  tooltip: { trigger: 'axis' },
                                  xAxis: {
                                    type: 'category',
                                    data: distribution.value_counts.slice(0, 15).map(v => v.value),
                                    axisLabel: { rotate: 45, fontSize: 10 },
                                  },
                                  yAxis: { type: 'value', name: 'Count' },
                                  series: [{
                                    type: 'bar',
                                    data: distribution.value_counts.slice(0, 15).map(v => v.count),
                                    itemStyle: { color: '#10b981' },
                                  }],
                                }}
                                style={{ height: '250px' }}
                              />
                            </div>
                          )}

                          {!distribution.histogram && !distribution.value_counts && (
                            <p className="text-center text-muted-foreground py-8">
                              {t('exploration.noDistributionData')}
                            </p>
                          )}


                        </div>
                      )}

                      {!selectedColumn && (
                        <p className="text-center text-muted-foreground py-8">
                          {t('exploration.selectColumnToAnalyze')}
                        </p>
                      )}
                    </TabsContent>

                    {/* Correlations Tab */}
                    <TabsContent value="correlations" className="space-y-4 mt-4">
                      {correlationsLoading && (
                        <ChartSkeleton height="h-80" />
                      )}

                      {correlations && !correlationsLoading && (
                        <>
                          {correlations.significant_pairs.length > 0 && (
                            <div className="space-y-4">
                              <p className="text-sm font-medium flex items-center gap-2">
                                <GitBranch className="h-4 w-4" />
                                {t('exploration.significantCorrelations')}
                              </p>
                              <div className="grid gap-2">
                                {correlations.significant_pairs.map((pair) => (
                                  <div
                                    key={`${pair.var1}-${pair.var2}`}
                                    className="flex items-center justify-between p-3 rounded-lg border"
                                  >
                                    <div className="flex items-center gap-2">
                                      <span className="font-medium">{pair.var1}</span>
                                      <span className="text-muted-foreground">↔</span>
                                      <span className="font-medium">{pair.var2}</span>
                                    </div>
                                    <div className="flex items-center gap-2">
                                      <span
                                        className={`px-2 py-1 text-xs rounded ${
                                          pair.correlation > 0
                                            ? 'bg-green-100 text-green-800'
                                            : 'bg-red-100 text-red-800'
                                        }`}
                                      >
                                        {pair.correlation.toFixed(3)}
                                      </span>
                                      <span className="text-xs text-muted-foreground capitalize">
                                        {pair.strength}
                                      </span>
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                          {/* Correlation Heatmap */}
                          {correlations.columns && correlations.matrix && (
                            <div className="p-4 rounded-lg border">
                              <p className="text-sm font-medium mb-4">{t('exploration.correlationHeatmap') || 'Correlation Heatmap'}</p>
                              <ReactECharts
                                option={{
                                  tooltip: {
                                    position: 'top',
                                    formatter: (params: { data: number[] }) => {
                                      const [x, y, val] = params.data;
                                      return `${correlations.columns[x]} vs ${correlations.columns[y]}: ${val.toFixed(4)}`;
                                    },
                                  },
                                  grid: { height: '70%', top: '10%' },
                                  xAxis: {
                                    type: 'category',
                                    data: correlations.columns,
                                    splitArea: { show: true },
                                    axisLabel: { rotate: 45, fontSize: 10 },
                                  },
                                  yAxis: {
                                    type: 'category',
                                    data: correlations.columns,
                                    splitArea: { show: true },
                                    axisLabel: { fontSize: 10 },
                                  },
                                  visualMap: {
                                    min: -1,
                                    max: 1,
                                    calculable: true,
                                    orient: 'horizontal',
                                    left: 'center',
                                    bottom: '0%',
                                    inRange: {
                                      color: ['#dc2626', '#fef2f2', '#3b82f6'],
                                    },
                                  },
                                  series: [{
                                    type: 'heatmap',
                                    data: correlations.matrix.flatMap((row: number[], i: number) =>
                                      row.map((val: number, j: number) => [i, j, parseFloat(val.toFixed(4))])
                                    ),
                                    label: { 
                                      show: correlations.columns.length <= 8, 
                                      fontSize: 9,
                                      formatter: (params: { data: number[] }) => params.data[2].toFixed(2),
                                    },
                                    emphasis: {
                                      itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0, 0, 0, 0.5)' },
                                    },
                                  }],
                                }}
                                style={{ height: '400px' }}
                              />
                            </div>
                          )}

                          {!correlations.significant_pairs.length && !correlations.matrix && (
                            <p className="text-center text-muted-foreground py-8">
                              {t('exploration.noSignificantCorrelations')}
                            </p>
                          )}
                        </>
                      )}

                      {summary && summary.numeric_columns.length < 2 && (
                        <p className="text-center text-muted-foreground py-8">
                          {t('exploration.needTwoNumericColumns')}
                        </p>
                      )}
                    </TabsContent>

                    {/* Missing Values Tab */}
                    <TabsContent value="missing" className="space-y-4 mt-4">
                      {missingLoading && (
                        <div className="space-y-4">
                          <StatsGridSkeleton count={4} />
                          <Skeleton className="h-32 w-full rounded-lg" />
                        </div>
                      )}

                      {missing && !missingLoading && (
                        <>
                          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                            <div className="p-4 rounded-lg border">
                              <p className="text-sm text-muted-foreground">{t('exploration.totalMissing')}</p>
                              <p className="text-2xl font-bold">{missing.total_missing.toLocaleString()}</p>
                            </div>
                            <div className="p-4 rounded-lg border">
                              <p className="text-sm text-muted-foreground">{t('exploration.missingPercent')}</p>
                              <p className="text-2xl font-bold">{missing.total_missing_pct.toFixed(2)}%</p>
                            </div>
                            <div className="p-4 rounded-lg border">
                              <p className="text-sm text-muted-foreground">{t('exploration.completeRows')}</p>
                              <p className="text-2xl font-bold">{missing.complete_rows.toLocaleString()}</p>
                            </div>
                            <div className="p-4 rounded-lg border">
                              <p className="text-sm text-muted-foreground">{t('exploration.completePercent')}</p>
                              <p className="text-2xl font-bold">{missing.complete_rows_pct.toFixed(1)}%</p>
                            </div>
                          </div>

                          {missing.columns.filter((c) => c.missing > 0).length > 0 ? (
                            <div className="p-4 rounded-lg border">
                              <p className="text-sm font-medium mb-3">{t('exploration.columnsWithMissing')}</p>
                              <div className="space-y-2">
                                {missing.columns
                                  .filter((c) => c.missing > 0)
                                  .sort((a, b) => b.missing_pct - a.missing_pct)
                                  .map((col) => (
                                    <div key={col.column} className="flex items-center gap-2">
                                      <div className="flex-1">
                                        <div className="flex justify-between text-sm">
                                          <span>{col.column}</span>
                                          <span className="text-muted-foreground">
                                            {col.missing} ({col.missing_pct.toFixed(1)}%)
                                          </span>
                                        </div>
                                        <div className="h-2 bg-muted rounded-full overflow-hidden">
                                          <div
                                            className="h-full bg-yellow-500"
                                            style={{ width: `${col.missing_pct}%` }}
                                          />
                                        </div>
                                      </div>
                                    </div>
                                  ))}
                              </div>
                            </div>
                          ) : (
                            <div className="text-center py-8">
                              <TrendingUp className="h-10 w-10 mx-auto text-green-500 mb-2" />
                              <p className="text-muted-foreground">{t('exploration.noMissingValues')}</p>
                            </div>
                          )}
                        </>
                      )}
                    </TabsContent>

                  </Tabs>
                </CardContent>
              </Card>
            ) : null}
          </>
        )}

        {/* Empty State */}
        {!selectedDatasetId && !datasetsLoading && datasets.length > 0 && (
          <Card variant="glass" className="animate-in-slow">
            <CardContent className="py-12 text-center">
              <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-primary opacity-20 mb-4">
                <BarChart3 className="h-8 w-8 text-primary" />
              </div>
              <p className="text-lg font-medium">{t('exploration.getStarted')}</p>
              <p className="text-muted-foreground">{t('exploration.selectDatasetToBegin')}</p>
            </CardContent>
          </Card>
        )}
      </div>
    </PageWrapper>
  );
}

// Chart Display Component
interface ChartDisplayProps {
  projectId: string;
  datasetId: string;
  xColumn: string;
  yColumns: string[];
  groupBy?: string;
  aggregation: 'sum' | 'mean' | 'count' | 'min' | 'max';
  chartType: 'bar' | 'line' | 'scatter';
}

function ChartDisplay({ projectId, datasetId, xColumn, yColumns, groupBy, aggregation, chartType }: ChartDisplayProps) {
  const { data: chartData, isLoading, error } = useQuery({
    queryKey: ['chart-data', projectId, datasetId, xColumn, yColumns, groupBy, aggregation],
    queryFn: () => explorationApi.getChartData(projectId, datasetId, xColumn, yColumns, groupBy, aggregation),
    retry: 1,
  });

  if (isLoading) {
    return <ChartSkeleton height="h-96" />;
  }

  if (error || !chartData) {
    return (
      <div className="p-4 text-center border rounded-lg text-destructive">
        Failed to load chart data
      </div>
    );
  }

  const colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16'];

  return (
    <div className="p-4 rounded-lg border">
      <ReactECharts
        option={{
          tooltip: { trigger: 'axis' },
          legend: {
            data: chartData.series.map(s => s.name),
            bottom: 0,
          },
          grid: { bottom: 60 },
          xAxis: {
            type: 'category',
            data: chartData.x_axis,
            name: xColumn,
            axisLabel: { rotate: chartData.x_axis.length > 10 ? 45 : 0, fontSize: 10 },
          },
          yAxis: { type: 'value' },
          series: chartData.series.map((s, i) => ({
            name: s.name,
            type: chartType,
            data: s.data,
            itemStyle: { color: colors[i % colors.length] },
            smooth: chartType === 'line',
          })),
        }}
        style={{ height: '400px' }}
      />
      <p className="text-xs text-muted-foreground mt-2 text-center">
        Aggregation: {aggregation.toUpperCase()} | X: {xColumn} | Y: {yColumns.join(', ')}{groupBy ? ` | Group: ${groupBy}` : ''}
      </p>
    </div>
  );
}
