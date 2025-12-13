import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, Trash2, Save, TrendingUp, TrendingDown, Percent } from 'lucide-react';
import { Button, Input, Label, Card } from '@/components/ui';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { scenariosApi } from '@/api/services/scenarios';
import type { Scenario, CreateScenarioRequest } from '@/api/services/scenarios';

interface VariableAdjustment {
  variable: string;
  type: 'percentage' | 'absolute' | 'multiplier';
  value: number;
}

interface ScenarioBuilderProps {
  projectId: string;
  modelId: string;
  availableVariables: string[];
  onScenarioCreated?: (scenarioId: string) => void;
}

export function ScenarioBuilder({
  projectId,
  modelId,
  availableVariables,
  onScenarioCreated,
}: ScenarioBuilderProps) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [adjustments, setAdjustments] = useState<VariableAdjustment[]>([]);

  const createMutation = useMutation({
    mutationFn: (data: CreateScenarioRequest) => scenariosApi.create(projectId, data),
    onSuccess: (scenario: Scenario) => {
      queryClient.invalidateQueries({ queryKey: ['scenarios', projectId] });
      onScenarioCreated?.(scenario.id);
      resetForm();
    },
  });

  const resetForm = () => {
    setName('');
    setDescription('');
    setAdjustments([]);
  };

  const addAdjustment = () => {
    if (availableVariables.length === 0) return;
    
    const usedVars = adjustments.map(a => a.variable);
    const availableVar = availableVariables.find(v => !usedVars.includes(v));
    
    if (availableVar) {
      setAdjustments([
        ...adjustments,
        { variable: availableVar, type: 'percentage', value: 0 },
      ]);
    }
  };

  const updateAdjustment = (index: number, field: keyof VariableAdjustment, value: string | number) => {
    const updated = [...adjustments];
    updated[index] = { ...updated[index], [field]: value };
    setAdjustments(updated);
  };

  const removeAdjustment = (index: number) => {
    setAdjustments(adjustments.filter((_, i) => i !== index));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    createMutation.mutate({
      name: name.trim(),
      description: description.trim(),
      model_id: modelId,
      adjustments,
    });
  };

  return (
    <Card className="p-6">
      <h3 className="text-lg font-semibold mb-4">{t('scenarios.createNew')}</h3>
      
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label htmlFor="scenario-name">{t('scenarios.scenarioName')}</Label>
            <Input
              id="scenario-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={t('scenarios.scenarioNamePlaceholder')}
              required
            />
          </div>
          <div>
            <Label htmlFor="scenario-desc">{t('scenarios.description')}</Label>
            <Input
              id="scenario-desc"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder={t('scenarios.descriptionPlaceholder')}
            />
          </div>
        </div>

        <div className="border rounded-lg p-4">
          <div className="flex items-center justify-between mb-3">
            <h4 className="font-medium">{t('scenarios.variableAdjustments')}</h4>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={addAdjustment}
              disabled={adjustments.length >= availableVariables.length}
            >
              <Plus className="w-4 h-4 mr-1" />
              {t('scenarios.addVariable')}
            </Button>
          </div>

          {adjustments.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-4">
              {t('scenarios.noAdjustments')}
            </p>
          ) : (
            <div className="space-y-3">
              {adjustments.map((adj, index) => (
                <div key={index} className="flex items-center gap-3 p-3 bg-muted/50 rounded">
                  <div className="flex-1">
                    <Label className="text-xs">{t('scenarios.variable')}</Label>
                    <Select
                      value={adj.variable}
                      onValueChange={(value) => updateAdjustment(index, 'variable', value)}
                    >
                      <SelectTrigger className="w-full">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {availableVariables.map((v) => (
                          <SelectItem
                            key={v}
                            value={v}
                            disabled={adjustments.some((a, i) => i !== index && a.variable === v)}
                          >
                            {v}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  
                  <div className="w-40">
                    <Label className="text-xs">{t('scenarios.adjustmentType')}</Label>
                    <Select
                      value={adj.type}
                      onValueChange={(value) => updateAdjustment(index, 'type', value)}
                    >
                      <SelectTrigger className="w-full">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="percentage">{t('scenarios.percentage')}</SelectItem>
                        <SelectItem value="multiplier">{t('scenarios.multiplier')}</SelectItem>
                        <SelectItem value="absolute">{t('scenarios.absolute')}</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  
                  <div className="w-28">
                    <Label className="text-xs">{t('scenarios.value')}</Label>
                    <div className="flex items-center">
                      <Input
                        type="number"
                        value={adj.value}
                        onChange={(e) => updateAdjustment(index, 'value', parseFloat(e.target.value) || 0)}
                        className="text-right"
                      />
                      {adj.type === 'percentage' && (
                        <Percent className="w-4 h-4 ml-1 text-muted-foreground" />
                      )}
                    </div>
                  </div>
                  
                  <div className="pt-5">
                    {adj.value > 0 ? (
                      <TrendingUp className="w-5 h-5 text-green-500" />
                    ) : adj.value < 0 ? (
                      <TrendingDown className="w-5 h-5 text-red-500" />
                    ) : null}
                  </div>
                  
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => removeAdjustment(index)}
                    className="pt-5"
                  >
                    <Trash2 className="w-4 h-4 text-red-500" />
                  </Button>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="flex justify-end gap-2">
          <Button type="button" variant="outline" onClick={resetForm}>
            {t('scenarios.reset')}
          </Button>
          <Button
            type="submit"
            disabled={!name.trim() || createMutation.isPending}
          >
            <Save className="w-4 h-4 mr-2" />
            {createMutation.isPending ? t('scenarios.creating') : t('scenarios.createScenario')}
          </Button>
        </div>
      </form>
    </Card>
  );
}

export default ScenarioBuilder;
