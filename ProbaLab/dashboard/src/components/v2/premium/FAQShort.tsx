interface Props {
  'data-testid'?: string;
}

interface QA {
  q: string;
  a: string;
}

const ENTRIES: QA[] = [
  {
    q: 'Pourquoi CLV vs ROI ?',
    a: "Le ROI mesure le résultat passé — le CLV mesure si nos cotes battent le marché à la fermeture. Un CLV > 0 prouve un edge durable : statistiquement, le ROI suit le CLV sur 12 mois. Les tipsters publient du ROI parce qu'il est biaisé par la chance ; nous publions les deux.",
  },
  {
    q: 'Puis-je annuler ?',
    a: "Oui, en un clic depuis le portail Stripe, sans pénalité ni engagement. Vous gardez l'accès Premium jusqu'à la fin du mois payé.",
  },
  {
    q: 'Vous vendez des pronos garantis ?',
    a: "Non. Aucun pari n'est garanti — nous publions des probabilités calibrées (Brier 0,21 sur 30j) et vous aidez à miser uniquement quand un edge existe. Le bon ROI vient du nombre de paris +EV, pas du feeling.",
  },
];

/**
 * 3-card FAQ for the Premium landing.
 *
 * Short questions chosen to defuse the most common objections :
 *   1) Why CLV and not just ROI ?
 *   2) Can I cancel ?
 *   3) Are you selling guaranteed tips ?
 *
 * Each entry is an `<article>` to keep the DOM semantic and searchable.
 */
export function FAQShort({ 'data-testid': dataTestId = 'faq-short' }: Props) {
  return (
    <section
      data-testid={dataTestId}
      aria-labelledby="faq-short-title"
      className="py-12"
    >
      <h2
        id="faq-short-title"
        className="text-center text-2xl md:text-3xl font-bold tracking-tight"
        style={{ color: 'var(--text)' }}
      >
        Questions fréquentes
      </h2>
      <div className="mt-8 grid gap-4 md:grid-cols-3">
        {ENTRIES.map((entry) => (
          <article
            key={entry.q}
            className="rounded-xl p-6"
            style={{
              background: 'var(--surface)',
              border: '1px solid var(--border)',
            }}
          >
            <h3 className="text-sm font-semibold" style={{ color: 'var(--text)' }}>
              {entry.q}
            </h3>
            <p className="mt-3 text-sm leading-relaxed" style={{ color: 'var(--text-muted)' }}>
              {entry.a}
            </p>
          </article>
        ))}
      </div>
    </section>
  );
}

export default FAQShort;
