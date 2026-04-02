import { useState, useEffect } from 'react'
import { supabase } from '@/lib/auth'
import { Globe, RefreshCw } from 'lucide-react'
import { API_ROOT } from '@/lib/api'

const FLAGS: Record<string, string> = {
    France: '🇫🇷', England: '🏴󠁧󠁢󠁥󠁮󠁧󠁿', Spain: '🇪🇸', Italy: '🇮🇹', Germany: '🇩🇪', World: '🏆',
}

export default function AdminLeagues() {
    const [leagues, setLeagues] = useState<any[]>([])
    const [loading, setLoading] = useState(true)

    const fetchLeagues = async () => {
        setLoading(true)
        try {
            const { data } = await supabase.auth.getSession()
            const token = data?.session?.access_token
            const res = await fetch(`${API_ROOT}/api/trigger/admin/leagues`, {
                headers: { 'Authorization': `Bearer ${token}` },
            })
            if (!res.ok) throw new Error(`HTTP ${res.status}`)
            const json = await res.json()
            setLeagues(json.leagues || [])
        } catch (e) { console.error('Erreur chargement ligues:', e) }
        finally { setLoading(false) }
    }

    useEffect(() => { fetchLeagues() }, [])

    const grouped = leagues.reduce((acc: Record<string, any[]>, l: any) => {
        const country = l.country || 'Other'
        if (!acc[country]) acc[country] = []
        acc[country].push(l)
        return acc
    }, {})

    return (
        <div className="glass rounded-2xl border border-white/5 p-6 shadow-xl">
            <div className="flex items-center justify-between mb-6">
                <h2 className="text-lg font-semibold flex items-center gap-2">
                    <Globe className="w-5 h-5 text-green-400" />
                    Ligues suivies
                </h2>
                <button onClick={fetchLeagues} disabled={loading}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-white/5 hover:bg-white/10 border border-white/10">
                    <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} /> Rafraîchir
                </button>
            </div>

            <p className="text-xs text-muted-foreground mb-4">
                Liste des ligues actuellement suivies par le pipeline quotidien. Pour ajouter/retirer une ligue, modifier <code className="bg-white/10 px-1 rounded">src/config.py → LEAGUES</code>.
            </p>

            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                {Object.entries(grouped).map(([country, countryLeagues]) => (
                    <div key={country} className="rounded-xl border border-white/10 p-4 bg-white/5">
                        <h3 className="text-sm font-bold mb-3 flex items-center gap-2">
                            <span className="text-lg">{FLAGS[country] || '🌍'}</span>
                            {country}
                        </h3>
                        <div className="space-y-2">
                            {(countryLeagues as any[]).map((league: any) => (
                                <div key={league.id} className="flex items-center justify-between p-2 rounded-lg bg-white/5 hover:bg-white/10 transition-colors">
                                    <span className="text-sm font-medium">{league.name}</span>
                                    <span className="text-[10px] font-mono text-muted-foreground bg-white/10 px-2 py-0.5 rounded">ID: {league.id}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                ))}
            </div>

            <div className="mt-6 p-4 rounded-xl bg-amber-500/5 border border-amber-500/20">
                <p className="text-xs text-amber-400">
                    💡 <strong>Astuce :</strong> Chaque ligue ajoutée augmente la consommation API-Football d'environ +5000 requêtes/jour. Actuellement {leagues.length} ligues = ~{leagues.length * 5000} req estimées.
                </p>
            </div>
        </div>
    )
}
