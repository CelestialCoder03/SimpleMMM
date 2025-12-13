import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useQuery, useMutation } from '@tanstack/react-query';
import { DollarSign, Target, ArrowRight, CheckCircle } from 'lucide-react';
import { Button, Input, Label, Card } from '@/components/ui';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { optimizationApi } from '@/api/services/optimization';
import type { OptimizationResult, ChannelConstraint } from '@/api/services/optimization';

interface BudgetOptimizerProps {
  projectId: string;
  modelId: string;
}

export function BudgetOptimizer({ projectId, modelId }: BudgetOptimizerProps) {
  const { t } = useTranslation();
  const [totalBudget, setTotalBudget] = useState<number>(100000);
  const [objective, setObjective] = useState<'maximize_response' | 'maximize_roi'>('maximize_response');
  const [constraints, setConstraints] = useState<ChannelConstraint[]>([]);
  const [result, setResult] = useState<OptimizationResult | null>(null);

  const channelsQuery = useQuery({
    queryKey: ['optimization-channels', projectId, modelId],
    queryFn: () => optimizationApi.getChannels(projectId, modelId),
    enabled: !!modelId,
  });

  const optimizeMutation = useMutation({
    mutationFn: () =>
      optimizationApi.optimize(projectId, {
        model_id: modelId,
        total_budget: totalBudget,
        objective,
        constraints,
      }),
    onSuccess: (data) => {
      setResult(data);
    },
  });

  const updateConstraint = (channel: string, field: keyof ChannelConstraint, value: number | undefined) => {
    setConstraints((prev) => {
      const existing = prev.find((c) => c.channel === channel);
      if (existing) {
        return prev.map((c) =>
          c.channel === channel ? { ...c, [field]: value } : c
        );
      }
      return [...prev, { channel, [field]: value }];
    });
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  const formatPercent = (value: number) => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(1)}%`;
  };

  return (
    <div className="space-y-6">
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-4 flex items-center">
          <Target className="w-5 h-5 mr-2 text-blue-600" />
          {t('optimization.settings')}
        </h3>

        <div className="grid grid-cols-2 gap-6">
          <div>
            <Label htmlFor="total-budget">{t('optimization.totalBudget')}</Label>
            <div className="relative mt-1">
              <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                id="total-budget"
                type="number"
                value={totalBudget}
                onChange={(e) => setTotalBudget(parseFloat(e.target.value) || 0)}
                className="pl-9"
              />
            </div>
          </div>

          <div>
            <Label htmlFor="objective">{t('optimization.objective')}</Label>
            <Select
              value={objective}
              onValueChange={(value) => setObjective(value as typeof objective)}
            >
              <SelectTrigger className="w-full mt-1">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="maximize_response">{t('optimization.maximizeResponse')}</SelectItem>
                <SelectItem value="maximize_roi">{t('optimization.maximizeRoi')}</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        {channelsQuery.data && (
          <div className="mt-6">
            <h4 className="font-medium mb-3">{t('optimization.channelConstraints')}</h4>
            <div className="border rounded-lg overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-muted/50">
                  <tr>
                    <th className="px-4 py-2 text-left">{t('optimization.channel')}</th>
                    <th className="px-4 py-2 text-left">{t('optimization.currentShare')}</th>
                    <th className="px-4 py-2 text-left">{t('optimization.minShare')}</th>
                    <th className="px-4 py-2 text-left">{t('optimization.maxShare')}</th>
                  </tr>
                </thead>
                <tbody>
                  {channelsQuery.data.channels.map((channel) => (
                    <tr key={channel.name} className="border-t">
                      <td className="px-4 py-2 font-medium">{channel.name}</td>
                      <td className="px-4 py-2 text-muted-foreground">{channel.share_pct.toFixed(1)}%</td>
                      <td className="px-4 py-2">
                        <Input
                          type="number"
                          min={0}
                          max={100}
                          placeholder="0"
                          className="w-20 text-sm"
                          onChange={(e) =>
                            updateConstraint(channel.name, 'min_share', e.target.value ? parseFloat(e.target.value) : undefined)
                          }
                        />
                      </td>
                      <td className="px-4 py-2">
                        <Input
                          type="number"
                          min={0}
                          max={100}
                          placeholder="100"
                          className="w-20 text-sm"
                          onChange={(e) =>
                            updateConstraint(channel.name, 'max_share', e.target.value ? parseFloat(e.target.value) : undefined)
                          }
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        <div className="mt-6 flex justify-end">
          <Button
            onClick={() => optimizeMutation.mutate()}
            disabled={optimizeMutation.isPending || !totalBudget}
          >
            {optimizeMutation.isPending ? t('optimization.optimizing') : t('optimization.runOptimization')}
            <ArrowRight className="w-4 h-4 ml-2" />
          </Button>
        </div>
      </Card>

      {result && (
        <Card className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold flex items-center">
              <CheckCircle className="w-5 h-5 mr-2 text-green-600" />
              {t('optimization.results')}
            </h3>
            {result.success && (
              <span className="px-2 py-1 bg-green-100 text-green-700 text-sm rounded">
                {t('optimization.success')}
              </span>
            )}
          </div>

          <div className="grid grid-cols-4 gap-4 mb-6">
            <div className="bg-blue-50 p-4 rounded-lg">
              <p className="text-sm text-blue-600 mb-1">{t('optimization.responseLift')}</p>
              <p className="text-2xl font-bold text-blue-700">
                {formatPercent(result.response_lift_pct)}
              </p>
            </div>
            <div className="bg-green-50 p-4 rounded-lg">
              <p className="text-sm text-green-600 mb-1">{t('optimization.optimizedResponse')}</p>
              <p className="text-2xl font-bold text-green-700">
                {formatCurrency(result.optimized_response)}
              </p>
            </div>
            <div className="bg-purple-50 p-4 rounded-lg">
              <p className="text-sm text-purple-600 mb-1">{t('optimization.roiImprovement')}</p>
              <p className="text-2xl font-bold text-purple-700">
                {result.roi_improvement >= 0 ? '+' : ''}{result.roi_improvement.toFixed(4)}
              </p>
            </div>
            <div className="bg-orange-50 p-4 rounded-lg">
              <p className="text-sm text-orange-600 mb-1">{t('optimization.totalBudgetLabel')}</p>
              <p className="text-2xl font-bold text-orange-700">
                {formatCurrency(result.total_budget)}
              </p>
            </div>
          </div>

          <h4 className="font-medium mb-3">{t('optimization.recommendedAllocation')}</h4>
          <div className="border rounded-lg overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-muted/50">
                <tr>
                  <th className="px-4 py-2 text-left">{t('optimization.channel')}</th>
                  <th className="px-4 py-2 text-right">{t('optimization.current')}</th>
                  <th className="px-4 py-2 text-center">→</th>
                  <th className="px-4 py-2 text-right">{t('optimization.optimized')}</th>
                  <th className="px-4 py-2 text-right">{t('optimization.change')}</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(result.channel_changes).map(([channel, change]) => (
                  <tr key={channel} className="border-t">
                    <td className="px-4 py-2 font-medium">{channel}</td>
                    <td className="px-4 py-2 text-right text-muted-foreground">
                      {formatCurrency(change.current)}
                    </td>
                    <td className="px-4 py-2 text-center">
                      <ArrowRight className="w-4 h-4 mx-auto text-muted-foreground" />
                    </td>
                    <td className="px-4 py-2 text-right font-medium">
                      {formatCurrency(change.optimized)}
                    </td>
                    <td className={`px-4 py-2 text-right font-medium ${
                      change.change_pct > 0 ? 'text-green-600' : change.change_pct < 0 ? 'text-red-600' : 'text-muted-foreground'
                    }`}>
                      {formatPercent(change.change_pct)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}

export default BudgetOptimizer;
