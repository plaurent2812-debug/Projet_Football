import { task, wait, schedules } from "@trigger.dev/sdk/v3";

const API_URL = process.env.API_URL || "https://probalab.railway.app";

export const monitorHalftime = task({
    id: "monitor-halftime",
    run: async (payload: { fixture_id: string; start_date: string }) => {
        const startTime = new Date(payload.start_date);

        // Wait until 48 minutes after kickoff
        const halftimeTime = new Date(startTime.getTime() + 48 * 60 * 1000);

        await wait.until({ date: halftimeTime });

        // Wake up and call Python backend
        const res = await fetch(`${API_URL}/api/trigger/analyze-halftime`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ fixture_id: payload.fixture_id }),
        });

        if (!res.ok) {
            throw new Error(`Analyze halftime failed: ${res.statusText}`);
        }

        const data = await res.json();
        return data;
    },
});

export const scheduleDailyMatches = schedules.task({
    id: "schedule-daily-matches",
    cron: "0 8 * * *", // Every day at 8:00 AM
    run: async () => {
        // 1. Fetch matches of the day
        const res = await fetch(`${API_URL}/api/trigger/daily-matches`);
        if (!res.ok) {
            throw new Error(`Failed to fetch daily matches: ${res.statusText}`);
        }
        const data = await res.json();
        const matches = data.matches || [];

        // 2. Schedule monitorHalftime for each
        const triggerPromises = matches.map((match: any) =>
            monitorHalftime.trigger({
                fixture_id: match.id,
                start_date: match.date,
            })
        );

        await Promise.all(triggerPromises);

        return { scheduled: matches.length };
    },
});
