import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { variableMetadataApi, variableGroupsApi, projectsApi, VARIABLE_TYPES, getVariableTypeColor } from '@/api/services';
import type { VariableSummary, VariableMetadataUpdate } from '@/api/services/variableMetadata';
import { Header } from '@/components/layout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Loader2,
  Save,
  Tag,
  DollarSign,
  BarChart3,
  Layers,
  Settings,
  Search,
  Filter,
  Plus,
  Trash2,
  Palette,
} from 'lucide-react';

interface VariableGroup {
  id: string;
  name: string;
  color: string | null;
  variables: string[];
}

export function VariableManagementPage() {
  const { t, i18n } = useTranslation();
  const { projectId } = useParams<{ projectId: string }>();
  const queryClient = useQueryClient();
  const lang = i18n.language;

  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState<string>('all');
  const [editingVariable, setEditingVariable] = useState<VariableSummary | null>(null);
  const [editForm, setEditForm] = useState<VariableMetadataUpdate>({});
  
  // Group management state
  const [showGroupDialog, setShowGroupDialog] = useState(false);
  const [editingGroup, setEditingGroup] = useState<VariableGroup | null>(null);
  const [newGroupName, setNewGroupName] = useState('');
  const [newGroupColor, setNewGroupColor] = useState('#3B82F6');
  const [selectedGroupVariables, setSelectedGroupVariables] = useState<string[]>([]);

  // Fetch project for name
  const { data: project } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => projectsApi.get(projectId!),
    enabled: !!projectId,
  });

  // Fetch variables
  const { data: variables = [], isLoading } = useQuery({
    queryKey: ['variables', projectId],
    queryFn: () => variableMetadataApi.list(projectId!),
    enabled: !!projectId,
  });

  // Fetch groups
  const { data: groups = [] } = useQuery({
    queryKey: ['variable-groups', projectId],
    queryFn: () => variableGroupsApi.list(projectId!),
    enabled: !!projectId,
  });

  // Get spending options for support variable mapping
  const { data: spendingOptions = [] } = useQuery({
    queryKey: ['spending-options', projectId],
    queryFn: () => variableMetadataApi.getSpendingOptions(projectId!),
    enabled: !!projectId,
  });

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: ({ variableName, data }: { variableName: string; data: VariableMetadataUpdate }) =>
      variableMetadataApi.update(projectId!, variableName, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['variables', projectId] });
      queryClient.invalidateQueries({ queryKey: ['spending-options', projectId] });
      setEditingVariable(null);
    },
  });

  // Create group mutation
  const createGroupMutation = useMutation({
    mutationFn: (data: { name: string; color: string }) =>
      variableGroupsApi.create(projectId!, { ...data, variables: [] }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['variable-groups', projectId] });
      setShowGroupDialog(false);
      setNewGroupName('');
      setNewGroupColor('#3B82F6');
    },
  });

  // Update group mutation
  const updateGroupMutation = useMutation({
    mutationFn: ({ groupId, data }: { groupId: string; data: { name: string; color: string; variables: string[] } }) =>
      variableGroupsApi.update(projectId!, groupId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['variable-groups', projectId] });
      queryClient.invalidateQueries({ queryKey: ['variables', projectId] });
      closeGroupDialog();
    },
  });

  // Delete group mutation
  const deleteGroupMutation = useMutation({
    mutationFn: (groupId: string) => variableGroupsApi.delete(projectId!, groupId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['variable-groups', projectId] });
      queryClient.invalidateQueries({ queryKey: ['variables', projectId] });
    },
  });

  const closeGroupDialog = () => {
    setShowGroupDialog(false);
    setEditingGroup(null);
    setNewGroupName('');
    setNewGroupColor('#3B82F6');
    setSelectedGroupVariables([]);
  };

  const openEditGroupDialog = (group: VariableGroup) => {
    setEditingGroup(group);
    setNewGroupName(group.name);
    setNewGroupColor(group.color || '#3B82F6');
    setSelectedGroupVariables(group.variables || []);
    setShowGroupDialog(true);
  };

  const handleSaveGroup = () => {
    if (!newGroupName.trim()) return;
    
    if (editingGroup) {
      updateGroupMutation.mutate({
        groupId: editingGroup.id,
        data: {
          name: newGroupName.trim(),
          color: newGroupColor,
          variables: selectedGroupVariables,
        },
      });
    } else {
      createGroupMutation.mutate({ name: newGroupName.trim(), color: newGroupColor });
    }
  };

  const toggleGroupVariable = (varName: string) => {
    setSelectedGroupVariables(prev =>
      prev.includes(varName)
        ? prev.filter(v => v !== varName)
        : [...prev, varName]
    );
  };

  // Filter variables
  const filteredVariables = variables.filter((v: VariableSummary) => {
    const matchesSearch = v.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      v.metadata?.display_name?.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesType = filterType === 'all' || 
      (v.metadata?.variable_type || 'other') === filterType;
    return matchesSearch && matchesType;
  });

  // Count by type
  const typeCounts = VARIABLE_TYPES.map(type => ({
    ...type,
    count: variables.filter((v: VariableSummary) => 
      (v.metadata?.variable_type || 'other') === type.value
    ).length,
  }));

  const handleEdit = (variable: VariableSummary) => {
    setEditingVariable(variable);
    setEditForm({
      display_name: variable.metadata?.display_name || '',
      variable_type: variable.metadata?.variable_type || 'other',
      unit: variable.metadata?.unit || '',
      related_spending_variable: variable.metadata?.related_spending_variable || '',
      cost_per_unit: variable.metadata?.cost_per_unit,
      group_id: variable.metadata?.group_id,
      description: variable.metadata?.description || '',
    });
  };

  const handleSave = () => {
    if (!editingVariable) return;
    updateMutation.mutate({
      variableName: editingVariable.name,
      data: editForm,
    });
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'target': return <BarChart3 className="h-4 w-4" />;
      case 'spending': return <DollarSign className="h-4 w-4" />;
      case 'support': return <Tag className="h-4 w-4" />;
      case 'dimension': return <Layers className="h-4 w-4" />;
      case 'control': return <Settings className="h-4 w-4" />;
      default: return <Tag className="h-4 w-4" />;
    }
  };

  return (
    <div className="flex flex-col min-h-screen bg-app-gradient">
      <Header title={t('variables.title', '变量管理')} projectName={project?.name} />

      <div className="p-6 space-y-6">
        {/* Summary Cards */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          {typeCounts.map((type) => (
            <Card
              key={type.value}
              variant="glass"
              hover="lift"
              className={`cursor-pointer ${filterType === type.value ? 'ring-2 ring-primary shadow-glow-primary' : ''}`}
              onClick={() => setFilterType(filterType === type.value ? 'all' : type.value)}
            >
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div className={`p-2.5 rounded-xl ${getVariableTypeColor(type.value)} text-white shadow-md`}>
                    {getTypeIcon(type.value)}
                  </div>
                  <span className="text-2xl font-bold">{type.count}</span>
                </div>
                <p className="text-sm text-muted-foreground mt-2">
                  {lang.startsWith('zh') ? type.label : type.labelEn}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Variable Groups Management */}
        <Card variant="glass">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-primary text-white">
                    <Palette className="h-4 w-4" />
                  </div>
                  {t('variables.groups', '变量分组')}
                </CardTitle>
                <CardDescription>
                  {t('variables.groupsDesc', '管理变量分组，用于图表着色和分类展示')}
                </CardDescription>
              </div>
              <Button variant="gradient" onClick={() => setShowGroupDialog(true)} size="sm">
                <Plus className="h-4 w-4 mr-2" />
                {t('variables.createGroup', '新建分组')}
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {groups.length === 0 ? (
              <p className="text-muted-foreground text-center py-4">
                {t('variables.noGroups', '暂无分组，点击上方按钮创建')}
              </p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {groups.map((group: VariableGroup) => (
                  <div
                    key={group.id}
                    className="flex items-center gap-2 px-3 py-2 glass-sm rounded-xl group cursor-pointer hover:bg-white/50 dark:hover:bg-white/10 transition-all duration-200"
                    onClick={() => openEditGroupDialog(group)}
                  >
                    <div
                      className="w-4 h-4 rounded-full shadow-sm"
                      style={{ backgroundColor: group.color || '#888' }}
                    />
                    <span className="font-medium">{group.name}</span>
                    <span className="text-xs text-muted-foreground">
                      ({group.variables?.length || 0})
                    </span>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        if (confirm(t('variables.confirmDeleteGroup', `确认删除分组 "${group.name}"？`))) {
                          deleteGroupMutation.mutate(group.id);
                        }
                      }}
                      className="opacity-0 group-hover:opacity-100 transition-opacity text-destructive hover:text-destructive/80"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Search and Filter */}
        <Card variant="glass">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>{t('variables.list', '变量列表')}</CardTitle>
                <CardDescription>
                  {t('variables.listDesc', '配置变量类型、显示名称和分组')}
                </CardDescription>
              </div>
              <div className="flex gap-2">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder={t('common.search', '搜索...')}
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-9 w-64"
                    variant="glass"
                  />
                </div>
                <Select value={filterType} onValueChange={setFilterType}>
                  <SelectTrigger className="w-40">
                    <Filter className="h-4 w-4 mr-2" />
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">{t('common.all', '全部')}</SelectItem>
                    {VARIABLE_TYPES.map((type) => (
                      <SelectItem key={type.value} value={type.value}>
                        {lang.startsWith('zh') ? type.label : type.labelEn}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-8 w-8 animate-spin" />
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>{t('variables.name', '变量名')}</TableHead>
                    <TableHead>{t('variables.displayName', '显示名称')}</TableHead>
                    <TableHead>{t('variables.type', '类型')}</TableHead>
                    <TableHead>{t('variables.unit', '单位')}</TableHead>
                    <TableHead>{t('variables.group', '分组')}</TableHead>
                    <TableHead>{t('variables.relatedSpending', '关联花费')}</TableHead>
                    <TableHead></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredVariables.map((variable: VariableSummary) => {
                    const type = variable.metadata?.variable_type || 'other';
                    const typeInfo = VARIABLE_TYPES.find(t => t.value === type);
                    
                    return (
                      <TableRow key={variable.name}>
                        <TableCell className="font-mono text-sm">
                          {variable.name}
                          {variable.dtype && (
                            <span className="ml-2 text-xs text-muted-foreground">
                              ({variable.dtype})
                            </span>
                          )}
                        </TableCell>
                        <TableCell>
                          {variable.metadata?.display_name || '-'}
                        </TableCell>
                        <TableCell>
                          <Badge className={`${getVariableTypeColor(type)} text-white`}>
                            {lang.startsWith('zh') ? typeInfo?.label : typeInfo?.labelEn}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          {variable.metadata?.unit || '-'}
                        </TableCell>
                        <TableCell>
                          {variable.group_name ? (
                            <div className="flex items-center gap-2">
                              <div
                                className="w-3 h-3 rounded-full"
                                style={{ backgroundColor: variable.group_color || '#888' }}
                              />
                              {variable.group_name}
                            </div>
                          ) : '-'}
                        </TableCell>
                        <TableCell>
                          {variable.metadata?.related_spending_variable || '-'}
                        </TableCell>
                        <TableCell>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleEdit(variable)}
                          >
                            {t('common.edit', '编辑')}
                          </Button>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Edit Dialog */}
      <Dialog open={!!editingVariable} onOpenChange={() => setEditingVariable(null)}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>{t('variables.edit', '编辑变量')}</DialogTitle>
            <DialogDescription>
              {editingVariable?.name}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>{t('variables.displayName', '显示名称')}</Label>
              <Input
                value={editForm.display_name || ''}
                onChange={(e) => setEditForm({ ...editForm, display_name: e.target.value })}
                placeholder={t('variables.displayNamePlaceholder', '例如：电视广告花费')}
              />
            </div>

            <div className="space-y-2">
              <Label>{t('variables.type', '变量类型')}</Label>
              <Select
                value={editForm.variable_type || 'other'}
                onValueChange={(v) => setEditForm({ ...editForm, variable_type: v })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {VARIABLE_TYPES.map((type) => (
                    <SelectItem key={type.value} value={type.value}>
                      <div className="flex items-center gap-2">
                        <div className={`w-2 h-2 rounded-full ${getVariableTypeColor(type.value)}`} />
                        {lang.startsWith('zh') ? type.label : type.labelEn}
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                {VARIABLE_TYPES.find(t => t.value === editForm.variable_type)?.description}
              </p>
            </div>

            <div className="space-y-2">
              <Label>{t('variables.unit', '单位')}</Label>
              <Input
                value={editForm.unit || ''}
                onChange={(e) => setEditForm({ ...editForm, unit: e.target.value })}
                placeholder={t('variables.unitPlaceholder', '例如：元、次、GRP')}
              />
            </div>

            <div className="space-y-2">
              <Label>{t('variables.group', '所属分组')}</Label>
              <Select
                value={editForm.group_id || '_none'}
                onValueChange={(v) => setEditForm({ ...editForm, group_id: v === '_none' ? undefined : v })}
              >
                <SelectTrigger>
                  <SelectValue placeholder={t('common.none', '无')} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="_none">{t('common.none', '无')}</SelectItem>
                  {groups.map((group: VariableGroup) => (
                    <SelectItem key={group.id} value={group.id}>
                      <div className="flex items-center gap-2">
                        <div
                          className="w-3 h-3 rounded-full"
                          style={{ backgroundColor: group.color || '#888' }}
                        />
                        {group.name}
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {editForm.variable_type === 'support' && (
              <>
                <div className="space-y-2">
                  <Label>{t('variables.relatedSpending', '关联花费变量')}</Label>
                  <Select
                    value={editForm.related_spending_variable || '_none'}
                    onValueChange={(v) => setEditForm({ ...editForm, related_spending_variable: v === '_none' ? undefined : v })}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder={t('variables.selectSpending', '选择关联的花费变量')} />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="_none">{t('common.none', '无')}</SelectItem>
                      {spendingOptions.map((name: string) => (
                        <SelectItem key={name} value={name}>{name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-muted-foreground">
                    {t('variables.relatedSpendingDesc', '用于ROI计算，将支持指标与对应的花费变量关联')}
                  </p>
                </div>

                <div className="space-y-2">
                  <Label>{t('variables.costPerUnit', '单位成本')}</Label>
                  <Input
                    type="number"
                    value={editForm.cost_per_unit || ''}
                    onChange={(e) => setEditForm({ ...editForm, cost_per_unit: parseFloat(e.target.value) || undefined })}
                    placeholder={t('variables.costPerUnitPlaceholder', '例如：每GRP 5000元')}
                  />
                  <p className="text-xs text-muted-foreground">
                    {t('variables.costPerUnitDesc', '如果没有关联花费变量，可以设置单位成本用于ROI计算')}
                  </p>
                </div>
              </>
            )}

            <div className="space-y-2">
              <Label>{t('common.description', '描述')}</Label>
              <Input
                value={editForm.description || ''}
                onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                placeholder={t('variables.descriptionPlaceholder', '变量说明...')}
              />
            </div>
          </div>

          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setEditingVariable(null)}>
              {t('common.cancel', '取消')}
            </Button>
            <Button onClick={handleSave} disabled={updateMutation.isPending}>
              {updateMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              <Save className="mr-2 h-4 w-4" />
              {t('common.save', '保存')}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Create/Edit Group Dialog */}
      <Dialog open={showGroupDialog} onOpenChange={closeGroupDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>
              {editingGroup 
                ? t('variables.editGroup', '编辑分组') 
                : t('variables.createGroup', '新建分组')}
            </DialogTitle>
            <DialogDescription>
              {editingGroup
                ? t('variables.editGroupDesc', '修改分组名称、颜色和成员变量')
                : t('variables.createGroupDesc', '创建一个新的变量分组')}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>{t('common.name', '名称')}</Label>
              <Input
                value={newGroupName}
                onChange={(e) => setNewGroupName(e.target.value)}
                placeholder={t('variables.groupNamePlaceholder', '例如：TV广告')}
              />
            </div>
            <div className="space-y-2">
              <Label>{t('variables.groupColor', '颜色')}</Label>
              <div className="flex items-center gap-3">
                <input
                  type="color"
                  value={newGroupColor}
                  onChange={(e) => setNewGroupColor(e.target.value)}
                  className="w-10 h-10 rounded border cursor-pointer"
                />
                <div className="flex gap-2">
                  {['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#06B6D4', '#84CC16'].map((color) => (
                    <button
                      key={color}
                      onClick={() => setNewGroupColor(color)}
                      className={`w-6 h-6 rounded-full border-2 ${newGroupColor === color ? 'border-foreground' : 'border-transparent'}`}
                      style={{ backgroundColor: color }}
                    />
                  ))}
                </div>
              </div>
            </div>
            {/* Variable selection (only for edit mode) */}
            {editingGroup && (
              <div className="space-y-2">
                <Label>{t('variables.groupMembers', '成员变量')}</Label>
                <div className="max-h-48 overflow-y-auto border rounded-lg p-2">
                  <div className="flex flex-wrap gap-1">
                    {variables.map((v: VariableSummary) => (
                      <button
                        key={v.name}
                        onClick={() => toggleGroupVariable(v.name)}
                        className={`px-2 py-1 text-xs rounded-md border transition-colors ${
                          selectedGroupVariables.includes(v.name)
                            ? 'bg-primary text-primary-foreground border-primary'
                            : 'bg-background hover:bg-muted border-input'
                        }`}
                      >
                        {v.name}
                      </button>
                    ))}
                  </div>
                </div>
                <p className="text-xs text-muted-foreground">
                  {t('variables.selectedCount', '已选择 {{count}} 个变量', { count: selectedGroupVariables.length })}
                </p>
              </div>
            )}
          </div>
          <div className="flex justify-end gap-2 mt-4">
            <Button variant="outline" onClick={closeGroupDialog}>
              {t('common.cancel', '取消')}
            </Button>
            <Button 
              onClick={handleSaveGroup} 
              disabled={!newGroupName.trim() || createGroupMutation.isPending || updateGroupMutation.isPending}
            >
              {(createGroupMutation.isPending || updateGroupMutation.isPending) && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {editingGroup ? (
                <>
                  <Save className="mr-2 h-4 w-4" />
                  {t('common.save', '保存')}
                </>
              ) : (
                <>
                  <Plus className="mr-2 h-4 w-4" />
                  {t('common.create', '创建')}
                </>
              )}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default VariableManagementPage;
