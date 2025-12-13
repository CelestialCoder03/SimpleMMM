import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import i18n from '@/i18n';
import { modelsApi, projectsApi, variableGroupsApi } from '@/api/services';
import type { VariableGroup } from '@/api/services/variableGroups';
import { Header, PageWrapper } from '@/components/layout';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { StatsGridSkeleton, ChartSkeleton } from '@/components/ui/skeleton';
import {
  ArrowLeft,
  Download,
  TrendingUp,
  PieChart,
  LineChart,
  BarChart3,
  Copy,
  Users,
  Variable,
  CheckCircle2,
  XCircle,
  FileSpreadsheet,
  FileText,
  FileCode,
  FileType,
  Presentation,
  ChevronDown,
} from 'lucide-react';
import ReactECharts from 'echarts-for-react';
import type { CoefficientResult, ContributionResult } from '@/types';
import { useUIStore } from '@/stores/uiStore';
import {
  getChartTheme,
  CHART_COLOR_PALETTE,
  CHART_COLORS,
  lineSeriesDefaults,
  areaSeriesDefaults,
} from '@/lib/chart-theme';

export function ModelResultsPage() {
  const { t } = useTranslation();
  const { projectId, modelId } = useParams<{ projectId: string; modelId: string }>();
  const navigate = useNavigate();

  const { data: model, isLoading: modelLoading } = useQuery({
    queryKey: ['model', projectId, modelId],
    queryFn: () => modelsApi.get(projectId!, modelId!),
    enabled: !!projectId && !!modelId,
  });

  const { data: results, isLoading: resultsLoading } = useQuery({
    queryKey: ['model-results', projectId, modelId],
    queryFn: () => modelsApi.getResults(projectId!, modelId!),
    enabled: !!projectId && !!modelId,
  });

  const { data: project } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => projectsApi.get(projectId!),
    enabled: !!projectId,
  });

  const { data: variableGroups = [] } = useQuery({
    queryKey: ['variableGroups', projectId],
    queryFn: () => variableGroupsApi.list(projectId!),
    enabled: !!projectId,
  });

  const [viewMode, setViewMode] = useState<'variable' | 'group'>('variable');

  const isLoading = modelLoading || resultsLoading;

  const downloadBlob = (blob: Blob, filename: string) => {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  const handleExport = async (format: string) => {
    const name = model?.name || 'results';
    const lang = i18n.language?.startsWith('zh') ? 'zh' : 'en';
    switch (format) {
      case 'excel': {
        const blob = await modelsApi.exportExcel(projectId!, modelId!, lang);
        downloadBlob(blob, `${name}.xlsx`);
        break;
      }
      case 'csv': {
        const blob = await modelsApi.exportCsv(projectId!, modelId!);
        downloadBlob(blob, `${name}.csv`);
        break;
      }
      case 'pdf': {
        const blob = await modelsApi.exportPdf(projectId!, modelId!);
        downloadBlob(blob, `${name}.pdf`);
        break;
      }
      case 'pptx': {
        const blob = await modelsApi.exportPptx(projectId!, modelId!);
        downloadBlob(blob, `${name}.pptx`);
        break;
      }
      case 'json': {
        const blob = await modelsApi.exportJson(projectId!, modelId!);
        downloadBlob(blob, `${name}.json`);
        break;
      }
      case 'html': {
        const blob = await modelsApi.exportHtml(projectId!, modelId!);
        downloadBlob(blob, `${name}_report.html`);
        break;
      }
    }
  };

  if (isLoading) {
    return (
      <div className="flex flex-col">
        <Header title={t('results.title')} />
        <main className="flex-1 p-6 space-y-6">
          <StatsGridSkeleton count={4} />
          <ChartSkeleton height="h-80" />
          <div className="grid gap-6 md:grid-cols-2">
            <ChartSkeleton height="h-64" />
            <ChartSkeleton height="h-64" />
          </div>
        </main>
      </div>
    );
  }

  if (!model || !results) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-muted-foreground">{t('results.resultsNotAvailable')}</p>
      </div>
    );
  }

  const { metrics, coefficients, contributions, decomposition } = results;

  return (
    <PageWrapper className="flex flex-col">
      <Header
        title={`${model.name} - ${t('results.title')}`}
        projectName={project?.name}
        actions={
          <div className="flex gap-2">
            <Button 
              variant="outline" 
              onClick={() => navigate(`/projects/${projectId}/models/new?clone=${modelId}`)}
            >
              <Copy className="mr-2 h-4 w-4" />
              {t('results.cloneModel')}
            </Button>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline">
                  <Download className="mr-2 h-4 w-4" />
                  {t('results.export', 'Export')}
                  <ChevronDown className="ml-2 h-3 w-3" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={() => handleExport('excel')}>
                  <FileSpreadsheet className="mr-2 h-4 w-4" />
                  Excel (.xlsx)
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => handleExport('csv')}>
                  <FileText className="mr-2 h-4 w-4" />
                  CSV (.csv)
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => handleExport('pdf')}>
                  <FileType className="mr-2 h-4 w-4" />
                  PDF (.pdf)
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => handleExport('pptx')}>
                  <Presentation className="mr-2 h-4 w-4" />
                  PowerPoint (.pptx)
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => handleExport('json')}>
                  <FileCode className="mr-2 h-4 w-4" />
                  JSON (.json)
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => handleExport('html')}>
                  <FileText className="mr-2 h-4 w-4" />
                  HTML Report (.html)
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
            <Button variant="ghost" onClick={() => navigate(`/projects/${projectId}`)}>
              <ArrowLeft className="mr-2 h-4 w-4" />
              {t('results.back')}
            </Button>
          </div>
        }
      />

      <div className="p-6 space-y-6">
        {/* Metrics Overview */}
        <div className="grid gap-4 md:grid-cols-4">
          <MetricCard
            title={t('results.rSquared')}
            value={(metrics.r_squared * 100).toFixed(1) + '%'}
            description={t('results.varianceExplained')}
            icon={TrendingUp}
            good={metrics.r_squared > 0.7}
          />
          <MetricCard
            title={t('results.adjRSquared')}
            value={(metrics.adj_r_squared * 100).toFixed(1) + '%'}
            description={t('results.adjustedForFeatures')}
            icon={TrendingUp}
            good={metrics.adj_r_squared > 0.65}
          />
          <MetricCard
            title={t('results.rmse')}
            value={metrics.rmse.toFixed(2)}
            description={t('results.rootMeanSquaredError')}
            icon={BarChart3}
          />
          <MetricCard
            title={t('results.mape')}
            value={metrics.mape > 1 ? metrics.mape.toFixed(1) + '%' : (metrics.mape * 100).toFixed(1) + '%'}
            description={t('results.meanAbsolutePercentError')}
            icon={BarChart3}
            good={metrics.mape < 0.1 || (metrics.mape > 1 && metrics.mape < 10)}
          />
        </div>

        {/* Charts Tabs */}
        <Tabs defaultValue="fit" className="w-full">
          <TabsList>
            <TabsTrigger value="fit">
              <LineChart className="mr-2 h-4 w-4" />
              {t('results.fitChart')}
            </TabsTrigger>
            <TabsTrigger value="decomposition">
              <BarChart3 className="mr-2 h-4 w-4" />
              {t('results.decomposition')}
            </TabsTrigger>
            <TabsTrigger value="contributions">
              <PieChart className="mr-2 h-4 w-4" />
              {t('results.contributions')}
            </TabsTrigger>
            <TabsTrigger value="coefficients">
              <BarChart3 className="mr-2 h-4 w-4" />
              {t('results.coefficients')}
            </TabsTrigger>
          </TabsList>

          <TabsContent value="fit" className="mt-4">
            <Card variant="glass">
              <CardHeader>
                <CardTitle>{t('results.modelFit')}</CardTitle>
                <CardDescription>
                  {t('results.actualVsFitted')}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <FitChart 
                  data={decomposition} 
                  labels={{
                    actual: t('results.actual'),
                    fitted: t('results.fitted'),
                    noData: t('results.noDataAvailable'),
                  }}
                />
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="decomposition" className="mt-4">
            <Card variant="glass">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle>{t('results.salesDecomposition')}</CardTitle>
                    <CardDescription>
                      {t('results.decompositionDesc')}
                    </CardDescription>
                  </div>
                  <ViewModeToggle value={viewMode} onChange={setViewMode} />
                </div>
              </CardHeader>
              <CardContent>
                <StackedDecompositionChart 
                  data={decomposition} 
                  viewMode={viewMode}
                  variableGroups={variableGroups}
                  labels={{
                    actual: t('results.actual'),
                    base: t('results.base'),
                    seasonality: t('results.seasonality'),
                    noData: t('results.noDataAvailable'),
                  }}
                />
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="contributions" className="mt-4">
            <Card variant="glass">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle>{t('results.channelContributions')}</CardTitle>
                    <CardDescription>
                      {t('results.contributionsDesc')}
                    </CardDescription>
                  </div>
                  <ViewModeToggle value={viewMode} onChange={setViewMode} />
                </div>
              </CardHeader>
              <CardContent>
                <ContributionsChart 
                  data={contributions} 
                  viewMode={viewMode}
                  variableGroups={variableGroups}
                  labels={{
                    contributionDetails: t('results.contributionDetails'),
                    base: t('results.base'),
                    seasonality: t('results.seasonality'),
                    noData: t('results.noDataAvailable'),
                  }}
                />
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="coefficients" className="mt-4">
            <Card variant="glass">
              <CardHeader>
                <CardTitle>{t('results.modelCoefficients')}</CardTitle>
                <CardDescription>
                  {t('results.coefficientsDesc')}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <CoefficientsTable 
                  data={coefficients} 
                  labels={{
                    variable: t('results.variable'),
                    coefficient: t('results.coefficient'),
                    stdError: t('results.stdError'),
                    tStatistic: t('results.tStatistic'),
                    pValue: t('results.pValue'),
                    significant: t('results.significant'),
                    yes: t('results.yes'),
                    no: t('results.no'),
                    noData: t('results.noDataAvailable'),
                  }}
                />
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </PageWrapper>
  );
}

