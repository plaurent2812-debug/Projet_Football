import { Link } from 'react-router-dom';

interface Props {
  'data-testid'?: string;
}

export function HeroLanding({ 'data-testid': dataTestId = 'hero-landing' }: Props) {
  return (
    <section
      data-testid={dataTestId}
      className="py-12 md:py-20 text-center"
    >
      <span
        className="inline-block text-xs font-semibold tracking-[0.2em]"
        style={{ color: 'var(--primary)' }}
      >
        PROBALAB
      </span>
      <h1
        className="mt-4 text-3xl md:text-5xl font-bold tracking-tight"
        style={{ color: 'var(--text)' }}
      >
        Parier avec une vraie probabilité, pas un feeling.
      </h1>
      <p
        className="mt-4 max-w-xl mx-auto text-base"
        style={{ color: 'var(--text-muted)' }}
      >
        Le seul pronostiqueur français qui publie son CLV vs Pinnacle en temps réel.
      </p>
      <div className="mt-8 flex flex-wrap justify-center gap-3">
        <Link
          to="/register"
          className="rounded-md px-5 py-3 text-sm font-semibold focus-visible:outline focus-visible:outline-2"
          style={{ background: 'var(--primary)', color: '#0a0e1a' }}
        >
          Essai gratuit 30 jours →
        </Link>
        <Link
          to="/premium"
          className="rounded-md px-5 py-3 text-sm font-semibold focus-visible:outline focus-visible:outline-2"
          style={{ border: '1px solid var(--border)', color: 'var(--text)' }}
        >
          Découvrir Premium
        </Link>
      </div>
      <p
        className="mt-4 text-xs"
        style={{ color: 'var(--text-muted)' }}
      >
        Sans engagement · Résiliation en 1 clic · Aucune carte requise pour la trial
      </p>
    </section>
  );
}

export default HeroLanding;
