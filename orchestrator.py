"""
Orchestrator - Multi-agent pipeline for CV evaluation.
Manages the execution flow, caching, and parallel processing where possible.

Architecture:
    Phase 1 (independent):   ExperienceAnalysisAgent
    Phase 2 (depends on 1):  SkillsEducationAgent + SummaryValidationAgent  (parallel)
    Phase 3 (depends on 1+2): ScoringAgent
    Phase 4 (depends on all): QualityControlAgent + TableGeneratorAgent  (parallel)
"""

import json
import logging
import time
from datetime import datetime, timezone
from typing import Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

from models.schemas import (
    ExperienceAnalysisOutput,
    SkillsEducationOutput,
    SummaryValidationOutput,
    ScoringOutput,
    QualityControlOutput,
    TableGeneratorOutput,
    FinalReport,
)
from agents import (
    ExperienceAnalysisAgent,
    SkillsEducationAgent,
    SummaryValidationAgent,
    ScoringAgent,
    QualityControlAgent,
    TableGeneratorAgent,
)
from utils.chunking import chunk_cv_by_sections, get_section_or_full
from utils.cache import ResultCache

logger = logging.getLogger(__name__)


# Models that belong to OpenAI — everything else is treated as Gemini
GEMINI_MODEL_PREFIXES = ("gemini-2.5-flash-lite", "gemini-2.5-flash", "gemini-2.5-pro")


def detect_provider(model_name: str) -> str:
    """Infer the provider from the model name."""
    model_lower = model_name.lower()
    if any(model_lower.startswith(p) for p in GEMINI_MODEL_PREFIXES):
        return "gemini"
    return "openai"


