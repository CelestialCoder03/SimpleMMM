import { useState, useEffect } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { datasetsApi, modelsApi, projectsApi } from '@/api/services';
import { Header, PageWrapper } from '@/components/layout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Slider } from '@/components/ui/slider';
import { Switch } from '@/components/ui/switch';
import {
  ArrowLeft,
  ArrowRight,
  Loader2,
  CheckCircle2,
  Settings2,
  Database,
  Target,
  Sliders,
  Info,
} from 'lucide-react';
import type { Dataset, ModelType, FeatureConfig, ColumnMetadata } from '@/types';
import { 
  AdvancedConstraintsPanel, 
  type ConstraintsConfig,
} from '@/components/features/models/AdvancedConstraintsPanel';
import { TransformationPreview } from '@/components/features/models/TransformationPreview';
import { 
  SeasonalityPanel, 
  type SeasonalityConfig,
  DEFAULT_SEASONALITY_CONFIG,
} from '@/components/features/models/SeasonalityPanel';

type WizardStep = 'basics' | 'features' | 'transformations' | 'constraints' | 'review';

const STEPS: { id: WizardStep; labelKey: string; icon: typeof Database }[] = [
  { id: 'basics', labelKey: 'models.steps.basics', icon: Database },
  { id: 'features', labelKey: 'models.steps.features', icon: Target },
  { id: 'transformations', labelKey: 'models.steps.transformations', icon: Sliders },
  { id: 'constraints', labelKey: 'models.steps.constraints', icon: Settings2 },
  { id: 'review', labelKey: 'models.steps.review', icon: CheckCircle2 },
];

