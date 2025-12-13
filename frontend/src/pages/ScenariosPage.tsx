import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { ArrowLeft, GitBranch } from 'lucide-react';
import { modelsApi } from '@/api/services';
import { Header, PageWrapper } from '@/components/layout';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Card, CardContent } from '@/components/ui/card';
import { ScenarioList, ScenarioBuilder, ScenarioResultsView } from '@/components/features/scenarios';
import type { Scenario } from '@/api/services/scenarios';
import type { ModelConfig } from '@/types';

export function ScenariosPage() {
  const { t } = useTranslation();
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const [selectedModelId, setSelectedModelId] = useState<string>('');
  const [selectedScenario, setSelectedScenario] = useState<Scenario | null>(null);

  const { data: models = [] } = useQuery({
    queryKey: ['models', projectId],
    queryFn: () => modelsApi.list(projectId!),
    enabled: !!projectId,
  });

  const completedModels = models.filter((m: ModelConfig) => m.status === 'completed');

  const selectedModel = completedModels.find((m: ModelConfig) => m.id === selectedModelId);
  const availableVariables = selectedModel?.features
    ?.filter((f) => f.enabled !== false)
    .map((f) => f.column) || [];

  const handleScenarioCreated = () => {
    // Scenario created, list will refresh via query invalidation
  };

  const handleSelectScenario = (scenario: Scenario) => {
    setSelectedScenario(scenario);
  };

  return (
    <PageWrapper className="flex flex-col">
      <Header
        title={t('scenarios.title')}
        actions={
          <div className="flex gap-2">
            <Button variant="ghost" onClick={() => navigate(`/projects/${projectId}`)}>
              <ArrowLeft className="mr-2 h-4 w-4" />
              {t('common.back', 'Back')}
            </Button>
          </div>
        }
      />

      <div className="p-6 space-y-6">
        {/* Model Selector */}
        <Card variant="glass">
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <GitBranch className="h-5 w-5 text-muted-foreground" />
              <div className="flex-1">
                <label className="text-sm font-medium mb-1 block">
                  {t('scenarios.selectModel', 'Select a completed model')}
                </label>
                {completedModels.length === 0 ? (
                  <p className="text-sm text-muted-foreground">
                    {t('scenarios.noCompletedModels', 'No completed models available. Train a model first.')}
                  </p>
                ) : (
                  <Select value={selectedModelId} onValueChange={setSelectedModelId}>
                    <SelectTrigger className="w-full max-w-md">
                      <SelectValue placeholder={t('scenarios.selectModelPlaceholder', 'Choose a model...')} />
                    </SelectTrigger>
                    <SelectContent>
                      {completedModels.map((model: ModelConfig) => (
                        <SelectItem key={model.id} value={model.id}>
                          {model.name} ({model.model_type})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        {selectedModelId && (
          <div className="grid gap-6 lg:grid-cols-3">
            {/* Left: Scenario List */}
            <div className="lg:col-span-1">
              <ScenarioList
                projectId={projectId!}
                onSelectScenario={handleSelectScenario}
                selectedScenarioId={selectedScenario?.id}
              />
            </div>

            {/* Right: Builder + Results */}
            <div className="lg:col-span-2 space-y-6">
              <ScenarioBuilder
                projectId={projectId!}
                modelId={selectedModelId}
                availableVariables={availableVariables}
                onScenarioCreated={handleScenarioCreated}
              />

              {selectedScenario && (
                <ScenarioResultsView
                  projectId={projectId!}
                  scenario={selectedScenario}
                />
              )}
            </div>
          </div>
        )}
      </div>
    </PageWrapper>
  );
}
