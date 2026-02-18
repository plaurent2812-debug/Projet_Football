import { BrowserRouter, Routes, Route, NavLink, useNavigate, useLocation } from "react-router-dom"
import { lazy, Suspense, useState, useEffect } from "react"
import { Zap, Trophy, Shield, Menu, X, Sun, Moon, LogOut, User, ChevronRight } from "lucide-react"
import { cn } from "@/lib/utils"
import { AuthProvider, useAuth } from "@/lib/auth"
import "./App.css"

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


function PageLoader() {
  return (
    <div className="flex items-center justify-center py-32">
      <div className="w-8 h-8 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
    </div>
  )
}

// ── Theme Toggle ──────────────────────────────────────────────
function useTheme() {
  const [theme, setTheme] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('probalab-theme') || 'light'
    }
    return 'light'
  })

  useEffect(() => {
    const root = document.documentElement
    root.classList.remove('light', 'dark')
    root.classList.add(theme)
    localStorage.setItem('probalab-theme', theme)
  }, [theme])

  return [theme, setTheme]
}

// ── Header ────────────────────────────────────────────────────
function Header({ theme, setTheme, mobileOpen, setMobileOpen }) {
  const { user, signOut, role, isPremium, isAdmin } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const navLinks = [
    { to: "/", label: "Accueil", exact: true },
    { to: "/football", label: "⚽ Football" },
    { to: "/nhl", label: "🏒 NHL" },
  ]

  return (
    <header className="sticky top-0 z-50 border-b border-border/60 bg-card/80 backdrop-blur-xl shadow-sm">
      <div className="max-w-[1400px] mx-auto px-4 sm:px-6">
        <div className="flex items-center justify-between h-14">

          {/* Logo */}
          <NavLink to="/" className="flex items-center gap-2 group shrink-0">
            <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center shadow-md shadow-primary/30">
              <Zap className="w-4 h-4 text-primary-foreground" />
            </div>
            <span className="text-lg font-black tracking-tight text-foreground">
              Proba<span className="text-primary">Lab</span>
            </span>
          </NavLink>

          {/* Desktop Nav */}
          <nav className="hidden md:flex items-center gap-1">
            {navLinks.map(link => (
              <NavLink
                key={link.to}
                to={link.to}
                end={link.exact}
                className={({ isActive }) => cn(
                  "px-3 py-1.5 rounded-lg text-sm font-medium transition-all duration-150",
                  isActive
                    ? "bg-primary/10 text-primary font-semibold"
                    : "text-muted-foreground hover:text-foreground hover:bg-accent/60"
                )}
              >
                {link.label}
              </NavLink>
            ))}
            {isAdmin && (
              <>
                <NavLink
                  to="/performance"
                  className={({ isActive }) => cn(
                    "px-3 py-1.5 rounded-lg text-sm font-medium transition-all duration-150",
                    isActive ? "bg-primary/10 text-primary" : "text-muted-foreground hover:text-foreground hover:bg-accent/60"
                  )}
                >
                  Performance
                </NavLink>
                <NavLink
                  to="/admin"
                  className={({ isActive }) => cn(
                    "px-3 py-1.5 rounded-lg text-sm font-medium transition-all duration-150",
                    isActive ? "bg-primary/10 text-primary" : "text-muted-foreground hover:text-foreground hover:bg-accent/60"
                  )}
                >
                  <Shield className="w-3.5 h-3.5 inline mr-1" />Admin
                </NavLink>
              </>
            )}
          </nav>

          {/* Right Actions */}
          <div className="flex items-center gap-2">
            {/* Theme toggle */}
            <button
              onClick={() => setTheme(t => t === 'dark' ? 'light' : 'dark')}
              className="p-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-accent/60 transition-colors"
              aria-label="Toggle theme"
            >
              {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            </button>

            {/* Premium badge */}
            {!isPremium && !isAdmin && (
              <button
                onClick={() => navigate('/premium')}
                className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold text-amber-600 dark:text-amber-400 bg-amber-500/10 hover:bg-amber-500/20 transition-colors border border-amber-500/20"
              >
                <Trophy className="w-3.5 h-3.5" />
                Premium
              </button>
            )}

            {/* Auth */}
            {user ? (
              <NavLink
                to="/profile"
                className={({ isActive }) => cn(
                  "flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors border",
                  isActive
                    ? "bg-primary/10 text-primary border-primary/20"
                    : "bg-accent/40 text-foreground border-border/50 hover:bg-accent/60"
                )}
              >
                <User className="w-4 h-4" />
                <span className="hidden lg:inline">Mon compte</span>
              </NavLink>
            ) : (
              <NavLink
                to="/login"
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-semibold bg-primary text-primary-foreground hover:bg-primary/90 transition-colors shadow-sm shadow-primary/20"
              >
                Connexion
              </NavLink>
            )}

            {/* Mobile menu toggle */}
            <button
              className="md:hidden p-2 rounded-lg text-muted-foreground hover:bg-accent/60 transition-colors"
              onClick={() => setMobileOpen(o => !o)}
            >
              {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Menu */}
      {mobileOpen && (
        <div className="md:hidden border-t border-border/40 bg-card/95 backdrop-blur-xl px-4 py-3 space-y-1">
          {navLinks.map(link => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.exact}
              onClick={() => setMobileOpen(false)}
              className={({ isActive }) => cn(
                "flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium transition-colors",
                isActive ? "bg-primary/10 text-primary" : "text-foreground hover:bg-accent/60"
              )}
            >
              {link.label}
              <ChevronRight className="w-4 h-4 text-muted-foreground/50" />
            </NavLink>
          ))}
          {!isPremium && !isAdmin && (
            <NavLink
              to="/premium"
              onClick={() => setMobileOpen(false)}
              className="flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm font-bold text-amber-600 bg-amber-500/10"
            >
              <Trophy className="w-4 h-4" /> Passer Premium
            </NavLink>
          )}
        </div>
      )}
    </header>
  )
}

