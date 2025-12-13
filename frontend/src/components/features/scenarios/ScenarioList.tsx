import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Trash2, ChevronRight, Clock, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import { Button, Card } from '@/components/ui';
import { scenariosApi } from '@/api/services/scenarios';
import type { Scenario } from '@/api/services/scenarios';

interface ScenarioListProps {
  projectId: string;
  onSelectScenario?: (scenario: Scenario) => void;
  selectedScenarioId?: string;
}

const statusIcons = {
  draft: Clock,
  calculating: Loader2,
  ready: CheckCircle,
  failed: AlertCircle,
};

const statusStyles: Record<string, { color: string; bg: string; animate?: boolean }> = {
  draft: { color: 'text-muted-foreground', bg: 'bg-muted' },
  calculating: { color: 'text-blue-500', bg: 'bg-blue-500/10', animate: true },
  ready: { color: 'text-green-500', bg: 'bg-green-500/10' },
  failed: { color: 'text-destructive', bg: 'bg-destructive/10' },
};

export function ScenarioList({ projectId, onSelectScenario, selectedScenarioId }: ScenarioListProps) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);

  const scenariosQuery = useQuery({
    queryKey: ['scenarios', projectId, page],
    queryFn: () => scenariosApi.list(projectId, page, 10),
  });

  const deleteMutation = useMutation({
    mutationFn: (scenarioId: string) => scenariosApi.delete(projectId, scenarioId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scenarios', projectId] });
    },
  });

  const handleDelete = (e: React.MouseEvent, scenarioId: string) => {
    e.stopPropagation();
    if (window.confirm(t('scenarios.deleteConfirm'))) {
      deleteMutation.mutate(scenarioId);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  if (scenariosQuery.isLoading) {
    return (
      <Card className="p-6">
        <div className="flex items-center justify-center py-8">
          <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
        </div>
      </Card>
    );
  }

  const scenarios = scenariosQuery.data?.items || [];
  const totalPages = Math.ceil((scenariosQuery.data?.total || 0) / 10);

  if (scenarios.length === 0) {
    return (
      <Card className="p-6">
        <div className="text-center py-8 text-muted-foreground">
          <p>{t('scenarios.noScenarios')}</p>
          <p className="text-sm mt-1">{t('scenarios.noScenariosDesc')}</p>
        </div>
      </Card>
    );
  }

  return (
    <Card className="p-4">
      <h3 className="font-semibold mb-4">{t('scenarios.title')}</h3>
      
      <div className="space-y-2">
        {scenarios.map((scenario: Scenario) => {
          const statusKey = scenario.status as keyof typeof statusIcons;
          const StatusIcon = statusIcons[statusKey];
          const style = statusStyles[statusKey];
          const isSelected = selectedScenarioId === scenario.id;

          return (
            <div
              key={scenario.id}
              onClick={() => onSelectScenario?.(scenario)}
              className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                isSelected
                  ? 'border-primary bg-primary/5'
                  : 'border-border hover:border-primary/50 hover:bg-muted/50'
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <h4 className="font-medium truncate">{scenario.name}</h4>
                    <span className={`px-2 py-0.5 text-xs rounded-full ${style.bg} ${style.color}`}>
                      <StatusIcon className={`w-3 h-3 inline-block mr-1 ${style.animate ? 'animate-spin' : ''}`} />
                      {t(`scenarios.status.${statusKey}`)}
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    {Object.keys(scenario.adjustments).length} {t('scenarios.adjustments')} • {formatDate(scenario.updated_at)}
                  </p>
                  {scenario.lift_percentage !== null && (
                    <p className={`text-sm font-medium mt-1 ${
                      scenario.lift_percentage >= 0 ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {scenario.lift_percentage >= 0 ? '+' : ''}{scenario.lift_percentage.toFixed(1)}% lift
                    </p>
                  )}
                </div>
                
                <div className="flex items-center gap-2 ml-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={(e) => handleDelete(e, scenario.id)}
                    disabled={deleteMutation.isPending}
                    className="text-red-500 hover:text-red-700"
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                  <ChevronRight className={`w-5 h-5 ${isSelected ? 'text-primary' : 'text-muted-foreground'}`} />
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-4 pt-4 border-t">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
          >
            {t('common.previous')}
          </Button>
          <span className="text-sm text-muted-foreground">
            {t('scenarios.page')} {page} {t('scenarios.of')} {totalPages}
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
          >
            {t('common.next')}
          </Button>
        </div>
      )}
    </Card>
  );
}

export default ScenarioList;
