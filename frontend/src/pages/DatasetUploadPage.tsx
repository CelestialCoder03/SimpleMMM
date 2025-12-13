import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useMutation, useQueryClient, useQuery } from '@tanstack/react-query';
import { datasetsApi, projectsApi } from '@/api/services';
import { Header, PageWrapper } from '@/components/layout';
import { FileUpload } from '@/components/features/datasets/FileUpload';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { ArrowLeft, Loader2 } from 'lucide-react';

export function DatasetUploadPage() {
  const { t } = useTranslation();
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [datasetName, setDatasetName] = useState('');
  const [uploadProgress, setUploadProgress] = useState(0);

  const { data: project } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => projectsApi.get(projectId!),
    enabled: !!projectId,
  });

  const uploadMutation = useMutation({
    mutationFn: async ({ file, name }: { file: File; name?: string }) => {
      // Simulate progress updates
      const progressInterval = setInterval(() => {
        setUploadProgress((prev) => Math.min(prev + 10, 90));
      }, 200);

      try {
        const result = await datasetsApi.upload(projectId!, file, name);
        clearInterval(progressInterval);
        setUploadProgress(100);
        return result;
      } catch (error) {
        clearInterval(progressInterval);
        throw error;
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['datasets', projectId] });
      setTimeout(() => {
        navigate(`/projects/${projectId}`);
      }, 1500);
    },
  });

  const handleFileSelect = (file: File) => {
    setSelectedFile(file);
    // Auto-fill name from filename if empty
    if (!datasetName) {
      const nameWithoutExt = file.name.replace(/\.[^/.]+$/, '');
      setDatasetName(nameWithoutExt);
    }
  };

  const handleUpload = () => {
    if (!selectedFile) return;
    setUploadProgress(0);
    uploadMutation.mutate({
      file: selectedFile,
      name: datasetName || undefined,
    });
  };

  return (
    <PageWrapper className="flex flex-col">
      <Header
        title={t('datasets.upload')}
        projectName={project?.name}
        actions={
          <Button variant="ghost" onClick={() => navigate(`/projects/${projectId}`)}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            {t('common.back')}
          </Button>
        }
      />

      <div className="mx-auto w-full max-w-2xl p-6">
        <Card>
          <CardHeader>
            <CardTitle>{t('datasets.uploadNew')}</CardTitle>
            <CardDescription>
              {t('datasets.uploadDesc')}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* File upload */}
            <FileUpload
              onFileSelect={handleFileSelect}
              uploading={uploadMutation.isPending}
              progress={uploadProgress}
              error={uploadMutation.error?.message}
              success={uploadMutation.isSuccess}
            />

            {/* Dataset name */}
            {selectedFile && !uploadMutation.isSuccess && (
              <div className="space-y-2">
                <Label htmlFor="dataset-name">{t('datasets.datasetName')}</Label>
                <Input
                  id="dataset-name"
                  placeholder={t('datasets.datasetNamePlaceholder')}
                  value={datasetName}
                  onChange={(e) => setDatasetName(e.target.value)}
                  disabled={uploadMutation.isPending}
                />
                <p className="text-xs text-muted-foreground">
                  {t('datasets.datasetNameHelp')}
                </p>
              </div>
            )}

            {/* Upload button */}
            {selectedFile && !uploadMutation.isSuccess && (
              <Button
                className="w-full"
                onClick={handleUpload}
                disabled={uploadMutation.isPending}
              >
                {uploadMutation.isPending ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    {t('datasets.uploading')}
                  </>
                ) : (
                  t('datasets.upload')
                )}
              </Button>
            )}

            {/* Success message */}
            {uploadMutation.isSuccess && (
              <div className="text-center">
                <p className="text-green-600">{t('datasets.uploadSuccess')}</p>
                <p className="text-sm text-muted-foreground">
                  {t('datasets.redirectingToProject')}
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Data format tips */}
        <Card className="mt-6">
          <CardHeader>
            <CardTitle className="text-base">{t('datasets.formatTips')}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-muted-foreground">
            <div>
              <p className="font-medium text-foreground">{t('datasets.requiredColumns')}</p>
              <ul className="ml-4 mt-1 list-disc">
                <li>{t('datasets.dateColumn')}</li>
                <li>{t('datasets.targetVariable')}</li>
                <li>{t('datasets.marketingSpend')}</li>
              </ul>
            </div>
            <div>
              <p className="font-medium text-foreground">{t('datasets.recommended')}</p>
              <ul className="ml-4 mt-1 list-disc">
                <li>{t('datasets.weeklyDaily')}</li>
                <li>{t('datasets.historicalData')}</li>
                <li>{t('datasets.controlVariables')}</li>
              </ul>
            </div>
          </CardContent>
        </Card>
      </div>
    </PageWrapper>
  );
}
