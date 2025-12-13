import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { BarChart3, TrendingUp, Award, ChevronDown, ChevronUp } from 'lucide-react';
import { Card, Button } from '@/components/ui';
import { modelsApi } from '@/api/services';
import type { ModelConfig } from '@/types';

interface ModelComparisonViewProps {
  projectId: string;
  models: ModelConfig[];
}

interface ComparisonResult {
  model_ids: string[];
  model_names: string[];
  metrics_comparison: Record<string, Record<string, number>>;
  coefficients_comparison: Record<string, Record<string, number>>;
  contributions_comparison: Record<string, Record<string, number>>;
  rankings: Record<string, string[]>;
  summary: {
    best_model_id: string;
    best_model_name: string;
    recommendation: string;
  };
}

const METRIC_LABELS: Record<string, { label: string; higherIsBetter: boolean; format: string }> = {
  r_squared: { label: 'R²', higherIsBetter: true, format: 'percent' },
  adjusted_r_squared: { label: 'Adj. R²', higherIsBetter: true, format: 'percent' },
  rmse: { label: 'RMSE', higherIsBetter: false, format: 'number' },
  mape: { label: 'MAPE', higherIsBetter: false, format: 'percent' },
  mae: { label: 'MAE', higherIsBetter: false, format: 'number' },
  aic: { label: 'AIC', higherIsBetter: false, format: 'number' },
  bic: { label: 'BIC', higherIsBetter: false, format: 'number' },
};

function formatMetricValue(value: number, format: string): string {
  if (format === 'percent') {
    return `${(value * 100).toFixed(2)}%`;
  }
  return value.toFixed(2);
}

