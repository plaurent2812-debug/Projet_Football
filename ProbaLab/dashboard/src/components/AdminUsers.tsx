import { useState, useEffect } from 'react'
import { supabase } from '@/lib/auth'
import { Users, Crown, Shield, User, Trash2, Search, RefreshCw, ChevronDown } from 'lucide-react'
import { API_ROOT } from '@/lib/api'

const ROLE_CONFIG = {
    admin: { label: 'Admin', color: 'text-red-400 bg-red-500/15 border-red-500/30', icon: Shield },
    premium: { label: 'Premium', color: 'text-amber-400 bg-amber-500/15 border-amber-500/30', icon: Crown },
    free: { label: 'Free', color: 'text-slate-400 bg-slate-500/15 border-slate-500/30', icon: User },
}

async function getAuthHeaders(): Promise<Record<string, string>> {
    const { data } = await supabase.auth.getSession()
    const token = data?.session?.access_token
    return {
        'Content-Type': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    }
}

export default function AdminUsers() {
    const [users, setUsers] = useState<any[]>([])
    const [loading, setLoading] = useState(true)
    const [search, setSearch] = useState('')
    const [roleFilter, setRoleFilter] = useState('all')
    const [editingId, setEditingId] = useState<string | null>(null)

    const fetchUsers = async () => {
        setLoading(true)
        try {
            const headers = await getAuthHeaders()
            const res = await fetch(`${API_ROOT}/api/trigger/admin/users`, { headers })
            if (!res.ok) throw new Error(`HTTP ${res.status}`)
            const data = await res.json()
            setUsers(data.users || [])
        } catch (e) {
            console.error('Error fetching users:', e)
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => { fetchUsers() }, [])

    const updateRole = async (userId: string, newRole: string) => {
        if (!window.confirm(`Changer le rôle en "${newRole}" ?`)) return
        try {
            const headers = await getAuthHeaders()
            const res = await fetch(`${API_ROOT}/api/trigger/admin/users/${userId}/role`, {
                method: 'PUT',
                headers,
                body: JSON.stringify({ role: newRole }),
            })
            if (!res.ok) throw new Error(`HTTP ${res.status}`)
            setUsers(prev => prev.map(u => u.id === userId ? { ...u, role: newRole } : u))
            setEditingId(null)
        } catch (e: any) {
            alert('Erreur: ' + e.message)
        }
    }

    const deleteUser = async (userId: string, email: string) => {
        if (!window.confirm(`⚠️ Supprimer définitivement ${email || userId} ?\n\nCette action supprime le compte de Supabase Auth ET le profil. C'est irréversible.`)) return
        try {
            const headers = await getAuthHeaders()
            const res = await fetch(`${API_ROOT}/api/trigger/admin/users/${userId}`, {
                method: 'DELETE',
                headers,
            })
            if (!res.ok) throw new Error(`HTTP ${res.status}`)
            setUsers(prev => prev.filter(u => u.id !== userId))
        } catch (e: any) {
            alert('Erreur: ' + e.message)
        }
    }

    const filtered = users.filter(u => {
        if (roleFilter !== 'all' && u.role !== roleFilter) return false
        if (search) {
            const q = search.toLowerCase()
            return (u.email || '').toLowerCase().includes(q) || (u.id || '').toLowerCase().includes(q)
        }
        return true
    })

    const stats = {
        total: users.length,
        admin: users.filter(u => u.role === 'admin').length,
        premium: users.filter(u => u.role === 'premium').length,
        free: users.filter(u => u.role === 'free').length,
    }

    return (
        <div className="glass rounded-2xl border border-white/5 p-6 shadow-xl">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
                <h2 className="text-lg font-semibold flex items-center gap-2">
                    <Users className="w-5 h-5 text-violet-400" />
                    Gestion des Utilisateurs
                </h2>
                <button onClick={fetchUsers} disabled={loading}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 transition-colors">
                    <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
                    Rafraîchir
                </button>
            </div>

            {/* Stats Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
                {[
                    { label: 'Total', value: stats.total, color: 'text-foreground', bg: 'bg-white/5 border-white/10' },
                    { label: 'Admin', value: stats.admin, color: 'text-red-400', bg: 'bg-red-500/5 border-red-500/20' },
                    { label: 'Premium', value: stats.premium, color: 'text-amber-400', bg: 'bg-amber-500/5 border-amber-500/20' },
                    { label: 'Free', value: stats.free, color: 'text-slate-400', bg: 'bg-slate-500/5 border-slate-500/20' },
                ].map(s => (
                    <div key={s.label} className={`rounded-xl border p-3 text-center ${s.bg}`}>
                        <div className={`text-2xl font-bold ${s.color}`}>{s.value}</div>
                        <div className="text-[10px] text-muted-foreground font-medium uppercase tracking-wider mt-0.5">{s.label}</div>
                    </div>
                ))}
            </div>

            {/* Filters */}
            <div className="flex flex-col sm:flex-row gap-3 mb-4">
                <div className="relative flex-1">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
                    <input type="text" placeholder="Rechercher par email..." value={search}
                        onChange={e => setSearch(e.target.value)}
                        className="w-full pl-9 pr-3 py-2 text-sm bg-white/5 border border-white/10 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500/50 placeholder:text-muted-foreground/50" />
                </div>
                <select value={roleFilter} onChange={e => setRoleFilter(e.target.value)}
                    className="px-3 py-2 text-sm bg-white/5 border border-white/10 rounded-lg focus:outline-none cursor-pointer">
                    <option value="all">Tous les rôles</option>
                    <option value="admin">Admin</option>
                    <option value="premium">Premium</option>
                    <option value="free">Free</option>
                </select>
            </div>

            {/* User Table */}
            <div className="overflow-x-auto rounded-xl border border-white/10">
                <table className="w-full text-sm">
                    <thead>
                        <tr className="border-b border-white/10 bg-white/5">
                            <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Email</th>
                            <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Rôle</th>
                            <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider hidden md:table-cell">Abonnement</th>
                            <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider hidden lg:table-cell">Inscrit le</th>
                            <th className="text-right px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Actions</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5">
                        {loading ? (
                            Array.from({ length: 5 }).map((_, i) => (
                                <tr key={i}><td colSpan={5} className="px-4 py-3">
                                    <div className="h-4 bg-white/5 rounded animate-pulse" />
                                </td></tr>
                            ))
                        ) : filtered.length === 0 ? (
                            <tr><td colSpan={5} className="px-4 py-8 text-center text-muted-foreground text-sm">Aucun utilisateur trouvé</td></tr>
                        ) : filtered.map(user => {
                            const rc = (ROLE_CONFIG as any)[user.role] || ROLE_CONFIG.free
                            const RoleIcon = rc.icon
                            return (
                                <tr key={user.id} className="hover:bg-white/5 transition-colors">
                                    <td className="px-4 py-3">
                                        <div className="font-medium text-sm truncate max-w-[200px]">{user.email || '—'}</div>
                                        <div className="text-[10px] text-muted-foreground/60 font-mono truncate max-w-[200px]">{user.id?.slice(0, 8)}...</div>
                                    </td>
                                    <td className="px-4 py-3">
                                        {editingId === user.id ? (
                                            <div className="flex items-center gap-1">
                                                {['free', 'premium', 'admin'].map(r => (
                                                    <button key={r} onClick={() => updateRole(user.id, r)}
                                                        className={`px-2 py-1 rounded text-[10px] font-bold uppercase border transition-all hover:scale-105 ${r === user.role ? 'ring-2 ring-violet-500' : ''} ${(ROLE_CONFIG as any)[r]?.color}`}>
                                                        {r}
                                                    </button>
                                                ))}
                                                <button onClick={() => setEditingId(null)} className="text-[10px] text-muted-foreground ml-1 hover:text-foreground">✕</button>
                                            </div>
                                        ) : (
                                            <button onClick={() => setEditingId(user.id)}
                                                className={`inline-flex items-center gap-1 px-2 py-1 rounded-md text-[11px] font-semibold border cursor-pointer hover:opacity-80 transition-opacity ${rc.color}`}>
                                                <RoleIcon className="w-3 h-3" />
                                                {rc.label}
                                                <ChevronDown className="w-2.5 h-2.5 opacity-50" />
                                            </button>
                                        )}
                                    </td>
                                    <td className="px-4 py-3 hidden md:table-cell">
                                        <span className={`text-xs ${user.subscription_status === 'active' ? 'text-emerald-400' : 'text-muted-foreground/60'}`}>
                                            {user.subscription_status || '—'}
                                        </span>
                                    </td>
                                    <td className="px-4 py-3 hidden lg:table-cell">
                                        <span className="text-xs text-muted-foreground">
                                            {user.created_at ? new Date(user.created_at).toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: 'numeric' }) : '—'}
                                        </span>
                                    </td>
                                    <td className="px-4 py-3 text-right">
                                        <button onClick={() => deleteUser(user.id, user.email)}
                                            className="p-1.5 rounded-lg text-red-400/50 hover:text-red-400 hover:bg-red-500/10 transition-all"
                                            title="Supprimer le compte">
                                            <Trash2 className="w-3.5 h-3.5" />
                                        </button>
                                    </td>
                                </tr>
                            )
                        })}
                    </tbody>
                </table>
            </div>
        </div>
    )
}
