import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useEffect } from 'react';
import { AnimatePresence } from 'framer-motion';
import { MainLayout } from '@/components/layout';
import { ProtectedRoute } from '@/components/features/auth';
import {
  LoginPage,
  RegisterPage,
  ForgotPasswordPage,
  ResetPasswordPage,
  ProjectsPage,
  ProjectDetailPage,
  DatasetUploadPage,
  DatasetDetailPage,
  DatasetUpdatePage,
  DataExplorationPage,
  ModelConfigPage,
  ModelResultsPage,
  ModelTrainingPage,
  DashboardPage,
  SettingsPage,
  HierarchicalConfigPage,
  HierarchicalDetailPage,
  VariableManagementPage,
  ScenariosPage,
  OptimizationPage,
} from '@/pages';
import { ErrorBoundary } from '@/components/common/ErrorBoundary';
import { useUIStore } from '@/stores/uiStore';
import { useAuthStore } from '@/stores/authStore';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      retry: 1,
    },
  },
});

function ThemeProvider({ children }: { children: React.ReactNode }) {
  const { theme } = useUIStore();

  useEffect(() => {
    const root = document.documentElement;
    root.classList.remove('light', 'dark');

    if (theme === 'system') {
      const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches
        ? 'dark'
        : 'light';
      root.classList.add(systemTheme);
    } else {
      root.classList.add(theme);
    }
  }, [theme]);

  return <>{children}</>;
}

function AuthInitializer({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, fetchUser } = useAuthStore();

  useEffect(() => {
    if (isAuthenticated) {
      fetchUser();
    }
  }, [isAuthenticated, fetchUser]);

  return <>{children}</>;
}

function AnimatedRoutes() {
  const location = useLocation();

  return (
    <AnimatePresence mode="wait">
      <Routes location={location} key={location.pathname}>
        {/* Public routes */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />

        {/* Protected routes */}
        <Route
          element={
            <ProtectedRoute>
              <MainLayout />
            </ProtectedRoute>
          }
        >
          <Route path="/" element={<Navigate to="/projects" replace />} />
          <Route path="/projects" element={<ProjectsPage />} />
          <Route path="/projects/:projectId" element={<ProjectDetailPage />} />
          <Route path="/projects/:projectId/datasets/upload" element={<DatasetUploadPage />} />
          <Route path="/projects/:projectId/datasets/:datasetId" element={<DatasetDetailPage />} />
          <Route path="/projects/:projectId/datasets/:datasetId/update" element={<DatasetUpdatePage />} />
          <Route path="/projects/:projectId/explore" element={<DataExplorationPage />} />
          <Route path="/projects/:projectId/models/new" element={<ModelConfigPage />} />
          <Route path="/projects/:projectId/models/:modelId" element={<ModelConfigPage />} />
          <Route path="/projects/:projectId/models/:modelId/results" element={<ModelResultsPage />} />
          <Route path="/projects/:projectId/models/:modelId/training" element={<ModelTrainingPage />} />
          <Route path="/projects/:projectId/hierarchical/new" element={<HierarchicalConfigPage />} />
          <Route path="/projects/:projectId/hierarchical/:configId" element={<HierarchicalDetailPage />} />
          <Route path="/projects/:projectId/variables" element={<VariableManagementPage />} />
          <Route path="/projects/:projectId/scenarios" element={<ScenariosPage />} />
          <Route path="/projects/:projectId/optimization" element={<OptimizationPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Route>

        {/* Catch all */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AnimatePresence>
  );
}

function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <ThemeProvider>
          <AuthInitializer>
            <BrowserRouter>
              <AnimatedRoutes />
            </BrowserRouter>
          </AuthInitializer>
        </ThemeProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}

export default App;