function MetricCard({
  title,
  value,
  description,
  icon: Icon,
  good,
}: {
  title: string;
  value: string;
  description: string;
  icon: typeof TrendingUp;
  good?: boolean;
}) {
  const getStatusClasses = () => {
    if (good === true) return 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400';
    if (good === false) return 'bg-red-500/10 text-red-600 dark:text-red-400';
    return 'bg-primary/10 text-primary';
  };

  return (
    <Card variant="subtle" hover="lift" className="relative overflow-hidden">
      {/* Subtle top border accent instead of gradient */}
      <div className={`absolute inset-x-0 top-0 h-0.5 ${
        good === true ? 'bg-emerald-500' :
        good === false ? 'bg-red-500' :
        'bg-primary'
      }`} />
      <CardHeader className="flex flex-row items-center justify-between pb-2 pt-4">
        <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
        <div className={`flex h-8 w-8 items-center justify-center rounded-md ${getStatusClasses()}`}>
          <Icon className="h-4 w-4" />
        </div>
      </CardHeader>
      <CardContent className="pb-4">
        <div className={`text-2xl font-semibold tracking-tight tabular-nums ${
          good === true ? 'text-emerald-600 dark:text-emerald-400' :
          good === false ? 'text-red-600 dark:text-red-400' :
          'text-foreground'
        }`}>
          {value}
        </div>
        <p className="mt-1 text-xs text-muted-foreground">{description}</p>
      </CardContent>
    </Card>
  );
}

