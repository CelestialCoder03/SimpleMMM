import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useQuery } from '@tanstack/react-query';
import { Plus, Trash2, AlertTriangle, Info, Users } from 'lucide-react';
import { variableGroupsApi, type VariableGroup } from '@/api/services/variableGroups';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';

export interface CoefficientConstraint {
  variable: string;
  sign: 'positive' | 'negative' | 'none';
  min?: number;
  max?: number;
}

export interface ContributionConstraint {
  variable: string;
  minPct?: number;
  maxPct?: number;
}

export interface GroupContributionConstraint {
  groupName: string;
  variables: string[];
  minPct?: number;
  maxPct?: number;
}

export interface ConstraintsConfig {
  applyPositiveToAll: boolean;
  coefficients: CoefficientConstraint[];
  contributions: ContributionConstraint[];
  groupContributions: GroupContributionConstraint[];
}

interface AdvancedConstraintsPanelProps {
  features: string[];
  value: ConstraintsConfig;
  onChange: (config: ConstraintsConfig) => void;
  projectId?: string;
}

export function AdvancedConstraintsPanel({
  features,
  value,
  onChange,
  projectId,
}: AdvancedConstraintsPanelProps) {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState<'coefficient' | 'contribution' | 'group'>('coefficient');

  // Fetch variable groups from project
  const { data: variableGroups = [] } = useQuery({
    queryKey: ['variableGroups', projectId],
    queryFn: () => variableGroupsApi.list(projectId!),
    enabled: !!projectId,
  });

  const addCoefficientConstraint = () => {
    const availableFeatures = features.filter(
      (f) => !value.coefficients.some((c) => c.variable === f)
    );
    if (availableFeatures.length === 0) return;

    onChange({
      ...value,
      coefficients: [
        ...value.coefficients,
        { variable: availableFeatures[0], sign: 'positive' },
      ],
    });
  };

  const updateCoefficientConstraint = (
    index: number,
    updates: Partial<CoefficientConstraint>
  ) => {
    const newConstraints = [...value.coefficients];
    newConstraints[index] = { ...newConstraints[index], ...updates };
    onChange({ ...value, coefficients: newConstraints });
  };

  const removeCoefficientConstraint = (index: number) => {
    onChange({
      ...value,
      coefficients: value.coefficients.filter((_, i) => i !== index),
    });
  };

  const addContributionConstraint = () => {
    const availableFeatures = features.filter(
      (f) => !value.contributions.some((c) => c.variable === f)
    );
    if (availableFeatures.length === 0) return;

    onChange({
      ...value,
      contributions: [
        ...value.contributions,
        { variable: availableFeatures[0], minPct: 0, maxPct: 100 },
      ],
    });
  };

  const updateContributionConstraint = (
    index: number,
    updates: Partial<ContributionConstraint>
  ) => {
    const newConstraints = [...value.contributions];
    newConstraints[index] = { ...newConstraints[index], ...updates };
    onChange({ ...value, contributions: newConstraints });
  };

  const removeContributionConstraint = (index: number) => {
    onChange({
      ...value,
      contributions: value.contributions.filter((_, i) => i !== index),
    });
  };

  const getAvailableFeaturesForCoefficient = (currentVariable?: string) => {
    return features.filter(
      (f) => f === currentVariable || !value.coefficients.some((c) => c.variable === f)
    );
  };

  const getAvailableFeaturesForContribution = (currentVariable?: string) => {
    return features.filter(
      (f) => f === currentVariable || !value.contributions.some((c) => c.variable === f)
    );
  };

  const addGroupConstraint = () => {
    const availableGroups = variableGroups.filter(
      (g: VariableGroup) => !value.groupContributions.some((gc) => gc.groupName === g.name)
    );
    if (availableGroups.length === 0) return;

    const group = availableGroups[0];
    onChange({
      ...value,
      groupContributions: [
        ...value.groupContributions,
        { groupName: group.name, variables: group.variables, minPct: 0, maxPct: 100 },
      ],
    });
  };

  const updateGroupConstraint = (
    index: number,
    updates: Partial<GroupContributionConstraint>
  ) => {
    const newConstraints = [...value.groupContributions];
    newConstraints[index] = { ...newConstraints[index], ...updates };
    onChange({ ...value, groupContributions: newConstraints });
  };

  const removeGroupConstraint = (index: number) => {
    onChange({
      ...value,
      groupContributions: value.groupContributions.filter((_, i) => i !== index),
    });
  };

  const getAvailableGroups = (currentGroupName?: string) => {
    return variableGroups.filter(
      (g: VariableGroup) => g.name === currentGroupName || !value.groupContributions.some((gc) => gc.groupName === g.name)
    );
  };

  // Check for potential conflicts
  const hasContributionConflict = () => {
    const totalMinPct = value.contributions.reduce((sum, c) => sum + (c.minPct || 0), 0);
    const totalMaxPct = value.contributions.reduce((sum, c) => sum + (c.maxPct || 100), 0);
    return totalMinPct > 100 || totalMaxPct < 100;
  };

  return (
    <div className="space-y-6">
      <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as typeof activeTab)}>
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="coefficient">{t('constraints.coefficientConstraints')}</TabsTrigger>
          <TabsTrigger value="contribution">{t('constraints.contributionConstraints')}</TabsTrigger>
          <TabsTrigger value="group" disabled={variableGroups.length === 0}>
            <Users className="h-4 w-4 mr-1" />
            {t('constraints.groupConstraints')}
          </TabsTrigger>
        </TabsList>

        {/* Coefficient Constraints Tab */}
        <TabsContent value="coefficient" className="space-y-4 mt-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">{t('constraints.coefficientConstraints')}</CardTitle>
              <CardDescription>
                {t('constraints.coefficientConstraintsDesc')}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Global positive constraint toggle */}
              <div className="flex items-center justify-between p-3 rounded-lg border bg-muted/50">
                <div className="flex items-center gap-2">
                  <Info className="h-4 w-4 text-muted-foreground" />
                  <div>
                    <p className="text-sm font-medium">{t('constraints.applyPositiveToAll')}</p>
                    <p className="text-xs text-muted-foreground">
                      {t('constraints.applyPositiveToAllDesc')}
                    </p>
                  </div>
                </div>
                <Switch
                  checked={value.applyPositiveToAll}
                  onCheckedChange={(checked) =>
                    onChange({ ...value, applyPositiveToAll: checked })
                  }
                />
              </div>

              {/* Per-variable constraints */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <Label>{t('constraints.perVariableConstraints')}</Label>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={addCoefficientConstraint}
                    disabled={value.coefficients.length >= features.length}
                  >
                    <Plus className="h-4 w-4 mr-1" />
                    {t('constraints.addConstraint')}
                  </Button>
                </div>

                {value.coefficients.length === 0 ? (
                  <p className="text-sm text-muted-foreground text-center py-4">
                    {t('constraints.noPerVariableConstraints')}
                  </p>
                ) : (
                  <div className="space-y-2">
                    {value.coefficients.map((constraint, index) => (
                      <div
                        key={index}
                        className="flex items-center gap-3 p-3 rounded-lg border bg-background"
                      >
                        <div className="flex-1 grid grid-cols-4 gap-3">
                          <div>
                            <Label className="text-xs">{t('constraints.variable')}</Label>
                            <Select
                              value={constraint.variable}
                              onValueChange={(v) =>
                                updateCoefficientConstraint(index, { variable: v })
                              }
                            >
                              <SelectTrigger className="h-8">
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                {getAvailableFeaturesForCoefficient(constraint.variable).map((f) => (
                                  <SelectItem key={f} value={f}>
                                    {f}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          </div>

                          <div>
                            <Label className="text-xs">{t('constraints.sign')}</Label>
                            <Select
                              value={constraint.sign}
                              onValueChange={(v) =>
                                updateCoefficientConstraint(index, {
                                  sign: v as CoefficientConstraint['sign'],
                                })
                              }
                            >
                              <SelectTrigger className="h-8">
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="positive">{t('constraints.positive')}</SelectItem>
                                <SelectItem value="negative">{t('constraints.negative')}</SelectItem>
                                <SelectItem value="none">{t('constraints.noConstraint')}</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>

                          <div>
                            <Label className="text-xs">{t('constraints.minValue')}</Label>
                            <Input
                              type="number"
                              step="0.01"
                              className="h-8"
                              placeholder={t('constraints.optional')}
                              value={constraint.min ?? ''}
                              onChange={(e) =>
                                updateCoefficientConstraint(index, {
                                  min: e.target.value ? parseFloat(e.target.value) : undefined,
                                })
                              }
                            />
                          </div>

                          <div>
                            <Label className="text-xs">{t('constraints.maxValue')}</Label>
                            <Input
                              type="number"
                              step="0.01"
                              className="h-8"
                              placeholder={t('constraints.optional')}
                              value={constraint.max ?? ''}
                              onChange={(e) =>
                                updateCoefficientConstraint(index, {
                                  max: e.target.value ? parseFloat(e.target.value) : undefined,
                                })
                              }
                            />
                          </div>
                        </div>

                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => removeCoefficientConstraint(index)}
                          className="text-destructive hover:text-destructive"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Contribution Constraints Tab */}
        <TabsContent value="contribution" className="space-y-4 mt-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">{t('constraints.contributionConstraints')}</CardTitle>
              <CardDescription>
                {t('constraints.contributionConstraintsDesc')}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Warning for conflicts */}
              {hasContributionConflict() && (
                <div className="flex items-center gap-2 p-3 rounded-lg border border-yellow-500 bg-yellow-50 dark:bg-yellow-900/20">
                  <AlertTriangle className="h-4 w-4 text-yellow-600" />
                  <p className="text-sm text-yellow-700 dark:text-yellow-400">
                    {t('constraints.contributionConflictWarning')}
                  </p>
                </div>
              )}

              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <Label>{t('constraints.variableContributions')}</Label>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={addContributionConstraint}
                    disabled={value.contributions.length >= features.length}
                  >
                    <Plus className="h-4 w-4 mr-1" />
                    {t('constraints.addConstraint')}
                  </Button>
                </div>

                {value.contributions.length === 0 ? (
                  <p className="text-sm text-muted-foreground text-center py-4">
                    {t('constraints.noContributionConstraints')}
                  </p>
                ) : (
                  <div className="space-y-2">
                    {value.contributions.map((constraint, index) => (
                      <div
                        key={index}
                        className="flex items-center gap-3 p-3 rounded-lg border bg-background"
                      >
                        <div className="flex-1 grid grid-cols-3 gap-3">
                          <div>
                            <Label className="text-xs">{t('constraints.variable')}</Label>
                            <Select
                              value={constraint.variable}
                              onValueChange={(v) =>
                                updateContributionConstraint(index, { variable: v })
                              }
                            >
                              <SelectTrigger className="h-8">
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                {getAvailableFeaturesForContribution(constraint.variable).map((f) => (
                                  <SelectItem key={f} value={f}>
                                    {f}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          </div>

                          <div>
                            <Label className="text-xs">{t('constraints.minContribution')}</Label>
                            <div className="relative">
                              <Input
                                type="number"
                                min={0}
                                max={100}
                                step={1}
                                className="h-8 pr-8"
                                value={constraint.minPct ?? ''}
                                onChange={(e) =>
                                  updateContributionConstraint(index, {
                                    minPct: e.target.value ? parseFloat(e.target.value) : undefined,
                                  })
                                }
                              />
                              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">
                                %
                              </span>
                            </div>
                          </div>

                          <div>
                            <Label className="text-xs">{t('constraints.maxContribution')}</Label>
                            <div className="relative">
                              <Input
                                type="number"
                                min={0}
                                max={100}
                                step={1}
                                className="h-8 pr-8"
                                value={constraint.maxPct ?? ''}
                                onChange={(e) =>
                                  updateContributionConstraint(index, {
                                    maxPct: e.target.value ? parseFloat(e.target.value) : undefined,
                                  })
                                }
                              />
                              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">
                                %
                              </span>
                            </div>
                          </div>
                        </div>

                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => removeContributionConstraint(index)}
                          className="text-destructive hover:text-destructive"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    ))}
                  </div>
                )}

                {/* Summary */}
                {value.contributions.length > 0 && (
                  <div className="p-3 rounded-lg bg-muted/50 text-sm">
                    <p className="font-medium mb-1">{t('constraints.summary')}</p>
                    <p className="text-muted-foreground">
                      {t('constraints.totalMinContribution')}: {value.contributions.reduce((sum, c) => sum + (c.minPct || 0), 0).toFixed(0)}%
                    </p>
                    <p className="text-muted-foreground">
                      {t('constraints.totalMaxContribution')}: {value.contributions.reduce((sum, c) => sum + (c.maxPct || 100), 0).toFixed(0)}%
                    </p>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Group Constraints Tab */}
        <TabsContent value="group" className="space-y-4 mt-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">{t('constraints.groupConstraints')}</CardTitle>
              <CardDescription>
                {t('constraints.groupConstraintsDesc')}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {variableGroups.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-4">
                  {t('constraints.noGroupsAvailable')}
                </p>
              ) : (
                <>
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <Label>{t('constraints.groupContributions')}</Label>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={addGroupConstraint}
                        disabled={value.groupContributions.length >= variableGroups.length}
                      >
                        <Plus className="h-4 w-4 mr-1" />
                        {t('constraints.addConstraint')}
                      </Button>
                    </div>

                    {value.groupContributions.length === 0 ? (
                      <p className="text-sm text-muted-foreground text-center py-4">
                        {t('constraints.noGroupConstraints')}
                      </p>
                    ) : (
                      <div className="space-y-2">
                        {value.groupContributions.map((constraint, index) => (
                          <div
                            key={index}
                            className="flex items-center gap-3 p-3 rounded-lg border bg-background"
                          >
                            <div className="flex-1 grid grid-cols-3 gap-3">
                              <div>
                                <Label className="text-xs">{t('constraints.group')}</Label>
                                <Select
                                  value={constraint.groupName}
                                  onValueChange={(v) => {
                                    const group = variableGroups.find((g: VariableGroup) => g.name === v);
                                    updateGroupConstraint(index, {
                                      groupName: v,
                                      variables: group?.variables || [],
                                    });
                                  }}
                                >
                                  <SelectTrigger className="h-8">
                                    <SelectValue />
                                  </SelectTrigger>
                                  <SelectContent>
                                    {getAvailableGroups(constraint.groupName).map((g: VariableGroup) => (
                                      <SelectItem key={g.id} value={g.name}>
                                        <div className="flex items-center gap-2">
                                          <div
                                            className="w-3 h-3 rounded-full"
                                            style={{ backgroundColor: g.color || '#3B82F6' }}
                                          />
                                          {g.name} ({g.variables.length})
                                        </div>
                                      </SelectItem>
                                    ))}
                                  </SelectContent>
                                </Select>
                              </div>

                              <div>
                                <Label className="text-xs">{t('constraints.minContribution')}</Label>
                                <div className="relative">
                                  <Input
                                    type="number"
                                    min={0}
                                    max={100}
                                    step={1}
                                    className="h-8 pr-8"
                                    value={constraint.minPct ?? ''}
                                    onChange={(e) =>
                                      updateGroupConstraint(index, {
                                        minPct: e.target.value ? parseFloat(e.target.value) : undefined,
                                      })
                                    }
                                  />
                                  <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">
                                    %
                                  </span>
                                </div>
                              </div>

                              <div>
                                <Label className="text-xs">{t('constraints.maxContribution')}</Label>
                                <div className="relative">
                                  <Input
                                    type="number"
                                    min={0}
                                    max={100}
                                    step={1}
                                    className="h-8 pr-8"
                                    value={constraint.maxPct ?? ''}
                                    onChange={(e) =>
                                      updateGroupConstraint(index, {
                                        maxPct: e.target.value ? parseFloat(e.target.value) : undefined,
                                      })
                                    }
                                  />
                                  <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">
                                    %
                                  </span>
                                </div>
                              </div>
                            </div>

                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => removeGroupConstraint(index)}
                              className="text-destructive hover:text-destructive"
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Group members info */}
                  {value.groupContributions.length > 0 && (
                    <div className="p-3 rounded-lg bg-muted/50 text-sm">
                      <p className="font-medium mb-2">{t('constraints.groupMembers')}</p>
                      {value.groupContributions.map((gc, index) => (
                        <div key={index} className="text-muted-foreground">
                          <span className="font-medium">{gc.groupName}:</span>{' '}
                          {gc.variables.join(', ')}
                        </div>
                      ))}
                    </div>
                  )}
                </>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

export default AdvancedConstraintsPanel;
