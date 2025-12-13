import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { explorationApi } from '@/api/services';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Loader2, BarChart3, GitBranch, AlertTriangle, TrendingUp } from 'lucide-react';

interface DataExplorationProps {
  projectId: string;
  datasetId: string;
}

export function DataExploration({ projectId, datasetId }: DataExplorationProps) {
  const { t } = useTranslation();
  const [selectedColumn, setSelectedColumn] = useState<string>('');

  const { data: summary, isLoading: summaryLoading, error: summaryError } = useQuery({
    queryKey: ['exploration-summary', projectId, datasetId],
    queryFn: () => explorationApi.getSummary(projectId, datasetId),
    retry: 1,
  });

  const { data: correlations, isLoading: correlationsLoading } = useQuery({
    queryKey: ['exploration-correlations', projectId, datasetId],
    queryFn: () => explorationApi.getCorrelations(projectId, datasetId),
    enabled: !!summary && summary.numeric_columns.length >= 2,
    retry: 1,
  });

  const { data: missing, isLoading: missingLoading } = useQuery({
    queryKey: ['exploration-missing', projectId, datasetId],
    queryFn: () => explorationApi.getMissingAnalysis(projectId, datasetId),
    retry: 1,
  });

  const { data: distribution, isLoading: distributionLoading } = useQuery({
    queryKey: ['exploration-distribution', projectId, datasetId, selectedColumn],
    queryFn: () => explorationApi.getDistribution(projectId, datasetId, selectedColumn),
    enabled: !!selectedColumn,
    retry: 1,
  });

  if (summaryLoading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          <span className="ml-2 text-muted-foreground">{t('common.loading')}</span>
        </CardContent>
      </Card>
    );
  }

  if (summaryError || !summary) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BarChart3 className="h-5 w-5" />
            {t('datasets.exploration.title')}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-center text-muted-foreground py-4">
            {t('datasets.exploration.loadError')}
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <BarChart3 className="h-5 w-5" />
          {t('datasets.exploration.title')}
        </CardTitle>
        <CardDescription>{t('datasets.exploration.description')}</CardDescription>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="overview" className="w-full">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="overview">{t('datasets.exploration.overview')}</TabsTrigger>
            <TabsTrigger value="distribution">{t('datasets.exploration.distribution')}</TabsTrigger>
            <TabsTrigger value="correlations">{t('datasets.exploration.correlations')}</TabsTrigger>
            <TabsTrigger value="missing">{t('datasets.exploration.missing')}</TabsTrigger>
          </TabsList>

          {/* Overview Tab */}
          <TabsContent value="overview" className="space-y-4 mt-4">
            {summary && (
              <>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="p-4 rounded-lg border">
                    <p className="text-sm text-muted-foreground">{t('datasets.rows')}</p>
                    <p className="text-2xl font-bold">{summary.n_rows.toLocaleString()}</p>
                  </div>
                  <div className="p-4 rounded-lg border">
                    <p className="text-sm text-muted-foreground">{t('datasets.columns')}</p>
                    <p className="text-2xl font-bold">{summary.n_columns}</p>
                  </div>
                  <div className="p-4 rounded-lg border">
                    <p className="text-sm text-muted-foreground">{t('datasets.exploration.memoryUsage')}</p>
                    <p className="text-2xl font-bold">{summary.memory_mb.toFixed(2)} MB</p>
                  </div>
                  <div className="p-4 rounded-lg border">
                    <p className="text-sm text-muted-foreground">{t('datasets.exploration.missingValues')}</p>
                    <p className="text-2xl font-bold">{summary.total_missing_pct.toFixed(1)}%</p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="p-4 rounded-lg border">
                    <p className="text-sm font-medium mb-2">{t('datasets.exploration.numericColumns')}</p>
                    <div className="flex flex-wrap gap-1">
                      {summary.numeric_columns.map((col) => (
                        <span key={col} className="px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded">
                          {col}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="p-4 rounded-lg border">
                    <p className="text-sm font-medium mb-2">{t('datasets.exploration.categoricalColumns')}</p>
                    <div className="flex flex-wrap gap-1">
                      {summary.categorical_columns.map((col) => (
                        <span key={col} className="px-2 py-1 text-xs bg-green-100 text-green-800 rounded">
                          {col}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="p-4 rounded-lg border">
                    <p className="text-sm font-medium mb-2">{t('datasets.exploration.datetimeColumns')}</p>
                    <div className="flex flex-wrap gap-1">
                      {summary.datetime_columns.map((col) => (
                        <span key={col} className="px-2 py-1 text-xs bg-purple-100 text-purple-800 rounded">
                          {col}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              </>
            )}
          </TabsContent>

          {/* Distribution Tab */}
          <TabsContent value="distribution" className="space-y-4 mt-4">
            <div className="flex items-center gap-4">
              <Select value={selectedColumn} onValueChange={setSelectedColumn}>
                <SelectTrigger className="w-64">
                  <SelectValue placeholder={t('datasets.exploration.selectColumn')} />
                </SelectTrigger>
                <SelectContent>
                  {summary?.columns.map((col) => (
                    <SelectItem key={col.name} value={col.name}>
                      {col.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {distributionLoading && (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin" />
              </div>
            )}

            {distribution && !distributionLoading && (
              <div className="space-y-4">
                {distribution.histogram && (
                  <div className="p-4 rounded-lg border">
                    <p className="text-sm font-medium mb-2">{t('datasets.exploration.histogram')}</p>
                    <div className="h-32 flex items-end gap-0.5">
                      {distribution.histogram.counts.map((count, i) => {
                        const maxCount = Math.max(...distribution.histogram!.counts);
                        const height = maxCount > 0 ? (count / maxCount) * 100 : 0;
                        return (
                          <div
                            key={i}
                            className="flex-1 bg-blue-500 rounded-t"
                            style={{ height: `${height}%` }}
                            title={`${count} values`}
                          />
                        );
                      })}
                    </div>
                  </div>
                )}

                {distribution.outliers && (
                  <div className="p-4 rounded-lg border">
                    <p className="text-sm font-medium mb-2 flex items-center gap-2">
                      <AlertTriangle className="h-4 w-4 text-yellow-500" />
                      {t('datasets.exploration.outliers')}
                    </p>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                      <div>
                        <p className="text-muted-foreground">{t('datasets.exploration.count')}</p>
                        <p className="font-medium">{distribution.outliers.count}</p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">{t('datasets.exploration.percentage')}</p>
                        <p className="font-medium">{distribution.outliers.pct.toFixed(2)}%</p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">{t('datasets.exploration.lowerBound')}</p>
                        <p className="font-medium">{distribution.outliers.lower_bound.toFixed(2)}</p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">{t('datasets.exploration.upperBound')}</p>
                        <p className="font-medium">{distribution.outliers.upper_bound.toFixed(2)}</p>
                      </div>
                    </div>
                  </div>
                )}

                {distribution.value_counts && (
                  <div className="p-4 rounded-lg border">
                    <p className="text-sm font-medium mb-2">{t('datasets.exploration.valueCounts')}</p>
                    <div className="space-y-2">
                      {distribution.value_counts.slice(0, 10).map((vc) => (
                        <div key={vc.value} className="flex items-center gap-2">
                          <div className="flex-1">
                            <div className="flex justify-between text-sm">
                              <span>{vc.value}</span>
                              <span className="text-muted-foreground">{vc.count} ({vc.pct.toFixed(1)}%)</span>
                            </div>
                            <div className="h-2 bg-muted rounded-full overflow-hidden">
                              <div
                                className="h-full bg-blue-500"
                                style={{ width: `${vc.pct}%` }}
                              />
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </TabsContent>

          {/* Correlations Tab */}
          <TabsContent value="correlations" className="space-y-4 mt-4">
            {correlationsLoading && (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin" />
              </div>
            )}

            {correlations && !correlationsLoading && (
              <>
                {correlations.significant_pairs.length > 0 ? (
                  <div className="space-y-4">
                    <p className="text-sm font-medium flex items-center gap-2">
                      <GitBranch className="h-4 w-4" />
                      {t('datasets.exploration.significantCorrelations')}
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
                ) : (
                  <p className="text-center text-muted-foreground py-8">
                    {t('datasets.exploration.noSignificantCorrelations')}
                  </p>
                )}
              </>
            )}

            {summary && summary.numeric_columns.length < 2 && (
              <p className="text-center text-muted-foreground py-8">
                {t('datasets.exploration.needTwoNumericColumns')}
              </p>
            )}
          </TabsContent>

          {/* Missing Values Tab */}
          <TabsContent value="missing" className="space-y-4 mt-4">
            {missingLoading && (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin" />
              </div>
            )}

            {missing && !missingLoading && (
              <>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="p-4 rounded-lg border">
                    <p className="text-sm text-muted-foreground">{t('datasets.exploration.totalMissing')}</p>
                    <p className="text-2xl font-bold">{missing.total_missing.toLocaleString()}</p>
                  </div>
                  <div className="p-4 rounded-lg border">
                    <p className="text-sm text-muted-foreground">{t('datasets.exploration.missingPercent')}</p>
                    <p className="text-2xl font-bold">{missing.total_missing_pct.toFixed(2)}%</p>
                  </div>
                  <div className="p-4 rounded-lg border">
                    <p className="text-sm text-muted-foreground">{t('datasets.exploration.completeRows')}</p>
                    <p className="text-2xl font-bold">{missing.complete_rows.toLocaleString()}</p>
                  </div>
                  <div className="p-4 rounded-lg border">
                    <p className="text-sm text-muted-foreground">{t('datasets.exploration.completePercent')}</p>
                    <p className="text-2xl font-bold">{missing.complete_rows_pct.toFixed(1)}%</p>
                  </div>
                </div>

                {missing.columns.filter((c) => c.missing > 0).length > 0 && (
                  <div className="p-4 rounded-lg border">
                    <p className="text-sm font-medium mb-3">{t('datasets.exploration.columnsWithMissing')}</p>
                    <div className="space-y-2">
                      {missing.columns
                        .filter((c) => c.missing > 0)
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
                )}

                {missing.columns.filter((c) => c.missing > 0).length === 0 && (
                  <div className="text-center py-8">
                    <TrendingUp className="h-10 w-10 mx-auto text-green-500 mb-2" />
                    <p className="text-muted-foreground">{t('datasets.exploration.noMissingValues')}</p>
                  </div>
                )}
              </>
            )}
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}
