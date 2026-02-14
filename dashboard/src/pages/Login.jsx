import { useState } from 'react'
import { useAuth } from '@/lib/auth'
import { Zap, Mail, ArrowRight, Loader2 } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

export default function LoginPage() {
    const { signInWithOtp } = useAuth()
    const [loading, setLoading] = useState(false)
    const [email, setEmail] = useState('')
    const [msg, setMsg] = useState('')
    const navigate = useNavigate()

    const handleLogin = async (e) => {
        e.preventDefault()
        setLoading(true)
        setMsg('')

        try {
            await signInWithOtp(email)
            setMsg('Vérifiez votre boîte mail pour le lien magique ! 📧')
        } catch (error) {
            console.error(error)
            setMsg(error.message || "Une erreur est survenue")
        } finally {
            setLoading(false)
        }
    }

    const handleSocialLogin = (provider) => {
        alert("Connexion " + provider + " bientôt disponible ! 🚧")
    }

    return (
        <div className="min-h-screen flex items-center justify-center relative overflow-hidden bg-background">
            {/* Background Effects */}
            <div className="absolute inset-0 w-full h-full bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-indigo-900/20 via-background to-background pointer-events-none" />
            <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[1000px] h-[500px] bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />

            {/* Login Card */}
            <div className="w-full max-w-md mx-4 relative z-10">
                <div className="glass border border-white/10 rounded-2xl p-8 shadow-2xl backdrop-blur-xl">
                    {/* Header */}
                    <div className="text-center mb-8">
                        <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center mx-auto mb-4 shadow-lg shadow-indigo-500/25">
                            <Zap className="w-6 h-6 text-white" />
                        </div>
                        <h1 className="text-2xl font-bold tracking-tight mb-2">Bon retour</h1>
                        <p className="text-muted-foreground text-sm">
                            Connectez-vous pour accéder à vos prédictions
                        </p>
                    </div>

                    {/* Social Login */}
                    <div className="grid grid-cols-2 gap-3 mb-6">
                        <button
                            onClick={() => handleSocialLogin('Google')}
                            className="flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl border border-border/50 bg-background/50 hover:bg-accent hover:text-accent-foreground transition-all duration-200 text-sm font-medium group"
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
                        <button
                            onClick={() => handleSocialLogin('Apple')}
                            className="flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl border border-border/50 bg-background/50 hover:bg-accent hover:text-accent-foreground transition-all duration-200 text-sm font-medium"
                        >
                            <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
                                <path d="M17.05 20.28c-.98.95-2.05.8-3.08.35-1.09-.46-2.09-.48-3.24 0-1.44.62-2.2.44-3.06-.35C2.79 15.25 3.51 7.59 9.05 7.31c1.35.07 2.29.74 3.08.74 1.18 0 2.24-.93 3.99-.71 1.35.2 2.53 1.1 3.24 2.15-2.91 1.76-2.43 6.09.46 7.27-.67 1.76-1.63 3.19-2.77 4.52zM12.03 7.25c-.15-2.23 1.66-4.07 3.74-4.25.29 2.58-2.34 4.5-3.74 4.25z" />
                            </svg>
                            Apple
                        </button>
                    </div>

                    <div className="relative mb-6">
                        <div className="absolute inset-0 flex items-center">
                            <span className="w-full border-t border-border/50" />
                        </div>
                        <div className="relative flex justify-center text-xs uppercase">
                            <span className="bg-background px-2 text-muted-foreground font-medium">
                                Ou par email
                            </span>
                        </div>
                    </div>

                    {/* Email Form */}
                    <form onSubmit={handleLogin} className="space-y-4">
                        <div className="space-y-2">
                            <div className="relative group">
                                <Mail className="absolute left-3 top-3 h-4 w-4 text-muted-foreground group-focus-within:text-primary transition-colors" />
                                <input
                                    className="flex h-10 w-full rounded-xl border border-input bg-background/50 px-3 py-2 pl-9 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 transition-all duration-200"
                                    type="email"
                                    placeholder="nom@exemple.com"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    required
                                />
                            </div>
                        </div>

                        {msg && (
                            <div className={`p-3 rounded-lg text-sm flex items-center gap-2 ${msg.includes('erreur') ? 'bg-destructive/10 text-destructive' : 'bg-primary/10 text-primary'}`}>
                                {msg.includes('erreur') ? null : <span className="text-lg">📧</span>}
                                {msg}
                            </div>
                        )}

                        <button
                            disabled={loading || !email}
                            className="w-full inline-flex items-center justify-center rounded-xl text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 py-2 group shadow-lg shadow-primary/20 hover:shadow-primary/40"
                        >
                            {loading ? (
                                <>
                                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                    Envoi en cours...
                                </>
                            ) : (
                                <>
                                    Rejoindre ProbaLab
                                    <ArrowRight className="ml-2 h-4 w-4 group-hover:translate-x-1 transition-transform" />
                                </>
                            )}
                        </button>
                    </form>

                    <p className="mt-6 text-center text-xs text-muted-foreground">
                        En continuant, vous acceptez nos{' '}
                        <a href="#" className="underline underline-offset-4 hover:text-primary">
                            Conditions d'utilisation
                        </a>{' '}
                        et notre{' '}
                        <a href="#" className="underline underline-offset-4 hover:text-primary">
                            Politique de confidentialité
                        </a>
                        .
                    </p>
                </div>
            </div>
        </div>
    )
}
