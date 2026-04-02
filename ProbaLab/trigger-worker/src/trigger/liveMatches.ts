import { task, wait, schedules } from "@trigger.dev/sdk/v3";

const CRON_SECRET = process.env.CRON_SECRET || "";
const API_URL = process.env.API_URL || "https://web-production-ff663.up.railway.app";

const standardRetry = {
    maxAttempts: 3,
    factor: 1.5,
    minTimeoutInMs: 2000,
    maxTimeoutInMs: 30000,
    randomize: true,
};

// ─── Task 1: Monitor Halftime (48 min) ──────────────────────────
export const monitorHalftime = task({
    id: "monitor-halftime",
    retry: standardRetry,
    run: async (payload: { fixture_id: string; start_date: string }) => {
        const startTime = new Date(payload.start_date);
        const halftimeTime = new Date(startTime.getTime() + 48 * 60 * 1000);
        await wait.until({ date: halftimeTime });

        const res = await fetch(`${API_URL}/api/trigger/analyze-halftime`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${CRON_SECRET}`
            },
            body: JSON.stringify({ fixture_id: payload.fixture_id }),
        });
        if (!res.ok) throw new Error(`Analyze halftime failed: ${res.statusText}`);
        return await res.json();
    },
});

// ─── Task 2: Monitor 70th Minute ────────────────────────────────
export const monitor70thMinute = task({
    id: "monitor-70th-minute",
    retry: standardRetry,
    run: async (payload: { fixture_id: string; start_date: string }) => {
        const startTime = new Date(payload.start_date);
        const seventyMinTime = new Date(startTime.getTime() + 70 * 60 * 1000);
        await wait.until({ date: seventyMinTime });

        const res = await fetch(`${API_URL}/api/trigger/analyze-halftime`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${CRON_SECRET}`
            },
            body: JSON.stringify({ fixture_id: payload.fixture_id }),
        });
        if (!res.ok) throw new Error(`Analyze 70th minute failed: ${res.statusText}`);
        return await res.json();
    },
});

// ─── Task 3: Schedule Daily Matches (CRON 08:00 UTC = 09:00 Paris) ──
// Fetches today's football matches and spawns halftime/70th monitors
export const scheduleDailyMatches = schedules.task({
    id: "schedule-daily-matches",
    cron: "0 8 * * *",
    retry: standardRetry,
    run: async () => {
        // NHL daily evaluation (non-blocking)
        await fetch(`${API_URL}/api/trigger/nhl-evaluate-performance`, {
            method: "POST",
            headers: { "Content-Type": "application/json", "Authorization": `Bearer ${CRON_SECRET}` },
        }).catch(e => console.error("NHL eval error:", e));

        // Fetch today's football matches
        const res = await fetch(`${API_URL}/api/trigger/daily-matches`, {
            headers: { "Authorization": `Bearer ${CRON_SECRET}` }
        });
        if (!res.ok) throw new Error(`Failed to fetch daily matches: ${res.statusText}`);

        const data = await res.json();
        const matches = data.matches || [];

        // Trigger halftime + 70th minute for each match (non-blocking per Trigger.dev guidelines)
        for (const match of matches) {
            await monitorHalftime.trigger({ fixture_id: match.id, start_date: match.date });
            await monitor70thMinute.trigger({ fixture_id: match.id, start_date: match.date });
        }

        return { scheduled: matches.length, tasks_created: matches.length * 2 };
    },
});

// ─── Task 4: Global Minutely Scheduler (Live Scores & Momentum) ─────
// Updates live scores every minute during active match windows
export const globalMinutelyScheduler = schedules.task({
    id: "global-minutely-scheduler",
    cron: "*/2 * * * *",   // Every 2 minutes
    retry: standardRetry,
    run: async () => {
        const now = new Date();
        const hour = now.getUTCHours();
        const min = now.getUTCMinutes();

        // 1. Gating: Check if we have any active or upcoming matches in the next 15 mins
        const checkRes = await fetch(`${API_URL}/api/trigger/check-active-matches`, {
            headers: { "Authorization": `Bearer ${CRON_SECRET}` }
        });

        if (checkRes.ok) {
            const checkData = await checkRes.json();
            if (!checkData.active && !checkData.upcoming_soon) {
                return { status: "skipped", reason: "No active or upcoming matches" };
            }
        }

        const promises: Promise<Response>[] = [];

        // Football live scores (11h–23h UTC)
        // detail=true every 10 min fetches events/stats; otherwise just score+elapsed
        if (hour >= 11 && hour <= 23) {
            const needDetail = min % 10 === 0;
            const scoreUrl = needDetail
                ? `${API_URL}/api/trigger/update-live-scores?detail=true`
                : `${API_URL}/api/trigger/update-live-scores`;
            promises.push(fetch(scoreUrl, {
                method: "POST",
                headers: { "Content-Type": "application/json", "Authorization": `Bearer ${CRON_SECRET}` }
            }));
        }

        // Football momentum every 6 min
        if (min % 6 === 0) {
            promises.push(fetch(`${API_URL}/api/trigger/football-momentum`, {
                method: "POST",
                headers: { "Content-Type": "application/json", "Authorization": `Bearer ${CRON_SECRET}` }
            }));
        }

        // NHL live scores (16h–08h UTC = soirée/nuit nord-américaine)
        if (hour >= 16 || hour <= 8) {
            promises.push(fetch(`${API_URL}/api/trigger/nhl-update-live-scores`, {
                method: "POST",
                headers: { "Content-Type": "application/json", "Authorization": `Bearer ${CRON_SECRET}` }
            }));
        }

        await Promise.allSettled(promises);
        return { jobs_ran: promises.length };
    },
});

// ─── Task 5: Fetch Lineups H-1 (every 15 min, 10h–22h UTC) ─────────
export const fetchLineups = schedules.task({
    id: "fetch-lineups",
    cron: "*/15 10-22 * * *",
    retry: standardRetry,
    run: async () => {
        const res = await fetch(`${API_URL}/api/trigger/fetch-lineups`, {
            method: "POST",
            headers: { "Content-Type": "application/json", "Authorization": `Bearer ${CRON_SECRET}` },
        });
        if (!res.ok) throw new Error(`Fetch lineups failed: ${res.statusText}`);
        return await res.json();
    },
});

// ─── Task 6: NHL ML Reminder (toutes les 2 semaines) ────────────────
// Long-running wait — checkpointed automatiquement par Trigger.dev
export const nhlMlReminder = task({
    id: "nhl-ml-reminder",
    retry: standardRetry,
    run: async () => {
        await wait.for({ days: 14 });

        const res = await fetch(`${API_URL}/api/trigger/nhl-ml-reminder`, {
            method: "POST",
            headers: { "Content-Type": "application/json", "Authorization": `Bearer ${CRON_SECRET}` },
        });
        if (!res.ok) throw new Error(`NHL ML reminder failed: ${res.statusText}`);
        return await res.json();
    },
});

// ─────────────────────────────────────────────────────────────────────
// SUPPRIMÉ (remplacés par pipelineSchedules.ts + resolveBestBets.ts) :
// - run-daily-pipeline     → schedule-football-data + schedule-football-analysis
// - nhl-run-pipeline       → schedule-nhl-pipeline
// - detect-value-bets      → intégré dans le pipeline football
// - daily-recap            → endpoint inexistant
// - nhl-fetch-odds         → endpoint inexistant
// ─────────────────────────────────────────────────────────────────────
