import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const badgeVariants = cva(
  'inline-flex items-center rounded-md border px-2.5 py-0.5 text-xs font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
  {
    variants: {
      variant: {
        default:
          'border-transparent bg-primary/10 text-primary',
        secondary:
          'border-transparent bg-secondary text-secondary-foreground',
        success:
          'border-transparent bg-success/10 text-success',
        warning:
          'border-transparent bg-warning/10 text-warning-foreground',
        destructive:
          'border-transparent bg-destructive/10 text-destructive',
        info:
          'border-transparent bg-info/10 text-info',
        outline:
          'text-foreground border-border',
        // Data-centric variants for metrics display
        positive:
          'border-transparent bg-emerald-500/10 text-emerald-700 dark:text-emerald-400',
        negative:
          'border-transparent bg-red-500/10 text-red-700 dark:text-red-400',
        neutral:
          'border-transparent bg-gray-500/10 text-gray-600 dark:text-gray-400',
        subtle:
          'border-transparent bg-muted text-muted-foreground',
        // Legacy decorative variants (kept for backward compatibility)
        gradient:
          'border-0 bg-gradient-primary text-white',
        'gradient-subtle':
          'border-0 bg-gradient-to-r from-primary/10 to-purple-500/10 text-primary',
        glass:
          'glass-sm border-[var(--glass-border)] text-foreground',
      },
      size: {
        sm: 'px-2 py-0.5 text-[10px]',
        default: 'px-2.5 py-0.5 text-xs',
        lg: 'px-3 py-1 text-sm',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, size, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant, size }), className)} {...props} />
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export { Badge, badgeVariants };
