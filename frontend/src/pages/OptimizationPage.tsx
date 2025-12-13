import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { ArrowLeft, Target } from 'lucide-react';
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
import { BudgetOptimizer } from '@/components/features/optimization';
import type { ModelConfig } from '@/types';

export function OptimizationPage() {
  const { t } = useTranslation();
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const [selectedModelId, setSelectedModelId] = useState<string>('');

  const { data: models = [] } = useQuery({
    queryKey: ['models', projectId],
    queryFn: () => modelsApi.list(projectId!),
    enabled: !!projectId,
  });

  const completedModels = models.filter((m: ModelConfig) => m.status === 'completed');

  return (
    <PageWrapper className="flex flex-col">
      <Header
        title={t('optimization.title')}
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
              <Target className="h-5 w-5 text-muted-foreground" />
              <div className="flex-1">
                <label className="text-sm font-medium mb-1 block">
                  {t('optimization.selectModel', 'Select a completed model')}
                </label>
                {completedModels.length === 0 ? (
                  <p className="text-sm text-muted-foreground">
                    {t('optimization.noCompletedModels', 'No completed models available. Train a model first.')}
                  </p>
                ) : (
                  <Select value={selectedModelId} onValueChange={setSelectedModelId}>
                    <SelectTrigger className="w-full max-w-md">
                      <SelectValue placeholder={t('optimization.selectModelPlaceholder', 'Choose a model...')} />
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
          <BudgetOptimizer
            projectId={projectId!}
            modelId={selectedModelId}
          />
        )}
      </div>
    </PageWrapper>
  );
}
