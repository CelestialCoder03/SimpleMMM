import { cn } from '@/lib/utils';

interface PageWrapperProps {
  children: React.ReactNode;
  className?: string;
}

/**
 * Wraps page content with entrance animations using CSS.
 * Use this component at the top level of each page for consistent transitions.
 */
export function PageWrapper({ children, className }: PageWrapperProps) {
  return (
    <div
      className={cn(
        'animate-in fade-in-0 slide-in-from-bottom-2 duration-300',
        className
      )}
    >
      {children}
    </div>
  );
}

export default PageWrapper;
