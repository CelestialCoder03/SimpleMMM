import { useTranslation } from 'react-i18next';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Play, RefreshCw, TrendingUp, TrendingDown, BarChart3 } from 'lucide-react';
import { Button, Card } from '@/components/ui';
import { scenariosApi } from '@/api/services/scenarios';
import type { Scenario } from '@/api/services/scenarios';

interface ScenarioResultsViewProps {
  projectId: string;
  scenario: Scenario;
  onRefresh?: () => void;
}

export function ScenarioResultsView({ projectId, scenario, onRefresh }: ScenarioResultsViewProps) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const resultsQuery = useQuery({
    queryKey: ['scenario-results', projectId, scenario.id],
    queryFn: () => scenariosApi.getResults(projectId, scenario.id),
    enabled: scenario.status === 'ready',
  });

  const calculateMutation = useMutation({
    mutationFn: () => scenariosApi.calculate(projectId, scenario.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scenarios', projectId] });
      queryClient.invalidateQueries({ queryKey: ['scenario-results', projectId, scenario.id] });
      onRefresh?.();
    },
  });

  const formatNumber = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  const formatPercent = (value: number) => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(1)}%`;
  };

  if (scenario.status === 'draft') {
    return (
      <Card className="p-6">
        <div className="text-center py-8">
          <BarChart3 className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
          <h3 className="text-lg font-medium mb-2">{t('scenarios.notCalculated')}</h3>
          <p className="text-muted-foreground mb-4">
            {t('scenarios.runCalculation')}
          </p>
          <Button
            onClick={() => calculateMutation.mutate()}
            disabled={calculateMutation.isPending}
          >
            <Play className="w-4 h-4 mr-2" />
            {calculateMutation.isPending ? t('scenarios.calculating') : t('scenarios.calculateScenario')}
          </Button>
        </div>
      </Card>
    );
  }

  if (scenario.status === 'calculating') {
    return (
      <Card className="p-6">
        <div className="text-center py-8">
          <RefreshCw className="w-12 h-12 mx-auto text-blue-500 mb-4 animate-spin" />
          <h3 className="text-lg font-medium mb-2">{t('scenarios.calculating')}</h3>
          <p className="text-muted-foreground">{t('scenarios.calculatingDesc')}</p>
        </div>
      </Card>
    );
  }

  if (scenario.status === 'failed') {
    return (
      <Card className="p-6">
        <div className="text-center py-8">
          <div className="w-12 h-12 mx-auto bg-red-100 rounded-full flex items-center justify-center mb-4">
            <span className="text-red-600 text-xl">!</span>
          </div>
          <h3 className="text-lg font-medium mb-2 text-destructive">{t('scenarios.calculationFailed')}</h3>
          <p className="text-muted-foreground mb-4">
            {t('scenarios.calculationFailedDesc')}
          </p>
          <Button
            variant="outline"
            onClick={() => calculateMutation.mutate()}
            disabled={calculateMutation.isPending}
          >
            <RefreshCw className="w-4 h-4 mr-2" />
            {t('scenarios.retry')}
          </Button>
        </div>
      </Card>
    );
  }

  const results = resultsQuery.data;
  const variableImpacts = (results?.summary as Record<string, unknown> | undefined)?.variable_impacts;
  const liftPct = scenario.lift_percentage ?? 0;

  return (
    <Card className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold">{scenario.name}</h3>
        <Button
          variant="outline"
          size="sm"
          onClick={() => calculateMutation.mutate()}
          disabled={calculateMutation.isPending}
        >
          <RefreshCw className="w-4 h-4 mr-2" />
          {t('scenarios.recalculate')}
        </Button>
      </div>

      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="bg-muted/50 p-4 rounded-lg">
          <p className="text-sm text-muted-foreground mb-1">{t('scenarios.baselineTotal')}</p>
          <p className="text-2xl font-bold">{formatNumber(scenario.baseline_total ?? 0)}</p>
        </div>
        <div className="bg-blue-50 p-4 rounded-lg">
          <p className="text-sm text-blue-600 mb-1">{t('scenarios.scenarioTotal')}</p>
          <p className="text-2xl font-bold text-blue-700">
            {formatNumber(scenario.scenario_total ?? 0)}
          </p>
        </div>
        <div className={`p-4 rounded-lg ${liftPct >= 0 ? 'bg-green-50' : 'bg-red-50'}`}>
          <p className={`text-sm mb-1 ${liftPct >= 0 ? 'text-green-600' : 'text-red-600'}`}>
            {t('scenarios.lift')}
          </p>
          <p className={`text-2xl font-bold flex items-center ${liftPct >= 0 ? 'text-green-700' : 'text-red-700'}`}>
            {liftPct >= 0 ? (
              <TrendingUp className="w-6 h-6 mr-1" />
            ) : (
              <TrendingDown className="w-6 h-6 mr-1" />
            )}
            {formatPercent(liftPct)}
          </p>
        </div>
      </div>

      {results && (
        <div>
          <h4 className="font-medium mb-3">{t('scenarios.adjustmentsApplied')}</h4>
          <div className="border rounded-lg overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-muted/50">
                <tr>
                  <th className="px-4 py-2 text-left">{t('scenarios.variable')}</th>
                  <th className="px-4 py-2 text-left">{t('common.type')}</th>
                  <th className="px-4 py-2 text-right">{t('scenarios.value')}</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(scenario.adjustments).map(([variable, adj]) => (
                  <tr key={variable} className="border-t">
                    <td className="px-4 py-2 font-medium">{variable}</td>
                    <td className="px-4 py-2 capitalize">{adj.type}</td>
                    <td className="px-4 py-2 text-right">
                      {adj.type === 'percentage' ? `${adj.value}%` : adj.value}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {Boolean(variableImpacts) && (
            <div className="mt-6">
              <h4 className="font-medium mb-3">{t('scenarios.impactByVariable')}</h4>
              <div className="border rounded-lg overflow-hidden">
                <table className="w-full text-sm">
                  <thead className="bg-muted/50">
                    <tr>
                      <th className="px-4 py-2 text-left">{t('scenarios.variable')}</th>
                      <th className="px-4 py-2 text-right">{t('scenarios.baseline')}</th>
                      <th className="px-4 py-2 text-right">{t('scenarios.scenario')}</th>
                      <th className="px-4 py-2 text-right">{t('scenarios.impact')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(() => {
                      type VariableImpact = {
                        baseline: number;
                        scenario: number;
                        impact_percentage: number;
                      };

                      const impacts = variableImpacts as Record<string, VariableImpact>;

                      return Object.entries(impacts).map(([variable, impact]) => (
                        <tr key={variable} className="border-t">
                          <td className="px-4 py-2 font-medium">{variable}</td>
                          <td className="px-4 py-2 text-right">{formatNumber(impact.baseline)}</td>
                          <td className="px-4 py-2 text-right">{formatNumber(impact.scenario)}</td>
                          <td className={`px-4 py-2 text-right font-medium ${
                            impact.impact_percentage >= 0 ? 'text-green-600' : 'text-red-600'
                          }`}>
                            {formatPercent(impact.impact_percentage)}
                          </td>
                        </tr>
                      ));
                    })()}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </Card>
  );
}

export default ScenarioResultsView;
