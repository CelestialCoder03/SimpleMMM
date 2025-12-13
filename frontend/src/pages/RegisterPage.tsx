import { RegisterForm } from '@/components/features/auth';
import { PageWrapper } from '@/components/layout';

export function RegisterPage() {
  return (
    <PageWrapper className="flex min-h-screen items-center justify-center bg-muted/50 p-4">
      <RegisterForm />
    </PageWrapper>
  );
}
