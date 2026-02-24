
import { useState, useEffect } from 'react'
import { Protected } from '@/lib/auth'
import { triggerPipeline, triggerNHLPipeline, fetchPipelineStatus, stopPipeline } from '@/lib/api'
import { Shield, Play, Loader2, Cpu, Terminal, Activity, Server, Database, StopCircle } from 'lucide-react'

function AdminDashboard() {
    const [status, setStatus] = useState(null)
    const [loading, setLoading] = useState(false)
    const [msg, setMsg] = useState('')
    const [nhlLoading, setNhlLoading] = useState(false)
    const [nhlMsg, setNhlMsg] = useState('')

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
        const interval = setInterval(refreshStatus, 3000)
        return () => clearInterval(interval)
    }, [])

    const handleRun = async (mode) => {
        setLoading(true)
        setMsg('')
        try {
            await triggerPipeline(mode)
            setTimeout(refreshStatus, 1000)
        } catch (err) {
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
        } catch (err) {
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
        } catch (err) {
            setMsg(`Erreur lors de l'arrêt: ${err.message}`)
        }
    }

    const isRunning = status?.status === 'running'

    return (
        <div className="relative min-h-[calc(100vh-4rem)] bg-background overflow-hidden p-6 md:p-10">
            {/* Background Effects */}
            <div className="absolute inset-0 w-full h-full bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-indigo-900/20 via-background to-background pointer-events-none" />
            <div className="absolute bottom-0 left-0 w-[500px] h-[500px] bg-indigo-500/5 rounded-full blur-3xl pointer-events-none" />

            <div className="relative z-10 max-w-6xl mx-auto space-y-8">
                {/* Header */}
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div className="flex items-center gap-4">
                        <div className="p-3 rounded-2xl bg-gradient-to-br from-indigo-500/20 to-purple-500/20 border border-indigo-500/30 shadow-lg shadow-indigo-500/10">
                            <Shield className="w-8 h-8 text-indigo-400" />
                        </div>
                        <div>
                            <h1 className="text-3xl font-bold tracking-tight">
                                <span className="gradient-text">Centre Admin</span>
                            </h1>
                            <p className="text-muted-foreground mt-1">Pilotage des pipelines Football & NHL</p>
                        </div>
                    </div>

                    <div className="flex items-center gap-4">
                        {isRunning && (
                            <button
                                onClick={handleStop}
                                className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-red-500/10 hover:bg-red-500/20 text-red-500 border border-red-500/30 transition-all font-semibold text-sm hover:shadow-[0_0_15px_-3px_rgba(239,68,68,0.4)]"
                                title="Arrêter de force le pipeline en cours"
                            >
                                <StopCircle className="w-4 h-4" /> Stop
                            </button>
                        )}
                        <div className="flex items-center gap-2 px-4 py-2 rounded-full glass border border-white/5">
                            <div className={`w-2.5 h-2.5 rounded-full ${isRunning ? 'bg-emerald-500 animate-pulse' : 'bg-slate-500'}`} />
                            <span className="text-sm font-medium text-muted-foreground">
                                Système: <span className={isRunning ? 'text-emerald-400' : 'text-slate-400'}>{status?.status?.toUpperCase() || 'HORS LIGNE'}</span>
                            </span>
                        </div>
                    </div>
                </div>

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
                                        {status.logs.split('\n').map((line, i) => {
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
                                    <div className="flex items-center justify-center h-full text-muted-foreground/50 italic">
                                        En attente de logs...
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}

export default function AdminPage() {
    return (
        <Protected requiredRole="admin" fallback={<div className="min-h-screen flex items-center justify-center text-muted-foreground">🚫 Accès non autorisé</div>}>
            <AdminDashboard />
        </Protected>
    )
}
