import { Suspense } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from '../../lib/auth';
import { v2Routes } from './routes';
import { LayoutShell } from '../../components/v2/layout/LayoutShell';
import { ErrorBoundary } from '../../components/v2/system/ErrorBoundary';
import { useV2User } from '../../hooks/v2/useV2User';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

function RouteFallback() {
  return (
    <div
      className="flex min-h-[40vh] items-center justify-center text-sm"
      style={{ color: 'var(--text-muted)' }}
      role="status"
      aria-label="Chargement de la page"
    >
      Chargement…
    </div>
  );
}

export function AppV2Content() {
  const user = useV2User();

  return (
    <div className="v2-root">
      <ErrorBoundary>
        <LayoutShell userRole={user.role} trialDaysLeft={user.trialDaysLeft}>
          <Suspense fallback={<RouteFallback />}>
            <Routes>
              {v2Routes.map((route) => (
                <Route key={route.path} path={route.path} element={route.element}>
                  {route.children?.map((child, idx) =>
                    child.index ? (
                      <Route key={`idx-${route.path}`} index element={child.element} />
                    ) : (
                      <Route
                        key={`${route.path}-${child.path ?? idx}`}
                        path={child.path}
                        element={child.element}
                      />
                    ),
                  )}
                </Route>
              ))}
            </Routes>
          </Suspense>
        </LayoutShell>
      </ErrorBoundary>
    </div>
  );
}

export function AppV2() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <AppV2Content />
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default AppV2;
