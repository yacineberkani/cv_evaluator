"""
TableGeneratorAgent - Generates structured evaluation table.
"""

import json
import logging

from agents.base_agent import BaseAgent
from models.schemas import (
    ExperienceAnalysisOutput,
    SkillsEducationOutput,
    SummaryValidationOutput,
    TableGeneratorOutput,
)
from prompts.templates import TABLE_GENERATOR_PROMPT

logger = logging.getLogger(__name__)


class TableGeneratorAgent(BaseAgent):
    def __init__(self, **kwargs):
        super().__init__(
            name="TableGeneratorAgent",
            role=(
                "Générer un tableau d'évaluation structuré avec emojis et justifications "
                "pour chaque section du CV."
            ),
            **kwargs,
        )

    def run(
        self,
        experience_analysis: ExperienceAnalysisOutput,
        skills_education: SkillsEducationOutput,
        summary_validation: SummaryValidationOutput,
    ) -> TableGeneratorOutput:
        """
        Generate structured evaluation table.

        Args:
            experience_analysis: Results from ExperienceAnalysisAgent.
            skills_education: Results from SkillsEducationAgent.
            summary_validation: Results from SummaryValidationAgent.

        Returns:
            TableGeneratorOutput: Structured evaluation table.
        """
        logger.info(f"[{self.name}] Generating evaluation table...")

        def truncated_json(obj, max_len=4000):
            s = json.dumps(obj.model_dump(), ensure_ascii=False, indent=2)
            return s[:max_len] if len(s) > max_len else s

        prompt = TABLE_GENERATOR_PROMPT.format(
            experience_analysis=truncated_json(experience_analysis),
            skills_education=truncated_json(skills_education),
            summary_validation=truncated_json(summary_validation),
        )

        result = self._call_llm_with_retry(prompt, TableGeneratorOutput)
        logger.info(f"[{self.name}] Table generated with {len(result.lignes)} rows.")
        return result
