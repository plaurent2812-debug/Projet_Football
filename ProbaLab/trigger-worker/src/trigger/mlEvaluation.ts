import { schedules } from "@trigger.dev/sdk/v3";

export const mlEvaluationTask = schedules.task({
    id: "ml-evaluation-daily",
    cron: "0 4 * * *", // Run every day at 04:00 AM UTC
    run: async (payload) => {
        console.log(`[ML Evaluation] Starting daily evaluation run at ${payload.timestamp}`);

        const API_URL = process.env.NEXT_PUBLIC_API_URL || "https://api.probalab.fr";
        const CRON_SECRET = process.env.CRON_SECRET;

        if (!CRON_SECRET) {
            throw new Error("Missing CRON_SECRET environment variable");
        }

        const response = await fetch(`${API_URL}/api/trigger/evaluate-performance`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${CRON_SECRET}`,
            },
        });

        if (!response.ok) {
            const text = await response.text();
            throw new Error(`API returned ${response.status}: ${text}`);
        }

        const evalData = await response.json();
        console.log("[ML Evaluation] Success:", evalData);

        // Retrain consolidé dans mlTraining.ts (vendredi 02:00 UTC)

        return {
            success: true,
            evaluatedAt: new Date().toISOString(),
            evalApiResponse: evalData,
        };
    },
});
