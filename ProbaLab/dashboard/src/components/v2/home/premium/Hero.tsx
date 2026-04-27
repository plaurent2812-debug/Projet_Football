import { motion, type Transition } from 'framer-motion';
import { ArrowRight, ChevronRight, Sparkles } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { fadeUp } from './animations';

function HeroBackdrop() {
  return (
    <div aria-hidden className="pointer-events-none absolute inset-0 overflow-hidden">
      <div
        className="absolute left-1/4 top-[-10%] h-[600px] w-[600px] rounded-full opacity-30 blur-3xl"
        style={{ background: 'radial-gradient(circle, #10b981 0%, transparent 65%)' }}
      />
      <div
        className="absolute right-[-10%] top-[30%] h-[500px] w-[500px] rounded-full opacity-20 blur-3xl"
        style={{ background: 'radial-gradient(circle, #3b82f6 0%, transparent 65%)' }}
      />
      <div
        className="absolute inset-0 opacity-[0.06]"
        style={{
          backgroundImage:
            'linear-gradient(rgba(255,255,255,0.3) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.3) 1px, transparent 1px)',
          backgroundSize: '60px 60px',
          maskImage: 'radial-gradient(ellipse at top, black 30%, transparent 70%)',
          WebkitMaskImage: 'radial-gradient(ellipse at top, black 30%, transparent 70%)',
        }}
      />
    </div>
  );
}

export function Hero() {
  const stagger: Transition = { staggerChildren: 0.08, delayChildren: 0.2 };

  return (
    <section className="relative overflow-hidden px-4 py-20 md:px-8 md:py-32">
      <HeroBackdrop />
      <motion.div
        initial="hidden"
        animate="show"
        variants={{ show: { transition: stagger } }}
        className="relative z-10 mx-auto max-w-5xl text-center"
      >
        <motion.div variants={fadeUp} className="mb-6 flex justify-center">
          <Badge
            variant="outline"
            className="gap-2 border-emerald-500/30 bg-emerald-500/5 text-emerald-400 backdrop-blur"
          >
            <Sparkles className="h-3 w-3" />
            Nouveau · analyses et probabilités en temps réel
          </Badge>
        </motion.div>

        <motion.h1
          variants={fadeUp}
          className="mx-auto max-w-4xl text-balance text-5xl font-bold leading-[1.05] tracking-tight text-white md:text-7xl"
        >
          Parier avec une{' '}
          <span
            className="bg-clip-text text-transparent"
            style={{
              backgroundImage:
                'linear-gradient(135deg, #10b981 0%, #34d399 50%, #60a5fa 100%)',
            }}
          >
            vraie probabilité
          </span>
          , pas un feeling.
        </motion.h1>

        <motion.p
          variants={fadeUp}
          className="mx-auto mt-8 max-w-2xl text-balance text-lg text-slate-400 md:text-xl"
        >
          Des probabilités sportives mises à jour avec les cotes du marché, des analyses
          courtes, et des pronos recommandés quand le modèle détecte un signal fort.
        </motion.p>

        <motion.div
          variants={fadeUp}
          className="mt-10 flex flex-col items-center justify-center gap-3 sm:flex-row"
        >
          <Button
            asChild
            size="lg"
            className="group gap-2 bg-emerald-500 text-black shadow-[0_0_0_1px_rgba(16,185,129,0.3),0_8px_24px_-8px_rgba(16,185,129,0.6)] transition-all hover:translate-y-[-1px] hover:bg-emerald-400"
          >
            <Link to="/premium">
              Essayer Premium 7 jours gratuits
              <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
            </Link>
          </Button>
          <Button
            asChild
            size="lg"
            variant="ghost"
            className="gap-2 text-slate-300 hover:bg-white/5 hover:text-white"
          >
            <Link to="/matchs">
              Voir les matchs du jour
              <ChevronRight className="h-4 w-4" />
            </Link>
          </Button>
        </motion.div>

        <motion.p variants={fadeUp} className="mt-5 text-xs text-slate-500">
          Sans engagement · Résiliation en 1 clic · Aucune carte requise pour l'essai
        </motion.p>

        {/* Stable E2E hook — primary hero CTAs go to /premium and /matchs */}
        <motion.p variants={fadeUp} className="mt-4">
          <Link
            to="/register"
            data-testid="cta-register-trial"
            className="text-sm font-medium text-emerald-400/90 underline-offset-4 transition hover:text-emerald-300 hover:underline"
          >
            Créer un compte (essai gratuit)
          </Link>
        </motion.p>
      </motion.div>
    </section>
  );
}