function ViewModeToggle({
  value,
  onChange
}: {
  value: 'variable' | 'group';
  onChange: (value: 'variable' | 'group') => void;
}) {
  return (
    <div className="flex rounded-xl glass-sm p-1 gap-1">
      <button
        onClick={() => onChange('variable')}
        className={`flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-lg transition-all duration-200 ${
          value === 'variable'
            ? 'bg-primary text-primary-foreground shadow-sm'
            : 'text-muted-foreground hover:text-foreground hover:bg-white/50 dark:hover:bg-white/10'
        }`}
      >
        <Variable className="h-3.5 w-3.5" />
        变量
      </button>
      <button
        onClick={() => onChange('group')}
        className={`flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-lg transition-all duration-200 ${
          value === 'group'
            ? 'bg-primary text-primary-foreground shadow-sm'
            : 'text-muted-foreground hover:text-foreground hover:bg-white/50 dark:hover:bg-white/10'
        }`}
      >
        <Users className="h-3.5 w-3.5" />
        分组
      </button>
    </div>
  );
}

// Helper function to aggregate contributions by group
function aggregateByGroup(
  contributions: ContributionResult[],
  variableGroups: VariableGroup[]
): ContributionResult[] {
  if (variableGroups.length === 0) return contributions;

  const groupedContributions: Record<string, { contribution: number; contribution_pct: number; roi?: number; variables: string[] }> = {};
  const ungroupedVariables: ContributionResult[] = [];

  // Create a map of variable -> group
  const variableToGroup: Record<string, string> = {};
  variableGroups.forEach(group => {
    group.variables.forEach(variable => {
      variableToGroup[variable] = group.name;
    });
  });

  // Aggregate contributions
  contributions.forEach(contrib => {
    const groupName = variableToGroup[contrib.variable];
    if (groupName) {
      if (!groupedContributions[groupName]) {
        groupedContributions[groupName] = {
          contribution: 0,
          contribution_pct: 0,
          variables: [],
        };
      }
      groupedContributions[groupName].contribution += contrib.contribution;
      groupedContributions[groupName].contribution_pct += contrib.contribution_pct;
      groupedContributions[groupName].variables.push(contrib.variable);
    } else {
      ungroupedVariables.push(contrib);
    }
  });

  // Convert to array
  const result: ContributionResult[] = Object.entries(groupedContributions).map(([name, data]) => ({
    variable: name,
    contribution: data.contribution,
    contribution_pct: data.contribution_pct,
  }));

  // Add ungrouped variables
  return [...result, ...ungroupedVariables];
}

