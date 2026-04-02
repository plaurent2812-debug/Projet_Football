import { schedules } from "@trigger.dev/sdk";

const API_URL = process.env.API_URL || "https://web-production-ff663.up.railway.app";
const CRON_SECRET = process.env.CRON_SECRET || "";

const standardRetry = {
    maxAttempts: 3,
    factor: 1.5,
    minTimeoutInMs: 3000,
    maxTimeoutInMs: 30000,
    randomize: true,
};

/** Helper: generate an array of date strings for the last N days */
function getLastNDays(from: Date, n: number): string[] {
    const dates: string[] = [];
    for (let i = 1; i <= n; i++) {
        const d = new Date(from);
        d.setDate(d.getDate() - i);
        dates.push(d.toISOString().slice(0, 10));
    }
    return dates;
}

/**
 * ── Resolve Football Best Bets ─────────────────────────────────────
 * Runs at 07:30 Paris (06:30 UTC). Sweeps the last 7 days to catch
 * any missed resolutions from prior runs.
 */
export const resolveFootballBets = schedules.task({
    id: "resolve-football-bets",
    cron: "30 6 * * *",   // 06:30 UTC = 07:30 Paris
    retry: standardRetry,
    run: async (payload) => {
        const dates = getLastNDays(new Date(payload.timestamp), 7);
        const results: Record<string, unknown> = {};

        for (const date of dates) {
            console.log(`[Football Resolve] Checking bets for ${date}`);
            try {
                const res = await fetch(`${API_URL}/api/best-bets/resolve`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "Authorization": `Bearer ${CRON_SECRET}`,
                    },
                    body: JSON.stringify({ date, sport: "football" }),
                });

                if (!res.ok) {
                    const text = await res.text();
                    console.error(`[Football Resolve] ${date} failed (${res.status}): ${text}`);
                    continue;
                }

                const result = await res.json();
                results[date] = result;
                if (result.resolved_count > 0) {
                    console.log(`[Football Resolve] ${date}: resolved ${result.resolved_count} bets`);
                }
            } catch (e) {
                console.error(`[Football Resolve] ${date} error:`, e);
            }
        }

        console.log(`[Football Resolve] Sweep done`);
        return results;
    },
});

/**
 * ── Resolve NHL Best Bets ──────────────────────────────────────────
 * Runs at 12:00 Paris (11:00 UTC). Sweeps the last 7 days.
 *
 * Step 1: Call /api/nhl/fetch-game-stats → fetches NHL API boxscores
 * Step 2: Call /api/best-bets/resolve → marks WIN/LOSS
 */
export const resolveNHLBets = schedules.task({
    id: "resolve-nhl-bets",
    cron: "0 11 * * *",   // 11:00 UTC = 12:00 Paris
    retry: standardRetry,
    run: async (payload) => {
        const dates = getLastNDays(new Date(payload.timestamp), 7);
        const results: Record<string, unknown> = {};

        const headers = {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${CRON_SECRET}`,
        };

        for (const date of dates) {
            console.log(`[NHL Resolve] Processing ${date}`);
            try {
                // Step 1 — Fetch real player stats
                const fetchRes = await fetch(`${API_URL}/api/nhl/fetch-game-stats`, {
                    method: "POST",
                    headers,
                    body: JSON.stringify({ date }),
                });

                if (!fetchRes.ok) {
                    console.error(`[NHL Resolve] ${date} fetch-game-stats failed (${fetchRes.status})`);
                    continue;
                }

                // Step 2 — Resolve pending bets
                const resolveRes = await fetch(`${API_URL}/api/best-bets/resolve`, {
                    method: "POST",
                    headers,
                    body: JSON.stringify({ date, sport: "nhl" }),
                });

                if (!resolveRes.ok) {
                    console.error(`[NHL Resolve] ${date} resolve failed (${resolveRes.status})`);
                    continue;
                }

                const resolveResult = await resolveRes.json();
                results[date] = resolveResult;
                if (resolveResult.resolved_count > 0) {
                    console.log(`[NHL Resolve] ${date}: resolved ${resolveResult.resolved_count} bets`);
                }
            } catch (e) {
                console.error(`[NHL Resolve] ${date} error:`, e);
            }
        }

        console.log(`[NHL Resolve] Sweep done`);
        return results;
    },
});

/**
 * ── Resolve Expert Picks: Football ─────────────────────────────────
 * Runs at 22:59 UTC (23:59 Paris). Sweeps today + last 7 days.
 */
export const resolveExpertPicksFootball = schedules.task({
    id: "resolve-expert-picks-football",
    cron: "59 22 * * *",   // 22:59 UTC = 23:59 Paris
    retry: standardRetry,
    run: async (payload) => {
        const today = new Date(payload.timestamp).toISOString().slice(0, 10);
        // Include today + last 7 days
        const dates = [today, ...getLastNDays(new Date(payload.timestamp), 7)];
        const results: Record<string, unknown> = {};

        for (const date of dates) {
            console.log(`[Expert Resolve Football] Checking picks for ${date}`);
            try {
                const res = await fetch(`${API_URL}/api/expert-picks/resolve`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "Authorization": `Bearer ${CRON_SECRET}`,
                    },
                    body: JSON.stringify({ date, sport: "football" }),
                });

                if (!res.ok) {
                    console.error(`[Expert Resolve Football] ${date} failed (${res.status})`);
                    continue;
                }

                const result = await res.json();
                results[date] = result;
                if (result.resolved_count > 0) {
                    console.log(`[Expert Resolve Football] ${date}: resolved ${result.resolved_count}`);
                }
            } catch (e) {
                console.error(`[Expert Resolve Football] ${date} error:`, e);
            }
        }

        console.log(`[Expert Resolve Football] Sweep done`);
        return results;
    },
});

/**
 * ── Resolve Expert Picks: NHL ──────────────────────────────────────
 * Runs at 07:00 UTC (08:00 Paris). Sweeps the last 7 days.
 */
export const resolveExpertPicksNHL = schedules.task({
    id: "resolve-expert-picks-nhl",
    cron: "0 7 * * *",   // 07:00 UTC = 08:00 Paris
    retry: standardRetry,
    run: async (payload) => {
        const dates = getLastNDays(new Date(payload.timestamp), 7);
        const results: Record<string, unknown> = {};

        for (const date of dates) {
            console.log(`[Expert Resolve NHL] Checking picks for ${date}`);
            try {
                const res = await fetch(`${API_URL}/api/expert-picks/resolve`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "Authorization": `Bearer ${CRON_SECRET}`,
                    },
                    body: JSON.stringify({ date, sport: "nhl" }),
                });

                if (!res.ok) {
                    console.error(`[Expert Resolve NHL] ${date} failed (${res.status})`);
                    continue;
                }

                const result = await res.json();
                results[date] = result;
                if (result.resolved_count > 0) {
                    console.log(`[Expert Resolve NHL] ${date}: resolved ${result.resolved_count}`);
                }
            } catch (e) {
                console.error(`[Expert Resolve NHL] ${date} error:`, e);
            }
        }

        console.log(`[Expert Resolve NHL] Sweep done`);
        return results;
    },
});

