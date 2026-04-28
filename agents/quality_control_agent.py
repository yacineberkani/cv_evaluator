"""
QualityControlAgent - Final quality assessment and verdict.
"""

import json
import logging

from agents.base_agent import BaseAgent
from models.schemas import (
    ExperienceAnalysisOutput,
    QualityControlOutput,
    ScoringOutput,
    SkillsEducationOutput,
    SummaryValidationOutput,
)
from prompts.templates import QUALITY_CONTROL_PROMPT

logger = logging.getLogger(__name__)


class QualityControlAgent(BaseAgent):
    def __init__(self, **kwargs):
        super().__init__(
            name="QualityControlAgent",
            role=(
                "Contrôle qualité final du CV. Vérifie la présence des éléments clés, "
                "évalue l'alignement global et rend un verdict : profil vendeur vs banal."
            ),
            **kwargs,
        )

    def run(
        self,
        experience_analysis: ExperienceAnalysisOutput,
        skills_education: SkillsEducationOutput,
        summary_validation: SummaryValidationOutput,
        scoring: ScoringOutput,
    ) -> QualityControlOutput:
        """
        Perform final quality control assessment.

        Args:
            experience_analysis: Results from ExperienceAnalysisAgent.
            skills_education: Results from SkillsEducationAgent.
            summary_validation: Results from SummaryValidationAgent.
            scoring: Results from ScoringAgent.

        Returns:
            QualityControlOutput: Final verdict and quality assessment.
        """
        logger.info(f"[{self.name}] Starting quality control...")

        def truncated_json(obj, max_len=4000):
            s = json.dumps(obj.model_dump(), ensure_ascii=False, indent=2)
            return s[:max_len] if len(s) > max_len else s

        prompt = QUALITY_CONTROL_PROMPT.format(
            experience_analysis=truncated_json(experience_analysis),
            skills_education=truncated_json(skills_education),
            summary_validation=truncated_json(summary_validation),
            scoring=truncated_json(scoring),
        )

        result = self._call_llm_with_retry(prompt, QualityControlOutput)
        logger.info(
            f"[{self.name}] Quality control complete. "
            f"Verdict: {result.verdict}, "
            f"Recommendation: {result.recommandation}"
        )
        return result