// Helper function to aggregate decomposition data by group
function aggregateDecompositionByGroup(
  data: Array<{ date: string; actual: number; predicted: number; base: number; [key: string]: string | number }>,
  variableGroups: VariableGroup[]
): Array<{ date: string; actual: number; predicted: number; base: number; [key: string]: string | number }> {
  if (variableGroups.length === 0 || data.length === 0) return data;

  // Create a map of variable -> group
  const variableToGroup: Record<string, string> = {};
  variableGroups.forEach(group => {
    group.variables.forEach(variable => {
      variableToGroup[variable] = group.name;
    });
  });

  // Get all contribution keys (exclude date, actual, predicted, base)
  const excludeKeys = ['date', 'actual', 'predicted', 'base'];
  const contributionKeys = Object.keys(data[0]).filter(k => !excludeKeys.includes(k));

  return data.map(row => {
    const newRow: { date: string; actual: number; predicted: number; base: number; [key: string]: string | number } = {
      date: row.date,
      actual: row.actual,
      predicted: row.predicted,
      base: row.base,
    };

    const groupSums: Record<string, number> = {};
    
    contributionKeys.forEach(key => {
      const groupName = variableToGroup[key];
      const value = typeof row[key] === 'number' ? row[key] as number : 0;
      
      if (groupName) {
        groupSums[groupName] = (groupSums[groupName] || 0) + value;
      } else {
        // Keep ungrouped variables as-is
        newRow[key] = value;
      }
    });

    // Add grouped sums
    Object.entries(groupSums).forEach(([groupName, sum]) => {
      newRow[groupName] = sum;
    });

    return newRow;
  });
}

function FitChart({ data, labels }: {
  data: Array<{ date: string; actual: number; predicted: number; base: number; [key: string]: string | number }>;
  labels: { actual: string; fitted: string; noData: string };
}) {
  const { theme } = useUIStore();
  const chartTheme = getChartTheme(theme === 'dark');

  if (!data || data.length === 0) {
    return (
      <div className="flex h-[400px] items-center justify-center">
        <p className="text-muted-foreground">{labels.noData}</p>
      </div>
    );
  }

  const dates = data.map((d) => d.date);
  const actual = data.map((d) => d.actual);
  const predicted = data.map((d) => d.predicted);

  const option = {
    ...chartTheme,
    tooltip: {
      ...chartTheme.tooltip,
      trigger: 'axis',
    },
    legend: {
      ...chartTheme.legend,
      data: [labels.actual, labels.fitted],
      bottom: 0,
    },
    grid: {
      ...chartTheme.grid,
      bottom: '15%',
    },
    xAxis: {
      ...chartTheme.xAxis,
      type: 'category',
      boundaryGap: false,
      data: dates,
    },
    yAxis: {
      ...chartTheme.yAxis,
      type: 'value',
    },
    series: [
      {
        ...lineSeriesDefaults,
        name: labels.actual,
        data: actual,
        itemStyle: { color: CHART_COLORS.primary },
        lineStyle: { width: 2.5 },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(59, 130, 246, 0.15)' },
              { offset: 1, color: 'rgba(59, 130, 246, 0.02)' },
            ],
          },
        },
      },
      {
        ...lineSeriesDefaults,
        name: labels.fitted,
        data: predicted,
        itemStyle: { color: CHART_COLORS.purple },
        lineStyle: { width: 2.5, type: 'dashed' },
      },
    ],
  };

  return <ReactECharts option={option} style={{ height: '400px' }} />;
}

