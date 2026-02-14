import { useState, createContext, useContext, useEffect } from 'react'
import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseKey = import.meta.env.VITE_SUPABASE_ANON_KEY

export const supabase = createClient(supabaseUrl, supabaseKey)

const AuthContext = createContext(null)

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null)
    const [profile, setProfile] = useState(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        // 1. Get initial session
        supabase.auth.getSession().then(({ data: { session } }) => {
            setUser(session?.user ?? null)
            if (session?.user) fetchProfile(session.user.id)
            else setLoading(false)
        })

        // 2. Listen for changes
        const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
            setUser(session?.user ?? null)
            if (session?.user) fetchProfile(session.user.id)
            else {
                setProfile(null)
                setLoading(false)
            }
        })

        return () => subscription.unsubscribe()
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
