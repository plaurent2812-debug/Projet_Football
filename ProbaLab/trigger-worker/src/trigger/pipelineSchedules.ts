import { schedules } from "@trigger.dev/sdk";

const API_URL = process.env.API_URL || "https://web-production-ff663.up.railway.app";
const CRON_SECRET = process.env.CRON_SECRET || "";

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

async function fetchNHLOdds(date: string, label: string): Promise<object> {
    const res = await fetch(`${API_URL}/api/nhl/fetch-odds`, {
        method: "POST",
        headers: cronHeaders,
        body: JSON.stringify({ date }),
    });

    if (!res.ok) {
        const text = await res.text();
        console.warn(`[${label}] fetch-odds failed (${res.status}): ${text} — continuing anyway`);
        return { ok: false, status: res.status };
    }

    const result = await res.json();
    console.log(`[${label}] fetch-odds result:`, result);
    return result;
}

/**
 * ── NHL Odds Fetch (early) ────────────────────────────────────────
 * Fetches real bookmaker odds at 18:00 UTC (19:00 Paris).
 * Lines for night games often open around 17-18h UTC.
 */
export const scheduleNHLOddsFetch = schedules.task({
    id: "schedule-nhl-odds-fetch",
    cron: "0 18 * * *",   // 18:00 UTC = 19:00 Paris
    retry: standardRetry,
    run: async (payload) => {
        const date = payload.timestamp.toISOString().slice(0, 10);
        console.log(`[NHL Odds] Fetching bookmaker odds for ${date}`);
        return await fetchNHLOdds(date, "NHL Odds Early");
    },
});

/**
 * ── NHL Pipeline ─────────────────────────────────────────────────────
 * Runs at 20:00 UTC (21:00 Paris) every day.
 * Step 1: Fetch real bookmaker odds from The Odds API → nhl_odds table
 * Step 2: Run ML pipeline → nhl_data_lake
 * Results are then available for "Paris du Soir" with real odds + EV.
 */
export const scheduleNHLPipeline = schedules.task({
    id: "schedule-nhl-pipeline",
    cron: "0 20 * * *",   // 20:00 UTC = 21:00 Paris
    retry: standardRetry,
    run: async (payload) => {
        const date = payload.timestamp.toISOString().slice(0, 10);
        console.log(`[NHL Pipeline] Launching for ${date}`);

        // Step 1: Fetch real odds first (non-blocking if it fails)
        await fetchNHLOdds(date, "NHL Pipeline Odds");

        // Step 2: Run ML pipeline
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
