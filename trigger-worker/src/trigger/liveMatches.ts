import { task, wait, schedules } from "@trigger.dev/sdk/v3";

const CRON_SECRET = process.env.CRON_SECRET || "super_secret_probalab_2026";
const API_URL = process.env.API_URL || "https://web-production-ff663.up.railway.app";

// ─── Task 1: Monitor Halftime (48 min) ─────────────────────────
export const monitorHalftime = task({
    id: "monitor-halftime",
    run: async (payload: { fixture_id: string; start_date: string }) => {
        const startTime = new Date(payload.start_date);

        // Wait until 48 minutes after kickoff (halftime buffer)
        const halftimeTime = new Date(startTime.getTime() + 48 * 60 * 1000);

        await wait.until({ date: halftimeTime });

        // Wake up and call Python backend
        const res = await fetch(`${API_URL}/api/trigger/analyze-halftime`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${CRON_SECRET}`
            },
            body: JSON.stringify({ fixture_id: payload.fixture_id }),
        });

        if (!res.ok) {
            throw new Error(`Analyze halftime failed: ${res.statusText}`);
        }

        const data = await res.json();
        return data;
    },
});

// ─── Task 2: Monitor 70th Minute ────────────────────────────────
export const monitor70thMinute = task({
    id: "monitor-70th-minute",
    run: async (payload: { fixture_id: string; start_date: string }) => {
        const startTime = new Date(payload.start_date);
        const seventyMinTime = new Date(startTime.getTime() + 70 * 60 * 1000);

        await wait.until({ date: seventyMinTime });

        const res = await fetch(`${API_URL}/api/trigger/analyze-halftime`, { // Assuming same endpoint for now
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${CRON_SECRET}`
            },
            body: JSON.stringify({ fixture_id: payload.fixture_id }),
        });

        if (!res.ok) {
            throw new Error(`Analyze 70th minute failed: ${res.statusText}`);
        }

        return await res.json();
    },
});

// ─── Task 3: Schedule Daily Matches (CRON 08:00) ──────────────
export const scheduleDailyMatches = schedules.task({
    id: "schedule-daily-matches",
    cron: "0 8 * * *",
    run: async () => {
        const res = await fetch(`${API_URL}/api/trigger/daily-matches`, {
            headers: { "Authorization": `Bearer ${CRON_SECRET}` }
        });
        if (!res.ok) {
            throw new Error(`Failed to fetch daily matches: ${res.statusText}`);
        }
        const data = await res.json();
        const matches = data.matches || [];

        // Schedule both halftime AND 70th minute monitors for each match
        const triggerPromises = matches.flatMap((match: any) => [
            monitorHalftime.trigger({
                fixture_id: match.id,
                start_date: match.date,
            }),
            monitor70thMinute.trigger({
                fixture_id: match.id,
                start_date: match.date,
            }),
        ]);

        await Promise.all(triggerPromises);

        return { scheduled: matches.length, tasks_created: matches.length * 2 };
    },
});

// ─── Task 4: Update Live Scores (CRON every 5 min, 12h-23h) ───
export const updateLiveScores = schedules.task({
    id: "update-live-scores",
    cron: "*/5 11-23 * * *",  // Every 5 min, 12h-00h Paris (11h-23h UTC)
    run: async () => {
        const res = await fetch(`${API_URL}/api/trigger/update-live-scores`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${CRON_SECRET}`
            },
        });

        if (!res.ok) {
            throw new Error(`Failed to update live scores: ${res.statusText}`);
        }

        return await res.json();
    },
});

// ─── Task 5: Run Daily Pipeline (CRON 06:00) ──────────────────
export const runDailyPipeline = schedules.task({
    id: "run-daily-pipeline",
    cron: "0 6 * * *",  // Every day at 06:00 UTC
    run: async () => {
        const res = await fetch(`${API_URL}/api/trigger/run-daily-pipeline`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${CRON_SECRET}`
            },
        });

        if (!res.ok) {
            throw new Error(`Pipeline failed: ${res.statusText}`);
        }

        return await res.json();
    },
});

// ─── Task 6: Detect Value Bets (CRON 10:00) ───────────────────
export const detectValueBets = schedules.task({
    id: "detect-value-bets",
    cron: "0 10 * * *",  // Every day at 10:00 UTC (after pipeline)
    run: async () => {
        const res = await fetch(`${API_URL}/api/trigger/detect-value-bets`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${CRON_SECRET}`
            },
        });

        if (!res.ok) {
            throw new Error(`Value bet detection failed: ${res.statusText}`);
        }

        return await res.json();
    },
});

// ─── Task 7: Daily Recap (CRON 23:30) ─────────────────────────
export const dailyRecap = schedules.task({
    id: "daily-recap",
    cron: "30 23 * * *",  // Every day at 23:30 UTC
    run: async () => {
        const res = await fetch(`${API_URL}/api/trigger/daily-recap`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${CRON_SECRET}`
            },
        });

        if (!res.ok) {
            throw new Error(`Daily recap failed: ${res.statusText}`);
        }

        return await res.json();
    },
});

// =============================================================================
// NHL TASKS
// =============================================================================

// ─── Task 8: NHL Pipeline (CRON 09:00 UTC = 10h Paris) ────────
export const nhlRunPipeline = schedules.task({
    id: "nhl-run-pipeline",
    cron: "0 9 * * *",  // 09:00 UTC = 10h Paris
    run: async () => {
        const res = await fetch(`${API_URL}/api/trigger/nhl-run-pipeline`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${CRON_SECRET}`
            },
        });

        if (!res.ok) {
            throw new Error(`NHL pipeline failed: ${res.statusText}`);
        }

        return await res.json();
    },
});

// ─── Task 9: NHL Value Bets (CRON 15:00 UTC = 16h Paris) ──────
export const nhlDetectValueBets = schedules.task({
    id: "nhl-detect-value-bets",
    cron: "0 15 * * *",  // 15:00 UTC = 16h Paris
    run: async () => {
        const res = await fetch(`${API_URL}/api/trigger/nhl-value-bets`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${CRON_SECRET}`
            },
        });

        if (!res.ok) {
            throw new Error(`NHL value bets failed: ${res.statusText}`);
        }

        return await res.json();
    },
});

// ─── Task 9: NHL Live Scores (CRON every 2 min, 16h-05h UTC) ──
export const nhlUpdateLiveScores = schedules.task({
    id: "nhl-update-live-scores",
    cron: "*/2 16,17,18,19,20,21,22,23,0,1,2,3,4,5 * * *",  // 17h-06h Paris
    run: async () => {
        const res = await fetch(`${API_URL}/api/trigger/nhl-update-live-scores`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${CRON_SECRET}`
            },
        });

        if (!res.ok) {
            throw new Error(`NHL live scores failed: ${res.statusText}`);
        }

        return await res.json();
    },
});

// ─── Task 10: NHL ML Training Reminder ──────────────────────
export const nhlMlReminder = task({
    id: "nhl-ml-reminder",
    run: async () => {
        // Automatically checkpoint and wait for 14 days
        await wait.for({ days: 14 });

        const res = await fetch(`${API_URL}/api/trigger/nhl-ml-reminder`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${CRON_SECRET}`
            },
        });

        if (!res.ok) {
            throw new Error(`NHL ML reminder failed: ${res.statusText}`);
        }

        return await res.json();
    },
});

