import { schedules, wait } from "@trigger.dev/sdk/v3";

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

        try {
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

            // ML Retrain (Runs Weekly on Saturdays at 05:00 UTC)
            // By putting it here we save 1 cron schedule
            const now = new Date();
            if (now.getUTCDay() === 6) { // 6 = Saturday
                console.log("[MLOps] Starting weekly continuous training round");
                
                await wait.for({ minutes: 60 }); // Wait until 05:00 UTC
                
                const trainResponse = await fetch(`${API_URL}/api/trigger/retrain-models`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "Authorization": `Bearer ${CRON_SECRET}`,
                    },
                });

                if (!trainResponse.ok) {
                    console.error(`API returned ${trainResponse.status} for retrain`);
                } else {
                    console.log("[MLOps] Success:", await trainResponse.json());
                }
            }

            return {
                success: true,
                evaluatedAt: new Date().toISOString(),
                evalApiResponse: evalData,
            };
        } catch (error) {
            console.error("[ML Evaluation] Failed to run evaluate-performance:", error);
            throw error;
        }
    },
});
