import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, Trash2, Edit2, Users, AlertTriangle, X } from 'lucide-react';
import { variableGroupsApi, type VariableGroup, type VariableGroupCreate } from '@/api/services/variableGroups';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

// Predefined colors for groups
const GROUP_COLORS = [
  '#3B82F6', // blue
  '#10B981', // green
  '#F59E0B', // amber
  '#EF4444', // red
  '#8B5CF6', // violet
  '#EC4899', // pink
  '#06B6D4', // cyan
  '#F97316', // orange
];

interface VariableGroupManagerProps {
  projectId: string;
  availableVariables?: string[];
  compact?: boolean;
}

export function VariableGroupManager({
  projectId,
  availableVariables = [],
}: VariableGroupManagerProps) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [editingGroup, setEditingGroup] = useState<VariableGroup | null>(null);
  const [formData, setFormData] = useState<VariableGroupCreate>({
    name: '',
    description: '',
    variables: [],
    color: GROUP_COLORS[0],
  });

  // Fetch groups
  const { data: groups = [], isLoading } = useQuery({
    queryKey: ['variable-groups', projectId],
    queryFn: () => variableGroupsApi.list(projectId),
  });

  // Check overlaps
  const { data: overlapCheck } = useQuery({
    queryKey: ['variable-groups-overlap', projectId],
    queryFn: () => variableGroupsApi.checkOverlap(projectId),
    enabled: groups.length > 0,
  });

  // Create mutation
  const createMutation = useMutation({
    mutationFn: (data: VariableGroupCreate) => variableGroupsApi.create(projectId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['variable-groups', projectId] });
      setIsCreateDialogOpen(false);
      resetForm();
    },
  });

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: ({ groupId, data }: { groupId: string; data: VariableGroupCreate }) =>
      variableGroupsApi.update(projectId, groupId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['variable-groups', projectId] });
      setEditingGroup(null);
      resetForm();
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (groupId: string) => variableGroupsApi.delete(projectId, groupId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['variable-groups', projectId] });
    },
  });

  const resetForm = () => {
    setFormData({
      name: '',
      description: '',
      variables: [],
      color: GROUP_COLORS[groups.length % GROUP_COLORS.length],
    });
  };

  const openEditDialog = (group: VariableGroup) => {
    setEditingGroup(group);
    setFormData({
      name: group.name,
      description: group.description || '',
      variables: group.variables,
      color: group.color || GROUP_COLORS[0],
    });
  };

  const handleSubmit = () => {
    if (editingGroup) {
      updateMutation.mutate({ groupId: editingGroup.id, data: formData });
    } else {
      createMutation.mutate(formData);
    }
  };

  const toggleVariable = (variable: string) => {
    setFormData((prev) => ({
      ...prev,
      variables: prev.variables.includes(variable)
        ? prev.variables.filter((v) => v !== variable)
        : [...prev.variables, variable],
    }));
  };

  const handleDelete = (groupId: string, groupName: string) => {
    if (window.confirm(t('variableGroups.deleteConfirm', { name: groupName }))) {
      deleteMutation.mutate(groupId);
    }
  };

  // Get variables already assigned to other groups
  const getAssignedVariables = (excludeGroupId?: string) => {
    const assigned = new Set<string>();
    groups
      .filter((g) => g.id !== excludeGroupId)
      .forEach((g) => g.variables.forEach((v) => assigned.add(v)));
    return assigned;
  };

  const isDialogOpen = isCreateDialogOpen || editingGroup !== null;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-medium">{t('variableGroups.title')}</h3>
          <p className="text-sm text-muted-foreground">
            {t('variableGroups.description')}
          </p>
        </div>
        <Button onClick={() => setIsCreateDialogOpen(true)}>
          <Plus className="h-4 w-4 mr-2" />
          {t('variableGroups.createGroup')}
        </Button>
      </div>

      {/* Overlap warning */}
      {overlapCheck?.has_overlaps && (
        <div className="flex items-start gap-2 p-3 rounded-lg border border-yellow-500 bg-yellow-50 dark:bg-yellow-900/20">
          <AlertTriangle className="h-4 w-4 text-yellow-600 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-yellow-700 dark:text-yellow-400">
              {t('variableGroups.overlapWarning')}
            </p>
            <ul className="text-xs text-yellow-600 dark:text-yellow-500 mt-1">
              {Object.entries(overlapCheck.overlaps).map(([variable, groupNames]) => (
                <li key={variable}>
                  <strong>{variable}</strong>: {groupNames.join(', ')}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {/* Groups list */}
      {isLoading ? (
        <div className="text-center py-8 text-muted-foreground">
          {t('common.loading')}...
        </div>
      ) : groups.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-8">
            <Users className="h-12 w-12 text-muted-foreground mb-4" />
            <p className="text-muted-foreground text-center">
              {t('variableGroups.noGroups')}
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-3 md:grid-cols-2">
          {groups.map((group) => (
            <Card key={group.id} className="relative">
              <div
                className="absolute top-0 left-0 w-1 h-full rounded-l-lg"
                style={{ backgroundColor: group.color || '#6B7280' }}
              />
              <CardHeader className="pb-2 pl-5">
                <div className="flex items-start justify-between">
                  <div>
                    <CardTitle className="text-base">{group.name}</CardTitle>
                    {group.description && (
                      <CardDescription className="text-xs mt-1">
                        {group.description}
                      </CardDescription>
                    )}
                  </div>
                  <div className="flex gap-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => openEditDialog(group)}
                    >
                      <Edit2 className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDelete(group.id, group.name)}
                      className="text-destructive hover:text-destructive"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="pl-5 pt-0">
                <div className="flex flex-wrap gap-1">
                  {group.variables.map((variable) => (
                    <span
                      key={variable}
                      className="px-2 py-0.5 text-xs rounded-full bg-muted"
                    >
                      {variable}
                    </span>
                  ))}
                </div>
                <p className="text-xs text-muted-foreground mt-2">
                  {t('variableGroups.members')}: {group.variables.length}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Create/Edit Dialog */}
      <Dialog
        open={isDialogOpen}
        onOpenChange={(open) => {
          if (!open) {
            setIsCreateDialogOpen(false);
            setEditingGroup(null);
            resetForm();
          }
        }}
      >
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>
              {editingGroup
                ? t('variableGroups.editGroup')
                : t('variableGroups.createGroup')}
            </DialogTitle>
            <DialogDescription>
              {t('variableGroups.dialogDescription')}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>{t('variableGroups.groupName')}</Label>
              <Input
                placeholder={t('variableGroups.groupNamePlaceholder')}
                value={formData.name}
                onChange={(e) =>
                  setFormData((prev) => ({ ...prev, name: e.target.value }))
                }
              />
            </div>

            <div className="space-y-2">
              <Label>{t('variableGroups.descriptionLabel')}</Label>
              <Input
                placeholder={t('variableGroups.descriptionPlaceholder')}
                value={formData.description || ''}
                onChange={(e) =>
                  setFormData((prev) => ({ ...prev, description: e.target.value }))
                }
              />
            </div>

            <div className="space-y-2">
              <Label>{t('variableGroups.color')}</Label>
              <div className="flex gap-2">
                {GROUP_COLORS.map((color) => (
                  <button
                    key={color}
                    type="button"
                    className={`w-6 h-6 rounded-full border-2 ${
                      formData.color === color
                        ? 'border-foreground'
                        : 'border-transparent'
                    }`}
                    style={{ backgroundColor: color }}
                    onClick={() => setFormData((prev) => ({ ...prev, color }))}
                  />
                ))}
              </div>
            </div>

            <div className="space-y-2">
              <Label>{t('variableGroups.selectVariables')}</Label>
              <div className="max-h-48 overflow-y-auto rounded-lg border p-2 space-y-1">
                {availableVariables.length === 0 ? (
                  <p className="text-sm text-muted-foreground text-center py-2">
                    {t('variableGroups.noVariablesAvailable')}
                  </p>
                ) : (
                  availableVariables.map((variable) => {
                    const assignedTo = getAssignedVariables(editingGroup?.id);
                    const isAssignedElsewhere = assignedTo.has(variable);
                    const isSelected = formData.variables.includes(variable);

                    return (
                      <label
                        key={variable}
                        className={`flex items-center gap-2 p-2 rounded hover:bg-muted cursor-pointer ${
                          isAssignedElsewhere && !isSelected
                            ? 'opacity-50'
                            : ''
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => toggleVariable(variable)}
                          className="h-4 w-4 rounded"
                        />
                        <span className="text-sm">{variable}</span>
                        {isAssignedElsewhere && !isSelected && (
                          <span className="text-xs text-muted-foreground ml-auto">
                            ({t('variableGroups.assignedToOther')})
                          </span>
                        )}
                      </label>
                    );
                  })
                )}
              </div>
              {formData.variables.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-2">
                  {formData.variables.map((v) => (
                    <span
                      key={v}
                      className="inline-flex items-center gap-1 px-2 py-0.5 text-xs rounded-full bg-primary/10 text-primary"
                    >
                      {v}
                      <button
                        type="button"
                        onClick={() => toggleVariable(v)}
                        className="hover:text-primary/80"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setIsCreateDialogOpen(false);
                setEditingGroup(null);
                resetForm();
              }}
            >
              {t('common.cancel')}
            </Button>
            <Button
              onClick={handleSubmit}
              disabled={
                !formData.name.trim() ||
                formData.variables.length === 0 ||
                createMutation.isPending ||
                updateMutation.isPending
              }
            >
              {createMutation.isPending || updateMutation.isPending
                ? t('common.saving')
                : editingGroup
                  ? t('common.save')
                  : t('variableGroups.createGroup')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default VariableGroupManager;
