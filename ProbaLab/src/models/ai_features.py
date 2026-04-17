from pydantic import BaseModel, Field


class AIFeatures(BaseModel):
    """Schéma de validation stricte pour l'extraction de features sportives par l'IA Gemini."""

    motivation_score: float = Field(
        ...,
        ge=-1.0,
        le=1.0,
        description="Niveau de motivation : 1.0 (Titre/CL, Derby intense, Survie décisive) à -1.0 (Rien à jouer, Démobilisation)",
    )
    media_pressure: float = Field(
        ...,
        ge=-1.0,
        le=1.0,
        description="Pression médiatique : 1.0 (Crise majeure, Entraîneur menacé) à -1.0 (Sérénité absolue)",
    )
    injury_tactical_impact: float = Field(
        ...,
        ge=-1.0,
        le=1.0,
        description="Impact tactique des absences : 1.0 (Avantage dom/Désastre ext) à -1.0 (Désastre dom/Avantage ext). 0.0 si équilibré.",
    )
    cohesion_score: float = Field(
        ...,
        ge=-1.0,
        le=1.0,
        description="Cohésion d'équipe : 1.0 (Excellente dynamique de vestiaire) à -1.0 (Rupture totale de vestiaire)",
    )
    style_risk: float = Field(
        ...,
        ge=-1.0,
        le=1.0,
        description="Prise de risque tactique attendue : 1.0 (Ultra offensif, doit absolument marquer) à -1.0 (Ultra défensif, bus devant le but)",
    )

    # Conservation de l'analyse textuelle pour le frontend/audit
    analysis_text: str = Field(
        ..., description="Analyse narrative courte (3-5 phrases) justifiant les scores attribués."
    )
    likely_scorer: str | None = Field(
        default=None, description="Nom du buteur le plus probable selon l'analyse du match."
    )
    likely_scorer_reason: str | None = Field(
        default=None, description="Explication courte justifiant le choix du buteur."
    )
