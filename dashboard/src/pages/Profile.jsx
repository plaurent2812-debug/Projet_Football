import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { useAuth } from "@/lib/auth"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { User, Mail, Shield, Calendar, LogOut, CreditCard } from "lucide-react"
import { format } from "date-fns"
import { fr } from "date-fns/locale"

export default function ProfilePage() {
    const { user, profile, role, signOut } = useAuth()
    const navigate = useNavigate()
    const [loading, setLoading] = useState(false)

    const handleSignOut = async () => {
        setLoading(true)
        await signOut()
        navigate("/login")
    }

    if (!user) {
        navigate("/login")
        return null
    }

    const joinDate = user.created_at ? new Date(user.created_at) : new Date()
    const isPremium = role === 'premium' || role === 'admin'

    return (
        <div className="max-w-2xl mx-auto py-8 animate-fade-in-up space-y-6">
            <div className="flex items-center justify-between">
                <h1 className="text-2xl font-black tracking-tight">Mon Profil</h1>
                <Button variant="ghost" className="text-destructive hover:text-destructive/90 hover:bg-destructive/10" onClick={handleSignOut} disabled={loading}>
                    <LogOut className="w-4 h-4 mr-2" />
                    Se déconnecter
                </Button>
            </div>

            {/* User Info Card */}
            <Card className="border-border/50 overflow-hidden">
                <div className="h-24 bg-gradient-to-r from-primary/20 to-blue-600/20" />
                <CardContent className="relative pt-0 pb-6">
                    <div className="flex flex-col sm:flex-row items-center sm:items-end gap-4 -mt-12 mb-4 px-2">
                        <Avatar className="w-24 h-24 border-4 border-card shadow-lg">
                            <AvatarImage src={user.user_metadata?.avatar_url} />
                            <AvatarFallback className="bg-primary text-primary-foreground text-2xl font-bold">
                                {user.email?.charAt(0).toUpperCase()}
                            </AvatarFallback>
                        </Avatar>
                        <div className="flex-1 text-center sm:text-left space-y-1 pb-2">
                            <h2 className="text-xl font-bold text-foreground">{user.email?.split('@')[0]}</h2>
                            <div className="flex flex-wrap items-center justify-center sm:justify-start gap-2">
                                <Badge variant={isPremium ? "default" : "secondary"} className="uppercase text-[10px] tracking-wider">
                                    {isPremium ? "Membre Premium" : "Membre Gratuit"}
                                </Badge>
                                {role === 'admin' && (
                                    <Badge variant="destructive" className="uppercase text-[10px] tracking-wider flex items-center gap-1">
                                        <Shield className="w-3 h-3" /> Admin
                                    </Badge>
                                )}
                            </div>
                        </div>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 px-2 mt-6">
                        <div className="flex items-center gap-3 p-3 rounded-lg bg-accent/30 border border-border/30">
                            <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                                <Mail className="w-4 h-4 text-primary" />
                            </div>
                            <div className="flex-1 min-w-0">
                                <p className="text-xs text-muted-foreground">Email</p>
                                <p className="text-sm font-medium truncate">{user.email}</p>
                            </div>
                        </div>
                        <div className="flex items-center gap-3 p-3 rounded-lg bg-accent/30 border border-border/30">
                            <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                                <Calendar className="w-4 h-4 text-primary" />
                            </div>
                            <div className="flex-1 min-w-0">
                                <p className="text-xs text-muted-foreground">Membre depuis</p>
                                <p className="text-sm font-medium capitalize">
                                    {format(joinDate, "MMMM yyyy", { locale: fr })}
                                </p>
                            </div>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Subscription Status */}
            <Card className="border-border/50">
                <CardHeader>
                    <CardTitle className="text-lg flex items-center gap-2">
                        <CreditCard className="w-5 h-5 text-primary" />
                        Abonnement
                    </CardTitle>
                    <CardDescription>Gérez votre abonnement et vos factures</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    {isPremium ? (
                        <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-lg p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
                            <div>
                                <p className="font-bold text-emerald-600 dark:text-emerald-400 mb-1">Abonnement Actif</p>
                                <p className="text-sm text-muted-foreground">
                                    Vous profitez de toutes les fonctionnalités ProbaLab.
                                </p>
                            </div>
                            <Button variant="outline" className="shrink-0" onClick={() => window.open(import.meta.env.VITE_STRIPE_CUSTOMER_PORTAL, '_blank')}>
                                Gérer mon abonnement
                            </Button>
                        </div>
                    ) : (
                        <div className="bg-accent/30 border border-border/30 rounded-lg p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
                            <div>
                                <p className="font-bold text-foreground mb-1">Plan Gratuit</p>
                                <p className="text-sm text-muted-foreground">
                                    Passez Premium pour accéder aux probas buteurs, scores exacts et analyses IA.
                                </p>
                            </div>
                            <Button className="shrink-0" onClick={() => navigate("/premium")}>
                                Passer Premium
                            </Button>
                        </div>
                    )}
                </CardContent>
            </Card>
        </div>
    )
}
