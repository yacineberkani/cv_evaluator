"""
SkillsEducationAgent - Evaluates skills and education sections.
"""

import json
import logging
from agents.base_agent import BaseAgent
from models.schemas import SkillsEducationOutput, ExperienceAnalysisOutput
from prompts.templates import SKILLS_EDUCATION_PROMPT

logger = logging.getLogger(__name__)


class SkillsEducationAgent(BaseAgent):
    def __init__(self, **kwargs):
        super().__init__(
            name="SkillsEducationAgent",
            role=(
                "Évaluer les compétences et formations du CV. "
                "Critères : clarté, structuration, correspondance compétences ↔ expériences, "
                "détection des compétences non démontrées, cohérence formation ↔ parcours."
            ),
            **kwargs,
        )

    def run(
        self,
        cv_competences: str,
        cv_formations: str,
        experience_analysis: ExperienceAnalysisOutput,
    ) -> SkillsEducationOutput:
        """
        Analyze skills and education sections.

        Args:
            cv_competences: Text of the skills section.
            cv_formations: Text of the education section.
            experience_analysis: Results from ExperienceAnalysisAgent for cross-checking.

        Returns:
            SkillsEducationOutput: Validated analysis results.
        """
        logger.info(f"[{self.name}] Starting skills & education analysis...")

        # Serialize experience analysis for context
        exp_json = json.dumps(
            experience_analysis.model_dump(),
            ensure_ascii=False,
            indent=2,
        )

        prompt = SKILLS_EDUCATION_PROMPT.format(
            cv_competences=cv_competences,
            cv_formations=cv_formations,
            experience_analysis=exp_json[:6000],
        )

        result = self._call_llm_with_retry(prompt, SkillsEducationOutput)
        logger.info(
            f"[{self.name}] Analysis complete. "
            f"Skills score: {result.score_competences}/10, "
            f"Education score: {result.score_formations}/10"
        )
        return result
