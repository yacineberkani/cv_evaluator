"""
SummaryValidationAgent - Validates resume/profile claims against experience evidence.
"""

import json
import logging
from agents.base_agent import BaseAgent
from models.schemas import SummaryValidationOutput, ExperienceAnalysisOutput
from prompts.templates import SUMMARY_VALIDATION_PROMPT

logger = logging.getLogger(__name__)


class SummaryValidationAgent(BaseAgent):
    def __init__(self, **kwargs):
        super().__init__(
            name="SummaryValidationAgent",
            role=(
                "Valider le résumé/profil du CV en confrontant chaque affirmation "
                "aux preuves trouvées dans les expériences. Distinguer les affirmations "
                "prouvées des déclaratives non étayées."
            ),
            **kwargs,
        )

    def run(
        self,
        cv_resume: str,
        experience_analysis: ExperienceAnalysisOutput,
    ) -> SummaryValidationOutput:
        """
        Validate the summary/profile section against experience analysis.

        Args:
            cv_resume: Text of the summary/profile section.
            experience_analysis: Results from ExperienceAnalysisAgent.

        Returns:
            SummaryValidationOutput: Validated analysis results.
        """
        logger.info(f"[{self.name}] Starting summary validation...")

        exp_json = json.dumps(
            experience_analysis.model_dump(),
            ensure_ascii=False,
            indent=2,
        )

        prompt = SUMMARY_VALIDATION_PROMPT.format(
            cv_resume=cv_resume,
            experience_analysis=exp_json[:6000],
        )

        result = self._call_llm_with_retry(prompt, SummaryValidationOutput)
        logger.info(
            f"[{self.name}] Validation complete. "
            f"Resume score: {result.score_resume}/10, "
            f"Claims proven: {result.taux_affirmations_prouvees}%"
        )
        return result
