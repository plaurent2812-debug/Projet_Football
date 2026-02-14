import { useState } from 'react'
import { useAuth } from '@/lib/auth'

export default function LoginPage() {
    const { signIn, signUp } = useAuth()
    const [loading, setLoading] = useState(false)
    const [email, setEmail] = useState('')
    const [msg, setMsg] = useState('')

    const handleLogin = async (e) => {
        e.preventDefault()
        setLoading(true)
        try {
            await signIn(email, 'passwordless-link') // Or password
            setMsg('Check your email for the login link!')
        } catch (error) {
            setMsg(error.message)
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="flex flex-col items-center justify-center min-h-screen">
            <h1 className="text-3xl font-bold mb-4">Login</h1>
            <p className="mb-4">{msg}</p>
            <form onSubmit={handleLogin} className="flex flex-col gap-2">
                <input
                    className="border p-2 rounded"
                    type="email"
                    placeholder="Your email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                />
                <button
                    disabled={loading}
                    className="bg-primary text-white p-2 rounded disabled:opacity-50"
                >
                    {loading ? 'Sending link...' : 'Send Magic Link'}
                </button>
            </form>
        </div>
    )
}