class CVEvaluationOrchestrator:
    """Orchestrates the multi-agent CV evaluation pipeline."""

    def __init__(
        self,
        api_key: str,
        model_name: str = "gemini-1.5-flash",
        cache_dir: Optional[str] = None,
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ):
        self.api_key = api_key
        self.model_name = model_name
        self.provider = detect_provider(model_name)
        self.cache = ResultCache(cache_dir=cache_dir)
        self.progress_callback = progress_callback or (lambda msg, pct: None)

        logger.info(f"[Orchestrator] Provider detected: '{self.provider}' for model '{model_name}'")

        # ✅ provider is now passed to every agent
        agent_kwargs = {
            "api_key": api_key,
            "model_name": model_name,
            "provider": self.provider,
        }
        self.experience_agent = ExperienceAnalysisAgent(**agent_kwargs)
        self.skills_education_agent = SkillsEducationAgent(**agent_kwargs)
        self.summary_validation_agent = SummaryValidationAgent(**agent_kwargs)
        self.scoring_agent = ScoringAgent(**agent_kwargs)
        self.quality_control_agent = QualityControlAgent(**agent_kwargs)
        self.table_generator_agent = TableGeneratorAgent(**agent_kwargs)

    def _update_progress(self, message: str, percentage: float):
        """Send progress update."""
        self.progress_callback(message, percentage)
        logger.info(f"[Orchestrator] {percentage:.0%} - {message}")

    def evaluate(self, cv_text: str) -> FinalReport:
        """
        Run the complete CV evaluation pipeline.

        Args:
            cv_text: Full text extracted from the CV PDF.

        Returns:
            FinalReport: Complete evaluation report.
        """
        start_time = time.time()
        self._update_progress("📄 Découpage sémantique du CV...", 0.05)

        # ── Phase 0: Semantic chunking ──
        sections = chunk_cv_by_sections(cv_text)
        cv_experiences = get_section_or_full(sections, "experiences")
        cv_competences = get_section_or_full(sections, "competences")
        cv_formations = get_section_or_full(sections, "formations")
        cv_resume = get_section_or_full(sections, "resume")
        cv_full = get_section_or_full(sections, "full_text")

        logger.info(
            f"[Orchestrator] Sections detected: {[k for k in sections.keys() if k != 'full_text']}"
        )

        # ── Phase 1: Experience Analysis (independent) ──
        self._update_progress("🔍 Agent 1/6 : Analyse des expériences...", 0.10)
        experience_result = self.experience_agent.run(
            cv_experiences=cv_experiences,
            cv_full_text=cv_full,
        )
        self.cache.set("experience", cv_text, experience_result.model_dump())

        # ── Phase 2: Skills/Education + Summary Validation (parallel, depend on Phase 1) ──
        self._update_progress(
            "🎯 Agents 2-3/6 : Compétences, formations et validation du résumé (parallèle)...",
            0.30,
        )

        skills_result: Optional[SkillsEducationOutput] = None
        summary_result: Optional[SummaryValidationOutput] = None

        with ThreadPoolExecutor(max_workers=2) as executor:
            future_skills = executor.submit(
                self.skills_education_agent.run,
                cv_competences=cv_competences,
                cv_formations=cv_formations,
                experience_analysis=experience_result,
            )
            future_summary = executor.submit(
                self.summary_validation_agent.run,
                cv_resume=cv_resume,
                experience_analysis=experience_result,
            )

            for future in as_completed([future_skills, future_summary]):
                if future == future_skills:
                    skills_result = future.result()
                    self.cache.set("skills", cv_text, skills_result.model_dump())
                    self._update_progress("✅ Compétences & formations analysées", 0.45)
                else:
                    summary_result = future.result()
                    self.cache.set("summary", cv_text, summary_result.model_dump())
                    self._update_progress("✅ Résumé validé", 0.50)

        # ── Phase 3: Scoring (depends on Phase 1 + 2) ──
        self._update_progress("📊 Agent 4/6 : Calcul des scores...", 0.60)
        scoring_result = self.scoring_agent.run(
            score_experiences=experience_result.score_global_experiences,
            score_competences=skills_result.score_competences,
            score_formations=skills_result.score_formations,
            score_resume=summary_result.score_resume,
        )
        self.cache.set("scoring", cv_text, scoring_result.model_dump())

        # ── Phase 4: Quality Control + Table Generation (parallel, depend on all previous) ──
        self._update_progress(
            "🏁 Agents 5-6/6 : Contrôle qualité et tableau d'évaluation (parallèle)...",
            0.75,
        )

        quality_result: Optional[QualityControlOutput] = None
        table_result: Optional[TableGeneratorOutput] = None

        with ThreadPoolExecutor(max_workers=2) as executor:
            future_quality = executor.submit(
                self.quality_control_agent.run,
                experience_analysis=experience_result,
                skills_education=skills_result,
                summary_validation=summary_result,
                scoring=scoring_result,
            )
            future_table = executor.submit(
                self.table_generator_agent.run,
                experience_analysis=experience_result,
                skills_education=skills_result,
                summary_validation=summary_result,
            )

            for future in as_completed([future_quality, future_table]):
                if future == future_quality:
                    quality_result = future.result()
                    self.cache.set("quality", cv_text, quality_result.model_dump())
                    self._update_progress("✅ Contrôle qualité terminé", 0.88)
                else:
                    table_result = future.result()
                    self.cache.set("table", cv_text, table_result.model_dump())
                    self._update_progress("✅ Tableau d'évaluation généré", 0.92)

        # ── Phase 5: Assemble final report ──
        self._update_progress("📋 Assemblage du rapport final...", 0.95)

        elapsed = round(time.time() - start_time, 2)

        report = FinalReport(
            experience_analysis=experience_result,
            skills_education=skills_result,
            summary_validation=summary_result,
            scoring=scoring_result,
            quality_control=quality_result,
            evaluation_table=table_result,
            metadata={
                "date_evaluation": datetime.now(timezone.utc).isoformat(),
                "modele_llm": self.model_name,
                "temperature": 0,
                "duree_evaluation_secondes": elapsed,
                "version": "1.0.0",
                "sections_detectees": [k for k in sections.keys() if k != "full_text"],
            },
        )

        self._update_progress("✅ Évaluation terminée !", 1.0)
        logger.info(f"[Orchestrator] Evaluation complete in {elapsed}s")

        return report
