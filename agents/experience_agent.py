"""
ExperienceAnalysisAgent - Extracts and evaluates each professional experience.
"""

import logging
from agents.base_agent import BaseAgent
from models.schemas import ExperienceAnalysisOutput
from prompts.templates import EXPERIENCE_ANALYSIS_PROMPT

logger = logging.getLogger(__name__)


class ExperienceAnalysisAgent(BaseAgent):
    def __init__(self, **kwargs):
        super().__init__(
            name="ExperienceAnalysisAgent",
            role=(
                "Extraire et évaluer chaque expérience professionnelle du CV. "
                "Critères : contexte métier, missions différenciantes, résultats mesurables, "
                "cohérence technique, détection d'erreurs naïves."
            ),
            **kwargs,
        )

    def run(self, cv_experiences: str, cv_full_text: str) -> ExperienceAnalysisOutput:
        """
        Analyze the experience section of a CV.

        Args:
            cv_experiences: Text content of the experiences section.
            cv_full_text: Full CV text for context.

        Returns:
            ExperienceAnalysisOutput: Validated analysis results.
        """
        logger.info(f"[{self.name}] Starting experience analysis...")

        prompt = EXPERIENCE_ANALYSIS_PROMPT.format(
            cv_experiences=cv_experiences,
            cv_full_text=cv_full_text[:8000],  # Limit context to avoid overflow
        )

        result = self._call_llm_with_retry(prompt, ExperienceAnalysisOutput)
        logger.info(
            f"[{self.name}] Analysis complete. "
            f"Found {len(result.experiences)} experiences. "
            f"Global score: {result.score_global_experiences}/10"
        )
        return result
