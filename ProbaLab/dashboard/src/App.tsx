import { BrowserRouter, Routes, Route, NavLink, useNavigate, useLocation } from "react-router-dom"
import { lazy, Suspense, useState, useEffect, Component } from "react"
import { Zap, Trophy, Shield, User, LayoutGrid, Target, BarChart2 } from "lucide-react"
import { cn } from "@/lib/utils"
import { AuthProvider, useAuth } from "@/lib/auth"
import { ThemeProvider } from "@/components/theme-provider"
import { ModeToggle } from "@/components/mode-toggle"
import SemanticSearch from "@/components/SemanticSearch"
import "./App.css"

// ── Error Boundary ────────────────────────────────────────────
class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }
  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }
  componentDidCatch(error, info) {
    console.error("ErrorBoundary caught:", error, info)
    // Auto-reload on stale chunk errors (happens after a new deploy)
    const msg = error?.message || error?.toString() || ""
    if (
      msg.includes("Failed to fetch dynamically imported module") ||
      msg.includes("Loading chunk") ||
      msg.includes("Loading CSS chunk")
    ) {
      // Prevent infinite reload loop
      const lastReload = sessionStorage.getItem("_chunk_reload")
      const now = Date.now()
      if (!lastReload || now - Number(lastReload) > 10000) {
        sessionStorage.setItem("_chunk_reload", String(now))
        window.location.reload()
        return
      }
    }
  }
  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: 40, color: '#fff', background: '#0B1120', minHeight: '100vh' }}>
          <h1 style={{ color: '#3B82F6', marginBottom: 16 }}>ProbaLab – Erreur</h1>
          <p style={{ marginBottom: 8 }}>Une erreur est survenue :</p>
          <pre style={{ background: '#1a1a2e', padding: 16, borderRadius: 8, fontSize: 12, overflow: 'auto' }}>
            {this.state.error?.toString()}
          </pre>
          <button
            onClick={() => window.location.reload()}
            style={{ marginTop: 16, padding: '8px 16px', background: '#3B82F6', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer' }}
          >
            Recharger
          </button>
        </div>
      )
    }
    return this.props.children
  }
}

// ── Lazy pages ────────────────────────────────────────────────
const HomePage = lazy(() => import("@/pages/HomePage"))
const FootballPage = lazy(() => import("@/pages/Dashboard"))
const MatchDetail = lazy(() => import("@/pages/MatchDetail"))
const NHLPage = lazy(() => import("@/pages/NHL/NHLPage"))
const NHLMatchDetail = lazy(() => import("@/pages/NHL/NHLMatchDetail"))
const PerformancePage = lazy(() => import("@/pages/Performance"))
const AdminPage = lazy(() => import("@/pages/Admin"))
const LoginPage = lazy(() => import("@/pages/Login"))
const PremiumPage = lazy(() => import("@/pages/Premium"))
const TeamProfile = lazy(() => import("@/pages/TeamProfile"))
const ProfilePage = lazy(() => import("@/pages/Profile"))
const WatchlistPage = lazy(() => import("@/pages/WatchlistPage"))
const ParisDuSoirPage = lazy(() => import("@/pages/ParisDuSoir"))
const UpdatePasswordPage = lazy(() => import("@/pages/UpdatePassword"))
const CGUPage = lazy(() => import("@/pages/CGU"))
const ConfidentialitePage = lazy(() => import("@/pages/Confidentialite"))
import GoalNotifications from "@/components/GoalNotifications"
import ExpertPickNotifications from "@/components/ExpertPickNotifications"
import Toaster from "@/components/Toaster"
import OfflineBanner from "@/components/OfflineBanner"


function PageLoader() {
  return (
    <div className="flex items-center justify-center py-24">
      <div className="w-6 h-6 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
    </div>
  )
}

