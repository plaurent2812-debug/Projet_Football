import { schedules } from "@trigger.dev/sdk";

const API_URL = process.env.API_URL || "https://web-production-ff663.up.railway.app";
const CRON_SECRET = process.env.CRON_SECRET || "super_secret_probalab_2026";

const standardRetry = {
    maxAttempts: 3,
    factor: 1.5,
    minTimeoutInMs: 3000,
    maxTimeoutInMs: 60000,
    randomize: true,
};

const cronHeaders = {
    "Content-Type": "application/json",
    "Authorization": `Bearer ${CRON_SECRET}`,
};

async function runPipeline(mode: string, label: string): Promise<object> {
    const res = await fetch(`${API_URL}/api/cron/run-pipeline`, {
        method: "POST",
        headers: cronHeaders,
        body: JSON.stringify({ mode }),
    });

    if (!res.ok) {
        const text = await res.text();
        throw new Error(`[${label}] Pipeline '${mode}' failed (${res.status}): ${text}`);
    }

    const result = await res.json();
    console.log(`[${label}] Pipeline '${mode}' started:`, result);
    return result;
}

/**
 * ── NHL Pipeline ─────────────────────────────────────────────────────
 * Runs at 21:00 Paris (20:00 UTC) every day.
 * Fetches upcoming game data, runs ML predictions, writes to nhl_data_lake.
 * Results are then available for "Paris du Soir" at midnight.
 */
export const scheduleNHLPipeline = schedules.task({
    id: "schedule-nhl-pipeline",
    cron: "0 20 * * *",   // 20:00 UTC = 21:00 Paris
    retry: standardRetry,
    run: async (payload) => {
        const date = payload.timestamp.toISOString().slice(0, 10);
        console.log(`[NHL Pipeline] Launching for ${date}`);
        return await runPipeline("nhl", "NHL Pipeline");
    },
});

/**
 * ── Football Pipeline — Data Fetch ──────────────────────────────────
 * Runs at 08:00 Paris (07:00 UTC) every day.
 * Pulls latest fixture data, odds, and team stats from API-Football.
 */
export const scheduleFootballData = schedules.task({
    id: "schedule-football-data",
    cron: "0 7 * * *",   // 07:00 UTC = 08:00 Paris
    retry: standardRetry,
    run: async (payload) => {
        const date = payload.timestamp.toISOString().slice(0, 10);
        console.log(`[Football Data] Fetching data for ${date}`);
        return await runPipeline("data", "Football Data");
    },
});

/**
 * ── Football Pipeline — Analysis ────────────────────────────────────
 * Runs at 13:00 Paris (12:00 UTC) every day.
 * Runs AI analysis and predictions so Paris du Soir is ready by 15:00.
 */
export const scheduleFootballAnalysis = schedules.task({
    id: "schedule-football-analysis",
    cron: "0 12 * * *",   // 12:00 UTC = 13:00 Paris
    retry: standardRetry,
    run: async (payload) => {
        const date = payload.timestamp.toISOString().slice(0, 10);
        console.log(`[Football Analysis] Running analysis for ${date}`);
        return await runPipeline("analyze", "Football Analysis");
    },
});
