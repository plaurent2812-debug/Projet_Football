import { Component, type ErrorInfo, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    const message = error.message || '';
    if (
      message.includes('Failed to fetch dynamically imported module') ||
      message.includes('Loading chunk') ||
      message.includes('Loading CSS chunk')
    ) {
      const now = Date.now();
      const lastReload = Number(window.sessionStorage.getItem('v2_chunk_reload_at') ?? 0);
      if (!lastReload || now - lastReload > 10_000) {
        window.sessionStorage.setItem('v2_chunk_reload_at', String(now));
        window.location.reload();
      }
      return;
    }
    // eslint-disable-next-line no-console
    console.error('ErrorBoundary V2 caught:', error, info);
  }

  private handleRetry = (): void => {
    this.setState({ hasError: false, error: null });
  };

  render(): ReactNode {
    if (!this.state.hasError) return this.props.children;
    if (this.props.fallback) return this.props.fallback;

    return (
      <div
        data-testid="error-boundary-fallback"
        role="alert"
        className="flex min-h-[60vh] flex-col items-center justify-center gap-4 px-6 text-center"
        style={{ color: 'var(--text)', background: 'var(--bg)' }}
      >
        <div
          className="max-w-md rounded-xl p-6 shadow-sm"
          style={{ border: '1px solid var(--border)', background: 'var(--surface)' }}
        >
          <h2 className="text-xl font-bold">Une erreur est survenue</h2>
          <p className="mt-2 text-sm leading-relaxed" style={{ color: 'var(--text-muted)' }}>
            La page a rencontre une erreur d'affichage. Vous pouvez reessayer sans quitter
            ProbaLab.
          </p>
          <button
            type="button"
            onClick={this.handleRetry}
            className="mt-4 rounded-lg px-4 py-2 text-sm font-semibold"
            style={{ background: 'var(--primary)', color: '#fff' }}
          >
            Réessayer
          </button>
        </div>
      </div>
    );
  }
}

export default ErrorBoundary;
