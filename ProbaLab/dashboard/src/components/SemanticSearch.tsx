import { useState, useRef, useEffect, useCallback } from "react"
import { Search, X, Sparkles, ArrowRight, Loader2 } from "lucide-react"
import { useNavigate } from "react-router-dom"
import { cn } from "@/lib/utils"

import { API_BASE } from "@/lib/api"

export default function SemanticSearch() {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState("")
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const inputRef = useRef(null)
  const debounceRef = useRef(null)
  const navigate = useNavigate()

  // Focus input when opened
  useEffect(() => {
    if (open && inputRef.current) {
      inputRef.current.focus()
    }
  }, [open])

  // Close on Escape
  useEffect(() => {
    const handleKey = (e) => {
      if (e.key === "Escape") setOpen(false)
      // Cmd+K / Ctrl+K to open
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault()
        setOpen(prev => !prev)
      }
    }
    window.addEventListener("keydown", handleKey)
    return () => window.removeEventListener("keydown", handleKey)
  }, [])

  // Debounced search
  const search = useCallback(async (q) => {
    if (!q || q.length < 3) {
      setResults(null)
      return
    }
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API_BASE}/search/semantic?q=${encodeURIComponent(q)}&limit=8`)
      if (!res.ok) throw new Error(`Erreur ${res.status}`)
      const data = await res.json()
      setResults(data)
    } catch (err) {
      setError(err.message)
      setResults(null)
    } finally {
      setLoading(false)
    }
  }, [])

  const handleInput = (e) => {
    const val = e.target.value
    setQuery(val)
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => search(val), 400)
  }

  const handleClose = () => {
    setOpen(false)
    setQuery("")
    setResults(null)
    setError(null)
  }

  const goToMatch = (fixtureId) => {
    handleClose()
    navigate(`/football/match/${fixtureId}`)
  }

  const hasPredictions = (results?.predictions?.length ?? 0) > 0
  const hasLearnings = (results?.learnings?.length ?? 0) > 0
  const hasResults = hasPredictions || hasLearnings

  return (
    <>
      {/* Trigger button */}
      <button
        onClick={() => setOpen(true)}
        className={cn(
          "flex items-center gap-1.5 px-2 py-1 rounded text-xs font-medium",
          "text-muted-foreground bg-muted/50 hover:bg-muted hover:text-foreground",
          "transition-all duration-150 border border-border/50"
        )}
        title="Recherche sémantique (⌘K)"
      >
        <Search className="w-3 h-3" />
        <span className="hidden sm:inline">Recherche IA</span>
        <kbd className="hidden md:inline-flex items-center gap-0.5 px-1 rounded text-xs font-mono bg-background/60 border border-border/60">
          ⌘K
        </kbd>
      </button>

      {/* Overlay */}
      {open && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="Recherche sémantique"
          className="fixed inset-0 z-[100] bg-black/50 backdrop-blur-sm animate-in fade-in duration-150"
          onClick={handleClose}
        >
          {/* Search panel */}
          <div
            className="mx-auto mt-[10vh] w-[92%] max-w-lg bg-card border border-border rounded-xl shadow-2xl overflow-hidden"
            onClick={e => e.stopPropagation()}
            style={{ animation: 'fade-in-up 0.2s ease-out' }}
          >
            {/* Search input */}
            <div className="flex items-center gap-2 px-4 py-3 border-b border-border">
              <Sparkles className="w-4 h-4 text-primary shrink-0" />
              <input
                ref={inputRef}
                value={query}
                onChange={handleInput}
                placeholder="Recherche en langage naturel... (ex: derby avec gros enjeu)"
                aria-label="Recherche en langage naturel"
                className="flex-1 bg-transparent text-sm text-foreground outline-none placeholder:text-muted-foreground/60"
              />
              {loading ? (
                <Loader2 className="w-4 h-4 text-muted-foreground animate-spin shrink-0" />
              ) : query ? (
                <button onClick={() => { setQuery(""); setResults(null) }} aria-label="Effacer la recherche" className="text-muted-foreground hover:text-foreground">
                  <X className="w-4 h-4" />
                </button>
              ) : null}
            </div>

            {/* Results */}
            <div className="max-h-[55vh] overflow-y-auto">
              {/* Empty state */}
              {!loading && !results && !error && (
                <div className="px-4 py-6 text-center">
                  <Sparkles className="w-6 h-6 text-primary/40 mx-auto mb-2" />
                  <p className="text-xs text-muted-foreground">
                    Recherche par <span className="font-bold text-primary/70">similarité sémantique</span>
                  </p>
                  <p className="text-xs text-muted-foreground/60 mt-1">
                    Tape une description de match, un style de jeu, un scénario...
                  </p>
                  <div className="flex flex-wrap gap-1.5 justify-center mt-3">
                    {["derby avec gros enjeu", "victoire surprise extérieur", "match défensif peu de buts", "équipe en série de victoires"].map(ex => (
                      <button
                        key={ex}
                        onClick={() => { setQuery(ex); search(ex) }}
                        className="px-2 py-1 rounded-full text-xs font-medium bg-muted/60 text-muted-foreground hover:bg-primary/10 hover:text-primary transition-colors"
                      >
                        {ex}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Error */}
              {error && (
                <div className="px-4 py-4 text-center">
                  <p className="text-xs text-destructive">{error}</p>
                </div>
              )}

              {/* No results */}
              {!loading && results && !hasResults && (
                <div className="px-4 py-6 text-center">
                  <p className="text-xs text-muted-foreground">Aucun résultat pour « {query} »</p>
                </div>
              )}

              {/* Predictions */}
              {hasPredictions && (
                <div>
                  <div className="px-4 py-2 bg-muted/30">
                    <span className="text-xs font-bold uppercase text-muted-foreground tracking-wider">
                      ⚽ Matchs similaires ({results.predictions.length})
                    </span>
                  </div>
                  {results.predictions.map((pred, i) => (
                    <button
                      key={i}
                      onClick={() => pred.fixture_id && goToMatch(pred.fixture_id)}
                      className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-muted/40 transition-colors text-left group border-b border-border/30 last:border-0"
                    >
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-bold text-foreground truncate">
                            {pred.home_team} vs {pred.away_team}
                          </span>
                          {pred.league && (
                            <span className="text-xs text-muted-foreground bg-muted/60 px-1.5 py-0.5 rounded shrink-0">
                              {pred.league}
                            </span>
                          )}
                        </div>
                        {pred.analysis_text && (
                          <p className="text-xs text-muted-foreground mt-0.5 line-clamp-1">
                            {pred.analysis_text}
                          </p>
                        )}
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <span className={cn(
                          "text-xs font-bold px-1.5 py-0.5 rounded",
                          pred.similarity >= 0.7 ? "bg-emerald-500/15 text-emerald-500" :
                          pred.similarity >= 0.5 ? "bg-amber-500/15 text-amber-500" :
                          "bg-muted text-muted-foreground"
                        )}>
                          {Math.round(pred.similarity * 100)}%
                        </span>
                        <ArrowRight className="w-3 h-3 text-muted-foreground/40 group-hover:text-primary transition-colors" />
                      </div>
                    </button>
                  ))}
                </div>
              )}

              {/* Learnings */}
              {hasLearnings && (
                <div>
                  <div className="px-4 py-2 bg-muted/30">
                    <span className="text-xs font-bold uppercase text-muted-foreground tracking-wider">
                      📚 Enseignements ({results.learnings.length})
                    </span>
                  </div>
                  {results.learnings.map((l, i) => (
                    <div
                      key={i}
                      className="px-4 py-2.5 border-b border-border/30 last:border-0"
                    >
                      <p className="text-xs text-foreground/90">{l.learning_text}</p>
                      <div className="flex items-center gap-2 mt-1">
                        <span className={cn(
                          "text-xs font-bold px-1.5 py-0.5 rounded",
                          l.similarity >= 0.7 ? "bg-emerald-500/15 text-emerald-500" :
                          l.similarity >= 0.5 ? "bg-amber-500/15 text-amber-500" :
                          "bg-muted text-muted-foreground"
                        )}>
                          {Math.round(l.similarity * 100)}% match
                        </span>
                        {l.tags?.map((tag, j) => (
                          <span key={j} className="text-xs text-muted-foreground/70 bg-muted/40 px-1 py-0.5 rounded">
                            {tag}
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="flex items-center justify-between px-4 py-2 border-t border-border bg-muted/20">
              <span className="text-xs text-muted-foreground/50">
                ProbaLab · Recherche sémantique
              </span>
              <span className="text-xs text-muted-foreground/50">
                ESC pour fermer
              </span>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
