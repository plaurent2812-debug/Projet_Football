import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom"
import { useState } from "react"
import { BarChart3, Home, Zap, Trophy, ListChecks, Shield } from "lucide-react"
import { cn } from "@/lib/utils"
import HomePage from "@/pages/HomePage"
import DashboardPage from "@/pages/Dashboard"
import PerformancePage from "@/pages/Performance"
import MatchDetailPage from "@/pages/MatchDetail"
import AdminPage from "@/pages/Admin"
import TeamProfile from "@/pages/TeamProfile"
import LoginPage from "@/pages/Login"
import PremiumPage from "@/pages/Premium"
import ThemeToggle from "@/components/ThemeToggle"
import { AuthProvider, useAuth } from "@/lib/auth"
import "./App.css"

function NavItem({ to, icon: Icon, label }) {
  return (
    <NavLink
      to={to}
      end
      className={({ isActive }) =>
        cn(
          "flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-medium transition-all duration-200",
          isActive
            ? "bg-primary/15 text-primary"
            : "text-muted-foreground hover:text-foreground hover:bg-accent/50"
        )
      }
    >
      <Icon className="w-4 h-4" />
      <span className="hidden sm:inline">{label}</span>
    </NavLink>
  )
}

function AdminLink() {
  const { hasAccess } = useAuth()
  if (!hasAccess('admin')) return null
  return <NavItem to="/admin" icon={Shield} label="Admin" />
}

function PremiumLink() {
  const { hasAccess } = useAuth()
  // Hide if already premium/admin
  if (hasAccess('premium')) return null

  return (
    <NavLink
      to="/abonnement"
      className="flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-medium text-amber-500 hover:bg-amber-500/10 transition-colors"
    >
      <Trophy className="w-4 h-4" />
      <span className="hidden sm:inline">Premium</span>
    </NavLink>
  )
}

function AuthButton() {
  const { user, signOut } = useAuth()

  if (user) {
    return (
      <button
        onClick={signOut}
        className="flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-medium text-red-500 hover:bg-red-500/10 transition-colors ml-2"
      >
        <span className="hidden sm:inline">Déconnexion</span>
      </button>
    )
  }

  return (
    <NavLink
      to="/login"
      className="flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-medium bg-primary text-primary-foreground hover:bg-primary/90 transition-colors ml-2 shadow-sm"
    >
      <span>Connexion</span>
    </NavLink>
  )
}

import { Sidebar } from "@/components/Sidebar"
import { SportsNav } from "@/components/SportsNav"

// ... existing imports ...

function App() {
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10))
  const [activeSport, setActiveSport] = useState("football")

  return (
    <AuthProvider>
      <BrowserRouter>
        <div className="min-h-screen bg-background text-foreground transition-colors duration-300 font-sans antialiased selection:bg-primary/20">

          {/* Header (Top Bar) */}
          <header className="sticky top-0 z-50 border-b border-border/40 glass backdrop-blur-md bg-background/80 supports-[backdrop-filter]:bg-background/60">
            <div className="max-w-[1400px] mx-auto px-4 sm:px-6">
              <div className="flex items-center justify-between h-14">
                {/* Logo */}
                <NavLink to="/" className="flex items-center gap-2.5 group">
                  <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-600 to-violet-600 flex items-center justify-center shadow-lg shadow-indigo-500/20 group-hover:shadow-indigo-500/40 transition-all duration-300">
                    <Zap className="w-5 h-5 text-white" />
                  </div>
                  <span className="text-lg font-black tracking-tight flex items-center gap-0.5">
                    Proba<span className="text-primary">Lab</span>
                  </span>
                </NavLink>

                {/* Right Actions (Theme, Auth) */}
                <div className="flex items-center gap-2">
                  <div className="hidden md:flex items-center gap-1">
                    <PremiumLink />
                    <AdminLink />
                    <div className="mx-2 w-px h-5 bg-border/50" />
                  </div>
                  <ThemeToggle />
                  <AuthButton />

                  {/* Mobile Menu Button (Placeholder for now) */}
                  <button className="md:hidden p-2 text-muted-foreground hover:bg-accent rounded-md">
                    <ListChecks className="w-5 h-5" />
                  </button>
                </div>
              </div>
            </div>
          </header>

          {/* Main Layout Grid */}
          <div className="max-w-[1400px] mx-auto px-4 sm:px-6 py-6 transition-all duration-500 ease-in-out">
            <div className="grid grid-cols-1 md:grid-cols-[240px_1fr] gap-8 items-start">

              {/* Left Sidebar (Hidden on mobile for now) */}
              <Sidebar className="hidden md:block sticky top-24" />

              {/* Main Content Area */}
              <main className="min-w-0">
                {/* Sports Navigation Tabs */}
                <SportsNav activeSport={activeSport} onSportChange={setActiveSport} />

                <div className="animate-in fade-in slide-in-from-bottom-2 duration-500">
                  <Routes>
                    <Route path="/" element={<HomePage />} />
                    <Route
                      path="/matchs"
                      element={
                        <DashboardPage
                          date={date}
                          setDate={setDate}
                        />
                      }
                    />
                    {/* Redirect root to /matchs or keep HomePage as landing */}
                    {/* If we want Flashscore style, root usually shows matches directly */}

                    <Route path="/performance" element={<PerformancePage />} />
                    <Route path="/abonnement" element={<PremiumPage />} />
                    <Route path="/match/:id" element={<MatchDetailPage />} />
                    <Route path="/equipe/:name" element={<TeamProfile />} />
                    <Route path="/admin" element={<AdminPage />} />
                    <Route path="/login" element={<LoginPage />} />
                  </Routes>
                </div>
              </main>

            </div>
          </div>

        </div>
      </BrowserRouter>
    </AuthProvider>
  )
}

export default App
