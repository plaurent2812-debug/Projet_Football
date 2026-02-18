import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { Zap, Eye, EyeOff, Mail, Lock, ArrowRight, CheckCircle } from "lucide-react"
import { useAuth } from "@/lib/auth"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"

const API_BASE = import.meta.env.VITE_API_URL || ""

function InputField({ label, type = "text", value, onChange, placeholder, icon: Icon }) {
    const [show, setShow] = useState(false)
    const isPassword = type === "password"
    return (
        <div className="space-y-1.5">
            <label className="text-sm font-medium text-foreground">{label}</label>
            <div className="relative">
                {Icon && <Icon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />}
                <input
                    type={isPassword && show ? "text" : type}
                    value={value}
                    onChange={e => onChange(e.target.value)}
                    placeholder={placeholder}
                    className="w-full h-10 rounded-lg border border-border bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-colors"
                    style={{ paddingLeft: Icon ? '2.25rem' : '0.75rem', paddingRight: isPassword ? '2.5rem' : '0.75rem' }}
                />
                {isPassword && (
                    <button
                        type="button"
                        onClick={() => setShow(s => !s)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                    >
                        {show ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                )}
            </div>
        </div>
    )
}

function LoginForm() {
    const { signIn } = useAuth()
    const navigate = useNavigate()
    const [email, setEmail] = useState("")
    const [password, setPassword] = useState("")
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState("")
    const [resetSent, setResetSent] = useState(false)
    const { resetPassword } = useAuth()

    const handleLogin = async (e) => {
        e.preventDefault()
        setError("")
        setLoading(true)
        try {
            await signIn(email, password)
            navigate("/")
        } catch (err) {
            setError(err.message || "Identifiants incorrects")
        } finally {
            setLoading(false)
        }
    }

    const handleReset = async () => {
        if (!email) { setError("Entrez votre email d'abord"); return }
        try {
            await resetPassword(email)
            setResetSent(true)
        } catch (err) {
            setError(err.message)
        }
    }

    return (
        <form onSubmit={handleLogin} className="space-y-4">
            <InputField label="Email" type="email" value={email} onChange={setEmail} placeholder="vous@exemple.fr" icon={Mail} />
            <InputField label="Mot de passe" type="password" value={password} onChange={setPassword} placeholder="••••••••" icon={Lock} />
            {error && <p className="text-sm text-red-500 bg-red-500/10 px-3 py-2 rounded-lg">{error}</p>}
            {resetSent && <p className="text-sm text-emerald-600 bg-emerald-500/10 px-3 py-2 rounded-lg">Email de réinitialisation envoyé !</p>}
            <Button type="submit" className="w-full" disabled={loading}>
                {loading ? "Connexion..." : "Se connecter"}
                <ArrowRight className="w-4 h-4 ml-1.5" />
            </Button>
            <button type="button" onClick={handleReset} className="w-full text-xs text-muted-foreground hover:text-primary transition-colors text-center">
                Mot de passe oublié ?
            </button>
        </form>
    )
}

function RegisterForm() {
    const { signUp } = useAuth()
    const navigate = useNavigate()
    const [email, setEmail] = useState("")
    const [password, setPassword] = useState("")
    const [confirm, setConfirm] = useState("")
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState("")
    const [success, setSuccess] = useState(false)

    const handleRegister = async (e) => {
        e.preventDefault()
        setError("")
        if (password !== confirm) { setError("Les mots de passe ne correspondent pas"); return }
        if (password.length < 6) { setError("Le mot de passe doit faire au moins 6 caractères"); return }
        setLoading(true)
        try {
            await signUp(email, password)
            // Send welcome email
            try {
                await fetch(`${API_BASE}/api/resend/welcome`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ email }),
                })
            } catch (_) { }
            setSuccess(true)
        } catch (err) {
            setError(err.message || "Erreur lors de l'inscription")
        } finally {
            setLoading(false)
        }
    }

    if (success) {
        return (
            <div className="text-center py-6 space-y-3">
                <CheckCircle className="w-12 h-12 text-emerald-500 mx-auto" />
                <h3 className="font-bold text-base">Compte créé !</h3>
                <p className="text-sm text-muted-foreground">
                    Vérifiez votre email pour confirmer votre compte. Un email de bienvenue vous a été envoyé.
                </p>
                <Button variant="outline" onClick={() => navigate("/")}>Retour à l'accueil</Button>
            </div>
        )
    }

    return (
        <form onSubmit={handleRegister} className="space-y-4">
            <InputField label="Email" type="email" value={email} onChange={setEmail} placeholder="vous@exemple.fr" icon={Mail} />
            <InputField label="Mot de passe" type="password" value={password} onChange={setPassword} placeholder="Min. 6 caractères" icon={Lock} />
            <InputField label="Confirmer le mot de passe" type="password" value={confirm} onChange={setConfirm} placeholder="••••••••" icon={Lock} />
            {error && <p className="text-sm text-red-500 bg-red-500/10 px-3 py-2 rounded-lg">{error}</p>}
            <Button type="submit" className="w-full" disabled={loading}>
                {loading ? "Création..." : "Créer mon compte"}
                <ArrowRight className="w-4 h-4 ml-1.5" />
            </Button>
            <p className="text-[11px] text-muted-foreground text-center">
                En créant un compte, vous acceptez nos CGU. ProbaLab ne constitue pas un conseil en paris sportifs.
            </p>
        </form>
    )
}

export default function LoginPage() {
    return (
        <div className="min-h-[70vh] flex items-center justify-center py-12 animate-fade-in-up">
            <div className="w-full max-w-md">
                {/* Logo */}
                <div className="text-center mb-8">
                    <div className="inline-flex items-center gap-2 mb-3">
                        <div className="w-10 h-10 rounded-xl bg-primary flex items-center justify-center shadow-lg shadow-primary/30">
                            <Zap className="w-5 h-5 text-primary-foreground" />
                        </div>
                        <span className="text-2xl font-black">Proba<span className="text-primary">Lab</span></span>
                    </div>
                    <p className="text-sm text-muted-foreground">Analyses sportives augmentées par l'IA</p>
                </div>

                <Card className="border-border/50 shadow-lg shadow-primary/5">
                    <CardContent className="p-6">
                        <Tabs defaultValue="login">
                            <TabsList className="grid grid-cols-2 mb-6">
                                <TabsTrigger value="login">Connexion</TabsTrigger>
                                <TabsTrigger value="register">Inscription</TabsTrigger>
                            </TabsList>
                            <TabsContent value="login"><LoginForm /></TabsContent>
                            <TabsContent value="register"><RegisterForm /></TabsContent>
                        </Tabs>
                    </CardContent>
                </Card>
            </div>
        </div>
    )
}
