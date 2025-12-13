import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Plus, Trash2, Info } from 'lucide-react';
import { Button, Card, Input, Label } from '@/components/ui';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import type { PriorConfig } from '@/types';

interface PriorConfigPanelProps {
  variables: string[];
  priors: Record<string, PriorConfig>;
  onChange: (priors: Record<string, PriorConfig>) => void;
  disabled?: boolean;
}

const DISTRIBUTIONS = [
  { 
    value: 'normal', 
    label: 'Normal',
    description: 'Symmetric distribution, can be positive or negative',
    params: ['mean', 'std'],
  },
  { 
    value: 'truncated_normal', 
    label: 'Truncated Normal',
    description: 'Normal distribution bounded between lower and upper limits',
    params: ['mean', 'std', 'lower', 'upper'],
  },
  { 
    value: 'half_normal', 
    label: 'Half Normal',
    description: 'Positive-only normal distribution (for positive coefficients)',
    params: ['std'],
  },
];

const DEFAULT_PRIORS: Record<string, PriorConfig> = {
  normal: { distribution: 'normal', mean: 0, std: 1 },
  truncated_normal: { distribution: 'truncated_normal', mean: 0, std: 1, lower: 0, upper: 10 },
  half_normal: { distribution: 'half_normal', std: 1 },
};

export function PriorConfigPanel({ 
  variables, 
  priors, 
  onChange,
  disabled = false,
}: PriorConfigPanelProps) {
  const { t } = useTranslation();
  const [selectedVariable, setSelectedVariable] = useState<string>('');

  const handleAddPrior = () => {
    if (!selectedVariable || priors[selectedVariable]) return;
    
    onChange({
      ...priors,
      [selectedVariable]: { ...DEFAULT_PRIORS.half_normal },
    });
    setSelectedVariable('');
  };

  const handleRemovePrior = (variable: string) => {
    const newPriors = { ...priors };
    delete newPriors[variable];
    onChange(newPriors);
  };

  const handleDistributionChange = (variable: string, distribution: string) => {
    const defaultPrior = DEFAULT_PRIORS[distribution as keyof typeof DEFAULT_PRIORS];
    onChange({
      ...priors,
      [variable]: { ...defaultPrior },
    });
  };

  const handleParamChange = (variable: string, param: string, value: number | undefined) => {
    onChange({
      ...priors,
      [variable]: {
        ...priors[variable],
        [param]: value,
      },
    });
  };

  const availableVariables = variables.filter((v) => !priors[v]);

  return (
    <Card className="p-4">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <h4 className="text-sm font-medium">{t('priors.title')}</h4>
          <div className="group relative">
            <Info className="h-4 w-4 text-muted-foreground cursor-help" />
            <div className="absolute left-0 top-6 w-64 p-2 bg-popover text-popover-foreground text-xs rounded shadow-lg opacity-0 group-hover:opacity-100 transition-opacity z-10 border">
              {t('priors.tooltip')}
            </div>
          </div>
        </div>
      </div>

      {/* Add new prior */}
      {!disabled && availableVariables.length > 0 && (
        <div className="flex gap-2 mb-4">
          <Select
            value={selectedVariable}
            onValueChange={setSelectedVariable}
          >
            <SelectTrigger className="flex-1">
              <SelectValue placeholder={t('priors.selectVariable')} />
            </SelectTrigger>
            <SelectContent>
              {availableVariables.map((v) => (
                <SelectItem key={v} value={v}>{v}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button
            size="sm"
            onClick={handleAddPrior}
            disabled={!selectedVariable}
          >
            <Plus className="h-4 w-4 mr-1" />
            {t('priors.addPrior')}
          </Button>
        </div>
      )}

      {/* Prior list */}
      <div className="space-y-4">
        {Object.entries(priors).map(([variable, prior]) => (
          <div key={variable} className="border rounded-lg p-3 bg-muted/50">
            <div className="flex items-center justify-between mb-2">
              <span className="font-medium text-sm">{variable}</span>
              {!disabled && (
                <button
                  onClick={() => handleRemovePrior(variable)}
                  className="text-red-500 hover:text-red-700"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              )}
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="col-span-2">
                <Label className="text-xs">{t('priors.distribution')}</Label>
                <Select
                  value={prior.distribution}
                  onValueChange={(value) => handleDistributionChange(variable, value)}
                  disabled={disabled}
                >
                  <SelectTrigger className="mt-1 w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {DISTRIBUTIONS.map((dist) => (
                      <SelectItem key={dist.value} value={dist.value}>
                        {t(`priors.distributions.${dist.value === 'truncated_normal' ? 'truncatedNormal' : dist.value === 'half_normal' ? 'halfNormal' : dist.value}`)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground mt-1">
                  {t(`priors.distributions.${prior.distribution === 'truncated_normal' ? 'truncatedNormalDesc' : prior.distribution === 'half_normal' ? 'halfNormalDesc' : 'normalDesc'}`)}
                </p>
              </div>

              {/* Distribution-specific parameters */}
              {prior.distribution !== 'half_normal' && (
                <div>
                  <Label className="text-xs">{t('priors.mean')}</Label>
                  <Input
                    type="number"
                    step="0.1"
                    value={prior.mean ?? ''}
                    onChange={(e) => handleParamChange(
                      variable, 
                      'mean', 
                      e.target.value ? parseFloat(e.target.value) : undefined
                    )}
                    disabled={disabled}
                    className="text-sm"
                  />
                </div>
              )}

              <div>
                <Label className="text-xs">{t('priors.stdDev')}</Label>
                <Input
                  type="number"
                  step="0.1"
                  min="0.01"
                  value={prior.std ?? ''}
                  onChange={(e) => handleParamChange(
                    variable, 
                    'std', 
                    e.target.value ? parseFloat(e.target.value) : undefined
                  )}
                  disabled={disabled}
                  className="text-sm"
                />
              </div>

              {prior.distribution === 'truncated_normal' && (
                <>
                  <div>
                    <Label className="text-xs">{t('priors.lowerBound')}</Label>
                    <Input
                      type="number"
                      step="0.1"
                      value={prior.lower ?? ''}
                      onChange={(e) => handleParamChange(
                        variable, 
                        'lower', 
                        e.target.value ? parseFloat(e.target.value) : undefined
                      )}
                      disabled={disabled}
                      className="text-sm"
                    />
                  </div>
                  <div>
                    <Label className="text-xs">{t('priors.upperBound')}</Label>
                    <Input
                      type="number"
                      step="0.1"
                      value={prior.upper ?? ''}
                      onChange={(e) => handleParamChange(
                        variable, 
                        'upper', 
                        e.target.value ? parseFloat(e.target.value) : undefined
                      )}
                      disabled={disabled}
                      className="text-sm"
                    />
                  </div>
                </>
              )}
            </div>
          </div>
        ))}

        {Object.keys(priors).length === 0 && (
          <p className="text-sm text-muted-foreground text-center py-4">
            {t('priors.noCustomPriors')}
          </p>
        )}
      </div>
    </Card>
  );
}

export default PriorConfigPanel;
