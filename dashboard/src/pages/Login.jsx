import { useState } from 'react'
import { useAuth } from '@/lib/auth'

export default function LoginPage() {
    const { signIn, signUp, signInWithOAuth } = useAuth()
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
            <form onSubmit={handleLogin} className="flex flex-col gap-2 w-full max-w-xs">
                <input
                    className="border p-2 rounded bg-background text-foreground"
                    type="email"
                    placeholder="Votre email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                />
                <button
                    disabled={loading}
                    className="bg-primary text-primary-foreground p-2 rounded disabled:opacity-50 font-medium"
                >
                    {loading ? 'Envoi...' : 'Envoyer Magic Link'}
                </button>
            </form>

            <div className="flex flex-col gap-2 mt-4 w-full max-w-xs">
                <div className="relative">
                    <div className="absolute inset-0 flex items-center">
                        <span className="w-full border-t" />
                    </div>
                    <div className="relative flex justify-center text-xs uppercase">
                        <span className="bg-background px-2 text-muted-foreground">Ou continuer avec</span>
                    </div>
                </div>

                <button
                    onClick={() => signInWithOAuth('google')}
                    className="flex items-center justify-center gap-2 border p-2 rounded hover:bg-accent transition-colors"
                >
                    <svg className="w-5 h-5" viewBox="0 0 24 24">
                        <path
                            d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                            fill="#4285F4"
                        />
                        <path
                            d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                            fill="#34A853"
                        />
                        <path
                            d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                            fill="#FBBC05"
                        />
                        <path
                            d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                            fill="#EA4335"
                        />
                    </svg>
                    Google
                </button>

                {/* Apple requires paid developer account usually, but we can add the button */}
                <button
                    onClick={() => signInWithOAuth('apple')}
                    className="flex items-center justify-center gap-2 border p-2 rounded hover:bg-accent transition-colors bg-black text-white"
                >
                    <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M17.05 20.28c-.98.95-2.05.8-3.08.35-1.09-.46-2.09-.48-3.24 0-1.44.62-2.2.44-3.06-.35C2.79 15.25 3.51 7.59 9.05 7.31c1.35.07 2.29.74 3.08.74 1.18 0 2.24-.93 3.99-.71 1.35.2 2.53 1.1 3.24 2.15-2.91 1.76-2.43 6.09.46 7.27-.67 1.76-1.63 3.19-2.77 4.52zM12.03 7.25c-.15-2.23 1.66-4.07 3.74-4.25.29 2.58-2.34 4.5-3.74 4.25z" />
                    </svg>
                    Apple
                </button>
            </div>
        </div>
    )
}
