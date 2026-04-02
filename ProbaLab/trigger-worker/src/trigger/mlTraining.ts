import { schedules } from "@trigger.dev/sdk/v3";

export const retrainMetaModelTask = schedules.task({
    id: "retrain-xgboost-meta-model",
    // S'exécute tous les vendredis à 02:00 UTC (avant le grand week-end de foot)
    cron: "0 2 * * 5",
    run: async (payload) => {
        console.log(`🚀 Déclenchement de l'entraînement XGBoost Méta-Modèle à ${payload.timestamp}`);

        const API_URL = process.env.API_URL || "http://localhost:8000";
        const CRON_SECRET = process.env.CRON_SECRET || "";

        try {
            // 1. Football Meta-Model Retrain
            const response = await fetch(`${API_URL}/api/trigger/retrain-meta-model`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${CRON_SECRET}`,
                },
            });

            if (!response.ok) {
                const errorText = await response.text();
                console.error(`❌ Football retrain error (${response.status}): ${errorText}`);
            } else {
                console.log("✅ Football Meta-Model retrained:", await response.json());
            }

            // 2. NHL Match-Level ML Retrain
            console.log("🏒🧠 Déclenchement du retrain NHL Match ML...");
            const nhlResponse = await fetch(`${API_URL}/api/trigger/nhl-retrain-model`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${CRON_SECRET}`,
                },
            });

            if (!nhlResponse.ok) {
                const errorText = await nhlResponse.text();
                console.error(`❌ NHL retrain error (${nhlResponse.status}): ${errorText}`);
            } else {
                console.log("✅ NHL Match ML retrained:", await nhlResponse.json());
            }

            return {
                success: true,
                message: "Both Football and NHL models retrained",
            };

        } catch (error: any) {
            console.error("❌ Echec de la tâche d'entraînement:", error.message);
            throw error;
        }
    },
});