// ── Header (FlashScore-style compact) ─────────────────────────
function Header() {
  const { user, isPremium, isAdmin } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const isFootball = location.pathname.startsWith('/football')
  const isNHL = location.pathname.startsWith('/nhl')

  return (
    <header className="sticky top-0 z-50 border-b border-border/60 bg-card">
      <div className="w-full mx-auto px-3 sm:px-4 md:px-8">
        <div className="flex items-center justify-between h-11">

          {/* Logo */}
          <NavLink to="/" className="flex items-center gap-1.5 shrink-0">
            <div className="w-6 h-6 rounded bg-primary flex items-center justify-center">
              <Zap className="w-3 h-3 text-primary-foreground" />
            </div>
            <span className="text-sm font-black tracking-tight text-foreground hidden sm:inline">
              Proba<span className="text-primary">Lab</span>
            </span>
          </NavLink>

          {/* Center: Sport tabs (hidden on mobile, bottom nav replaces) */}
          <nav className="hidden md:flex items-center gap-0">
            <NavLink
              to="/football"
              className={cn(
                "px-3 py-2 text-xs font-bold transition-colors border-b-2",
                isFootball
                  ? "text-primary border-primary"
                  : "text-muted-foreground border-transparent hover:text-foreground"
              )}
            >
              ⚽ Football
            </NavLink>
            <NavLink
              to="/nhl"
              className={cn(
                "px-3 py-2 text-xs font-bold transition-colors border-b-2",
                isNHL
                  ? "text-primary border-primary"
                  : "text-muted-foreground border-transparent hover:text-foreground"
              )}
            >
              🏒 NHL
            </NavLink>
            {(isPremium || isAdmin) && (
              <NavLink
                to="/paris-du-soir"
                className={({ isActive }) => cn(
                  "px-3 py-2 text-xs font-bold transition-colors border-b-2 flex items-center gap-1",
                  isActive ? "text-amber-400 border-amber-400" : "text-muted-foreground border-transparent hover:text-foreground"
                )}
              >
                <Target className="w-3 h-3" />Pronos
              </NavLink>
            )}
            {isAdmin && (
              <>
                <NavLink
                  to="/performance"
                  className={({ isActive }) => cn(
                    "px-3 py-2 text-xs font-bold transition-colors border-b-2",
                    isActive ? "text-primary border-primary" : "text-muted-foreground border-transparent hover:text-foreground"
                  )}
                >
                  📊 Perf
                </NavLink>
                <NavLink
                  to="/admin"
                  className={({ isActive }) => cn(
                    "px-3 py-2 text-xs font-bold transition-colors border-b-2",
                    isActive ? "text-primary border-primary" : "text-muted-foreground border-transparent hover:text-foreground"
                  )}
                >
                  <Shield className="w-3 h-3 inline mr-0.5" />Admin
                </NavLink>
              </>
            )}
          </nav>

          {/* Right Actions */}
          <div className="flex items-center gap-1.5">
            <SemanticSearch />
            <ModeToggle />

            {!isPremium && !isAdmin && (
              <button
                onClick={() => navigate('/premium')}
                className="hidden sm:flex items-center gap-1 px-2 py-1 rounded text-[10px] font-bold text-amber-500 bg-amber-500/10 hover:bg-amber-500/20 transition-colors"
              >
                <Trophy className="w-3 h-3" />
                PRO
              </button>
            )}

            {user ? (
              <NavLink
                to="/profile"
                aria-label="Profil"
                className={({ isActive }) => cn(
                  "p-1.5 rounded transition-colors",
                  isActive ? "text-primary bg-primary/10" : "text-muted-foreground hover:text-foreground hover:bg-accent/60"
                )}
              >
                <User className="w-4 h-4" />
              </NavLink>
            ) : (
              <NavLink
                to="/login"
                aria-label="Connexion"
                className="px-2.5 py-1 rounded text-xs font-bold bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
              >
                Connexion
              </NavLink>
            )}
          </div>
        </div>
      </div>
    </header>
  )
}

// ── Bottom Navigation (mobile only) ───────────────────────────
function NHLIcon() {
  return <span className="text-base leading-none">🏒</span>
}

function BottomNav() {
  const location = useLocation()
  const { isPremium, isAdmin } = useAuth()

  // Emoji icon components for sports
  const FootballIcon = () => <span className="text-base leading-none">⚽</span>
  const NHLIcon = () => <span className="text-base leading-none">🏒</span>

  const tabs = isPremium || isAdmin
    ? [
      { to: "/", label: "Tous", icon: LayoutGrid, exact: true },
      { to: "/football", label: "Football", icon: FootballIcon },
      { to: "/nhl", label: "NHL", icon: NHLIcon },
      { to: "/paris-du-soir", label: "Pronos", icon: Trophy },
      ...(isAdmin ? [
          { to: "/performance", label: "Perf", icon: BarChart2 },
          { to: "/admin", label: "Admin", icon: Shield }
      ] : []),
    ]
    : [
      { to: "/", label: "Tous", icon: LayoutGrid, exact: true },
      { to: "/football", label: "Football", icon: FootballIcon },
      { to: "/nhl", label: "NHL", icon: NHLIcon },
      { to: "/premium", label: "Premium", icon: Trophy },
    ]

  return (
    <nav className="fs-bottom-nav md:hidden">
      {tabs.map(tab => {
        const isActive = tab.exact
          ? location.pathname === tab.to
          : location.pathname.startsWith(tab.to)
        const Icon = tab.icon
        return (
          <NavLink
            key={tab.to}
            to={tab.to}
            className={cn("fs-bottom-nav-item", isActive && "active")}
          >
            <Icon />
            <span>{tab.label}</span>
          </NavLink>
        )
      })}
    </nav>
  )
}

