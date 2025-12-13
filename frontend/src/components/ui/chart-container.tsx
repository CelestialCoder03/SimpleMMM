import { useRef, useEffect, useState } from 'react';
import { cn } from '@/lib/utils';
import { ChartSkeleton } from './skeleton';

interface ChartContainerProps {
  children: React.ReactNode;
  className?: string;
  height?: string;
  loading?: boolean;
  title?: string;
  description?: string;
}

/**
 * Responsive chart container that handles:
 * - Responsive sizing with ResizeObserver
 * - Loading states with skeleton
 * - Optional title and description
 * - Consistent styling
 */
export function ChartContainer({
  children,
  className,
  height = 'h-80',
  loading = false,
  title,
  description,
}: ChartContainerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });

  useEffect(() => {
    if (!containerRef.current) return;

    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect;
        setDimensions({ width, height });
      }
    });

    observer.observe(containerRef.current);

    return () => observer.disconnect();
  }, []);

  if (loading) {
    return (
      <div className={cn('space-y-2', className)}>
        {title && <div className="h-5 w-32 bg-muted rounded animate-pulse" />}
        {description && <div className="h-4 w-48 bg-muted rounded animate-pulse" />}
        <ChartSkeleton height={height} />
      </div>
    );
  }

  return (
    <div className={cn('space-y-2', className)}>
      {title && (
        <h4 className="text-sm font-medium text-foreground">{title}</h4>
      )}
      {description && (
        <p className="text-xs text-muted-foreground">{description}</p>
      )}
      <div
        ref={containerRef}
        className={cn(
          'relative rounded-lg border bg-card transition-shadow',
          'hover:shadow-md',
          height
        )}
        data-width={dimensions.width}
        data-height={dimensions.height}
      >
        <div className="absolute inset-0 p-4">
          {children}
        </div>
      </div>
    </div>
  );
}

export default ChartContainer;