export function ModelComparisonView({ projectId, models }: ModelComparisonViewProps) {
  const [selectedModelIds, setSelectedModelIds] = useState<string[]>([]);
  const [showCoefficients, setShowCoefficients] = useState(false);
  const [showContributions, setShowContributions] = useState(false);

  const completedModels = models.filter((m) => m.status === 'completed');

  const { data: comparison, isLoading, refetch } = useQuery({
    queryKey: ['model-comparison', projectId, selectedModelIds],
    queryFn: async () => {
      if (selectedModelIds.length < 2) return null;
      const [primaryId, ...compareWith] = selectedModelIds;
      return modelsApi.compareModels(projectId, primaryId, compareWith) as Promise<ComparisonResult>;
    },
    enabled: selectedModelIds.length >= 2,
  });

  const handleModelToggle = (modelId: string) => {
    setSelectedModelIds((prev) =>
      prev.includes(modelId)
        ? prev.filter((id) => id !== modelId)
        : [...prev, modelId]
    );
  };

  const getBestValue = (metric: string, values: Record<string, number>): string => {
    const metricInfo = METRIC_LABELS[metric];
    if (!metricInfo) return '';
    
    const entries = Object.entries(values);
    if (entries.length === 0) return '';
    
    const sorted = entries.sort((a, b) => 
      metricInfo.higherIsBetter ? b[1] - a[1] : a[1] - b[1]
    );
    return sorted[0][0];
  };

  return (
    <div className="space-y-6">
      {/* Model Selection */}
      <Card className="p-4">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <BarChart3 className="h-5 w-5" />
          Select Models to Compare
        </h3>
        
        {completedModels.length < 2 ? (
          <p className="text-gray-500">
            You need at least 2 completed models to compare. 
            Currently have {completedModels.length} completed model(s).
          </p>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
            {completedModels.map((model) => (
              <label
                key={model.id}
                className={`flex items-center gap-2 p-3 border rounded-lg cursor-pointer transition-colors ${
                  selectedModelIds.includes(model.id)
                    ? 'border-blue-500 bg-blue-50'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <input
                  type="checkbox"
                  checked={selectedModelIds.includes(model.id)}
                  onChange={() => handleModelToggle(model.id)}
                  className="rounded border-gray-300"
                />
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-sm truncate">{model.name}</p>
                  <p className="text-xs text-gray-500">{model.model_type}</p>
                </div>
              </label>
            ))}
          </div>
        )}

        {selectedModelIds.length >= 2 && (
          <div className="mt-4 flex justify-end">
            <Button onClick={() => refetch()} disabled={isLoading}>
              {isLoading ? 'Comparing...' : 'Compare Selected'}
            </Button>
          </div>
        )}
      </Card>

      {/* Comparison Results */}
      {comparison && (
        <>
          {/* Summary */}
          <Card className="p-4 bg-green-50 border-green-200">
            <div className="flex items-start gap-3">
              <Award className="h-6 w-6 text-green-600 flex-shrink-0 mt-1" />
              <div>
                <h4 className="font-semibold text-green-800">
                  Recommended: {comparison.summary.best_model_name}
                </h4>
                <p className="text-sm text-green-700 mt-1">
                  {comparison.summary.recommendation}
                </p>
              </div>
            </div>
          </Card>

          {/* Metrics Comparison Table */}
          <Card className="p-4">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <TrendingUp className="h-5 w-5" />
              Metrics Comparison
            </h3>
            
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b">
                    <th className="text-left py-2 px-3 font-medium">Metric</th>
                    {comparison.model_names.map((name, idx) => (
                      <th key={idx} className="text-right py-2 px-3 font-medium">
                        {name}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(METRIC_LABELS).map(([metric, info]) => {
                    const values = comparison.metrics_comparison[metric];
                    if (!values) return null;
                    
                    const bestModelId = getBestValue(metric, values);
                    
                    return (
                      <tr key={metric} className="border-b">
                        <td className="py-2 px-3 font-medium">{info.label}</td>
                        {comparison.model_ids.map((modelId, idx) => {
                          const value = values[modelId];
                          const isBest = modelId === bestModelId;
                          
                          return (
                            <td 
                              key={idx} 
                              className={`text-right py-2 px-3 ${
                                isBest ? 'font-bold text-green-600' : ''
                              }`}
                            >
                              {value !== undefined ? formatMetricValue(value, info.format) : '-'}
                              {isBest && ' ✓'}
                            </td>
                          );
                        })}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </Card>

          {/* Coefficients Comparison */}
          <Card className="p-4">
            <button
              className="w-full flex items-center justify-between text-lg font-semibold"
              onClick={() => setShowCoefficients(!showCoefficients)}
            >
              <span>Coefficients Comparison</span>
              {showCoefficients ? (
                <ChevronUp className="h-5 w-5" />
              ) : (
                <ChevronDown className="h-5 w-5" />
              )}
            </button>
            
            {showCoefficients && (
              <div className="mt-4 overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b">
                      <th className="text-left py-2 px-3 font-medium">Variable</th>
                      {comparison.model_names.map((name, idx) => (
                        <th key={idx} className="text-right py-2 px-3 font-medium">
                          {name}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(comparison.coefficients_comparison)
                      .filter(([key]) => key !== '_intercept')
                      .map(([variable, values]) => (
                        <tr key={variable} className="border-b">
                          <td className="py-2 px-3 font-medium">{variable}</td>
                          {comparison.model_ids.map((modelId, idx) => (
                            <td key={idx} className="text-right py-2 px-3">
                              {values[modelId]?.toFixed(4) ?? '-'}
                            </td>
                          ))}
                        </tr>
                      ))}
                    {comparison.coefficients_comparison['_intercept'] && (
                      <tr className="border-b bg-gray-50">
                        <td className="py-2 px-3 font-medium italic">Intercept</td>
                        {comparison.model_ids.map((modelId, idx) => (
                          <td key={idx} className="text-right py-2 px-3">
                            {comparison.coefficients_comparison['_intercept'][modelId]?.toFixed(2) ?? '-'}
                          </td>
                        ))}
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </Card>

          {/* Contributions Comparison */}
          {Object.keys(comparison.contributions_comparison).length > 0 && (
            <Card className="p-4">
              <button
                className="w-full flex items-center justify-between text-lg font-semibold"
                onClick={() => setShowContributions(!showContributions)}
              >
                <span>Contributions Comparison (%)</span>
                {showContributions ? (
                  <ChevronUp className="h-5 w-5" />
                ) : (
                  <ChevronDown className="h-5 w-5" />
                )}
              </button>
              
              {showContributions && (
                <div className="mt-4 overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b">
                        <th className="text-left py-2 px-3 font-medium">Channel</th>
                        {comparison.model_names.map((name, idx) => (
                          <th key={idx} className="text-right py-2 px-3 font-medium">
                            {name}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(comparison.contributions_comparison).map(([variable, values]) => (
                        <tr key={variable} className="border-b">
                          <td className="py-2 px-3 font-medium">{variable}</td>
                          {comparison.model_ids.map((modelId, idx) => (
                            <td key={idx} className="text-right py-2 px-3">
                              {values[modelId]?.toFixed(1) ?? '-'}%
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Card>
          )}
        </>
      )}
    </div>
  );
}

export default ModelComparisonView;
