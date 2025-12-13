import { Link, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { ChevronRight } from 'lucide-react';

interface BreadcrumbItem {
  label: string;
  labelKey?: string; // i18n key
  path?: string;
}

function generateBreadcrumbs(pathname: string, projectName?: string): BreadcrumbItem[] {
  const segments = pathname.split('/').filter(Boolean);
  const breadcrumbs: BreadcrumbItem[] = [];

  let currentPath = '';
  let projectId: string | null = null;

  for (let i = 0; i < segments.length; i++) {
    const segment = segments[i];
    currentPath += `/${segment}`;

    // Track projectId for proper navigation
    if (segments[i - 1] === 'projects' && segment !== 'new') {
      projectId = segment;
      // Add project name breadcrumb item
      if (projectName) {
        breadcrumbs.push({
          label: projectName,
          path: `/projects/${projectId}`,
        });
      }
      continue; // Skip adding the UUID to breadcrumbs
    }

    // Skip UUID segments in breadcrumb display
    const isUUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(segment);
    if (isUUID) {
      continue;
    }

    // Determine the correct path for navigation
    let path = currentPath;
    let label = segment
      .replace(/-/g, ' ')
      .replace(/\b\w/g, (c) => c.toUpperCase());
    let labelKey: string | undefined;

    // Map segments to i18n keys
    if (segment === 'projects') {
      labelKey = 'nav.projects';
      label = 'Projects';
    } else if (segment === 'datasets' && projectId) {
      path = `/projects/${projectId}`;
      labelKey = 'nav.datasets';
      label = 'Datasets';
    } else if (segment === 'models' && projectId) {
      path = `/projects/${projectId}`;
      labelKey = 'nav.models';
      label = 'Models';
    } else if (segment === 'new') {
      labelKey = 'common.new';
      label = 'New';
    } else if (segment === 'training') {
      labelKey = 'models.training';
      label = 'Training';
    } else if (segment === 'results') {
      labelKey = 'models.results';
      label = 'Results';
    } else if (segment === 'variables') {
      labelKey = 'variables.title';
      label = '变量管理';
    } else if (segment === 'hierarchical') {
      labelKey = 'hierarchical.title';
      label = '分层模型';
    } else if (segment === 'explore') {
      labelKey = 'exploration.title';
      label = '数据探索';
    }

    breadcrumbs.push({
      label,
      labelKey,
      path,
    });
  }

  return breadcrumbs;
}

interface HeaderProps {
  title?: string;
  projectName?: string;
  actions?: React.ReactNode;
}

export function Header({ title, projectName, actions }: HeaderProps) {
  const { t } = useTranslation();
  const location = useLocation();
  const breadcrumbs = generateBreadcrumbs(location.pathname, projectName);

  const getBreadcrumbLabel = (crumb: BreadcrumbItem) => {
    if (crumb.labelKey) {
      return t(crumb.labelKey);
    }
    return crumb.label;
  };

  return (
    <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-border bg-background/95 backdrop-blur-sm px-6">
      <div className="flex items-center gap-2">
        {/* Breadcrumbs */}
        <nav className="flex items-center gap-1 text-sm">
          <Link
            to="/"
            className="text-muted-foreground transition-colors duration-100 hover:text-foreground"
          >
            {t('nav.home')}
          </Link>
          {breadcrumbs.map((crumb, index) => (
            <div key={`${crumb.path}-${index}`} className="flex items-center gap-1">
              <ChevronRight className="h-3.5 w-3.5 text-muted-foreground/50" />
              {index === breadcrumbs.length - 1 ? (
                <span className="font-medium text-foreground">{title || getBreadcrumbLabel(crumb)}</span>
              ) : (
                <Link
                  to={crumb.path || '/'}
                  className="text-muted-foreground transition-colors duration-100 hover:text-foreground"
                >
                  {getBreadcrumbLabel(crumb)}
                </Link>
              )}
            </div>
          ))}
        </nav>
      </div>

      {/* Actions */}
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </header>
  );
}
