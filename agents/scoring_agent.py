"""
ScoringAgent - Calculates weighted scores according to the strict formula.
"""

import logging

from agents.base_agent import BaseAgent
from models.schemas import ScoringOutput
from prompts.templates import SCORING_PROMPT

logger = logging.getLogger(__name__)


class ScoringAgent(BaseAgent):
    def __init__(self, **kwargs):
        super().__init__(
            name="ScoringAgent",
            role=(
                "Calculer le score final pondéré du CV selon la formule stricte : "
                "Note/10 = (Exp × 0.5) + (Comp × 0.2) + (Form × 0.1) + (Résumé × 0.2). "
                "Afficher les calculs intermédiaires et valider mathématiquement."
            ),
            **kwargs,
        )

    def run(
        self,
        score_experiences: float,
        score_competences: float,
        score_formations: float,
        score_resume: float,
    ) -> ScoringOutput:
        """
        Calculate the final weighted score.

        Args:
            score_experiences: Experience score /10
            score_competences: Skills score /10
            score_formations: Education score /10
            score_resume: Summary score /10

        Returns:
            ScoringOutput: Validated scoring results.
        """
        logger.info(f"[{self.name}] Calculating scores...")

        prompt = SCORING_PROMPT.format(
            score_experiences=score_experiences,
            score_competences=score_competences,
            score_formations=score_formations,
            score_resume=score_resume,
        )

        result = self._call_llm_with_retry(prompt, ScoringOutput)

        # Double-check the math programmatically
        expected = (
            score_experiences * 0.5
            + score_competences * 0.2
            + score_formations * 0.1
            + score_resume * 0.2
        )
        expected = round(expected, 2)

        if abs(result.note_finale_sur_10 - expected) > 0.1:
            logger.warning(
                f"[{self.name}] Math discrepancy detected! "
                f"LLM: {result.note_finale_sur_10}, Expected: {expected}. Correcting..."
            )
            result.note_finale_sur_10 = expected
            result.note_finale_sur_20 = round(expected * 2, 2)
            result.note_finale_sur_100 = round(expected * 10, 2)
            result.validation_mathematique = True
            result.erreur_calcul = (
                f"Corrigé programmatiquement. LLM avait calculé différemment. "
                f"Valeur correcte : {expected}/10"
            )
            result.calcul_intermediaire = (
                f"({score_experiences} × 0.5) + ({score_competences} × 0.2) + "
                f"({score_formations} × 0.1) + ({score_resume} × 0.2) = {expected}"
            )

        logger.info(
            f"[{self.name}] Final score: {result.note_finale_sur_10}/10 "
            f"({result.note_finale_sur_100}/100)"
        )
        return result
