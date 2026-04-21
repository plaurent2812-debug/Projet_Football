import type { ReactNode } from 'react';

export interface LayoutShellProps {
  children: ReactNode;
}

export function LayoutShell({ children }: LayoutShellProps) {
  return <div data-testid="layout-shell">{children}</div>;
}