// ── Footer ────────────────────────────────────────────────────
function Footer() {
  return (
    <footer className="border-t border-border/40 bg-card/50 mt-auto">
      <div className="max-w-[1400px] mx-auto px-4 sm:px-6 py-4">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Zap className="w-3.5 h-3.5 text-primary" />
            <span className="text-sm font-bold text-foreground">ProbaLab</span>
          </div>
          <p className="disclaimer-text text-center max-w-lg">
            ProbaLab fournit des analyses statistiques à titre informatif uniquement.
            Ce site ne constitue pas un conseil en paris sportifs. Jouez de manière responsable. 18+
          </p>
          <div className="flex items-center gap-4 text-xs text-muted-foreground">
            <a href="#" className="hover:text-foreground transition-colors">CGU</a>
            <a href="#" className="hover:text-foreground transition-colors">Confidentialité</a>
            <a href="#" className="hover:text-foreground transition-colors">Contact</a>
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

// ── Main App ──────────────────────────────────────────────────
function AppContent() {
  const [theme, setTheme] = useTheme()
  const [mobileOpen, setMobileOpen] = useState(false)
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10))
  const [selectedLeague, setSelectedLeague] = useState(null)
  const location = useLocation()

  // Close mobile menu on route change
  useEffect(() => { setMobileOpen(false) }, [location.pathname])

  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground transition-colors duration-300">
      <Header theme={theme} setTheme={setTheme} mobileOpen={mobileOpen} setMobileOpen={setMobileOpen} />

      <main className="flex-1 max-w-[1400px] mx-auto w-full px-4 sm:px-6 py-6">
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
              {/* Legacy route */}
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
            </Routes>
          </div>
        </Suspense>
      </main>

      <Footer />
    </div>
  )
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AppContent />
      </BrowserRouter>
    </AuthProvider>
  )
}

export default App
