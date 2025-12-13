import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { projectsApi } from '@/api/services';
import { Header } from '@/components/layout';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  FolderKanban,
  Database,
  LineChart,
  TrendingUp,
  Plus,
  ArrowRight,
  Loader2,
} from 'lucide-react';
import type { Project } from '@/types';

export function DashboardPage() {
  const { t } = useTranslation();
  const { data: projectsData, isLoading } = useQuery({
    queryKey: ['projects'],
    queryFn: () => projectsApi.list(1, 10),
  });

  const projects = projectsData?.items || [];
  const totalProjects = projectsData?.total || 0;

  return (
    <div className="flex flex-col">
      <Header
        title={t('dashboard.title')}
        actions={
          <Button asChild>
            <Link to="/projects">
              <Plus className="mr-2 h-4 w-4" />
              {t('projects.newProject')}
            </Link>
          </Button>
        }
      />

      <div className="p-6 space-y-6">
        {/* Stats Overview */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">{t('dashboard.totalProjects')}</CardTitle>
              <FolderKanban className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{totalProjects}</div>
              <p className="text-xs text-muted-foreground">
                {t('dashboard.marketingMixModels')}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">{t('dashboard.activeDatasets')}</CardTitle>
              <Database className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">-</div>
              <p className="text-xs text-muted-foreground">
                {t('dashboard.acrossAllProjects')}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">{t('dashboard.modelsTrained')}</CardTitle>
              <LineChart className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">-</div>
              <p className="text-xs text-muted-foreground">
                {t('dashboard.completedModels')}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">{t('dashboard.avgRSquared')}</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">-</div>
              <p className="text-xs text-muted-foreground">
                {t('dashboard.modelAccuracy')}
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Recent Projects */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>{t('dashboard.recentProjects')}</CardTitle>
                <CardDescription>{t('dashboard.recentProjectsDesc')}</CardDescription>
              </div>
              <Button variant="ghost" size="sm" asChild>
                <Link to="/projects">
                  {t('common.viewAll')}
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Link>
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : projects.length === 0 ? (
              <div className="text-center py-8">
                <FolderKanban className="mx-auto h-10 w-10 text-muted-foreground/50" />
                <p className="mt-2 text-muted-foreground">{t('dashboard.noProjects')}</p>
                <Button className="mt-4" asChild>
                  <Link to="/projects">
                    <Plus className="mr-2 h-4 w-4" />
                    {t('dashboard.createFirst')}
                  </Link>
                </Button>
              </div>
            ) : (
              <div className="space-y-4">
                {projects.slice(0, 5).map((project: Project) => (
                  <Link
                    key={project.id}
                    to={`/projects/${project.id}`}
                    className="flex items-center justify-between rounded-lg border p-4 transition-colors hover:bg-muted/50"
                  >
                    <div className="flex items-center gap-4">
                      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                        <FolderKanban className="h-5 w-5" />
                      </div>
                      <div>
                        <p className="font-medium">{project.name}</p>
                        <p className="text-sm text-muted-foreground">
                          {project.description || t('projects.noDescription')}
                        </p>
                      </div>
                    </div>
                    <div className="text-right text-sm text-muted-foreground">
                      <p>{t('projects.updated')}</p>
                      <p>{new Date(project.updated_at).toLocaleDateString()}</p>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Quick Action - Create Project Only */}
        {projects.length === 0 && (
          <Card className="cursor-pointer transition-shadow hover:shadow-md">
            <Link to="/projects">
              <CardHeader>
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-500/10 text-blue-500">
                    <Plus className="h-5 w-5" />
                  </div>
                  <div>
                    <CardTitle className="text-base">{t('dashboard.quickActions.createProject')}</CardTitle>
                    <CardDescription>{t('dashboard.quickActions.createProjectDesc')}</CardDescription>
                  </div>
                </div>
              </CardHeader>
            </Link>
          </Card>
        )}
      </div>
    </div>
  );
}
