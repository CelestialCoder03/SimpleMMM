import { useState, useEffect } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Settings, Save } from 'lucide-react';
import { projectsApi } from '@/api/services/projects';
import { Button, Card, Input, Label } from '@/components/ui';
import type { ProjectSettings } from '@/types';

interface ProjectSettingsPanelProps {
  projectId: string;
  isOwner: boolean;
}

const MODEL_TYPES = [
  { value: 'ridge', label: 'Ridge Regression' },
  { value: 'elasticnet', label: 'Elastic Net' },
  { value: 'ols', label: 'OLS (Linear)' },
  { value: 'bayesian', label: 'Bayesian' },
];

const CURRENCIES = [
  { value: 'USD', label: 'USD ($)' },
  { value: 'EUR', label: 'EUR (€)' },
  { value: 'GBP', label: 'GBP (£)' },
  { value: 'CNY', label: 'CNY (¥)' },
  { value: 'JPY', label: 'JPY (¥)' },
];

const CHART_THEMES = [
  { value: 'default', label: 'Default' },
  { value: 'colorful', label: 'Colorful' },
  { value: 'monochrome', label: 'Monochrome' },
  { value: 'pastel', label: 'Pastel' },
];

const EXPORT_FORMATS = [
  { value: 'excel', label: 'Excel (.xlsx)' },
  { value: 'csv', label: 'CSV' },
  { value: 'json', label: 'JSON' },
];

export function ProjectSettingsPanel({ projectId, isOwner }: ProjectSettingsPanelProps) {
  const queryClient = useQueryClient();
  const [localSettings, setLocalSettings] = useState<Partial<ProjectSettings>>({});
  const [hasChanges, setHasChanges] = useState(false);

  const { data: settings, isLoading } = useQuery({
    queryKey: ['project-settings', projectId],
    queryFn: () => projectsApi.getSettings(projectId),
  });

  useEffect(() => {
    if (!settings) return;
    if (hasChanges) return;

    const timer = setTimeout(() => {
      setLocalSettings(settings);
    }, 0);

    return () => clearTimeout(timer);
  }, [settings, hasChanges]);

  const updateMutation = useMutation({
    mutationFn: (newSettings: Partial<ProjectSettings>) =>
      projectsApi.updateSettings(projectId, newSettings),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['project-settings', projectId] });
      setHasChanges(false);
    },
  });

  const handleChange = (key: keyof ProjectSettings, value: unknown) => {
    setLocalSettings((prev) => ({ ...prev, [key]: value }));
    setHasChanges(true);
  };

  const handleSave = () => {
    updateMutation.mutate(localSettings);
  };

  if (isLoading) {
    return (
      <Card className="p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-4 bg-gray-200 rounded w-1/4"></div>
          <div className="h-10 bg-gray-200 rounded"></div>
          <div className="h-10 bg-gray-200 rounded"></div>
        </div>
      </Card>
    );
  }

  return (
    <Card className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <Settings className="h-5 w-5 text-gray-500" />
          <h3 className="text-lg font-semibold">Project Settings</h3>
        </div>
        {isOwner && hasChanges && (
          <Button
            onClick={handleSave}
            disabled={updateMutation.isPending}
            size="sm"
          >
            <Save className="h-4 w-4 mr-2" />
            {updateMutation.isPending ? 'Saving...' : 'Save Changes'}
          </Button>
        )}
      </div>

      <div className="space-y-6">
        {/* Model Settings */}
        <div>
          <h4 className="text-sm font-medium text-gray-700 mb-3">Model Defaults</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label htmlFor="default_model_type">Default Model Type</Label>
              <select
                id="default_model_type"
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                value={localSettings.default_model_type || ''}
                onChange={(e) => handleChange('default_model_type', e.target.value || undefined)}
                disabled={!isOwner}
              >
                <option value="">Select default...</option>
                {MODEL_TYPES.map((type) => (
                  <option key={type.value} value={type.value}>
                    {type.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* Display Settings */}
        <div>
          <h4 className="text-sm font-medium text-gray-700 mb-3">Display Settings</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label htmlFor="currency">Currency</Label>
              <select
                id="currency"
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                value={localSettings.currency || ''}
                onChange={(e) => handleChange('currency', e.target.value || undefined)}
                disabled={!isOwner}
              >
                <option value="">Select currency...</option>
                {CURRENCIES.map((curr) => (
                  <option key={curr.value} value={curr.value}>
                    {curr.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <Label htmlFor="decimal_places">Decimal Places</Label>
              <Input
                id="decimal_places"
                type="number"
                min={0}
                max={6}
                value={localSettings.decimal_places ?? ''}
                onChange={(e) => handleChange('decimal_places', e.target.value ? parseInt(e.target.value) : undefined)}
                disabled={!isOwner}
                placeholder="2"
              />
            </div>

            <div>
              <Label htmlFor="chart_theme">Chart Theme</Label>
              <select
                id="chart_theme"
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                value={localSettings.chart_theme || ''}
                onChange={(e) => handleChange('chart_theme', e.target.value || undefined)}
                disabled={!isOwner}
              >
                <option value="">Select theme...</option>
                {CHART_THEMES.map((theme) => (
                  <option key={theme.value} value={theme.value}>
                    {theme.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <Label htmlFor="date_format">Date Format</Label>
              <Input
                id="date_format"
                type="text"
                value={localSettings.date_format || ''}
                onChange={(e) => handleChange('date_format', e.target.value || undefined)}
                disabled={!isOwner}
                placeholder="YYYY-MM-DD"
              />
            </div>
          </div>
        </div>

        {/* Export Settings */}
        <div>
          <h4 className="text-sm font-medium text-gray-700 mb-3">Export Settings</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label htmlFor="export_format">Default Export Format</Label>
              <select
                id="export_format"
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                value={localSettings.export_format || ''}
                onChange={(e) => handleChange('export_format', e.target.value || undefined)}
                disabled={!isOwner}
              >
                <option value="">Select format...</option>
                {EXPORT_FORMATS.map((format) => (
                  <option key={format.value} value={format.value}>
                    {format.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex items-center">
              <input
                id="include_raw_data"
                type="checkbox"
                className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                checked={localSettings.include_raw_data || false}
                onChange={(e) => handleChange('include_raw_data', e.target.checked)}
                disabled={!isOwner}
              />
              <Label htmlFor="include_raw_data" className="ml-2">
                Include raw data in exports
              </Label>
            </div>
          </div>
        </div>
      </div>

      {!isOwner && (
        <p className="mt-4 text-sm text-gray-500">
          Only the project owner can modify settings.
        </p>
      )}
    </Card>
  );
}

export default ProjectSettingsPanel;
