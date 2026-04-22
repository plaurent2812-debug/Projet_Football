import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe, toHaveNoViolations } from 'jest-axe';
import { FilterSidebar } from './FilterSidebar';
import type { MatchesFilters } from '@/types/v2/matches';

expect.extend(toHaveNoViolations);

const baseFilters: MatchesFilters = { date: '2026-04-21' };

describe('FilterSidebar', () => {
  it('renders Sport, Ligue, Signaux and Tri sections', () => {
    render(<FilterSidebar filters={baseFilters} onChange={() => {}} />);
    expect(screen.getByRole('heading', { name: /sport/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /ligue/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /signaux/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /tri/i })).toBeInTheDocument();
  });

  it('toggles Football sport checkbox and emits filters', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<FilterSidebar filters={baseFilters} onChange={onChange} />);
    await user.click(screen.getByRole('checkbox', { name: /football/i }));
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ sports: ['football'] }),
    );
  });

  it('toggles a signal checkbox', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<FilterSidebar filters={baseFilters} onChange={onChange} />);
    await user.click(screen.getByRole('checkbox', { name: /value bet/i }));
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ signals: ['value'] }),
    );
  });

  it('changes sort via select', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<FilterSidebar filters={baseFilters} onChange={onChange} />);
    await user.selectOptions(screen.getByRole('combobox', { name: /tri/i }), 'edge');
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ sort: 'edge' }));
  });

  it('renders league counts when provided', () => {
    render(
      <FilterSidebar
        filters={baseFilters}
        onChange={() => {}}
        matchesByLeague={{
          L1: 4,
          L2: 0,
          PL: 3,
          LaLiga: 2,
          SerieA: 1,
          Bundesliga: 0,
          UCL: 0,
          UEL: 0,
          NHL: 2,
        }}
      />,
    );
    expect(screen.getByLabelText(/Ligue 1/i).closest('label')?.textContent).toMatch(/4/);
  });

  it('accepts data-testid', () => {
    render(
      <FilterSidebar
        filters={baseFilters}
        onChange={() => {}}
        data-testid="filter-sidebar"
      />,
    );
    expect(screen.getByTestId('filter-sidebar')).toBeInTheDocument();
  });

  it('has no axe violations', async () => {
    const { container } = render(
      <FilterSidebar filters={baseFilters} onChange={() => {}} />,
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
