import { useCallback, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Upload, File, X, AlertCircle, CheckCircle2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';

interface FileUploadProps {
  onFileSelect: (file: File) => void;
  accept?: string;
  maxSize?: number; // in MB
  uploading?: boolean;
  progress?: number;
  error?: string;
  success?: boolean;
}

export function FileUpload({
  onFileSelect,
  accept = '.csv,.xlsx,.xls',
  maxSize = 100,
  uploading = false,
  progress = 0,
  error,
  success,
}: FileUploadProps) {
  const { t } = useTranslation();
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);

  const validateFile = useCallback(
    (file: File): boolean => {
      setValidationError(null);

      // Check file extension
      const validExtensions = accept.split(',').map((ext) => ext.trim().toLowerCase());
      const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase();
      if (!validExtensions.includes(fileExtension)) {
        setValidationError(`Invalid file type. Accepted: ${accept}`);
        return false;
      }

      // Check file size
      const fileSizeMB = file.size / (1024 * 1024);
      if (fileSizeMB > maxSize) {
        setValidationError(`File too large. Maximum size: ${maxSize}MB`);
        return false;
      }

      return true;
    },
    [accept, maxSize]
  );

  const handleFile = useCallback(
    (file: File) => {
      if (validateFile(file)) {
        setSelectedFile(file);
        onFileSelect(file);
      }
    },
    [validateFile, onFileSelect]
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);

      const file = e.dataTransfer.files[0];
      if (file) {
        handleFile(file);
      }
    },
    [handleFile]
  );

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) {
        handleFile(file);
      }
    },
    [handleFile]
  );

  const clearFile = useCallback(() => {
    setSelectedFile(null);
    setValidationError(null);
  }, []);

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  const displayError = validationError || error;

  return (
    <div className="space-y-4">
      {/* Drop zone */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={cn(
          'relative rounded-lg border-2 border-dashed p-8 text-center transition-colors',
          isDragging
            ? 'border-primary bg-primary/5'
            : 'border-muted-foreground/25 hover:border-muted-foreground/50',
          displayError && 'border-destructive/50 bg-destructive/5',
          success && 'border-green-500/50 bg-green-500/5'
        )}
      >
        <input
          type="file"
          accept={accept}
          onChange={handleInputChange}
          className="absolute inset-0 cursor-pointer opacity-0"
          disabled={uploading}
        />

        <div className="flex flex-col items-center gap-3">
          {success ? (
            <CheckCircle2 className="h-12 w-12 text-green-500" />
          ) : displayError ? (
            <AlertCircle className="h-12 w-12 text-destructive" />
          ) : (
            <Upload
              className={cn(
                'h-12 w-12',
                isDragging ? 'text-primary' : 'text-muted-foreground'
              )}
            />
          )}

          <div>
            <p className="text-lg font-medium">
              {success
                ? t('datasets.uploadComplete')
                : isDragging
                  ? t('datasets.dropHere')
                  : t('datasets.dragDrop')}
            </p>
            <p className="mt-1 text-sm text-muted-foreground">
              {t('datasets.clickToBrowse')} • {t('datasets.acceptedFormats', { size: maxSize })}
            </p>
          </div>
        </div>
      </div>

      {/* Error message */}
      {displayError && (
        <div className="flex items-center gap-2 text-sm text-destructive">
          <AlertCircle className="h-4 w-4" />
          {displayError}
        </div>
      )}

      {/* Selected file */}
      {selectedFile && !success && (
        <div className="rounded-lg border bg-muted/50 p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                <File className="h-5 w-5 text-primary" />
              </div>
              <div>
                <p className="font-medium">{selectedFile.name}</p>
                <p className="text-sm text-muted-foreground">
                  {formatFileSize(selectedFile.size)}
                </p>
              </div>
            </div>
            {!uploading && (
              <Button variant="ghost" size="icon" onClick={clearFile}>
                <X className="h-4 w-4" />
              </Button>
            )}
          </div>

          {/* Upload progress */}
          {uploading && (
            <div className="mt-4 space-y-2">
              <Progress value={progress} />
              <p className="text-center text-sm text-muted-foreground">
                {t('datasets.uploading')} {progress}%
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
