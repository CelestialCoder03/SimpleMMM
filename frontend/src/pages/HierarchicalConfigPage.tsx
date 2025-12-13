import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { datasetsApi, modelsApi, hierarchicalApi, projectsApi } from '@/api/services';
import { Header } from '@/components/layout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Slider } from '@/components/ui/slider';
import { ArrowLeft, Loader2, Layers, Info } from 'lucide-react';
import type { Dataset, ColumnMetadata } from '@/types';

export function HierarchicalConfigPage() {
  const { t } = useTranslation();
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  // Form state
  const [name, setName] = useState('');
  const [parentModelId, setParentModelId] = useState<string>('');
  const [datasetId, setDatasetId] = useState('');
  const [dimensionColumns, setDimensionColumns] = useState<string[]>([]);
  const [granularityType] = useState('region');
  const [modelType, setModelType] = useState('ridge');
  const [targetColumn, setTargetColumn] = useState('');
  const [dateColumn, setDateColumn] = useState('');
  const [inheritConstraints, setInheritConstraints] = useState(true);
  const [constraintRelaxation, setConstraintRelaxation] = useState(0.2);
  const [inheritPriors, setInheritPriors] = useState(true);
  const [priorWeight, setPriorWeight] = useState(0.5);
  const [minObservations, setMinObservations] = useState(30);

  // Fetch project for breadcrumb
  const { data: project } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => projectsApi.get(projectId!),
    enabled: !!projectId,
  });

  // Fetch datasets
  const { data: datasets = [] } = useQuery({
    queryKey: ['datasets', projectId],
    queryFn: () => datasetsApi.list(projectId!),
    enabled: !!projectId,
  });

  // Fetch models for parent selection
  const { data: models = [] } = useQuery({
    queryKey: ['models', projectId],
    queryFn: () => modelsApi.list(projectId!),
    enabled: !!projectId,
  });

  // Get selected dataset columns
  const selectedDataset = datasets.find((d: Dataset) => d.id === datasetId);
  const columns: ColumnMetadata[] = selectedDataset?.columns || [];
  const numericColumns = columns.filter((c) => c.dtype === 'numeric' || c.dtype === 'float64' || c.dtype === 'int64');
  const stringColumns = columns.filter((c) => c.dtype === 'object' || c.dtype === 'string' || c.dtype === 'category');
  const dateColumns = columns.filter((c) => c.dtype === 'datetime64[ns]' || c.name.toLowerCase().includes('date'));

  // Create mutation
  const createMutation = useMutation({
    mutationFn: () => hierarchicalApi.create(projectId!, {
      name,
      parent_model_id: parentModelId || undefined,
      dataset_id: datasetId,
      dimension_columns: dimensionColumns,
      granularity_type: granularityType,
      model_type: modelType,
      target_variable: targetColumn,
      date_column: dateColumn || undefined,
      inherit_constraints: inheritConstraints,
      constraint_relaxation: constraintRelaxation,
      inherit_priors: inheritPriors,
      prior_weight: priorWeight,
      min_observations: minObservations,
    }),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['hierarchical-models', projectId] });
      navigate(`/projects/${projectId}/hierarchical/${data.id}`);
    },
  });

  const canSubmit = name && datasetId && dimensionColumns.length > 0 && targetColumn;

  return (
    <div className="flex flex-col">
      <Header title={t('hierarchical.createTitle', '创建分层模型')} projectName={project?.name} />

      <div className="p-6 max-w-4xl mx-auto w-full space-y-6">
        {/* Back button */}
        <Button variant="ghost" onClick={() => navigate(`/projects/${projectId}`)}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          {t('common.back')}
        </Button>

        {/* Basic Settings */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Layers className="h-5 w-5" />
              {t('hierarchical.basicSettings', '基础设置')}
            </CardTitle>
            <CardDescription>
              {t('hierarchical.basicSettingsDesc', '配置分层模型的基本信息')}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>{t('hierarchical.modelName', '模型名称')}</Label>
              <Input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder={t('hierarchical.modelNamePlaceholder', '例如：区域分层模型')}
              />
            </div>

            <div className="space-y-2">
              <Label>{t('hierarchical.parentModel', '父模型（全国模型）')}</Label>
              <Select value={parentModelId || '_none'} onValueChange={(v) => setParentModelId(v === '_none' ? '' : v)}>
                <SelectTrigger>
                  <SelectValue placeholder={t('hierarchical.selectParentModel', '选择父模型（可选）')} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="_none">{t('common.none', '无')}</SelectItem>
                  {models.filter((m: { status: string }) => m.status === 'completed').map((m: { id: string; name: string }) => (
                    <SelectItem key={m.id} value={m.id}>{m.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                {t('hierarchical.parentModelDesc', '选择已训练的全国模型，其系数将作为子模型的约束/先验')}
              </p>
            </div>

            <div className="space-y-2">
              <Label>{t('models.dataset', '数据集')}</Label>
              <Select value={datasetId} onValueChange={setDatasetId}>
                <SelectTrigger>
                  <SelectValue placeholder={t('models.selectDataset', '选择数据集')} />
                </SelectTrigger>
                <SelectContent>
                  {datasets.map((ds: Dataset) => (
                    <SelectItem key={ds.id} value={ds.id}>
                      {ds.name} ({ds.row_count ?? '-'} rows)
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>{t('models.modelType', '模型类型')}</Label>
              <Select value={modelType} onValueChange={setModelType}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ols">{t('models.types.ols', 'OLS')}</SelectItem>
                  <SelectItem value="ridge">{t('models.types.ridge', 'Ridge')}</SelectItem>
                  <SelectItem value="bayesian">{t('models.types.bayesian', 'Bayesian')}</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        {/* Dimension Settings */}
        <Card>
          <CardHeader>
            <CardTitle>{t('hierarchical.dimensionSettings', '维度设置')}</CardTitle>
            <CardDescription>
              {t('hierarchical.dimensionSettingsDesc', '选择用于分层的维度列')}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>{t('hierarchical.dimensionColumns', '维度列')}</Label>
              <Select
                value={dimensionColumns[0] || ''}
                onValueChange={(v) => setDimensionColumns(v ? [v] : [])}
              >
                <SelectTrigger>
                  <SelectValue placeholder={t('hierarchical.selectDimensionColumn', '选择维度列')} />
                </SelectTrigger>
                <SelectContent>
                  {stringColumns.map((col) => (
                    <SelectItem key={col.name} value={col.name}>
                      {col.name} ({col.unique_count ?? '-'} unique values)
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                {t('hierarchical.dimensionColumnsDesc', '选择用于分割数据的维度列，如区域(region)或渠道(channel)')}
              </p>
            </div>

            <div className="space-y-2">
              <Label>{t('models.targetVariable', '目标变量')}</Label>
              <Select value={targetColumn} onValueChange={setTargetColumn}>
                <SelectTrigger>
                  <SelectValue placeholder={t('models.selectTargetVariable', '选择目标变量')} />
                </SelectTrigger>
                <SelectContent>
                  {numericColumns.map((col) => (
                    <SelectItem key={col.name} value={col.name}>{col.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>{t('models.dateColumn', '日期列')}</Label>
              <Select value={dateColumn} onValueChange={setDateColumn}>
                <SelectTrigger>
                  <SelectValue placeholder={t('models.selectDateColumn', '选择日期列')} />
                </SelectTrigger>
                <SelectContent>
                  {dateColumns.map((col) => (
                    <SelectItem key={col.name} value={col.name}>{col.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>{t('hierarchical.minObservations', '最小观测数')}</Label>
              <Input
                type="number"
                value={minObservations}
                onChange={(e) => setMinObservations(parseInt(e.target.value) || 30)}
                min={10}
              />
              <p className="text-xs text-muted-foreground">
                {t('hierarchical.minObservationsDesc', '每个子模型需要的最小数据行数')}
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Inheritance Settings */}
        {parentModelId && (
          <Card>
            <CardHeader>
              <CardTitle>{t('hierarchical.inheritanceSettings', '继承设置')}</CardTitle>
              <CardDescription>
                {t('hierarchical.inheritanceSettingsDesc', '配置如何从父模型继承约束或先验')}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {modelType !== 'bayesian' ? (
                <>
                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <Label>{t('hierarchical.inheritConstraints', '继承约束')}</Label>
                      <p className="text-xs text-muted-foreground">
                        {t('hierarchical.inheritConstraintsDesc', '使用父模型的系数置信区间作为子模型的约束')}
                      </p>
                    </div>
                    <Switch
                      checked={inheritConstraints}
                      onCheckedChange={setInheritConstraints}
                    />
                  </div>

                  {inheritConstraints && (
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <Label>{t('hierarchical.constraintRelaxation', '约束放宽比例')}</Label>
                        <span className="text-sm text-muted-foreground">{constraintRelaxation.toFixed(2)}</span>
                      </div>
                      <Slider
                        value={[constraintRelaxation]}
                        onValueChange={([v]) => setConstraintRelaxation(v)}
                        min={0}
                        max={1}
                        step={0.05}
                      />
                      <p className="text-xs text-muted-foreground">
                        {t('hierarchical.constraintRelaxationDesc', '0表示严格约束，1表示完全放宽')}
                      </p>
                    </div>
                  )}
                </>
              ) : (
                <>
                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <Label>{t('hierarchical.inheritPriors', '继承先验')}</Label>
                      <p className="text-xs text-muted-foreground">
                        {t('hierarchical.inheritPriorsDesc', '使用父模型的系数作为子模型的先验均值')}
                      </p>
                    </div>
                    <Switch
                      checked={inheritPriors}
                      onCheckedChange={setInheritPriors}
                    />
                  </div>

                  {inheritPriors && (
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <Label>{t('hierarchical.priorWeight', '先验权重')}</Label>
                        <span className="text-sm text-muted-foreground">{priorWeight.toFixed(2)}</span>
                      </div>
                      <Slider
                        value={[priorWeight]}
                        onValueChange={([v]) => setPriorWeight(v)}
                        min={0.1}
                        max={1}
                        step={0.05}
                      />
                      <p className="text-xs text-muted-foreground">
                        {t('hierarchical.priorWeightDesc', '权重越高，先验越紧（子模型系数越接近父模型）')}
                      </p>
                    </div>
                  )}
                </>
              )}

              <div className="bg-blue-50 dark:bg-blue-900/20 p-4 rounded-lg">
                <div className="flex items-start gap-2">
                  <Info className="h-4 w-4 mt-0.5 text-blue-500" />
                  <div className="text-sm text-blue-700 dark:text-blue-300">
                    {t('hierarchical.inheritanceInfo', '继承设置可以帮助子模型利用全国模型的知识，避免数据不足时的过拟合问题。')}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Submit */}
        <div className="flex justify-end gap-4">
          <Button variant="outline" onClick={() => navigate(`/projects/${projectId}`)}>
            {t('common.cancel')}
          </Button>
          <Button
            onClick={() => createMutation.mutate()}
            disabled={!canSubmit || createMutation.isPending}
          >
            {createMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {t('hierarchical.create', '创建分层模型')}
          </Button>
        </div>
      </div>
    </div>
  );
}

export default HierarchicalConfigPage;
