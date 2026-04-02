
import { useState, useEffect } from 'react'
import { Protected } from '@/lib/auth'
import { triggerPipeline, triggerNHLPipeline, fetchPipelineStatus, stopPipeline } from '@/lib/api'
import { Shield, Play, Loader2, Cpu, Terminal, Activity, Server, Database, StopCircle, Clock, Calendar, Users, Wrench, Globe, BarChart3 } from 'lucide-react'
import AdminUsers from '@/components/AdminUsers'
import AdminOverview from '@/components/AdminOverview'
import AdminLeagues from '@/components/AdminLeagues'
import AdminTools from '@/components/AdminTools'

const TABS = [
    { id: 'overview', label: 'Vue d\'ensemble', icon: BarChart3 },
    { id: 'users', label: 'Utilisateurs', icon: Users },
    { id: 'pipeline', label: 'Pipeline', icon: Cpu },
    { id: 'automations', label: 'Automatisations', icon: Clock },
    { id: 'leagues', label: 'Ligues', icon: Globe },
    { id: 'tools', label: 'Outils', icon: Wrench },
] as const

type TabId = typeof TABS[number]['id']

function AdminDashboard() {
    const [status, setStatus] = useState<any>(null)
    const [loading, setLoading] = useState(false)
    const [msg, setMsg] = useState('')
    const [nhlLoading, setNhlLoading] = useState(false)
    const [nhlMsg, setNhlMsg] = useState('')
    const [activeTab, setActiveTab] = useState<TabId>('overview')

    const refreshStatus = async () => {
        try {
            const s = await fetchPipelineStatus()
            setStatus(s)
        } catch (err) {
            console.error(err)
        }
    }

    useEffect(() => {
        refreshStatus()
        const interval = setInterval(() => {
            // Pause polling when tab is not visible to save bandwidth
            if (document.visibilityState === 'visible') {
                refreshStatus()
            }
        }, 3000)
        return () => clearInterval(interval)
    }, [])

    const handleRun = async (mode: string) => {
        setLoading(true)
        setMsg('')
        try {
            await triggerPipeline(mode)
            setTimeout(refreshStatus, 1000)
        } catch (err: any) {
            setMsg(`Erreur: ${err.message}`)
        } finally {
            setLoading(false)
        }
    }

    const handleNHLRun = async () => {
        setNhlLoading(true)
        setNhlMsg('')
        try {
            await triggerNHLPipeline()
            setTimeout(refreshStatus, 1000)
        } catch (err: any) {
            setNhlMsg(`Erreur: ${err.message}`)
        } finally {
            setNhlLoading(false)
        }
    }

    const handleStop = async () => {
        if (!window.confirm('Voulez-vous vraiment forcer l\'arrêt de l\'analyse en cours ?')) return
        try {
            await stopPipeline()
            setMsg('Arrêt en cours...')
            setTimeout(refreshStatus, 1500)
        } catch (err: any) {
            setMsg(`Erreur lors de l'arrêt: ${err.message}`)
        }
    }

    const isRunning = status?.status === 'running'

    return (
        <div className="relative min-h-[calc(100vh-4rem)] bg-background overflow-hidden p-3 sm:p-6 md:p-10">
            {/* Background Effects */}
            <div className="absolute inset-0 w-full h-full bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-indigo-900/20 via-background to-background pointer-events-none" />
            <div className="absolute bottom-0 left-0 w-[500px] h-[500px] bg-indigo-500/5 rounded-full blur-3xl pointer-events-none" />

            <div className="relative z-10 w-full mx-auto space-y-4 sm:space-y-6 md:space-y-8">
                {/* Header */}
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
                    <div className="flex items-center gap-3">
                        <div className="p-2 sm:p-3 rounded-xl sm:rounded-2xl bg-gradient-to-br from-indigo-500/20 to-purple-500/20 border border-indigo-500/30 shadow-lg shadow-indigo-500/10">
                            <Shield className="w-5 h-5 sm:w-8 sm:h-8 text-indigo-400" />
                        </div>
                        <div>
                            <h1 className="text-xl sm:text-3xl font-bold tracking-tight">
                                <span className="gradient-text">Centre Admin</span>
                            </h1>
                            <p className="text-muted-foreground text-xs sm:text-base mt-0.5">Pilotage des pipelines Football & NHL</p>
                        </div>
                    </div>

                    <div className="flex items-center gap-2 sm:gap-4">
                        {isRunning && (
                            <button
                                onClick={handleStop}
                                className="flex items-center gap-1.5 px-2.5 py-1 sm:px-3 sm:py-1.5 rounded-full bg-red-500/10 hover:bg-red-500/20 text-red-500 border border-red-500/30 transition-all font-semibold text-xs sm:text-sm hover:shadow-[0_0_15px_-3px_rgba(239,68,68,0.4)]"
                                title="Arrêter de force le pipeline en cours"
                            >
                                <StopCircle className="w-3.5 h-3.5" /> Stop
                            </button>
                        )}
                        <div className="flex items-center gap-1.5 px-3 py-1.5 sm:px-4 sm:py-2 rounded-full glass border border-white/5">
                            <div className={`w-2 h-2 sm:w-2.5 sm:h-2.5 rounded-full ${isRunning ? 'bg-emerald-500 animate-pulse' : 'bg-slate-500'}`} />
                            <span className="text-xs sm:text-sm font-medium text-muted-foreground">
                                <span className="hidden sm:inline">Système: </span><span className={isRunning ? 'text-emerald-400' : 'text-slate-400'}>{status?.status?.toUpperCase() || 'HORS LIGNE'}</span>
                            </span>
                        </div>
                    </div>
                </div>

                {/* ── Tab Navigation (mobile: scrollable, icons + short labels) ── */}
                <div className="overflow-x-auto -mx-3 px-3 sm:mx-0 sm:px-0 scrollbar-none">
                    <div className="flex gap-1 p-1 rounded-xl bg-white/5 border border-white/10 w-max sm:w-fit min-w-full sm:min-w-0">
                        {TABS.map(tab => {
                            const Icon = tab.icon
                            const isActive = activeTab === tab.id
                            return (
                                <button
                                    key={tab.id}
                                    onClick={() => setActiveTab(tab.id)}
                                    className={`flex items-center gap-1.5 px-2.5 py-2 sm:px-4 sm:py-2 rounded-lg text-xs sm:text-sm font-semibold transition-all whitespace-nowrap ${isActive
                                        ? 'bg-primary text-primary-foreground shadow-md'
                                        : 'text-muted-foreground hover:text-foreground hover:bg-white/5'
                                        }`}
                                >
                                    <Icon className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
                                    <span>{tab.label}</span>
                                </button>
                            )
                        })}
                    </div>
                </div>

                {/* ── Tab: Overview ── */}
                {activeTab === 'overview' && <AdminOverview />}

                {/* ── Tab: Users ── */}
                {activeTab === 'users' && <AdminUsers />}

                {/* ── Tab: Pipeline ── */}
                {activeTab === 'pipeline' && (
                    <div className="grid lg:grid-cols-3 gap-6">
                        {/* Colonne Gauche : Contrôles */}
                        <div className="lg:col-span-1 space-y-6">
                            {/* ⚽ Football Pipeline */}
                            <div className="glass rounded-2xl border border-white/5 p-6 shadow-xl relative overflow-hidden group">
                                <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />

                                <h2 className="text-lg font-semibold flex items-center gap-2 mb-6">
                                    <Cpu className="w-5 h-5 text-indigo-400" />
                                    <span>⚽ Pipeline Football</span>
                                </h2>

                                <div className="space-y-3 relative z-10">
                                    <button
                                        onClick={() => handleRun('full')}
                                        disabled={loading || isRunning}
                                        className="w-full relative group overflow-hidden rounded-xl p-[1px] focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                                    >
                                        <span className="absolute inset-0 bg-gradient-to-r from-indigo-500 via-purple-500 to-indigo-500 opacity-70 group-hover:opacity-100 animate-gradient-xy transition-opacity" />
                                        <div className="relative bg-background/90 backdrop-blur-sm rounded-xl px-4 py-4 flex items-center justify-between group-hover:bg-background/80 transition-all">
                                            <div className="flex flex-col items-start">
                                                <span className="font-semibold text-white">Lancer Analyse Complète</span>
                                                <span className="text-xs text-muted-foreground">Données + IA + Prédictions</span>
                                            </div>
                                            {loading ? (
                                                <Loader2 className="w-5 h-5 text-indigo-400 animate-spin" />
                                            ) : (
                                                <Play className="w-5 h-5 text-indigo-400 group-hover:scale-110 transition-transform" />
                                            )}
                                        </div>
                                    </button>

                                    <div className="grid grid-cols-2 gap-3 pt-2">
                                        <button
                                            onClick={() => handleRun('data')}
                                            disabled={loading || isRunning}
                                            className="flex flex-col items-center justify-center gap-2 p-4 rounded-xl border border-white/10 bg-white/5 hover:bg-white/10 hover:border-indigo-500/30 transition-all"
                                        >
                                            <Database className="w-5 h-5 text-blue-400" />
                                            <span className="text-xs font-medium">Données</span>
                                        </button>
                                        <button
                                            onClick={() => handleRun('analyze')}
                                            disabled={loading || isRunning}
                                            className="flex flex-col items-center justify-center gap-2 p-4 rounded-xl border border-white/10 bg-white/5 hover:bg-white/10 hover:border-purple-500/30 transition-all"
                                        >
                                            <Activity className="w-5 h-5 text-purple-400" />
                                            <span className="text-xs font-medium">IA Seule</span>
                                        </button>
                                    </div>
                                </div>

                                {msg && (
                                    <div className="mt-4 p-3 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-xs text-indigo-300 flex items-center gap-2 animate-in fade-in slide-in-from-top-2">
                                        <Server className="w-3 h-3" />
                                        {msg}
                                    </div>
                                )}
                            </div>

                            {/* 🏒 NHL Pipeline */}
                            <div className="glass rounded-2xl border border-cyan-500/20 p-6 shadow-xl relative overflow-hidden group">
                                <div className="absolute inset-0 bg-gradient-to-br from-cyan-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />

                                <h2 className="text-lg font-semibold flex items-center gap-2 mb-6">
                                    <span className="text-xl">🏒</span>
                                    <span>Pipeline NHL</span>
                                </h2>

                                <div className="space-y-3 relative z-10">
                                    <button
                                        onClick={handleNHLRun}
                                        disabled={nhlLoading}
                                        className="w-full relative group overflow-hidden rounded-xl p-[1px] focus:outline-none focus:ring-2 focus:ring-cyan-500/50"
                                    >
                                        <span className="absolute inset-0 bg-gradient-to-r from-cyan-500 via-teal-500 to-cyan-500 opacity-70 group-hover:opacity-100 animate-gradient-xy transition-opacity" />
                                        <div className="relative bg-background/90 backdrop-blur-sm rounded-xl px-4 py-4 flex items-center justify-between group-hover:bg-background/80 transition-all">
                                            <div className="flex flex-col items-start">
                                                <span className="font-semibold text-white">Lancer Pipeline NHL</span>
                                                <span className="text-xs text-muted-foreground">Schedule + Roster + Scoring</span>
                                            </div>
                                            {nhlLoading ? (
                                                <Loader2 className="w-5 h-5 text-cyan-400 animate-spin" />
                                            ) : (
                                                <Play className="w-5 h-5 text-cyan-400 group-hover:scale-110 transition-transform" />
                                            )}
                                        </div>
                                    </button>
                                </div>

                                {nhlMsg && (
                                    <div className={`mt-4 p-3 rounded-lg text-xs flex items-center gap-2 animate-in fade-in slide-in-from-top-2 ${nhlMsg.startsWith('✅')
                                        ? 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-300'
                                        : 'bg-red-500/10 border border-red-500/20 text-red-300'
                                        }`}>
                                        <Server className="w-3 h-3" />
                                        {nhlMsg}
                                    </div>
                                )}
                            </div>

                            {/* Stats Rapides */}
                            {status?.started_at && (
                                <div className="glass rounded-xl border border-white/5 p-5 space-y-3">
                                    <div className="flex justify-between items-center text-sm">
                                        <span className="text-muted-foreground">Démarré :</span>
                                        <span className="font-mono text-xs">{new Date(status.started_at).toLocaleTimeString()}</span>
                                    </div>
                                    {status.finished_at && (
                                        <div className="flex justify-between items-center text-sm">
                                            <span className="text-muted-foreground">Terminé :</span>
                                            <span className="font-mono text-xs text-emerald-400">{new Date(status.finished_at).toLocaleTimeString()}</span>
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>

                        {/* Colonne Droite : Terminal */}
                        <div className="lg:col-span-2">
                            <div className="glass rounded-2xl border border-white/5 p-0 shadow-2xl overflow-hidden flex flex-col h-[500px]">
                                <div className="px-4 py-3 border-b border-white/5 bg-black/20 flex items-center justify-between">
                                    <div className="flex items-center gap-2">
                                        <Terminal className="w-4 h-4 text-muted-foreground" />
                                        <span className="text-xs font-medium text-muted-foreground">Logs en Direct</span>
                                    </div>
                                    <div className="flex gap-1.5">
                                        <div className="w-2.5 h-2.5 rounded-full bg-red-500/20 border border-red-500/50" />
                                        <div className="w-2.5 h-2.5 rounded-full bg-amber-500/20 border border-amber-500/50" />
                                        <div className="w-2.5 h-2.5 rounded-full bg-emerald-500/20 border border-emerald-500/50" />
                                    </div>
                                </div>

                                <div className="flex-1 bg-[#0a0a0a] p-4 overflow-y-auto font-mono text-xs leading-relaxed scrollbar-thin scrollbar-thumb-white/10 scrollbar-track-transparent">
                                    {status?.logs ? (
                                        <div className="text-slate-300 whitespace-pre-wrap">
                                            {status.logs.split('\n').map((line: string, i: number) => {
                                                if (line.includes('[INFO]')) return <div key={i}><span className="text-blue-500">[INFO]</span> {line.replace(/.*\[INFO\]/, '')}</div>
                                                if (line.includes('[ERROR]')) return <div key={i}><span className="text-red-500">[ERROR]</span> {line.replace(/.*\[ERROR\]/, '')}</div>
                                                if (line.includes('✅')) return <div key={i} className="text-emerald-400">{line}</div>
                                                if (line.includes('📊')) return <div key={i} className="text-purple-400 font-bold mt-2">{line}</div>
                                                if (line.includes('🏒')) return <div key={i} className="text-cyan-400 font-bold">{line}</div>
                                                return <div key={i} className="opacity-80">{line}</div>
                                            })}
                                            {isRunning && <span className="inline-block w-2 h-4 bg-emerald-500 animate-pulse ml-1 align-middle" />}
                                        </div>
                                    ) : (
                                        <div className="flex flex-col items-center justify-center h-full text-muted-foreground/40 gap-3">
                                            <Terminal className="w-8 h-8" />
                                            <div className="text-center">
                                                <p className="text-sm font-medium">Aucun pipeline actif</p>
                                                <p className="text-xs mt-1">Lancez un pipeline pour voir les logs en temps réel</p>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {/* ── Tab: Automations ── */}
                {activeTab === 'automations' && (
                    <div className="glass rounded-2xl border border-white/5 p-6 shadow-xl">
                        <h2 className="text-lg font-semibold flex items-center gap-2 mb-6">
                            <Clock className="w-5 h-5 text-amber-400" />
                            <span>Automatisations Trigger.dev</span>
                            <span className="text-xs font-normal text-muted-foreground ml-auto">Heures en UTC → Paris</span>
                        </h2>

                        <div className="grid md:grid-cols-3 gap-6">
                            {/* ⚽ Football Only */}
                            <div className="space-y-3">
                                <h3 className="text-sm font-bold text-indigo-400 flex items-center gap-1.5 mb-3">
                                    <span>⚽</span> Football
                                </h3>
                                {[
                                    { time: '06:00', paris: '07:00', cron: '0 6 * * *', name: 'Pipeline Quotidien', desc: 'Reflection + Fetch données + IA + Prédictions + DeepThink' },
                                    { time: '*/15 (10h-22h)', paris: '11h-23h', cron: '*/15 10-22 * * *', name: 'Fetch Lineups', desc: 'Compos probables H-1 avant kickoff' },
                                    { time: '23:30', paris: '00:30', cron: '30 23 * * *', name: 'Recap Journée', desc: 'Résumé des résultats + bilan du jour' },
                                ].map((t, i) => (
                                    <div key={i} className="flex items-start gap-3 p-2.5 rounded-lg bg-white/5 hover:bg-white/8 transition-colors">
                                        <div className="shrink-0 w-[85px] text-right">
                                            <div className="text-xs font-mono font-bold text-foreground">{t.paris}</div>
                                            <div className="text-[10px] font-mono text-muted-foreground">{t.time} UTC</div>
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <div className="text-xs font-semibold flex items-center gap-1.5">
                                                {t.name}
                                                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500/60" title="Automatisé" />
                                            </div>
                                            <div className="text-[10px] text-muted-foreground">{t.desc}</div>
                                            <div className="text-[9px] font-mono text-muted-foreground/60 mt-0.5">{t.cron}</div>
                                        </div>
                                    </div>
                                ))}
                            </div>

                            {/* ⚽🏒 Mixed */}
                            <div className="space-y-3">
                                <h3 className="text-sm font-bold text-amber-400 flex items-center gap-1.5 mb-3">
                                    <span>⚽🏒</span> Mixte
                                </h3>
                                {[
                                    { time: '08:00', paris: '09:00', cron: '0 8 * * *', name: 'Schedule Daily', desc: '⚽ Matchs du jour + halftime/70min monitors\n🏒 NHL Performance eval' },
                                    { time: '*/1 min', paris: '24/7', cron: '* * * * *', name: 'Live Tracker', desc: '⚽ Scores */1min (1 call) · Events+Stats */5min (detail)\n🏒 NHL live scores (16h-08h)' },
                                    { time: '10:00 / 15:00', paris: '11:00 / 16:00', cron: '0 10,15 * * *', name: 'Value Bets', desc: '⚽ Football value bets (10h UTC)\n🏒 NHL value bets (15h UTC)' },
                                ].map((t, i) => (
                                    <div key={i} className="flex items-start gap-3 p-2.5 rounded-lg bg-white/5 hover:bg-white/8 transition-colors">
                                        <div className="shrink-0 w-[85px] text-right">
                                            <div className="text-xs font-mono font-bold text-foreground">{t.paris}</div>
                                            <div className="text-[10px] font-mono text-muted-foreground">{t.time} UTC</div>
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <div className="text-xs font-semibold flex items-center gap-1.5">
                                                {t.name}
                                                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500/60" title="Automatisé" />
                                            </div>
                                            <div className="text-[10px] text-muted-foreground whitespace-pre-line">{t.desc}</div>
                                            <div className="text-[9px] font-mono text-muted-foreground/60 mt-0.5">{t.cron}</div>
                                        </div>
                                    </div>
                                ))}
                            </div>

                            {/* 🏒 NHL + 🧠 ML */}
                            <div className="space-y-3">
                                <h3 className="text-sm font-bold text-cyan-400 flex items-center gap-1.5 mb-3">
                                    <span>🏒</span> NHL + <span className="text-purple-400">🧠 ML</span>
                                </h3>
                                {[
                                    { time: '09:00', paris: '10:00', cron: '0 9 * * *', name: '🏒 Pipeline NHL', desc: 'Schedule + Roster + Scoring + ML Blend + DeepThink' },
                                    { time: '22:00', paris: '23:00', cron: '0 22 * * *', name: '🏒 Fetch Odds NHL', desc: 'Cotes des bookmakers pour value bets' },
                                    { time: '04:00', paris: '05:00', cron: '0 4 * * *', name: '🧠 ML Évaluation', desc: '⚽ Football: Brier Score + Log Loss + ECE\n🏒 NHL: history sync' },
                                    { time: 'Ven 02:00', paris: 'Ven 03:00', cron: '0 2 * * 5', name: '🧠 Retrain XGBoost', desc: '⚽ Football Meta-Modèle + 🏒 NHL Match ML\nRetrain hebdomadaire des deux modèles' },
                                ].map((t, i) => (
                                    <div key={i} className="flex items-start gap-3 p-2.5 rounded-lg bg-white/5 hover:bg-white/8 transition-colors">
                                        <div className="shrink-0 w-[85px] text-right">
                                            <div className="text-xs font-mono font-bold text-foreground">{t.paris}</div>
                                            <div className="text-[10px] font-mono text-muted-foreground">{t.time} UTC</div>
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <div className="text-xs font-semibold flex items-center gap-1.5">
                                                {t.name}
                                                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500/60" title="Automatisé" />
                                            </div>
                                            <div className="text-[10px] text-muted-foreground">{t.desc}</div>
                                            <div className="text-[9px] font-mono text-muted-foreground/60 mt-0.5">{t.cron}</div>
                                        </div>
                                    </div>
                                ))}

                                {/* Leagues info */}
                                <div className="mt-4 p-3 rounded-lg bg-indigo-500/5 border border-indigo-500/10">
                                    <div className="text-xs font-semibold flex items-center gap-1.5 mb-2">
                                        <Calendar className="w-3.5 h-3.5 text-indigo-400" />
                                        Ligues suivies
                                    </div>
                                    <div className="text-[10px] text-muted-foreground space-y-0.5">
                                        <div>🇫🇷 Ligue 1 · Ligue 2 · Coupe de France</div>
                                        <div>🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League · FA Cup</div>
                                        <div>🇪🇸 La Liga · Copa del Rey</div>
                                        <div>🇮🇹 Serie A · Coppa Italia</div>
                                        <div>🇩🇪 Bundesliga · DFB-Pokal</div>
                                        <div>🏆 Champions League · Europa League</div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {/* ── Tab: Leagues ── */}
                {activeTab === 'leagues' && <AdminLeagues />}

                {/* ── Tab: Tools ── */}
                {activeTab === 'tools' && <AdminTools />}
            </div>
        </div >
    )
}

export default function AdminPage() {
    return (
        <Protected requiredRole="admin" fallback={<div className="min-h-screen flex items-center justify-center text-muted-foreground">🚫 Accès non autorisé</div>}>
            <AdminDashboard />
        </Protected>
    )
}
