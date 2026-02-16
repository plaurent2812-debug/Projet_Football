import { BrowserRouter, Routes, Route, NavLink, useNavigate } from "react-router-dom"
import { lazy, Suspense, useState } from "react"
import { BarChart3, Home, Zap, Trophy, ListChecks, Shield, Menu } from "lucide-react"
import { cn } from "@/lib/utils"
import ThemeToggle from "@/components/ThemeToggle"
import { AuthProvider, useAuth } from "@/lib/auth"
import { Sidebar } from "@/components/Sidebar"
import { SportsNav } from "@/components/SportsNav"
import { RightSidebar } from "@/components/RightSidebar"
import "./App.css"

const HomePage = lazy(() => import("@/pages/HomePage"))
const DashboardPage = lazy(() => import("@/pages/Dashboard"))
const PerformancePage = lazy(() => import("@/pages/Performance"))
const MatchDetailPage = lazy(() => import("@/pages/MatchDetail"))
const AdminPage = lazy(() => import("@/pages/Admin"))
const TeamProfile = lazy(() => import("@/pages/TeamProfile"))
const LoginPage = lazy(() => import("@/pages/Login"))
const PremiumPage = lazy(() => import("@/pages/Premium"))

function PageLoader() {
  return (
    <div className="flex items-center justify-center py-32">
      <div className="w-8 h-8 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
    </div>
  )
}

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

function AdminGuard({ children }) {
  const { hasAccess } = useAuth()
  const navigate = useNavigate()

  // Simple check, redirect to home if not admin
  if (!hasAccess('admin')) {
    // Return null or redirect
    return <div className="p-8 text-center text-muted-foreground">Accès non autorisé</div>
  }
  return children
}

function AuthButton() {
  // ... existing code ...
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

function App() {
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10))
  const [activeSport, setActiveSport] = useState("football")

  return (
    <AuthProvider>
      <BrowserRouter>
        <div className="min-h-screen bg-[#f3f4f6] text-foreground transition-colors duration-300 font-sans antialiased selection:bg-primary/20">

          {/* Header (Top Bar) */}
          <header className="sticky top-0 z-50 bg-[#374df5] border-b border-white/10 shadow-sm">
            <div className="max-w-[1400px] mx-auto px-4 sm:px-6">
              <div className="flex items-center justify-between h-14">
                {/* Logo */}
                <NavLink to="/" className="flex items-center gap-2.5 group">
                  <div className="p-1.5 bg-white/10 rounded-lg">
                    <Zap className="w-5 h-5 text-white" />
                  </div>
                  <span className="text-xl font-black tracking-tight text-white flex items-center gap-0.5">
                    Proba<span className="opacity-80 font-bold">Lab</span>
                  </span>
                </NavLink>

                {/* Right Actions (Theme, Auth) */}
                <div className="flex items-center gap-3 text-white">
                  <div className="hidden md:flex items-center gap-2">
                    {/* Placeholder Search */}
                    <div className="bg-white/10 rounded-full px-3 py-1.5 flex items-center gap-2 text-sm text-white/70 min-w-[200px]">
                      <ListChecks className="w-4 h-4" />
                      <span>Rechercher...</span>
                    </div>
                  </div>
                  <ThemeToggle className="text-white hover:bg-white/10" />
                  <AuthButton />
                  <button className="md:hidden p-2 hover:bg-white/10 rounded-md">
                    <Menu className="w-6 h-6" />
                  </button>
                </div>
              </div>
            </div>
            {/* Sports Nav attached to header */}
            <SportsNav activeSport={activeSport} onSportChange={setActiveSport} />
          </header>

          {/* Main Layout Grid */}
          <div className="max-w-[1400px] mx-auto px-4 sm:px-6 py-6 transition-all duration-500 ease-in-out">
            <div className="grid grid-cols-1 md:grid-cols-[240px_1fr] lg:grid-cols-[240px_1fr_340px] gap-6 items-start">

              {/* Left Sidebar */}
              <Sidebar className="hidden md:block sticky top-36" />

              {/* Main Content Area */}
              <main className="min-w-0 bg-white rounded-xl shadow-sm border border-border/40 min-h-[80vh]">
                <Suspense fallback={<PageLoader />}>
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
                      <Route
                        path="/performance"
                        element={
                          <AdminGuard>
                            <PerformancePage />
                          </AdminGuard>
                        }
                      />
                      <Route path="/abonnement" element={<PremiumPage />} />
                      <Route path="/match/:id" element={<MatchDetailPage />} />
                      <Route path="/equipe/:name" element={<TeamProfile />} />
                      <Route path="/admin" element={<AdminPage />} />
                      <Route path="/login" element={<LoginPage />} />
                    </Routes>
                  </div>
                </Suspense>
              </main>

              {/* Right Sidebar */}
              <RightSidebar />

            </div>
          </div>

        </div>
      </BrowserRouter>
    </AuthProvider>
  )
}

export default App
