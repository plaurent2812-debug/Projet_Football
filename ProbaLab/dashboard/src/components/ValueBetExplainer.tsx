import { useState } from "react"
import { TrendingUp, ChevronDown, ChevronUp, Target, BarChart2, ShieldCheck } from "lucide-react"

/**
 * ValueBetExplainer — Educational component explaining value betting.
 *
 * Collapsible by default. Uses a concrete example to explain
 * edge, expected value, and why it works long-term.
 * Designed to convert curious free users into understanding premium users.
 */

export function ValueBetExplainer({ defaultOpen = false }: { defaultOpen?: boolean }) {
    const [open, setOpen] = useState(defaultOpen)

    return (
        <div className="rounded-xl border border-primary/20 bg-primary/5 overflow-hidden">
            {/* Header — always visible */}
            <button
                onClick={() => setOpen(!open)}
                className="w-full flex items-center justify-between px-4 py-3 hover:bg-primary/10 transition-colors"
            >
                <div className="flex items-center gap-2">
                    <div className="w-7 h-7 rounded-lg bg-primary/20 flex items-center justify-center">
                        <TrendingUp className="w-3.5 h-3.5 text-primary" />
                    </div>
                    <span className="text-sm font-bold text-foreground">
                        C'est quoi un Value Bet ?
                    </span>
                </div>
                {open
                    ? <ChevronUp className="w-4 h-4 text-muted-foreground" />
                    : <ChevronDown className="w-4 h-4 text-muted-foreground" />
                }
            </button>

            {/* Content — collapsible */}
            {open && (
                <div className="px-4 pb-4 animate-fade-in-up">
                    {/* Simple explanation */}
                    <p className="text-sm text-muted-foreground leading-relaxed mb-4">
                        Un <strong className="text-foreground">Value Bet</strong>, c'est un pari
                        o&ugrave; le bookmaker <strong className="text-primary">sous-estime
                        la probabilit&eacute;</strong> d'un r&eacute;sultat. Sa cote est trop
                        haute par rapport aux chances r&eacute;elles — c'est votre avantage.
                    </p>

                    {/* Visual example */}
                    <div className="rounded-lg border border-border/50 bg-card p-4 mb-4">
                        <p className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-3">
                            Exemple concret
                        </p>

                        <div className="flex items-center gap-3 mb-3">
                            <span className="text-xs text-muted-foreground">Lyon vs Marseille</span>
                            <span className="text-xs font-bold text-primary bg-primary/10 px-2 py-0.5 rounded-full">
                                BTTS Oui
                            </span>
                        </div>

                        <div className="grid grid-cols-3 gap-2 mb-3">
                            <div className="text-center p-2 rounded-lg bg-muted/50">
                                <div className="text-lg font-black text-foreground tabular-nums">2.10</div>
                                <div className="text-xs text-muted-foreground">Cote Bet365</div>
                            </div>
                            <div className="text-center p-2 rounded-lg bg-muted/50">
                                <div className="text-lg font-black text-foreground tabular-nums">55%</div>
                                <div className="text-xs text-muted-foreground">Notre mod&egrave;le</div>
                            </div>
                            <div className="text-center p-2 rounded-lg bg-primary/10 border border-primary/30">
                                <div className="text-lg font-black text-primary tabular-nums">+7.4%</div>
                                <div className="text-xs text-primary/80 font-semibold">Edge</div>
                            </div>
                        </div>

                        <p className="text-xs text-muted-foreground leading-relaxed">
                            Le bookmaker estime 47.6% de chances (1/2.10).
                            Notre mod&egrave;le dit <strong className="text-foreground">55%</strong>.
                            L'&eacute;cart de <strong className="text-primary">+7.4%</strong> est
                            votre avantage math&eacute;matique.
                        </p>
                    </div>

                    {/* 3 key points */}
                    <div className="space-y-2.5">
                        <div className="flex items-start gap-2.5">
                            <div className="w-6 h-6 rounded-md bg-primary/15 flex items-center justify-center shrink-0 mt-0.5">
                                <Target className="w-3 h-3 text-primary" />
                            </div>
                            <div>
                                <p className="text-xs font-bold text-foreground">D&eacute;tection par nos experts</p>
                                <p className="text-xs text-muted-foreground">
                                    Nos experts s'appuient sur l'IA pour comparer
                                    les probabilit&eacute;s aux cotes Bet365 sur chaque match.
                                </p>
                            </div>
                        </div>

                        <div className="flex items-start gap-2.5">
                            <div className="w-6 h-6 rounded-md bg-primary/15 flex items-center justify-center shrink-0 mt-0.5">
                                <BarChart2 className="w-3 h-3 text-primary" />
                            </div>
                            <div>
                                <p className="text-xs font-bold text-foreground">Sizing intelligent</p>
                                <p className="text-xs text-muted-foreground">
                                    Le crit&egrave;re de Kelly calcule la mise optimale
                                    selon l'edge et la cote. Pas de pari au feeling.
                                </p>
                            </div>
                        </div>

                        <div className="flex items-start gap-2.5">
                            <div className="w-6 h-6 rounded-md bg-primary/15 flex items-center justify-center shrink-0 mt-0.5">
                                <ShieldCheck className="w-3 h-3 text-primary" />
                            </div>
                            <div>
                                <p className="text-xs font-bold text-foreground">Rentable sur le long terme</p>
                                <p className="text-xs text-muted-foreground">
                                    M&ecirc;me en perdant certains paris, un edge positif
                                    r&eacute;p&eacute;t&eacute; g&eacute;n&egrave;re un ROI positif
                                    sur des centaines de paris.
                                </p>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}
