"""
Base agent class for all CV evaluation agents.
Provides common LangChain + OpenAI integration with JSON parsing and retry logic.
"""

import json
import re
import os
import logging
from typing import Any, Dict, Optional, Type, TypeVar
from pydantic import BaseModel, ValidationError
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class BaseAgent:
    """Base class for all CV evaluation agents."""

    def __init__(
        self,
        name: str,
        role: str,
        model_name: Optional[str] = None,
        temperature: float = 0,
        api_key: Optional[str] = None,
    ):
        self.name = name
        self.role = role
        self.model_name = model_name or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.temperature = temperature
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")

        if not self.api_key:
            raise ValueError(
                "OPENAI_API_KEY not found. Set it in .env or pass it directly."
            )

        self.llm = ChatOpenAI(
            model=self.model_name,
            api_key=self.api_key,
            temperature=self.temperature,
        )

    def _extract_json_from_response(self, text: str) -> str:
        """Extract JSON from LLM response, handling markdown code blocks."""
        # Try to find JSON in code blocks
        patterns = [
            r"```json\s*([\s\S]*?)```",
            r"```\s*([\s\S]*?)```",
            r"(\{[\s\S]*\})",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                candidate = match.group(1).strip()
                try:
                    json.loads(candidate)
                    return candidate
                except json.JSONDecodeError:
                    continue

        # If no pattern worked, try the raw text
        return text.strip()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((json.JSONDecodeError, ValidationError)),
        reraise=True,
    )
    def _call_llm_with_retry(self, prompt: str, output_model: Type[T]) -> T:
        """Call LLM with retry logic for JSON parsing failures."""
        logger.info(f"[{self.name}] Calling OpenAI...")

        # On peut utiliser SystemMessage pour le rôle, mais ici on garde HumanMessage
        # pour rester compatible avec les prompts existants (qui étaient conçus pour Gemini).
        # Si tu préfères utiliser SystemMessage, il faudra ajuster les prompts.
        response = self.llm.invoke([HumanMessage(content=prompt)])
        raw_text = response.content

        logger.debug(f"[{self.name}] Raw response length: {len(raw_text)}")

        # Extract JSON
        json_str = self._extract_json_from_response(raw_text)

        # Parse JSON
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.warning(f"[{self.name}] JSON parse error: {e}. Retrying with fix prompt...")
            # Retry with a fix prompt
            fix_prompt = (
                f"Le texte suivant devait être un JSON valide mais contient des erreurs. "
                f"Corrige-le et renvoie UNIQUEMENT le JSON valide :\n\n{json_str}"
            )
            response = self.llm.invoke([HumanMessage(content=fix_prompt)])
            json_str = self._extract_json_from_response(response.content)
            data = json.loads(json_str)

        # Validate with Pydantic
        result = output_model.model_validate(data)
        logger.info(f"[{self.name}] Successfully parsed and validated output.")
        return result

    def run(self, **kwargs) -> Any:
        """Override in subclasses."""
        raise NotImplementedError("Subclasses must implement run()")
