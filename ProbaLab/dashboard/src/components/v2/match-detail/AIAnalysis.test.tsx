import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { axe } from 'jest-axe';
import { AIAnalysis } from './AIAnalysis';
import type { AnalysisPayload } from '../../../types/v2/match-detail';

const analysis: AnalysisPayload = {
  paragraphs: [
    'Nice a remporté ses 4 derniers matchs à domicile.',
    'Lens peine en déplacement avec 2 buts encaissés en moyenne.',
    'Le xG de Nice explose cette saison.',
  ],
  generated_at: '2026-04-21T10:00:00Z',
};

describe('AIAnalysis', () => {
  it('renders section heading', () => {
    render(<AIAnalysis analysis={analysis} userRole="premium" />);
    expect(
      screen.getByRole('heading', { name: /analyse ia/i }),
    ).toBeInTheDocument();
  });

  it('premium sees all paragraphs, no lock overlay', () => {
    render(<AIAnalysis analysis={analysis} userRole="premium" />);
    for (const p of analysis.paragraphs) {
      expect(screen.getByText(p)).toBeInTheDocument();
    }
    expect(screen.queryByTestId('lock-overlay')).not.toBeInTheDocument();
  });

  it('trial sees all paragraphs, no lock overlay', () => {
    render(<AIAnalysis analysis={analysis} userRole="trial" />);
    for (const p of analysis.paragraphs) {
      expect(screen.getByText(p)).toBeInTheDocument();
    }
    expect(screen.queryByTestId('lock-overlay')).not.toBeInTheDocument();
  });

  it('admin sees all paragraphs, no lock overlay', () => {
    render(<AIAnalysis analysis={analysis} userRole="admin" />);
    for (const p of analysis.paragraphs) {
      expect(screen.getByText(p)).toBeInTheDocument();
    }
    expect(screen.queryByTestId('lock-overlay')).not.toBeInTheDocument();
  });

  it('free sees first paragraph and locked rest with upgrade message', () => {
    render(<AIAnalysis analysis={analysis} userRole="free" />);
    expect(screen.getByText(analysis.paragraphs[0])).toBeInTheDocument();
    // Remaining paragraphs exist in the DOM behind the lock (blurred)
    expect(screen.getByText(analysis.paragraphs[1])).toBeInTheDocument();
    expect(screen.getByText(analysis.paragraphs[2])).toBeInTheDocument();
    const lock = screen.getByTestId('lock-overlay');
    expect(lock).toBeInTheDocument();
    // Message should mention Premium
    expect(lock.textContent).toMatch(/premium/i);
  });

  it('free without remaining paragraphs does not render a lock', () => {
    const single: AnalysisPayload = {
      paragraphs: ['Seul paragraphe visible.'],
      generated_at: '2026-04-21T10:00:00Z',
    };
    render(<AIAnalysis analysis={single} userRole="free" />);
    expect(screen.getByText('Seul paragraphe visible.')).toBeInTheDocument();
    expect(screen.queryByTestId('lock-overlay')).not.toBeInTheDocument();
  });

  it('visitor sees full lock with signup CTA message', () => {
    render(<AIAnalysis analysis={analysis} userRole="visitor" />);
    const lock = screen.getByTestId('lock-overlay');
    expect(lock).toBeInTheDocument();
    // message mentions account creation
    expect(lock.textContent).toMatch(/cr[ée]er un compte|compte/i);
  });

  it('renders text safely (no HTML injection from paragraphs)', () => {
    const malicious = "<script>alert('x')</script>Nice gagne.";
    const mal: AnalysisPayload = {
      paragraphs: [malicious],
      generated_at: '2026-04-21T10:00:00Z',
    };
    render(<AIAnalysis analysis={mal} userRole="premium" />);
    expect(screen.getByText(malicious)).toBeInTheDocument();
    expect(document.querySelector('script')).toBeNull();
  });

  it('accepts a custom data-testid on the root', () => {
    render(
      <AIAnalysis
        analysis={analysis}
        userRole="premium"
        data-testid="ai-root"
      />,
    );
    expect(screen.getByTestId('ai-root')).toBeInTheDocument();
  });

  it('has no accessibility violations (premium)', async () => {
    const { container } = render(
      <AIAnalysis analysis={analysis} userRole="premium" />,
    );
    expect(await axe(container)).toHaveNoViolations();
  });

  it('has no accessibility violations (free gated)', async () => {
    const { container } = render(
      <AIAnalysis analysis={analysis} userRole="free" />,
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
