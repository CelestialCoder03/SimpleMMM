import { useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { datasetsApi, projectsApi } from '@/api/services';
import { Header } from '@/components/layout';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Upload,
  Loader2,
  FileSpreadsheet,
  AlertCircle,
  CheckCircle2,
  ArrowLeft,
} from 'lucide-react';

type UpdateMode = 'new_version' | 'replace';

export function DatasetUpdatePage() {
  const { t } = useTranslation();
  const { projectId, datasetId } = useParams<{ projectId: string; datasetId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [file, setFile] = useState<File | null>(null);
  const [updateMode, setUpdateMode] = useState<UpdateMode>('new_version');
  const [preserveMetadata, setPreserveMetadata] = useState(true);

  // Fetch project
  const { data: project } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => projectsApi.get(projectId!),
    enabled: !!projectId,
  });

  // Fetch current dataset
  const { data: dataset } = useQuery({
    queryKey: ['dataset', projectId, datasetId],
    queryFn: () => datasetsApi.get(projectId!, datasetId!),
    enabled: !!projectId && !!datasetId,
  });

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: () => {
      if (!file) throw new Error('No file selected');
      return datasetsApi.update(projectId!, datasetId!, file, updateMode, preserveMetadata);
    },
    onSuccess: (updatedDataset) => {
      queryClient.invalidateQueries({ queryKey: ['datasets', projectId] });
      queryClient.invalidateQueries({ queryKey: ['dataset', projectId, datasetId] });
      navigate(`/projects/${projectId}/datasets/${updatedDataset.id}`);
    },
  });

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0]);
    }
  };

  const handleSubmit = () => {
    if (file) {
      updateMutation.mutate();
    }
  };

  return (
    <div className="flex flex-col">
      <Header title={t('datasets.updateTitle', '更新数据集')} projectName={project?.name} />

      <div className="mx-auto w-full max-w-2xl p-6">
        <Button
          variant="ghost"
          className="mb-4"
          onClick={() => navigate(`/projects/${projectId}/datasets/${datasetId}`)}
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          {t('common.back', '返回')}
        </Button>

        <Card>
          <CardHeader>
            <CardTitle>{t('datasets.updateDataset', '更新数据集')}</CardTitle>
            <CardDescription>
              {t('datasets.updateDesc', '上传新的数据文件来更新数据集 "{{name}}"', { name: dataset?.name })}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Current dataset info */}
            {dataset && (
              <div className="p-4 rounded-lg bg-muted">
                <p className="text-sm font-medium">{t('datasets.currentDataset', '当前数据集')}</p>
                <p className="text-sm text-muted-foreground mt-1">
                  {dataset.name} · {dataset.row_count?.toLocaleString()} {t('datasets.rows', '行')} · {dataset.column_count} {t('datasets.columns', '列')}
                </p>
              </div>
            )}

            {/* Update mode selection */}
            <div className="space-y-3">
              <Label>{t('datasets.updateMode', '更新方式')}</Label>
              <Select value={updateMode} onValueChange={(v) => setUpdateMode(v as UpdateMode)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="new_version">
                    {t('datasets.newVersion', '创建新版本')}
                  </SelectItem>
                  <SelectItem value="replace">
                    {t('datasets.replace', '替换现有文件')}
                  </SelectItem>
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                {updateMode === 'new_version'
                  ? t('datasets.newVersionDesc', '创建一个新的数据集版本，保留原始数据')
                  : t('datasets.replaceDesc', '直接替换现有数据文件，不创建新版本')}
              </p>
            </div>j

            {/* Preserve metadata option */}
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label>{t('datasets.preserveMetadata', '保留元数据')}</Label>
                <p className="text-xs text-muted-foreground">
                  {t('datasets.preserveMetadataDesc', '保留变量类型、显示名称等元数据设置')}
                </p>
              </div>
              <Switch
                checked={preserveMetadata}
                onCheckedChange={setPreserveMetadata}
              />
            </div>

            {/* File upload area */}
            <div
              onClick={() => fileInputRef.current?.click()}
              className={`
                border-2 border-dashed rounded-lg p-8 text-center cursor-pointer
                transition-colors border-muted-foreground/25 hover:border-primary/50
                ${file ? 'bg-green-50 border-green-300 dark:bg-green-900/20 dark:border-green-700' : ''}
              `}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv,.xlsx,.xls"
                onChange={handleFileChange}
                className="hidden"
              />
              {file ? (
                <div className="flex flex-col items-center gap-2">
                  <CheckCircle2 className="h-10 w-10 text-green-500" />
                  <p className="font-medium">{file.name}</p>
                  <p className="text-sm text-muted-foreground">
                    {(file.size / 1024 / 1024).toFixed(2)} MB
                  </p>
                  <Button variant="outline" size="sm" onClick={(e) => { e.stopPropagation(); setFile(null); }}>
                    {t('common.change', '更换文件')}
                  </Button>
                </div>
              ) : (
                <div className="flex flex-col items-center gap-2">
                  <FileSpreadsheet className="h-10 w-10 text-muted-foreground" />
                  <p className="font-medium">
                    {t('datasets.clickToSelect', '点击选择文件')}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    {t('datasets.supportedFormats', '支持 CSV, Excel (.xlsx, .xls) 格式')}
                  </p>
                </div>
              )}
            </div>

            {/* Error message */}
            {updateMutation.isError && (
              <div className="flex items-center gap-2 p-3 rounded-lg bg-destructive/10 text-destructive">
                <AlertCircle className="h-4 w-4" />
                <span className="text-sm">
                  {updateMutation.error instanceof Error
                    ? updateMutation.error.message
                    : t('common.error', '发生错误')}
                </span>
              </div>
            )}

            {/* Submit button */}
            <div className="flex justify-end gap-2">
              <Button
                variant="outline"
                onClick={() => navigate(`/projects/${projectId}/datasets/${datasetId}`)}
              >
                {t('common.cancel', '取消')}
              </Button>
              <Button
                onClick={handleSubmit}
                disabled={!file || updateMutation.isPending}
              >
                {updateMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                <Upload className="mr-2 h-4 w-4" />
                {t('datasets.uploadUpdate', '上传更新')}
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

export default DatasetUpdatePage;
