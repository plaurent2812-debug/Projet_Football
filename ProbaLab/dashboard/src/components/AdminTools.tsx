import { useState } from 'react'
import { supabase } from '@/lib/auth'
import { Wrench, Trash2, Zap, CheckCircle, AlertCircle, Loader2 } from 'lucide-react'
import { API_ROOT } from '@/lib/api'

export default function AdminTools() {
    const [testFixtureId, setTestFixtureId] = useState('')
    const [testResult, setTestResult] = useState<any>(null)
    const [testLoading, setTestLoading] = useState(false)
    const [cacheMsg, setCacheMsg] = useState('')
    const [cacheLoading, setCacheLoading] = useState(false)

    const runTestPrediction = async () => {
        const id = testFixtureId.trim()
        if (!id) return
        if (!/^\d+$/.test(id)) {
            setTestResult({ ok: false, data: { error: "Le Fixture ID doit être numérique (ex: 1208736)" } })
            return
        }
        setTestLoading(true)
        setTestResult(null)
        try {
            const { data } = await supabase.auth.getSession()
            const token = data?.session?.access_token
            const res = await fetch(`${API_ROOT}/api/trigger/analyze-fixture`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                body: JSON.stringify({ fixture_id: testFixtureId.trim() }),
            })
            const json = await res.json()
            setTestResult({ ok: res.ok, data: json })
        } catch (e: any) {
            setTestResult({ ok: false, data: { error: e.message } })
        } finally {
            setTestLoading(false)
        }
    }

    const clearPredictionCache = async () => {
        setCacheLoading(true)
        setCacheMsg('')
        try {
            // Clear the frontend prediction cache by reloading
            if ('caches' in window) {
                const keys = await caches.keys()
                await Promise.all(keys.map(k => caches.delete(k)))
            }
            // Clear localStorage cache entries
            const keysToRemove: string[] = []
            for (let i = 0; i < localStorage.length; i++) {
                const key = localStorage.key(i)
                if (key && (key.includes('cache') || key.includes('predictions'))) {
                    keysToRemove.push(key)
                }
            }
            keysToRemove.forEach(k => localStorage.removeItem(k))
            setCacheMsg(`✅ Cache vidé (${keysToRemove.length} entrées supprimées)`)
        } catch (e: any) {
            setCacheMsg(`❌ Erreur: ${e.message}`)
        } finally {
            setCacheLoading(false)
        }
    }

    return (
        <div className="space-y-6">
            {/* Test Prediction */}
            <div className="glass rounded-2xl border border-white/5 p-6 shadow-xl">
                <h2 className="text-lg font-semibold flex items-center gap-2 mb-4">
                    <Zap className="w-5 h-5 text-amber-400" />
                    Test de Prédiction
                </h2>
                <p className="text-xs text-muted-foreground mb-4">
                    Lancer une analyse Gemini sur un match spécifique. Entrez l'ID de la fixture API-Football.
                </p>
                <div className="flex gap-3">
                    <input
                        type="text"
                        value={testFixtureId}
                        onChange={e => setTestFixtureId(e.target.value)}
                        placeholder="Ex: 1234567"
                        className="flex-1 px-4 py-2.5 rounded-lg bg-white/5 border border-white/10 focus:outline-none focus:ring-2 focus:ring-amber-500/50 text-sm font-mono"
                    />
                    <button
                        onClick={runTestPrediction}
                        disabled={testLoading || !testFixtureId.trim()}
                        className="px-4 py-2.5 rounded-lg bg-amber-500/20 hover:bg-amber-500/30 text-amber-400 border border-amber-500/30 text-sm font-semibold disabled:opacity-50 transition-colors flex items-center gap-2"
                    >
                        {testLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
                        Analyser
                    </button>
                </div>
                {testResult && (
                    <div className={`mt-4 p-4 rounded-xl border text-xs font-mono overflow-auto max-h-[300px] ${testResult.ok ? 'bg-emerald-500/5 border-emerald-500/20' : 'bg-red-500/5 border-red-500/20'}`}>
                        <div className="flex items-center gap-2 mb-2">
                            {testResult.ok ? <CheckCircle className="w-4 h-4 text-emerald-400" /> : <AlertCircle className="w-4 h-4 text-red-400" />}
                            <span className={testResult.ok ? 'text-emerald-400' : 'text-red-400'}>{testResult.ok ? 'Succès' : 'Erreur'}</span>
                        </div>
                        <pre className="whitespace-pre-wrap text-muted-foreground">{JSON.stringify(testResult.data, null, 2)}</pre>
                    </div>
                )}
            </div>

            {/* Cache Manager */}
            <div className="glass rounded-2xl border border-white/5 p-6 shadow-xl">
                <h2 className="text-lg font-semibold flex items-center gap-2 mb-4">
                    <Trash2 className="w-5 h-5 text-red-400" />
                    Gestion du Cache
                </h2>
                <p className="text-xs text-muted-foreground mb-4">
                    Vider le cache frontend (localStorage + Service Worker). Utile après un changement de données ou un bug d'affichage.
                </p>
                <button
                    onClick={clearPredictionCache}
                    disabled={cacheLoading}
                    className="px-4 py-2.5 rounded-lg bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/30 text-sm font-semibold disabled:opacity-50 transition-colors flex items-center gap-2"
                >
                    {cacheLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                    Vider le cache
                </button>
                {cacheMsg && (
                    <p className={`mt-3 text-sm ${cacheMsg.startsWith('✅') ? 'text-emerald-400' : 'text-red-400'}`}>{cacheMsg}</p>
                )}
            </div>

            {/* System Info */}
            <div className="glass rounded-2xl border border-white/5 p-6 shadow-xl">
                <h2 className="text-lg font-semibold flex items-center gap-2 mb-4">
                    <Wrench className="w-5 h-5 text-slate-400" />
                    Informations Système
                </h2>
                <div className="grid md:grid-cols-2 gap-3">
                    {[
                        { label: 'Backend API', value: API_ROOT },
                        { label: 'Frontend', value: window.location.origin },
                        { label: 'Modèle IA', value: 'Gemini 2.5 Flash' },
                        { label: 'Base de données', value: 'Supabase (PostgreSQL)' },
                        { label: 'Scheduler', value: 'Trigger.dev v4' },
                        { label: 'Hébergement API', value: 'Railway' },
                    ].map(info => (
                        <div key={info.label} className="flex items-center justify-between p-3 rounded-lg bg-white/5 border border-white/5">
                            <span className="text-xs text-muted-foreground">{info.label}</span>
                            <span className="text-xs font-mono font-medium truncate max-w-[200px]">{info.value}</span>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    )
}
