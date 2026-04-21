// ─────────────────────────────────────────────────────────────────
//  H2-SS1 — CLV pipeline schedules (ajouté 2026-04-21)
//  4 schedules qui appellent les endpoints /api/trigger/clv/* sur
//  le service Railway web (api.probalab.net).
// ─────────────────────────────────────────────────────────────────
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

const cronHeaders: Record<string, string> = {
    "Content-Type": "application/json",
    "Authorization": `Bearer ${CRON_SECRET}`,
};

async function callEndpoint(path: string, label: string): Promise<unknown> {
    const res = await fetch(`${API_URL}${path}`, {
        method: "POST",
        headers: cronHeaders,
        body: JSON.stringify({}),
    });
    if (!res.ok) {
        const text = await res.text();
        throw new Error(`[${label}] ${path} failed (${res.status}): ${text}`);
    }
    const result = await res.json();
    console.log(`[${label}] OK:`, result);
    return result;
}

// 08:00 UTC — snapshot opening odds (matchs J+1 / J)
export const clvOpeningSnapshot = schedules.task({
    id: "clv-opening-snapshot",
    cron: "0 8 * * *",
    retry: standardRetry,
    run: async () => callEndpoint("/api/trigger/clv/opening", "clv-opening"),
});

// 09:00 UTC — CLV daily snapshot pour J-1 (model_health_log)
export const clvDailySnapshot = schedules.task({
    id: "clv-daily-snapshot",
    cron: "0 9 * * *",
    retry: standardRetry,
    run: async () => callEndpoint("/api/trigger/clv/daily-snapshot", "clv-daily"),
});

// 09:30 UTC — feature drift KS test + Telegram alert
export const clvFeatureDrift = schedules.task({
    id: "clv-feature-drift",
    cron: "30 9 * * *",
    retry: standardRetry,
    run: async () => callEndpoint("/api/trigger/clv/drift", "clv-drift"),
});

// Every 15 min — snapshot closing odds pour matchs dont kickoff ∈ [+15, +45]
export const clvClosingTick = schedules.task({
    id: "clv-closing-tick",
    cron: "*/15 * * * *",
    retry: standardRetry,
    run: async () => callEndpoint("/api/trigger/clv/closing-tick", "clv-closing"),
});