function StackedDecompositionChart({
  data,
  viewMode = 'variable',
  variableGroups = [],
  labels
}: {
  data: Array<{ date: string; actual: number; predicted: number; base: number; [key: string]: string | number }>;
  viewMode?: 'variable' | 'group';
  variableGroups?: VariableGroup[];
  labels: { actual: string; base: string; seasonality: string; noData: string };
}) {
  const { theme } = useUIStore();
  const chartTheme = getChartTheme(theme === 'dark');
  const isDark = theme === 'dark';

  if (!data || data.length === 0) {
    return (
      <div className="flex h-[400px] items-center justify-center">
        <p className="text-muted-foreground">{labels.noData}</p>
      </div>
    );
  }

  // Apply grouping if in group mode
  const displayData = viewMode === 'group' && variableGroups.length > 0
    ? aggregateDecompositionByGroup(data, variableGroups)
    : data;

  const dates = displayData.map((d) => d.date);
  const actual = displayData.map((d) => d.actual);

  // Get all contribution keys (exclude date, actual, predicted - include base and all channels)
  const excludeKeys = ['date', 'actual', 'predicted'];
  const contributionKeys = Object.keys(displayData[0]).filter(k => !excludeKeys.includes(k));

  // Sort so base comes first, and translate special keys
  const sortedKeys = contributionKeys.sort((a, b) => {
    if (a === 'base') return -1;
    if (b === 'base') return 1;
    return a.localeCompare(b);
  });

  // Translate special keys for display
  const translateKey = (key: string) => {
    if (key === 'base') return labels.base;
    if (key === 'seasonality') return labels.seasonality;
    return key;
  };

  // Enhanced colors with base being neutral
  const baseColor = isDark ? 'hsl(215, 20%, 35%)' : 'hsl(215, 20%, 70%)';
  const stackColors = [baseColor, ...CHART_COLOR_PALETTE];

  const series = [
    // Actual sales line (overlay, not stacked)
    {
      ...lineSeriesDefaults,
      name: labels.actual,
      data: actual,
      lineStyle: { width: 3, color: isDark ? 'hsl(210, 40%, 98%)' : 'hsl(222, 47%, 11%)' },
      itemStyle: { color: isDark ? 'hsl(210, 40%, 98%)' : 'hsl(222, 47%, 11%)' },
      symbol: 'circle',
      symbolSize: 6,
      z: 10,
    },
    // Stacked area for contributions
    ...sortedKeys.map((key, i) => ({
      ...areaSeriesDefaults,
      name: translateKey(key),
      data: displayData.map((d) => typeof d[key] === 'number' ? d[key] : 0),
      itemStyle: { color: stackColors[i % stackColors.length] },
      areaStyle: { opacity: 0.75 },
    })),
  ];

  const option = {
    ...chartTheme,
    tooltip: {
      ...chartTheme.tooltip,
      trigger: 'axis',
      axisPointer: { type: 'cross', ...chartTheme.axisPointer },
    },
    legend: {
      ...chartTheme.legend,
      data: [labels.actual, ...sortedKeys.map(translateKey)],
      bottom: 0,
      type: 'scroll',
    },
    grid: {
      ...chartTheme.grid,
      bottom: '15%',
    },
    xAxis: {
      ...chartTheme.xAxis,
      type: 'category',
      boundaryGap: false,
      data: dates,
    },
    yAxis: {
      ...chartTheme.yAxis,
      type: 'value',
    },
    series,
  };

  return <ReactECharts option={option} style={{ height: '400px' }} />;
}

