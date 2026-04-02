import { useState, useCallback, useEffect } from "react"

const STARRED_KEY = "probalab_starred_matches"
const FAV_TEAMS_KEY = "probalab_fav_teams"

function loadSet(key) {
    try {
        const raw = localStorage.getItem(key)
        return raw ? new Set(JSON.parse(raw)) : new Set()
    } catch {
        return new Set()
    }
}

function saveSet(key, set) {
    try {
        localStorage.setItem(key, JSON.stringify([...set]))
    } catch {
        // localStorage full or unavailable
    }
}

export function useWatchlist() {
    const [starredMatches, setStarredMatches] = useState(() => loadSet(STARRED_KEY))
    const [favTeams, setFavTeams] = useState(() => loadSet(FAV_TEAMS_KEY))

    // Sync to localStorage whenever state changes
    useEffect(() => { saveSet(STARRED_KEY, starredMatches) }, [starredMatches])
    useEffect(() => { saveSet(FAV_TEAMS_KEY, favTeams) }, [favTeams])

    const toggleMatch = useCallback((id) => {
        setStarredMatches(prev => {
            const next = new Set(prev)
            if (next.has(id)) next.delete(id)
            else next.add(id)
            return next
        })
    }, [])

    const toggleTeam = useCallback((name) => {
        setFavTeams(prev => {
            const next = new Set(prev)
            if (next.has(name)) next.delete(name)
            else next.add(name)
            return next
        })
    }, [])

    const isStarred = useCallback((id) => starredMatches.has(id), [starredMatches])
    const isFavTeam = useCallback((name) => favTeams.has(name), [favTeams])

    return { starredMatches, favTeams, toggleMatch, toggleTeam, isStarred, isFavTeam }
}
