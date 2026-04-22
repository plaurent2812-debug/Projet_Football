import { Sparkles } from 'lucide-react';
import type { UserRole } from '../../../types/v2/common';
import type { AnalysisPayload } from '../../../types/v2/match-detail';
import { LockOverlay } from '../system/LockOverlay';

export interface AIAnalysisProps {
  analysis: AnalysisPayload;
  userRole: UserRole;
  'data-testid'?: string;
}

const UPGRADE_MESSAGE = "Débloque l'analyse complète avec Premium";
const SIGNUP_MESSAGE = 'Crée un compte pour accéder à l’analyse IA';

function Paragraphs({ paragraphs }: { paragraphs: string[] }) {
  return (
    <>
      {paragraphs.map((p, i) => (
        <p
          key={i}
          className="mb-2 text-sm leading-relaxed text-slate-700 last:mb-0"
        >
          {p}
        </p>
      ))}
    </>
  );
}

export function AIAnalysis({
  analysis,
  userRole,
  'data-testid': dataTestId = 'ai-analysis',
}: AIAnalysisProps) {
  const { paragraphs } = analysis;
  const isVisitor = userRole === 'visitor';
  const isFree = userRole === 'free';

  if (isVisitor) {
    return (
      <section
        data-testid={dataTestId}
        className="rounded-xl border border-slate-200 bg-white p-4"
      >
        <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-900">
          <Sparkles className="h-4 w-4 text-violet-600" aria-hidden="true" />
          Analyse IA
        </h3>
        <LockOverlay message={SIGNUP_MESSAGE}>
          <Paragraphs paragraphs={paragraphs} />
        </LockOverlay>
      </section>
    );
  }

  const [first, ...rest] = paragraphs;
  const gated = isFree && rest.length > 0;

  return (
    <section
      data-testid={dataTestId}
      className="rounded-xl border border-slate-200 bg-white p-4"
    >
      <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-900">
        <Sparkles className="h-4 w-4 text-violet-600" aria-hidden="true" />
        Analyse IA
      </h3>
      {first && (
        <p className="mb-2 text-sm leading-relaxed text-slate-800">{first}</p>
      )}
      {rest.length > 0 &&
        (gated ? (
          <div className="relative mt-2">
            <LockOverlay message={UPGRADE_MESSAGE}>
              <Paragraphs paragraphs={rest} />
            </LockOverlay>
          </div>
        ) : (
          <Paragraphs paragraphs={rest} />
        ))}
    </section>
  );
}

export default AIAnalysis;
