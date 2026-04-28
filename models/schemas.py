"""
Pydantic schemas for strict JSON validation across all agents.
Each model enforces deterministic, structured output.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# ─────────────────────────────────────────────
# ExperienceAnalysisAgent models
# ─────────────────────────────────────────────


class ExperienceEntry(BaseModel):
    poste: str = Field(..., description="Intitulé du poste")
    entreprise: str = Field(..., description="Nom de l'entreprise")
    periode: str = Field(..., description="Période (ex: Jan 2020 - Dec 2022)")
    duree_estimee: str | None = Field(None, description="Durée estimée")
    contexte_metier: str = Field(..., description="Contexte métier décrit ou inféré")
    missions: list[str] = Field(default_factory=list, description="Liste des missions")
    missions_differenciantes: list[str] = Field(
        default_factory=list, description="Missions qui se démarquent"
    )
    resultats_mesurables: list[str] = Field(
        default_factory=list, description="Résultats chiffrés/mesurables"
    )
    coherence_technique: str = Field(
        ..., description="Évaluation de la cohérence technique"
    )
    erreurs_naives: list[str] = Field(
        default_factory=list, description="Erreurs naïves détectées"
    )
    score: float = Field(
        ..., ge=0, le=10, description="Score /10 pour cette expérience"
    )
    justification_score: str = Field(..., description="Justification du score attribué")


class ExperienceAnalysisOutput(BaseModel):
    experiences: list[ExperienceEntry] = Field(default_factory=list)
    score_global_experiences: float = Field(..., ge=0, le=10)
    synthese: str = Field(..., description="Synthèse globale des expériences")
    points_forts: list[str] = Field(default_factory=list)
    points_faibles: list[str] = Field(default_factory=list)
    donnees_manquantes: list[str] = Field(
        default_factory=list, description="Informations critiques absentes"
    )


# ─────────────────────────────────────────────
# SkillsEducationAgent models
# ─────────────────────────────────────────────


class CompetenceEntry(BaseModel):
    nom: str = Field(..., description="Nom de la compétence")
    categorie: str = Field(
        ..., description="Catégorie (technique, soft skill, métier...)"
    )
    demontree_dans_experience: bool = Field(
        ..., description="Si la compétence est démontrée dans les expériences"
    )
    experience_associee: str | None = Field(
        None, description="Expérience où elle est démontrée"
    )
    niveau_estime: str | None = Field(None, description="Niveau estimé si mentionné")


class FormationEntry(BaseModel):
    diplome: str = Field(..., description="Intitulé du diplôme")
    etablissement: str = Field(..., description="Établissement")
    annee: str | None = Field(None, description="Année d'obtention")
    coherence_parcours: str = Field(
        ..., description="Cohérence avec le parcours professionnel"
    )


class SkillsEducationOutput(BaseModel):
    competences: list[CompetenceEntry] = Field(default_factory=list)
    formations: list[FormationEntry] = Field(default_factory=list)
    score_competences: float = Field(..., ge=0, le=10)
    score_formations: float = Field(..., ge=0, le=10)
    competences_non_demontrees: list[str] = Field(default_factory=list)
    coherence_formation_parcours: str = Field(...)
    points_forts: list[str] = Field(default_factory=list)
    points_faibles: list[str] = Field(default_factory=list)
    donnees_manquantes: list[str] = Field(default_factory=list)


# ─────────────────────────────────────────────
# SummaryValidationAgent models
# ─────────────────────────────────────────────


class AffirmationCheck(BaseModel):
    affirmation: str = Field(..., description="Affirmation extraite du résumé")
    prouvee: bool = Field(
        ..., description="Si l'affirmation est prouvée par les expériences"
    )
    preuve: str | None = Field(None, description="Preuve trouvée dans les expériences")
    commentaire: str = Field(..., description="Commentaire sur la validation")


class SummaryValidationOutput(BaseModel):
    affirmations_analysees: list[AffirmationCheck] = Field(default_factory=list)
    score_resume: float = Field(..., ge=0, le=10)
    taux_affirmations_prouvees: float = Field(
        ..., ge=0, le=100, description="Pourcentage d'affirmations prouvées"
    )
    ecarts_alignement: list[str] = Field(
        default_factory=list, description="Écarts entre positionnement et réalité"
    )
    positionnement_declare: str = Field(
        ..., description="Positionnement déclaré dans le résumé"
    )
    positionnement_reel: str = Field(
        ..., description="Positionnement réel basé sur les expériences"
    )
    synthese: str = Field(...)
    donnees_manquantes: list[str] = Field(default_factory=list)


# ─────────────────────────────────────────────
# ScoringAgent models
# ─────────────────────────────────────────────


class ScoreDetail(BaseModel):
    critere: str = Field(...)
    score_brut: float = Field(..., ge=0, le=10)
    poids: float = Field(..., ge=0, le=1)
    score_pondere: float = Field(..., ge=0, le=10)
    justification: str = Field(...)


class ScoringOutput(BaseModel):
    details: list[ScoreDetail] = Field(...)
    note_finale_sur_10: float = Field(..., ge=0, le=10)
    note_finale_sur_20: float = Field(..., ge=0, le=20)
    note_finale_sur_100: float = Field(..., ge=0, le=100)
    calcul_intermediaire: str = Field(..., description="Détail du calcul mathématique")
    validation_mathematique: bool = Field(
        ..., description="True si le calcul est cohérent"
    )
    erreur_calcul: str | None = Field(
        None, description="Description de l'erreur si incohérence"
    )


# ─────────────────────────────────────────────
# QualityControlAgent models
# ─────────────────────────────────────────────


class QualityCheckItem(BaseModel):
    element: str = Field(...)
    present: bool = Field(...)
    qualite: Literal["excellent", "bon", "moyen", "faible", "absent"] = Field(...)
    commentaire: str = Field(...)


class QualityControlOutput(BaseModel):
    elements_verifies: list[QualityCheckItem] = Field(default_factory=list)
    alignement_global: str = Field(
        ..., description="Évaluation de l'alignement compétences ↔ expériences ↔ résumé"
    )
    score_alignement: float = Field(..., ge=0, le=10)
    verdict: Literal["profil_vendeur", "profil_banal", "profil_intermediaire"] = Field(
        ...
    )
    justification_verdict: str = Field(...)
    recommandation: Literal["Oui", "Non", "Peut-être"] = Field(...)
    justification_recommandation: str = Field(...)
    forces: list[str] = Field(default_factory=list)
    faiblesses: list[str] = Field(default_factory=list)


# ─────────────────────────────────────────────
# TableGeneratorAgent models
# ─────────────────────────────────────────────


class TableCell(BaseModel):
    emoji: Literal["✅", "⚠️", "❌"] = Field(...)
    justification: str = Field(..., max_length=200)


class TableRow(BaseModel):
    element: str = Field(
        ..., description="Nom de l'élément évalué (expérience, compétences, etc.)"
    )
    clarte: TableCell = Field(...)
    coherence: TableCell = Field(...)
    qualite_redactionnelle: TableCell = Field(...)
    pertinence: TableCell = Field(...)
    respect_regles: TableCell = Field(...)
    erreurs_naives: TableCell = Field(...)


class TableGeneratorOutput(BaseModel):
    lignes: list[TableRow] = Field(default_factory=list)
    resume_tableau: str = Field(..., description="Résumé textuel du tableau")


# ─────────────────────────────────────────────
# Final Report model
# ─────────────────────────────────────────────


class FinalReport(BaseModel):
    experience_analysis: ExperienceAnalysisOutput = Field(...)
    skills_education: SkillsEducationOutput = Field(...)
    summary_validation: SummaryValidationOutput = Field(...)
    scoring: ScoringOutput = Field(...)
    quality_control: QualityControlOutput = Field(...)
    evaluation_table: TableGeneratorOutput = Field(...)
    metadata: dict = Field(
        default_factory=dict, description="Métadonnées (date, modèle, version...)"
    )