function ContributionsChart({ 
  data,
  viewMode = 'variable',
  variableGroups = [],
  labels
}: { 
  data: ContributionResult[];
  viewMode?: 'variable' | 'group';
  variableGroups?: VariableGroup[];
  labels: { contributionDetails: string; base: string; seasonality: string; noData: string };
}) {
  if (!data || data.length === 0) {
    return <p className="text-center text-muted-foreground py-8">{labels.noData}</p>;
  }

  // Apply grouping if in group mode
  const displayData = viewMode === 'group' && variableGroups.length > 0
    ? aggregateByGroup(data, variableGroups)
    : data;

  // Normalize contributions to sum to 100%
  const totalAbsContribution = displayData.reduce((sum, d) => sum + Math.abs(d.contribution_pct), 0);
  const normalizedData = displayData.map((d) => ({
    ...d,
    normalized_pct: totalAbsContribution > 0 ? (Math.abs(d.contribution_pct) / totalAbsContribution) * 100 : 0,
  }));

  const pieData = normalizedData.map((d) => ({
    name: d.variable,
    value: d.normalized_pct,
  }));

  const option = {
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {d}%',
    },
    legend: {
      orient: 'vertical',
      right: '5%',
      top: 'center',
    },
    series: [
      {
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['40%', '50%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 4,
          borderColor: '#fff',
          borderWidth: 2,
        },
        label: {
          show: false,
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 14,
            fontWeight: 'bold',
          },
        },
        data: pieData,
      },
    ],
  };

  // Translate variable names for display
  const translateVariable = (name: string) => {
    if (name === 'base') return labels.base;
    if (name === 'seasonality') return labels.seasonality;
    return name;
  };

  return (
    <div className="grid md:grid-cols-2 gap-4">
      <ReactECharts option={option} style={{ height: '350px' }} />
      <div className="space-y-2">
        <h4 className="font-medium mb-3">{labels.contributionDetails}</h4>
        {normalizedData.map((item) => (
          <div key={item.variable} className="flex items-center justify-between py-2 border-b border-border/50">
            <span className="font-medium text-sm">{translateVariable(item.variable)}</span>
            <div className="text-right">
              <span className="text-base font-semibold tabular-nums">
                {item.normalized_pct.toFixed(1)}%
              </span>
              {item.roi && (
                <span className="ml-2 text-xs text-muted-foreground tabular-nums">
                  ROI: {item.roi.toFixed(2)}x
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function CoefficientsTable({ data, labels }: { 
  data: CoefficientResult[];
  labels: { variable: string; coefficient: string; stdError: string; tStatistic: string; pValue: string; significant: string; yes: string; no: string; noData: string };
}) {
  if (!data || data.length === 0) {
    return <p className="text-center text-muted-foreground py-8">{labels.noData}</p>;
  }

  // Safe number formatting helper
  const formatNumber = (val: number | undefined | null, decimals: number = 4): string => {
    if (val === undefined || val === null || isNaN(val)) return '-';
    return val.toFixed(decimals);
  };

  return (
    <div className="overflow-x-auto rounded-lg border border-border/50">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b bg-muted/30">
            <th className="px-4 py-2.5 text-left text-xs font-semibold text-muted-foreground tracking-tight">{labels.variable}</th>
            <th className="px-4 py-2.5 text-right text-xs font-semibold text-muted-foreground tracking-tight">{labels.coefficient}</th>
            <th className="px-4 py-2.5 text-right text-xs font-semibold text-muted-foreground tracking-tight">{labels.stdError}</th>
            <th className="px-4 py-2.5 text-right text-xs font-semibold text-muted-foreground tracking-tight">{labels.tStatistic}</th>
            <th className="px-4 py-2.5 text-right text-xs font-semibold text-muted-foreground tracking-tight">{labels.pValue}</th>
            <th className="px-4 py-2.5 text-center text-xs font-semibold text-muted-foreground tracking-tight">{labels.significant}</th>
          </tr>
        </thead>
        <tbody>
          {data.map((coef, index) => (
            <tr key={coef.variable || index} className={`transition-colors hover:bg-muted/30 ${index % 2 === 0 ? '' : 'bg-muted/10'}`}>
              <td className="px-4 py-2 font-medium text-sm">{coef.variable || '-'}</td>
              <td className="px-4 py-2 text-right font-mono text-sm tabular-nums">
                {formatNumber(coef.coefficient)}
              </td>
              <td className="px-4 py-2 text-right font-mono text-sm tabular-nums text-muted-foreground">
                {formatNumber(coef.std_error)}
              </td>
              <td className="px-4 py-2 text-right font-mono text-sm tabular-nums">
                {formatNumber(coef.t_statistic, 2)}
              </td>
              <td className="px-4 py-2 text-right font-mono text-sm tabular-nums">
                {coef.p_value !== undefined && coef.p_value !== null
                  ? (coef.p_value < 0.001 ? '<0.001' : formatNumber(coef.p_value, 3))
                  : '-'}
              </td>
              <td className="px-4 py-2 text-center">
                {coef.significant ? (
                  <span className="inline-flex items-center gap-1 rounded-md bg-emerald-500/10 px-2 py-0.5 text-xs font-medium text-emerald-600 dark:text-emerald-400">
                    <CheckCircle2 className="h-3 w-3" />
                    {labels.yes}
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 rounded-md bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground">
                    <XCircle className="h-3 w-3" />
                    {labels.no}
                  </span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
