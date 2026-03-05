import { schedules } from "@trigger.dev/sdk/v3";

export const retrainMetaModelTask = schedules.task({
    id: "retrain-xgboost-meta-model",
    // S'exécute tous les vendredis à 02:00 UTC (avant le grand week-end de foot)
    cron: "0 2 * * 5",
    run: async (payload) => {
        console.log(`🚀 Déclenchement de l'entraînement XGBoost Méta-Modèle à ${payload.timestamp}`);

        const API_URL = process.env.API_URL || "http://localhost:8000";
        const CRON_SECRET = process.env.CRON_SECRET || "super_secret_probalab_2026";

        try {
            const response = await fetch(`${API_URL}/api/trigger/retrain-meta-model`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${CRON_SECRET}`,
                },
            });

            if (!response.ok) {
                const errorText = await response.text();
                console.error(`❌ Erreur API (${response.status}): ${errorText}`);
                throw new Error(`API returned status ${response.status}`);
            }

            const result = await response.json();
            console.log("✅ Entraînement réussi:", result);

            return {
                success: true,
                message: "Meta-Model successfully retrained",
                details: result
            };

        } catch (error: any) {
            console.error("❌ Echec de la tâche d'entraînement:", error.message);
            throw error;
        }
    },
});
