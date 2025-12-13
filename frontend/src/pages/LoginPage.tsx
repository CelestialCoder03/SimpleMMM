import { LoginForm } from '@/components/features/auth';
import { PageWrapper } from '@/components/layout';

export function LoginPage() {
  return (
    <PageWrapper>
      <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-app-gradient p-4">
        {/* Decorative gradient orbs */}
        <div className="pointer-events-none absolute -left-40 -top-40 h-80 w-80 rounded-full bg-gradient-primary opacity-20 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-40 -right-40 h-80 w-80 rounded-full bg-gradient-accent opacity-20 blur-3xl" />
        <div className="pointer-events-none absolute left-1/2 top-1/4 h-60 w-60 -translate-x-1/2 rounded-full bg-gradient-secondary opacity-10 blur-3xl" />

        <LoginForm />
      </div>
    </PageWrapper>
  );
}
