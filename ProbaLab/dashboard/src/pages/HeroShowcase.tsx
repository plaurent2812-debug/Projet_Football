import { NeuralCortex } from "@/components/visuals/NeuralCortex"
import { DataMatrix } from "@/components/visuals/DataMatrix"
import { TopoMesh } from "@/components/visuals/TopoMesh"
import { OrbitalRings } from "@/components/visuals/OrbitalRings"
import { WaveGrid } from "@/components/visuals/WaveGrid"
import { Target } from "lucide-react"
import { Link } from "react-router-dom"

/**
 * HeroShowcase — Preview page to compare 4 hero visual styles.
 * Accessible at /hero-showcase (temporary, remove after choosing).
 */

const heroContent = (
    <div className="relative z-10 text-center">
        <h1 className="text-3xl sm:text-4xl font-black text-foreground mb-1 tracking-tighter">
            Proba<span className="gradient-text-premium">Lab</span>
        </h1>
        <p className="text-[0.6rem] font-semibold text-primary/60 uppercase tracking-[0.2em] mb-3">
            Smart Betting Assistant
        </p>
        <p className="text-sm text-muted-foreground max-w-xs mx-auto leading-relaxed mb-5">
            Notre IA analyse le march&eacute; et d&eacute;tecte les cotes sous-&eacute;valu&eacute;es en temps r&eacute;el.
        </p>
        <Link
            to="/paris-du-soir"
            className="inline-flex items-center gap-2 px-6 py-2.5 rounded-xl bg-primary text-primary-foreground text-sm font-bold hover:bg-primary/90 transition-all hover:scale-105 glow-value"
        >
            <Target className="w-4 h-4" />
            Value Bets du jour
        </Link>
    </div>
)

function HeroCard({ title, children }: { title: string; children: React.ReactNode }) {
    return (
        <div className="mb-8">
            <h2 className="text-lg font-bold text-foreground mb-3 px-4">{title}</h2>
            <div className="relative overflow-hidden border border-border/30 rounded-xl" style={{ height: 280 }}>
                {children}
                <div className="absolute inset-0 flex items-center justify-center">
                    {heroContent}
                </div>
            </div>
        </div>
    )
}

export default function HeroShowcase() {
    return (
        <div className="animate-fade-in-up px-3 py-6 max-w-2xl mx-auto">
            <h1 className="text-2xl font-black mb-2">Hero Showcase</h1>
            <p className="text-sm text-muted-foreground mb-8">4 variantes — choisis ton style.</p>

            <HeroCard title="1. Neural Cortex (actuel)">
                <NeuralCortex nodeCount={60} pulseSpeed={0.012} />
            </HeroCard>

            <HeroCard title="2. Data Matrix">
                <DataMatrix />
            </HeroCard>

            <HeroCard title="3. Topo Mesh (terrain 3D)">
                <TopoMesh />
            </HeroCard>

            <HeroCard title="4. Wave Grid (ripples)">
                <WaveGrid />
            </HeroCard>
        </div>
    )
}