// ── Footer (hidden on mobile, bottom nav replaces it) ─────────
function Footer() {
  return (
    <footer className="hidden md:block border-t border-border/40 bg-card/50 mt-auto">
      <div className="w-full mx-auto px-4 md:px-8 py-3">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-1.5">
            <Zap className="w-3 h-3 text-primary" />
            <span className="text-xs font-bold text-foreground">ProbaLab</span>
          </div>
          <p className="disclaimer-text text-center max-w-md">
            Analyses statistiques à titre informatif. Pas un conseil en paris. 18+
          </p>
          <div className="flex items-center gap-3 text-[10px] text-muted-foreground">
            <NavLink to="/cgu" className="hover:text-foreground transition-colors">CGU</NavLink>
            <NavLink to="/confidentialite" className="hover:text-foreground transition-colors">Confidentialité</NavLink>
          </div>
        </div>
      </div>
    </footer>
  )
}

// ── Admin Guard ───────────────────────────────────────────────
function AdminGuard({ children }) {
  const { hasAccess } = useAuth()
  if (!hasAccess('admin')) {
    return (
      <div className="flex flex-col items-center justify-center py-32 text-center">
        <Shield className="w-12 h-12 text-muted-foreground/30 mb-4" />
        <p className="text-muted-foreground font-medium">Accès réservé aux administrateurs</p>
      </div>
    )
  }
  return children
}

// ── Premium Guard ─────────────────────────────────────────────
function PremiumGuard({ children }) {
  const { hasAccess } = useAuth()
  if (!hasAccess('premium')) {
    return (
      <div className="flex flex-col items-center justify-center py-32 text-center">
        <Trophy className="w-12 h-12 text-amber-500/30 mb-4" />
        <p className="text-muted-foreground font-medium mb-4">Accès réservé aux abonnés Premium</p>
        <NavLink
          to="/premium"
          className="px-4 py-2 rounded-lg bg-amber-500 hover:bg-amber-400 text-black font-bold text-sm transition-colors"
        >
          Découvrir Premium
        </NavLink>
      </div>
    )
  }
  return children
}

// ── Protected Route Guard ─────────────────────────────────────
function Protected({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <PageLoader />
  if (!user) return <LoginRedirect />
  return children
}

function LoginRedirect() {
  const navigate = useNavigate()
  useEffect(() => { navigate('/login') }, [navigate])
  return null
}

// ── Main App ──────────────────────────────────────────────────
function AppContent() {
  const [date, setDate] = useState(() => {
    const d = new Date()
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
  })
  const [selectedLeague, setSelectedLeague] = useState(null)

  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground has-bottom-nav">
      <a href="#main-content" className="sr-only focus:not-sr-only focus:absolute focus:top-0 focus:left-0 focus:z-[100] focus:bg-primary focus:text-primary-foreground focus:px-4 focus:py-2 focus:text-sm focus:font-bold">
        Aller au contenu principal
      </a>
      <Header />
      <OfflineBanner />

      <main id="main-content" className="flex-1 w-full mx-auto px-4 md:px-8">
        <Suspense fallback={<PageLoader />}>
          <div className="animate-fade-in-up">
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/football" element={
                <FootballPage
                  date={date} setDate={setDate}
                  selectedLeague={selectedLeague} setSelectedLeague={setSelectedLeague}
                />
              } />
              <Route path="/football/match/:id" element={<MatchDetail />} />
              <Route path="/match/:id" element={<MatchDetail />} />
              <Route path="/nhl" element={<NHLPage date={date} setDate={setDate} />} />
              <Route path="/nhl/match/:id" element={<NHLMatchDetail />} />
              <Route path="/performance" element={<AdminGuard><PerformancePage /></AdminGuard>} />
              <Route path="/premium" element={<PremiumPage />} />
              <Route path="/abonnement" element={<PremiumPage />} />
              <Route path="/login" element={<LoginPage />} />
              <Route path="/equipe/:name" element={<TeamProfile />} />
              <Route path="/admin" element={<AdminGuard><AdminPage /></AdminGuard>} />
              <Route path="/profile" element={<Protected><ProfilePage /></Protected>} />
              <Route path="/watchlist" element={<WatchlistPage />} />
              <Route path="/paris-du-soir" element={<PremiumGuard><ParisDuSoirPage /></PremiumGuard>} />
              <Route path="/update-password" element={<UpdatePasswordPage />} />
              <Route path="/cgu" element={<CGUPage />} />
              <Route path="/confidentialite" element={<ConfidentialitePage />} />
            </Routes>
          </div>
        </Suspense>
      </main>

      <Footer />
      <BottomNav />
      <GoalNotifications />
      <ExpertPickNotifications />
      <Toaster />
    </div>
  )
}

function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <ThemeProvider defaultTheme="dark" storageKey="vite-ui-theme">
          <BrowserRouter>
            <AppContent />
          </BrowserRouter>
        </ThemeProvider>
      </AuthProvider>
    </ErrorBoundary>
  )
}

export default App
