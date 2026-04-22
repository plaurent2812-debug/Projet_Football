import type { ReactNode } from 'react';
import { Lock } from 'lucide-react';

export type LockOverlayVariant = 'inline' | 'fullCover';

export interface LockOverlayProps {
  children: ReactNode;
  message: string;
  variant?: LockOverlayVariant;
  'data-testid'?: string;
}

export function LockOverlay({
  children,
  message,
  variant = 'inline',
  'data-testid': dataTestId = 'lock-overlay',
}: LockOverlayProps) {
  const isFullCover = variant === 'fullCover';
  return (
    <div
      data-testid={dataTestId}
      data-variant={variant}
      role="region"
      aria-label="Contenu verrouillé"
      style={{
        position: isFullCover ? 'fixed' : 'relative',
        inset: isFullCover ? 0 : undefined,
        zIndex: isFullCover ? 100 : undefined,
      }}
    >
      <div
        data-testid="lock-children"
        aria-hidden="true"
        style={{
          filter: 'blur(4px)',
          pointerEvents: 'none',
          userSelect: 'none',
        }}
      >
        {children}
      </div>
      <div
        style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 'var(--space-2)',
          background: 'rgba(10, 14, 26, 0.5)',
          borderRadius: 'var(--radius-md)',
        }}
      >
        <Lock size={24} aria-hidden="true" color="var(--primary)" />
        <p
          style={{
            margin: 0,
            color: 'var(--text)',
            fontSize: 14,
            fontWeight: 500,
            textAlign: 'center',
          }}
        >
          {message}
        </p>
      </div>
    </div>
  );
}

export default LockOverlay;
