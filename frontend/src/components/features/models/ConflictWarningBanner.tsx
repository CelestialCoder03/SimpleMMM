import { useTranslation } from 'react-i18next';
import { AlertCircle, AlertTriangle, Info, X } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface ConstraintConflict {
  type: 'error' | 'warning' | 'info';
  code: string;
  message: string;
  affected_variables: string[];
  affected_groups: string[];
  suggestion: string | null;
}

interface ConflictWarningBannerProps {
  conflicts: ConstraintConflict[];
  onDismiss?: (index: number) => void;
  className?: string;
}

export function ConflictWarningBanner({
  conflicts,
  onDismiss,
  className,
}: ConflictWarningBannerProps) {
  const { t } = useTranslation();

  if (conflicts.length === 0) return null;

  const errors = conflicts.filter((c) => c.type === 'error');
  const warnings = conflicts.filter((c) => c.type === 'warning');
  const infos = conflicts.filter((c) => c.type === 'info');

  const getIcon = (type: ConstraintConflict['type']) => {
    switch (type) {
      case 'error':
        return <AlertCircle className="h-4 w-4 text-destructive" />;
      case 'warning':
        return <AlertTriangle className="h-4 w-4 text-yellow-600" />;
      case 'info':
        return <Info className="h-4 w-4 text-blue-600" />;
    }
  };

  const getBorderColor = (type: ConstraintConflict['type']) => {
    switch (type) {
      case 'error':
        return 'border-destructive bg-destructive/5';
      case 'warning':
        return 'border-yellow-500 bg-yellow-50 dark:bg-yellow-900/20';
      case 'info':
        return 'border-blue-500 bg-blue-50 dark:bg-blue-900/20';
    }
  };

  const renderConflict = (conflict: ConstraintConflict, index: number) => (
    <div
      key={`${conflict.code}-${index}`}
      className={cn(
        'flex items-start gap-3 p-3 rounded-lg border',
        getBorderColor(conflict.type)
      )}
    >
      <div className="mt-0.5">{getIcon(conflict.type)}</div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium">{conflict.message}</p>
        
        {conflict.affected_variables.length > 0 && (
          <p className="text-xs text-muted-foreground mt-1">
            {t('constraints.affectedVariables')}: {conflict.affected_variables.join(', ')}
          </p>
        )}
        
        {conflict.affected_groups.length > 0 && (
          <p className="text-xs text-muted-foreground mt-0.5">
            {t('constraints.affectedGroups')}: {conflict.affected_groups.join(', ')}
          </p>
        )}
        
        {conflict.suggestion && (
          <p className="text-xs text-muted-foreground mt-1 italic">
            💡 {conflict.suggestion}
          </p>
        )}
      </div>
      
      {onDismiss && (
        <button
          type="button"
          onClick={() => onDismiss(index)}
          className="text-muted-foreground hover:text-foreground"
        >
          <X className="h-4 w-4" />
        </button>
      )}
    </div>
  );

  return (
    <div className={cn('space-y-2', className)}>
      {/* Summary header */}
      {(errors.length > 0 || warnings.length > 0) && (
        <div className="flex items-center gap-4 text-sm">
          {errors.length > 0 && (
            <span className="flex items-center gap-1 text-destructive">
              <AlertCircle className="h-4 w-4" />
              {t('constraints.errorsCount', { count: errors.length })}
            </span>
          )}
          {warnings.length > 0 && (
            <span className="flex items-center gap-1 text-yellow-600">
              <AlertTriangle className="h-4 w-4" />
              {t('constraints.warningsCount', { count: warnings.length })}
            </span>
          )}
        </div>
      )}

      {/* Error messages first */}
      {errors.map((c, i) => renderConflict(c, i))}
      
      {/* Then warnings */}
      {warnings.map((c, i) => renderConflict(c, errors.length + i))}
      
      {/* Then info messages */}
      {infos.map((c, i) => renderConflict(c, errors.length + warnings.length + i))}
    </div>
  );
}

export default ConflictWarningBanner;