export function ModelConfigPage() {
  const { t } = useTranslation();
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [searchParams] = useSearchParams();
  const cloneModelId = searchParams.get('clone');

  const [currentStep, setCurrentStep] = useState<WizardStep>('basics');
  const [isCreated, setIsCreated] = useState(false);
  const [isCloneLoaded, setIsCloneLoaded] = useState(false);
  
  // Form state
  const [modelName, setModelName] = useState('');
  const [modelType, setModelType] = useState<ModelType>('ols');
  const [selectedDatasetId, setSelectedDatasetId] = useState('');
  const [dateColumn, setDateColumn] = useState('');
  const [targetColumn, setTargetColumn] = useState('');
  const [selectedFeatures, setSelectedFeatures] = useState<string[]>([]);
  const [featureConfigs, setFeatureConfigs] = useState<Record<string, FeatureConfig>>({});
  const [constraintsConfig, setConstraintsConfig] = useState<ConstraintsConfig>({
    applyPositiveToAll: true,
    coefficients: [],
    contributions: [],
    groupContributions: [],
  });
  
  // Bayesian priors state
  const [priorsConfig, setPriorsConfig] = useState<Record<string, {
    distribution: string;
    mu: number;
    sigma: number;
    lower?: number;
    upper?: number;
  }>>({});

  // Seasonality config state
  const [seasonalityConfig, setSeasonalityConfig] = useState<SeasonalityConfig>(DEFAULT_SEASONALITY_CONFIG);
  
  // Fetch project details for breadcrumb
  const { data: project } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => projectsApi.get(projectId!),
    enabled: !!projectId,
  });

  // Fetch source model for cloning
  const { data: sourceModel } = useQuery({
    queryKey: ['model', projectId, cloneModelId],
    queryFn: () => modelsApi.get(projectId!, cloneModelId!),
    enabled: !!projectId && !!cloneModelId,
  });

  // Pre-populate form when cloning - synchronous setState is intentional for one-time initialization
  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    if (sourceModel && !isCloneLoaded) {
      setModelName(`${sourceModel.name} (Copy)`);
      setModelType(sourceModel.model_type as ModelType);
      setSelectedDatasetId(sourceModel.dataset_id);
      setDateColumn(sourceModel.date_column || '');
      setTargetColumn(sourceModel.target_variable);
      
      // Extract feature columns and configs from features array
      if (sourceModel.features && Array.isArray(sourceModel.features)) {
        const featureCols = sourceModel.features.map((f: FeatureConfig) => f.column);
        setSelectedFeatures(featureCols);
        
        const configs: Record<string, FeatureConfig> = {};
        sourceModel.features.forEach((f: FeatureConfig) => {
          configs[f.column] = f;
        });
        setFeatureConfigs(configs);
      }
      
      // Handle constraints - map backend format to frontend format
      if (sourceModel.constraints) {
        const c = sourceModel.constraints as {
          apply_positive_to_all?: boolean;
          coefficients?: Array<{ variable: string; sign?: string; min?: number; max?: number }>;
          contributions?: Array<{ variable: string; min_contribution_pct?: number; max_contribution_pct?: number }>;
          group_contributions?: Array<{ name: string; variables: string[]; min_contribution_pct?: number; max_contribution_pct?: number }>;
        };
        setConstraintsConfig({
          applyPositiveToAll: c.apply_positive_to_all ?? true,
          coefficients: (c.coefficients || []).map((coef) => ({
            variable: coef.variable,
            sign: (coef.sign as 'positive' | 'negative') || 'none',
            min: coef.min,
            max: coef.max,
          })),
          contributions: (c.contributions || []).map((contrib) => ({
            variable: contrib.variable,
            minPct: contrib.min_contribution_pct,
            maxPct: contrib.max_contribution_pct,
          })),
          groupContributions: (c.group_contributions || []).map((group) => ({
            groupName: group.name,
            variables: group.variables || [],
            minPct: group.min_contribution_pct,
            maxPct: group.max_contribution_pct,
          })),
        });
      }
      
      // Handle priors for Bayesian models
      if (sourceModel.priors?.priors && Array.isArray(sourceModel.priors.priors)) {
        const priorConfigs: Record<string, { distribution: string; mu: number; sigma: number; lower?: number; upper?: number }> = {};
        sourceModel.priors.priors.forEach((p: { variable: string; distribution: string; params: { mu?: number; sigma?: number; lower?: number; upper?: number } }) => {
          priorConfigs[p.variable] = {
            distribution: p.distribution || 'normal',
            mu: p.params?.mu ?? 0,
            sigma: p.params?.sigma ?? 2,
            lower: p.params?.lower,
            upper: p.params?.upper,
          };
        });
        setPriorsConfig(priorConfigs);
      }
      
      // Handle seasonality config
      if (sourceModel.seasonality) {
        setSeasonalityConfig(prev => ({
          ...prev,
          enabled: sourceModel.seasonality?.enabled ?? false,
          method: sourceModel.seasonality?.method ?? 'calendar',
          calendar: {
            ...prev.calendar,
            ...sourceModel.seasonality?.calendar,
          },
          fourier: {
            ...prev.fourier,
            ...sourceModel.seasonality?.fourier,
          },
        }));
      }
      
      setIsCloneLoaded(true);
    }
  }, [sourceModel, isCloneLoaded]);
  /* eslint-enable react-hooks/set-state-in-effect */

  // Fetch datasets
  const { data: datasets = [] } = useQuery({
    queryKey: ['datasets', projectId],
    queryFn: () => datasetsApi.list(projectId!),
    enabled: !!projectId,
  });

  // Fetch selected dataset details
  const { data: selectedDataset } = useQuery({
    queryKey: ['dataset', projectId, selectedDatasetId],
    queryFn: () => datasetsApi.get(projectId!, selectedDatasetId),
    enabled: !!projectId && !!selectedDatasetId,
  });

  // Fetch dataset preview for transformation preview
  const { data: datasetPreview } = useQuery({
    queryKey: ['dataset-preview', projectId, selectedDatasetId],
    queryFn: () => datasetsApi.getPreview(projectId!, selectedDatasetId, 200),
    enabled: !!projectId && !!selectedDatasetId,
  });

  // Get actual column data from preview for transformation preview
  const getColumnData = (columnName: string): number[] => {
    if (!datasetPreview?.data) return [];
    return datasetPreview.data
      .map((row) => {
        const val = row[columnName];
        return typeof val === 'number' ? val : parseFloat(String(val));
      })
      .filter((v) => !isNaN(v));
  };

  const createMutation = useMutation({
    mutationFn: () =>
      modelsApi.create(projectId!, {
        dataset_id: selectedDatasetId,
        name: modelName,
        model_type: modelType,
        target_variable: targetColumn,
        date_column: dateColumn,
        features: selectedFeatures.map((col) => {
          const cfg = featureConfigs[col];
          return (
            cfg ?? {
              column: col,
              transformations: {
                adstock: { type: 'geometric', decay: 0.5, max_lag: 8 },
                saturation: { type: 'hill', k: 'auto', s: 'auto' },
              },
              enabled: true,
            }
          );
        }),
        constraints: modelType !== 'bayesian' ? {
          coefficients: constraintsConfig.coefficients.map((c) => ({
            variable: c.variable,
            sign: c.sign !== 'none' ? c.sign : undefined,
            min: c.min,
            max: c.max,
          })),
          contributions: constraintsConfig.contributions.map((c) => ({
            variable: c.variable,
            min_contribution_pct: c.minPct,
            max_contribution_pct: c.maxPct,
          })),
          group_contributions: constraintsConfig.groupContributions.map((c) => ({
            name: c.groupName,
            variables: c.variables || [],
            min_contribution_pct: c.minPct,
            max_contribution_pct: c.maxPct,
          })),
        } : undefined,
        // Bayesian priors
        priors: modelType === 'bayesian' ? {
          priors: selectedFeatures.map((feature) => {
            const prior = priorsConfig[feature] || { distribution: 'normal', mu: 0, sigma: 2 };
            return {
              variable: feature,
              distribution: prior.distribution,
              params: {
                mu: prior.mu,
                sigma: prior.sigma,
                ...(prior.lower !== undefined && { lower: prior.lower }),
                ...(prior.upper !== undefined && { upper: prior.upper }),
              },
            };
          }),
        } : undefined,
        // Seasonality auto-generation
        seasonality: seasonalityConfig.enabled ? seasonalityConfig : undefined,
      }),
    onSuccess: (model) => {
      queryClient.invalidateQueries({ queryKey: ['models', projectId] });
      setIsCreated(true);
      // Navigate to training page after a short delay to show success message
      setTimeout(() => {
        navigate(`/projects/${projectId}/models/${model.id}/training`);
      }, 1500);
    },
  });

  const numericColumns = selectedDataset?.columns?.filter(
    (col: ColumnMetadata) => col.dtype.includes('int') || col.dtype.includes('float')
  ) || [];

  const dateColumns = selectedDataset?.columns?.filter(
    (col: ColumnMetadata) => col.column_type === 'datetime' || col.dtype.includes('date') || col.dtype.includes('datetime')
  ) || [];

  const currentStepIndex = STEPS.findIndex((s) => s.id === currentStep);

  const goNext = () => {
    const nextIndex = currentStepIndex + 1;
    if (nextIndex < STEPS.length) {
      setCurrentStep(STEPS[nextIndex].id);
    }
  };

  const goPrev = () => {
    const prevIndex = currentStepIndex - 1;
    if (prevIndex >= 0) {
      setCurrentStep(STEPS[prevIndex].id);
    }
  };

  const canProceed = () => {
    switch (currentStep) {
      case 'basics':
        return modelName && modelType && selectedDatasetId;
      case 'features':
        return dateColumn && targetColumn && selectedFeatures.length > 0;
      case 'transformations':
        return true;
      case 'constraints':
        return true;
      case 'review':
        return true;
      default:
        return false;
    }
  };

  const toggleFeature = (column: string) => {
    setSelectedFeatures((prev) =>
      prev.includes(column)
        ? prev.filter((c) => c !== column)
        : [...prev, column]
    );
    
    // Initialize feature config if not exists - default transformations OFF
    if (!featureConfigs[column]) {
      setFeatureConfigs((prev) => ({
        ...prev,
        [column]: {
          column,
          transformations: {
            adstock: { type: 'geometric', decay: 0.5, max_lag: 8, enabled: false },
            saturation: { type: 'hill', k: 'auto', s: 'auto', enabled: false },
          },
          enabled: true,
        },
      }));
    }
  };

  const updateFeatureConfig = (column: string, config: Partial<FeatureConfig>) => {
    setFeatureConfigs((prev) => ({
      ...prev,
      [column]: { ...prev[column], ...config },
    }));
  };

  return (
    <PageWrapper className="flex flex-col">
      <Header
        title={t('models.createModel')}
        projectName={project?.name}
        actions={
          <Button variant="ghost" onClick={() => navigate(`/projects/${projectId}`)}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            {t('common.cancel')}
          </Button>
        }
      />

      <div className="mx-auto w-full max-w-4xl p-6">
        {/* Progress Steps */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            {STEPS.map((step, index) => (
              <div
                key={step.id}
                className="flex flex-1 items-center"
              >
                <div
                  className={`flex items-center gap-2 ${
                    index <= currentStepIndex
                      ? 'text-primary'
                      : 'text-muted-foreground'
                  }`}
                >
                  <div
                    className={`flex h-8 w-8 items-center justify-center rounded-full border-2 transition-all duration-300 ${
                      index < currentStepIndex
                        ? 'border-primary bg-gradient-primary text-white shadow-md'
                        : index === currentStepIndex
                          ? 'border-primary bg-primary/10'
                          : 'border-muted-foreground/30'
                    }`}
                  >
                    {index < currentStepIndex ? (
                      <CheckCircle2 className="h-4 w-4" />
                    ) : (
                      <step.icon className="h-4 w-4" />
                    )}
                  </div>
                  <span className="hidden text-sm font-medium md:block">
                    {t(step.labelKey)}
                  </span>
                </div>
                {index < STEPS.length - 1 && (
                  <div
                    className={`mx-4 h-0.5 flex-1 ${
                      index < currentStepIndex ? 'bg-primary' : 'bg-muted'
                    }`}
                  />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Step Content */}
        <Card variant="glass">
          <CardContent className="p-6">
            {/* Step 1: Basics */}
            {currentStep === 'basics' && (
              <div className="space-y-6">
                <div>
                  <CardTitle>{t('models.basicConfiguration')}</CardTitle>
                  <CardDescription className="mt-1">
                    {t('models.basicConfigurationDesc')}
                  </CardDescription>
                </div>

                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="model-name">{t('models.modelName')}</Label>
                    <Input
                      id="model-name"
                      placeholder={t('models.modelNamePlaceholder')}
                      value={modelName}
                      onChange={(e) => setModelName(e.target.value)}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label>{t('models.modelType')}</Label>
                    <Select value={modelType} onValueChange={(v) => setModelType(v as ModelType)}>
                      <SelectTrigger>
                        <SelectValue placeholder={t('models.selectModelType')} />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="ols">{t('models.types.ols')}</SelectItem>
                        <SelectItem value="ridge">{t('models.types.ridge')}</SelectItem>
                        <SelectItem value="bayesian">{t('models.types.bayesian')}</SelectItem>
                      </SelectContent>
                    </Select>
                    <p className="text-xs text-muted-foreground">
                      {modelType === 'ols' && t('models.types.olsDesc')}
                      {modelType === 'ridge' && t('models.types.ridgeDesc')}
                      {modelType === 'bayesian' && t('models.types.bayesianDesc')}
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label>{t('models.dataset')}</Label>
                    <Select value={selectedDatasetId} onValueChange={setSelectedDatasetId}>
                      <SelectTrigger>
                        <SelectValue placeholder={t('models.selectDataset')} />
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
                </div>
              </div>
            )}

            {/* Step 2: Features */}
            {currentStep === 'features' && (
              <div className="space-y-6">
                <div>
                  <CardTitle>{t('models.selectVariables')}</CardTitle>
                  <CardDescription className="mt-1">
                    {t('models.selectVariablesDesc')}
                  </CardDescription>
                </div>

                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label>{t('models.dateColumn')}</Label>
                    <Select value={dateColumn} onValueChange={setDateColumn}>
                      <SelectTrigger>
                        <SelectValue placeholder={t('models.selectDateColumn')} />
                      </SelectTrigger>
                      <SelectContent>
                        {dateColumns.map((col: ColumnMetadata) => (
                          <SelectItem key={col.name} value={col.name}>
                            {col.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <p className="text-xs text-muted-foreground">
                      {t('models.dateColumnDesc')}
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label>{t('models.targetVariable')}</Label>
                    <Select value={targetColumn} onValueChange={setTargetColumn}>
                      <SelectTrigger>
                        <SelectValue placeholder={t('models.selectTargetColumn')} />
                      </SelectTrigger>
                      <SelectContent>
                        {numericColumns.map((col: ColumnMetadata) => (
                          <SelectItem key={col.name} value={col.name}>
                            {col.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <p className="text-xs text-muted-foreground">
                      {t('models.targetVariableDesc')}
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label>{t('models.marketingFeatures')}</Label>
                    <p className="text-xs text-muted-foreground mb-2">
                      {t('models.marketingFeaturesDesc')}
                    </p>
                    <div className="max-h-64 space-y-2 overflow-y-auto rounded-lg border p-3">
                      {numericColumns
                        .filter((col: ColumnMetadata) => col.name !== targetColumn)
                        .map((col: ColumnMetadata) => (
                          <label
                            key={col.name}
                            className="flex cursor-pointer items-center justify-between rounded-lg p-2 hover:bg-muted"
                          >
                            <div className="flex items-center gap-3">
                              <input
                                type="checkbox"
                                checked={selectedFeatures.includes(col.name)}
                                onChange={() => toggleFeature(col.name)}
                                className="h-4 w-4 rounded border-input"
                              />
                              <span className="font-medium">{col.name}</span>
                            </div>
                            <span className="text-sm text-muted-foreground">
                              {col.dtype}
                            </span>
                          </label>
                        ))}
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {t('models.featuresSelected', { count: selectedFeatures.length })}
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Step 3: Transformations */}
            {currentStep === 'transformations' && (
              <div className="space-y-6">
                <div>
                  <CardTitle>{t('models.configureTransformations')}</CardTitle>
                  <CardDescription className="mt-1">
                    {t('models.configureTransformationsDesc')}
                  </CardDescription>
                </div>

                {selectedFeatures.length === 0 ? (
                  <p className="text-center text-muted-foreground py-8">
                    {t('models.noFeaturesSelected')}
                  </p>
                ) : (
                  <Tabs defaultValue={selectedFeatures[0]} className="w-full">
                    <TabsList className="w-full justify-start overflow-x-auto">
                      {selectedFeatures.map((feature) => (
                        <TabsTrigger key={feature} value={feature} className="min-w-max">
                          {feature}
                        </TabsTrigger>
                      ))}
                    </TabsList>

                    {selectedFeatures.map((feature) => {
                      const config = featureConfigs[feature] || {
                        column: feature,
                        transformations: {
                          adstock: { type: 'geometric', decay: 0.5, max_lag: 8, enabled: false },
                          saturation: { type: 'hill', k: 'auto', s: 'auto', enabled: false },
                        },
                        enabled: true,
                      };

                      const adstockEnabled = config.transformations?.adstock?.enabled ?? false;
                      const saturationEnabled = config.transformations?.saturation?.enabled ?? false;

                      const adstock = config.transformations?.adstock;
                      const saturation = config.transformations?.saturation;

                      // Convert decay to number (handle 'auto' case)
                      const decayValue = typeof adstock?.decay === 'number' ? adstock.decay : 0.5;

                      return (
                        <TabsContent key={feature} value={feature} className="space-y-6 mt-4">
                          {/* Transformation Preview */}
                          <TransformationPreview
                            featureName={feature}
                            originalData={getColumnData(feature).length > 0 ? getColumnData(feature) : [0.1, 0.2, 0.3, 0.4, 0.5]}
                            adstock={{
                              type: adstock?.type ?? 'geometric',
                              decay: decayValue,
                              max_lag: adstock?.max_lag ?? 8,
                            }}
                            saturation={{
                              type: saturation?.type ?? 'hill',
                              k: saturation?.k ?? 'auto',
                              s: saturation?.s ?? 'auto',
                            }}
                            adstockEnabled={adstockEnabled}
                            saturationEnabled={saturationEnabled}
                          />

                          {/* Adstock */}
                          <Card variant="glass-subtle">
                            <CardHeader className="pb-3">
                              <div className="flex items-center justify-between">
                                <div>
                                  <CardTitle className="text-base">{t('models.adstock')}</CardTitle>
                                  <CardDescription>
                                    {t('models.adstockDesc')}
                                  </CardDescription>
                                </div>
                                <Switch
                                  checked={adstockEnabled}
                                  onCheckedChange={(checked) =>
                                    updateFeatureConfig(feature, {
                                      transformations: {
                                        ...config.transformations,
                                        adstock: { ...(adstock ?? { type: 'geometric', decay: 0.5, max_lag: 8 }), enabled: checked },
                                      },
                                    })
                                  }
                                />
                              </div>
                            </CardHeader>
                            <CardContent className={`space-y-4 ${!adstockEnabled ? 'opacity-50 pointer-events-none' : ''}`}>
                              <div className="space-y-2">
                                <div className="flex items-center justify-between">
                                  <Label>{t('models.decayRate')}</Label>
                                  <span className="text-sm font-medium">
                                    {decayValue.toFixed(2)}
                                  </span>
                                </div>
                                <Slider
                                  value={[decayValue]}
                                  min={0}
                                  max={1}
                                  step={0.05}
                                  onValueChange={([v]) =>
                                    updateFeatureConfig(feature, {
                                      transformations: {
                                        ...config.transformations,
                                        adstock: { ...(adstock ?? { type: 'geometric', decay: 0.5, max_lag: 8 }), decay: v },
                                      },
                                    })
                                  }
                                />
                                <p className="text-xs text-muted-foreground">
                                  {t('models.decayRateDesc')}
                                </p>
                              </div>

                              <div className="space-y-2">
                                <div className="flex items-center justify-between">
                                  <Label>{t('models.maxLag')}</Label>
                                  <span className="text-sm font-medium">
                                    {adstock?.max_lag ?? 8}
                                  </span>
                                </div>
                                <Slider
                                  value={[adstock?.max_lag ?? 8]}
                                  min={1}
                                  max={26}
                                  step={1}
                                  onValueChange={([v]) =>
                                    updateFeatureConfig(feature, {
                                      transformations: {
                                        ...config.transformations,
                                        adstock: { ...(adstock ?? { type: 'geometric', decay: 0.5, max_lag: 8 }), max_lag: v },
                                      },
                                    })
                                  }
                                />
                              </div>
                            </CardContent>
                          </Card>

                          {/* Saturation */}
                          <Card variant="glass-subtle">
                            <CardHeader className="pb-3">
                              <div className="flex items-center justify-between">
                                <div>
                                  <CardTitle className="text-base">{t('models.saturation')}</CardTitle>
                                  <CardDescription>
                                    {t('models.saturationDesc')}
                                  </CardDescription>
                                </div>
                                <Switch
                                  checked={saturationEnabled}
                                  onCheckedChange={(checked) =>
                                    updateFeatureConfig(feature, {
                                      transformations: {
                                        ...config.transformations,
                                        saturation: { ...(saturation ?? { type: 'hill', k: 'auto', s: 'auto' }), enabled: checked },
                                      },
                                    })
                                  }
                                />
                              </div>
                            </CardHeader>
                            <CardContent className={`space-y-4 ${!saturationEnabled ? 'opacity-50 pointer-events-none' : ''}`}>
                              <div className="space-y-2">
                                <Label>{t('models.saturationType')}</Label>
                                <Select
                                  value={saturation?.type ?? 'hill'}
                                  onValueChange={(v) =>
                                    updateFeatureConfig(feature, {
                                      transformations: {
                                        ...config.transformations,
                                        saturation: { ...(saturation ?? { type: 'hill', k: 'auto', s: 'auto' }), type: v as 'hill' | 'logistic' },
                                      },
                                    })
                                  }
                                >
                                  <SelectTrigger>
                                    <SelectValue />
                                  </SelectTrigger>
                                  <SelectContent>
                                    <SelectItem value="hill">{t('models.hillFunction')}</SelectItem>
                                    <SelectItem value="logistic">{t('models.logistic')}</SelectItem>
                                  </SelectContent>
                                </Select>
                              </div>

                              <div className="flex items-center justify-between">
                                <div>
                                  <Label>{t('models.autoFitParameters')}</Label>
                                  <p className="text-xs text-muted-foreground">
                                    {t('models.autoFitParametersDesc')}
                                  </p>
                                </div>
                                <Switch
                                  checked={saturation?.k === 'auto'}
                                  onCheckedChange={(checked) =>
                                    updateFeatureConfig(feature, {
                                      transformations: {
                                        ...config.transformations,
                                        saturation: {
                                          ...(saturation ?? { type: 'hill', k: 'auto', s: 'auto' }),
                                          k: checked ? 'auto' : 1.0,
                                          s: checked ? 'auto' : 1.0,
                                        },
                                      },
                                    })
                                  }
                                />
                              </div>
                            </CardContent>
                          </Card>
                        </TabsContent>
                      );
                    })}
                  </Tabs>
                )}

                {/* Seasonality Configuration */}
                <div className="mt-6">
                  <SeasonalityPanel
                    config={seasonalityConfig}
                    onChange={setSeasonalityConfig}
                  />
                </div>
              </div>
            )}

            {/* Step 4: Constraints / Priors */}
            {currentStep === 'constraints' && (
              <div className="space-y-6">
                {modelType === 'bayesian' ? (
                  <>
                    <div>
                      <CardTitle>{t('priors.title')}</CardTitle>
                      <CardDescription className="mt-1">
                        {t('priors.description')}
                      </CardDescription>
                    </div>

                    {/* Bayesian prior info */}
                    <div className="flex items-start gap-3 p-4 rounded-xl glass-sm border border-purple-500/30 bg-purple-500/10">
                      <Info className="h-5 w-5 text-purple-600 dark:text-purple-400 flex-shrink-0 mt-0.5" />
                      <div>
                        <p className="text-sm font-medium text-purple-800 dark:text-purple-200">
                          {t('priors.bayesianInfo')}
                        </p>
                        <p className="text-xs text-purple-700 dark:text-purple-300 mt-1">
                          {t('priors.bayesianInfoDesc')}
                        </p>
                      </div>
                    </div>

                    {/* Prior settings for each feature */}
                    <div className="space-y-4">
                      {selectedFeatures.map((feature) => {
                        const prior = priorsConfig[feature] || { distribution: 'normal', mu: 0, sigma: 2 };
                        const updatePrior = (updates: Partial<typeof prior>) => {
                          setPriorsConfig(prev => ({
                            ...prev,
                            [feature]: { ...prior, ...updates }
                          }));
                        };
                        return (
                          <Card key={feature} variant="glass-subtle">
                            <CardHeader className="py-3">
                              <CardTitle className="text-sm font-medium">{feature}</CardTitle>
                            </CardHeader>
                            <CardContent className="space-y-3">
                              <div className="grid grid-cols-2 gap-4">
                                <div>
                                  <Label className="text-xs">{t('priors.distribution')}</Label>
                                  <Select 
                                    value={prior.distribution} 
                                    onValueChange={(v) => updatePrior({ distribution: v })}
                                  >
                                    <SelectTrigger className="mt-1">
                                      <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                      <SelectItem value="half_normal">{t('priors.halfNormal')}</SelectItem>
                                      <SelectItem value="normal">{t('priors.normal')}</SelectItem>
                                      <SelectItem value="truncated_normal">{t('priors.truncatedNormal')}</SelectItem>
                                      <SelectItem value="uniform">{t('priors.uniform')}</SelectItem>
                                      <SelectItem value="exponential">{t('priors.exponential')}</SelectItem>
                                    </SelectContent>
                                  </Select>
                                </div>
                                <div>
                                  <Label className="text-xs">{t('priors.sigma')}</Label>
                                  <Input 
                                    type="number" 
                                    className="mt-1" 
                                    value={prior.sigma} 
                                    onChange={(e) => updatePrior({ sigma: parseFloat(e.target.value) || 1 })}
                                    step="0.1" 
                                    min="0.01"
                                  />
                                </div>
                              </div>
                              {(prior.distribution === 'normal' || prior.distribution === 'truncated_normal') && (
                                <div className="grid grid-cols-2 gap-4">
                                  <div>
                                    <Label className="text-xs">{t('priors.mean')}</Label>
                                    <Input 
                                      type="number" 
                                      className="mt-1" 
                                      value={prior.mu} 
                                      onChange={(e) => updatePrior({ mu: parseFloat(e.target.value) || 0 })}
                                      step="0.1" 
                                    />
                                  </div>
                                </div>
                              )}
                              {prior.distribution === 'truncated_normal' && (
                                <div className="grid grid-cols-2 gap-4">
                                  <div>
                                    <Label className="text-xs">{t('priors.lowerBound')}</Label>
                                    <Input 
                                      type="number" 
                                      className="mt-1" 
                                      value={prior.lower ?? 0} 
                                      onChange={(e) => updatePrior({ lower: parseFloat(e.target.value) })}
                                      step="0.1" 
                                    />
                                  </div>
                                  <div>
                                    <Label className="text-xs">{t('priors.upperBound')}</Label>
                                    <Input 
                                      type="number" 
                                      className="mt-1" 
                                      value={prior.upper ?? 10} 
                                      onChange={(e) => updatePrior({ upper: parseFloat(e.target.value) })}
                                      step="0.1" 
                                    />
                                  </div>
                                </div>
                              )}
                              <p className="text-xs text-muted-foreground">
                                {prior.distribution === 'half_normal' && t('priors.halfNormalDesc')}
                                {prior.distribution === 'normal' && t('priors.distributions.normalDesc')}
                                {prior.distribution === 'truncated_normal' && t('priors.distributions.truncatedNormalDesc')}
                              </p>
                            </CardContent>
                          </Card>
                        );
                      })}
                    </div>
                  </>
                ) : (
                  <>
                    <div>
                      <CardTitle>{t('models.coefficientConstraints')}</CardTitle>
                      <CardDescription className="mt-1">
                        {t('models.coefficientConstraintsDesc')}
                      </CardDescription>
                    </div>

                    {/* Constraint support info */}
                    <div className="flex items-start gap-3 p-4 rounded-xl glass-sm border border-blue-500/30 bg-blue-500/10">
                      <Info className="h-5 w-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
                      <div>
                        <p className="text-sm font-medium text-blue-800 dark:text-blue-200">
                          {t('constraints.constraintSupport')}
                        </p>
                        <p className="text-xs text-blue-700 dark:text-blue-300 mt-1">
                          {t('constraints.constraintSupportDesc')}
                        </p>
                      </div>
                    </div>

                    <AdvancedConstraintsPanel
                      features={selectedFeatures}
                      value={constraintsConfig}
                      onChange={setConstraintsConfig}
                      projectId={projectId}
                    />

                    <p className="text-sm text-muted-foreground">
                      {t('models.constraintsHelp')}
                    </p>
                  </>
                )}
              </div>
            )}

            {/* Step 5: Review */}
            {currentStep === 'review' && (
              <div className="space-y-6">
                <div>
                  <CardTitle>{t('models.reviewConfiguration')}</CardTitle>
                  <CardDescription className="mt-1">
                    {t('models.reviewConfigurationDesc')}
                  </CardDescription>
                </div>

                <div className="space-y-4">
                  <div className="rounded-xl glass-sm p-4">
                    <h4 className="font-medium mb-2">{t('models.modelDetails')}</h4>
                    <dl className="grid grid-cols-2 gap-2 text-sm">
                      <dt className="text-muted-foreground">{t('common.name')}:</dt>
                      <dd>{modelName}</dd>
                      <dt className="text-muted-foreground">{t('common.type')}:</dt>
                      <dd className="capitalize">{modelType}</dd>
                      <dt className="text-muted-foreground">{t('models.dataset')}:</dt>
                      <dd>{datasets.find((d: Dataset) => d.id === selectedDatasetId)?.name}</dd>
                    </dl>
                  </div>

                  <div className="rounded-xl glass-sm p-4">
                    <h4 className="font-medium mb-2">{t('models.variables')}</h4>
                    <dl className="grid grid-cols-2 gap-2 text-sm">
                      <dt className="text-muted-foreground">{t('models.target')}:</dt>
                      <dd>{targetColumn}</dd>
                      <dt className="text-muted-foreground">{t('models.features')}:</dt>
                      <dd>{t('models.variablesCount', { count: selectedFeatures.length })}</dd>
                    </dl>
                    <div className="mt-2 flex flex-wrap gap-1">
                      {selectedFeatures.map((f) => (
                        <span
                          key={f}
                          className="rounded-full bg-primary/10 px-2 py-1 text-xs text-primary"
                        >
                          {f}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Navigation */}
        <div className="mt-6 flex justify-between">
          <Button
            variant="outline"
            onClick={goPrev}
            disabled={currentStepIndex === 0}
          >
            <ArrowLeft className="mr-2 h-4 w-4" />
            {t('common.previous')}
          </Button>

          {currentStep === 'review' ? (
            <Button
              variant="gradient"
              onClick={() => createMutation.mutate()}
              disabled={createMutation.isPending || isCreated}
            >
              {isCreated ? (
                <>
                  <CheckCircle2 className="mr-2 h-4 w-4 text-green-500" />
                  {t('models.modelCreated')}
                </>
              ) : createMutation.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  {t('common.creating')}
                </>
              ) : (
                t('models.createModel')
              )}
            </Button>
          ) : (
            <Button onClick={goNext} disabled={!canProceed()}>
              {t('common.next')}
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          )}
        </div>
      </div>
    </PageWrapper>
  );
}
