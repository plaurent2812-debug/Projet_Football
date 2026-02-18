import { useState, createContext, useContext, useEffect } from 'react'
import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || "https://yskpqdnidxojoclmqcxn.supabase.co"
const supabaseKey = import.meta.env.VITE_SUPABASE_ANON_KEY || "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inlza3BxZG5pZHhvam9jbG1xY3huIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzA2MTk4MTEsImV4cCI6MjA4NjE5NTgxMX0.8n3OW6Gq4DY9qd5FQURVbtrbwwEo3BhxRMNLumu5Dsk"

// Fail gracefully if env vars are missing to avoid white page
let supabase
try {
    if (!supabaseUrl || !supabaseKey) {
        console.error("CRITICAL: Missing Supabase env vars (VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY)")
        // Create a dummy client that warns on usage
        supabase = {
            auth: {
                getSession: () => Promise.resolve({ data: { session: null }, error: new Error("Missing Supabase config") }),
                onAuthStateChange: () => ({ data: { subscription: { unsubscribe: () => { } } } }),
                signInWithPassword: () => Promise.resolve({ error: new Error("Missing Supabase config") }),
                signInWithOtp: () => Promise.resolve({ error: new Error("Missing Supabase config") }),
                signUp: () => Promise.resolve({ error: new Error("Missing Supabase config") }),
                signOut: () => Promise.resolve({ error: null }),
                signInWithOAuth: () => Promise.resolve({ error: new Error("Missing Supabase config") }),
                resetPasswordForEmail: () => Promise.resolve({ error: new Error("Missing Supabase config") }),
            },
            from: () => ({
                select: () => ({ eq: () => ({ single: () => Promise.resolve({ data: null, error: new Error("Missing Supabase config") }) }) })
            })
        }
    } else {
        supabase = createClient(supabaseUrl, supabaseKey)
    }
} catch (e) {
    console.error("Supabase init error:", e)
}

const AuthContext = createContext(null)

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null)
    const [profile, setProfile] = useState(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        console.log("AuthProvider mounted")

        // Safety timeout in case Supabase hangs
        const timer = setTimeout(() => {
            console.warn("AuthProvider timeout - forcing loading false")
            setLoading(false)
        }, 3000)

        // 1. Get initial session
        supabase.auth.getSession().then(({ data: { session } }) => {
            console.log("Session loaded:", session ? "User logged in" : "No user")
            clearTimeout(timer)
            setUser(session?.user ?? null)
            if (session?.user) fetchProfile(session.user.id)
            else setLoading(false)
        }).catch(err => {
            console.error("Session error:", err)
            clearTimeout(timer)
            setLoading(false)
        })

        // 2. Listen for changes
        const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
            console.log("Auth state change:", _event)
            setUser(session?.user ?? null)
            if (session?.user) fetchProfile(session.user.id)
            else {
                setProfile(null)
                setLoading(false)
            }
        })

        return () => {
            subscription.unsubscribe()
            clearTimeout(timer)
        }
    }, [])

    async function fetchProfile(userId) {
        try {
            const { data, error } = await supabase
                .from('profiles')
                .select('*')
                .eq('id', userId)
                .single()

            if (error) throw error
            setProfile(data)
        } catch (error) {
            console.error('Error fetching profile:', error)
            // Fallback for dev or missing profile
            setProfile({ role: 'free' })
        } finally {
            setLoading(false)
        }
    }

    const signIn = async (email, password) => {
        const { error } = await supabase.auth.signInWithPassword({ email, password })
        if (error) throw error
    }

    const signInWithOtp = async (email) => {
        const { error } = await supabase.auth.signInWithOtp({
            email,
            options: {
                emailRedirectTo: window.location.origin,
            },
        })
        if (error) throw error
    }

    const signUp = async (email, password) => {
        const { error } = await supabase.auth.signUp({ email, password })
        if (error) throw error
    }

    const signOut = async () => {
        await supabase.auth.signOut()
    }

    const signInWithOAuth = async (provider) => {
        const { error } = await supabase.auth.signInWithOAuth({
            provider: provider,
            options: {
                redirectTo: window.location.origin
            }
        })
        if (error) throw error
    }

    const resetPassword = async (email) => {
        const { error } = await supabase.auth.resetPasswordForEmail(email, {
            redirectTo: `${window.location.origin}/update-password`,
        })
        if (error) throw error
    }

    const role = profile?.role || 'anonymous'

    const value = {
        user,
        profile,
        loading,
        signIn,
        signInWithOtp,
        signUp,
        signOut,
        signInWithOAuth,
        resetPassword,
        role,
        isAnonymous: !user,
        isFree: role === 'free',
        isPremium: role === 'premium',
        isAdmin: role === 'admin',
        hasAccess: (requiredRole) => {
            if (!user) return requiredRole === 'anonymous'
            const levels = { anonymous: 0, free: 1, premium: 2, admin: 3 }
            return levels[role] >= levels[requiredRole]
        }
    }

    return (
        <AuthContext.Provider value={value}>
            {!loading && children}
        </AuthContext.Provider>
    )
}

export const useAuth = () => {
    const context = useContext(AuthContext)
    if (!context) {
        throw new Error("useAuth must be used within an AuthProvider")
    }
    return context
}

export const Protected = ({ children, requiredRole = 'free', fallback = null }) => {
    const { hasAccess, loading } = useAuth()
    if (loading) return null // Or a spinner
    return hasAccess(requiredRole) ? children : fallback
}

export { supabase }
