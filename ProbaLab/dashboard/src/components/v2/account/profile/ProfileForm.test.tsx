import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { axe } from 'jest-axe';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { ProfileForm } from './ProfileForm';

const updateMock = vi.fn().mockResolvedValue({
  email: 'demo@probalab.net',
  pseudo: 'john2',
  role: 'premium',
});
const deleteMock = vi.fn().mockResolvedValue(undefined);
const passwordMock = vi.fn().mockResolvedValue(undefined);
let profileState: {
  data: {
    email: string;
    pseudo: string;
    role: 'premium';
    avatarUrl?: string;
  } | null;
  isLoading: boolean;
} = {
  data: { email: 'demo@probalab.net', pseudo: 'john', role: 'premium' },
  isLoading: false,
};

vi.mock('@/hooks/v2/useProfile', () => ({
  useProfile: () => profileState,
  useUpdateProfile: () => ({ mutateAsync: updateMock, isPending: false }),
  useChangePassword: () => ({ mutateAsync: passwordMock, isPending: false }),
  useDeleteAccount: () => ({ mutateAsync: deleteMock, isPending: false }),
}));

function wrap(ui: ReactNode) {
  const client = new QueryClient();
  return <QueryClientProvider client={client}>{ui}</QueryClientProvider>;
}

beforeEach(() => {
  updateMock.mockClear();
  deleteMock.mockClear();
  passwordMock.mockClear();
  profileState = {
    data: { email: 'demo@probalab.net', pseudo: 'john', role: 'premium' },
    isLoading: false,
  };
});

describe('ProfileForm', () => {
  it('shows a skeleton while the profile is loading', () => {
    profileState = { data: null, isLoading: true };
    render(wrap(<ProfileForm />));
    expect(screen.getByTestId('profile-form-skeleton')).toBeInTheDocument();
  });

  it('renders email as readonly with a "Vérifié" badge', () => {
    render(wrap(<ProfileForm />));
    const email = screen.getByLabelText(/^email$/i) as HTMLInputElement;
    expect(email.readOnly).toBe(true);
    expect(email.value).toBe('demo@probalab.net');
    expect(screen.getByText(/vérifié/i)).toBeInTheDocument();
  });

  it('prefills the pseudo field with the current pseudo', () => {
    render(wrap(<ProfileForm />));
    const pseudo = screen.getByLabelText(/pseudo/i) as HTMLInputElement;
    expect(pseudo.value).toBe('john');
  });

  it('submits pseudo update when valid', async () => {
    const user = userEvent.setup();
    render(wrap(<ProfileForm />));
    const pseudo = screen.getByLabelText(/pseudo/i);
    await user.clear(pseudo);
    await user.type(pseudo, 'john2');
    await user.click(screen.getByRole('button', { name: /enregistrer/i }));
    await waitFor(() =>
      expect(updateMock).toHaveBeenCalledWith(
        expect.objectContaining({ pseudo: 'john2' }),
      ),
    );
  });

  it('shows a validation error when pseudo too short and does not submit', async () => {
    const user = userEvent.setup();
    render(wrap(<ProfileForm />));
    const pseudo = screen.getByLabelText(/pseudo/i);
    await user.clear(pseudo);
    await user.type(pseudo, 'ab');
    await user.click(screen.getByRole('button', { name: /enregistrer/i }));
    expect(await screen.findByText(/trop court/i)).toBeInTheDocument();
    expect(updateMock).not.toHaveBeenCalled();
  });

  it('toggles password visibility on show/hide click', async () => {
    const user = userEvent.setup();
    render(wrap(<ProfileForm />));
    const input = screen.getByLabelText(/^mot de passe actuel$/i) as HTMLInputElement;
    expect(input.type).toBe('password');
    const toggle = screen.getByRole('button', {
      name: /afficher le mot de passe actuel/i,
    });
    await user.click(toggle);
    expect(input.type).toBe('text');
  });

  it('submits password change with current + next', async () => {
    const user = userEvent.setup();
    render(wrap(<ProfileForm />));
    await user.type(screen.getByLabelText(/^mot de passe actuel$/i), 'oldpass123');
    await user.type(screen.getByLabelText(/^nouveau mot de passe$/i), 'newpass123');
    await user.type(
      screen.getByLabelText(/^confirmer le nouveau mot de passe$/i),
      'newpass123',
    );
    await user.click(
      screen.getByRole('button', { name: /mettre à jour le mot de passe/i }),
    );
    await waitFor(() =>
      expect(passwordMock).toHaveBeenCalledWith({
        current: 'oldpass123',
        next: 'newpass123',
      }),
    );
  });

  it('rejects password change when confirmation does not match', async () => {
    const user = userEvent.setup();
    render(wrap(<ProfileForm />));
    await user.type(screen.getByLabelText(/^mot de passe actuel$/i), 'oldpass123');
    await user.type(screen.getByLabelText(/^nouveau mot de passe$/i), 'newpass123');
    await user.type(
      screen.getByLabelText(/^confirmer le nouveau mot de passe$/i),
      'different1',
    );
    await user.click(
      screen.getByRole('button', { name: /mettre à jour le mot de passe/i }),
    );
    expect(
      await screen.findByText(/ne correspondent pas/i),
    ).toBeInTheDocument();
    expect(passwordMock).not.toHaveBeenCalled();
  });

  it('opens and confirms delete flow (RGPD)', async () => {
    const user = userEvent.setup();
    render(wrap(<ProfileForm />));
    await user.click(
      screen.getByRole('button', { name: /supprimer mon compte/i }),
    );
    const confirmInput = await screen.findByLabelText(/tapez supprimer/i);
    await user.type(confirmInput, 'SUPPRIMER');
    await user.click(
      screen.getByRole('button', { name: /confirmer la suppression/i }),
    );
    await waitFor(() => expect(deleteMock).toHaveBeenCalled());
  });

  it('does not allow confirming delete until the user types SUPPRIMER', async () => {
    const user = userEvent.setup();
    render(wrap(<ProfileForm />));
    await user.click(
      screen.getByRole('button', { name: /supprimer mon compte/i }),
    );
    const confirmBtn = screen.getByRole('button', {
      name: /confirmer la suppression/i,
    });
    expect(confirmBtn).toBeDisabled();
    await user.type(screen.getByLabelText(/tapez supprimer/i), 'no');
    expect(confirmBtn).toBeDisabled();
  });

  it('cancels the delete confirm and returns to the initial danger button', async () => {
    const user = userEvent.setup();
    render(wrap(<ProfileForm />));
    await user.click(
      screen.getByRole('button', { name: /supprimer mon compte/i }),
    );
    expect(screen.getByLabelText(/tapez supprimer/i)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /annuler/i }));
    expect(screen.queryByLabelText(/tapez supprimer/i)).not.toBeInTheDocument();
  });

  it('accepts a custom data-testid on the root', () => {
    render(wrap(<ProfileForm data-testid="my-form" />));
    expect(screen.getByTestId('my-form')).toBeInTheDocument();
  });

  it('has no accessibility violations', async () => {
    const { container } = render(wrap(<ProfileForm />));
    expect(await axe(container)).toHaveNoViolations();
  });
});
