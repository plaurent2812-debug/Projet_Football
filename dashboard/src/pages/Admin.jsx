import { useState, useEffect } from 'react'
import { Protected } from '@/lib/auth'
import { triggerPipeline, fetchPipelineStatus } from '@/lib/api'
import { Shield, Play, Loader2, CheckCircle, XCircle } from 'lucide-react'

function AdminDashboard() {
    const [status, setStatus] = useState(null)
    const [loading, setLoading] = useState(false)
    const [msg, setMsg] = useState('')

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
        const interval = setInterval(refreshStatus, 5000)
        return () => clearInterval(interval)
    }, [])

    const handleRun = async (mode) => {
        setLoading(true)
        setMsg('')
        try {
            await triggerPipeline(mode)
            setMsg(`Pipeline '${mode}' started!`)
            await refreshStatus()
        } catch (err) {
            setMsg(`Error: ${err.message}`)
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="space-y-6">
            <div className="flex items-center gap-3">
                <div className="p-3 bg-red-500/10 rounded-xl">
                    <Shield className="w-8 h-8 text-red-500" />
                </div>
                <div>
                    <h1 className="text-3xl font-bold">Admin Dashboard</h1>
                    <p className="text-muted-foreground">Manage data pipeline and system status</p>
                </div>
            </div>

            <div className="grid md:grid-cols-2 gap-6">
                {/* Pipeline Controls */}
                <div className="card p-6 space-y-4">
                    <h2 className="text-xl font-semibold flex items-center gap-2">
                        <Play className="w-5 h-5" /> Pipeline Controls
                    </h2>

                    <div className="flex flex-col gap-3">
                        <button
                            onClick={() => handleRun('full')}
                            disabled={loading || status?.status === 'running'}
                            className="btn btn-primary w-full justify-between"
                        >
                            <span>Run Full Pipeline</span>
                            <span className="text-xs opacity-70">Data + Analysis</span>
                        </button>

                        <div className="grid grid-cols-2 gap-3">
                            <button
                                onClick={() => handleRun('data')}
                                disabled={loading || status?.status === 'running'}
                                className="btn btn-outline"
                            >
                                Fetch Data Only
                            </button>
                            <button
                                onClick={() => handleRun('analyze')}
                                disabled={loading || status?.status === 'running'}
                                className="btn btn-outline"
                            >
                                Run Analysis Only
                            </button>
                        </div>
                    </div>
                    {msg && <p className="text-sm text-blue-500 animate-pulse">{msg}</p>}
                </div>

                {/* Pipeline Status */}
                <div className="card p-6 space-y-4">
                    <h2 className="text-xl font-semibold flex items-center gap-2">
                        <Loader2 className={`w-5 h-5 ${status?.status === 'running' ? 'animate-spin' : ''}`} />
                        Current Status
                    </h2>

                    <div className="space-y-4">
                        <div className="flex justify-between items-center p-3 bg-accent/50 rounded-lg">
                            <span className="text-sm font-medium">State</span>
                            <span className={`badge ${status?.status === 'running' ? 'bg-blue-500/20 text-blue-500' :
                                    status?.status === 'done' ? 'bg-green-500/20 text-green-500' :
                                        status?.status === 'error' ? 'bg-red-500/20 text-red-500' :
                                            'bg-gray-500/20 text-gray-500'
                                }`}>
                                {status?.status?.toUpperCase() || 'UNKNOWN'}
                            </span>
                        </div>

                        {status?.started_at && (
                            <div className="text-sm space-y-1">
                                <p className="flex justify-between">
                                    <span className="text-muted-foreground">Started:</span>
                                    <span>{new Date(status.started_at).toLocaleString()}</span>
                                </p>
                                {status.finished_at && (
                                    <p className="flex justify-between">
                                        <span className="text-muted-foreground">Finished:</span>
                                        <span>{new Date(status.finished_at).toLocaleString()}</span>
                                    </p>
                                )}
                            </div>
                        )}

                        {status?.logs && (
                            <div className="mt-4">
                                <p className="text-xs font-medium mb-1 text-muted-foreground">Last Logs:</p>
                                <pre className="bg-black/50 p-3 rounded-lg text-xs font-mono h-32 overflow-y-auto text-green-400">
                                    {status.logs}
                                </pre>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    )
}

export default function AdminPage() {
    return (
        <Protected requiredRole="admin" fallback={<div className="p-10 text-center">🚫 Access Denied</div>}>
            <AdminDashboard />
        </Protected>
    )
}
