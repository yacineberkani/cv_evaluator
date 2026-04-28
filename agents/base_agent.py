"""
Base agent class for all CV evaluation agents.
Supports multiple LLM providers: OpenAI (ChatGPT), Google (Gemini) via LangChain.
"""

import json
import re
import os
import logging
from typing import Any, Dict, Optional, Type, TypeVar, Literal
from pydantic import BaseModel, ValidationError
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.language_models.chat_models import BaseChatModel
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, retry_if_exception
import requests

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

# Supported provider types
ProviderType = Literal["gemini", "openai", "ollama"]


def create_llm(
    provider: ProviderType,
    model_name: Optional[str],
    temperature: float,
    api_key: Optional[str],
) -> BaseChatModel:
    """Factory function to instantiate the correct LangChain LLM based on provider."""

    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        resolved_key = api_key or os.getenv("GOOGLE_API_KEY", "")
        resolved_model = model_name or os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

        if not resolved_key:
            raise ValueError("GOOGLE_API_KEY not found. Set it in .env or pass it directly.")

        return ChatGoogleGenerativeAI(
            model=resolved_model,
            google_api_key=resolved_key,
            temperature=temperature,
            convert_system_message_to_human=True,  # Gemini doesn't support SystemMessage natively
        )

    elif provider == "openai":
        from langchain_openai import ChatOpenAI

        resolved_key = api_key or os.getenv("OPENAI_API_KEY", "")
        resolved_model = model_name or os.getenv("OPENAI_MODEL", "gpt-4o-mini")

        if not resolved_key:
            raise ValueError("OPENAI_API_KEY not found. Set it in .env or pass it directly.")

        return ChatOpenAI(
            model=resolved_model,
            openai_api_key=resolved_key,
            temperature=temperature,
            request_timeout=60,  # 60s timeout
            max_retries=2,
        )

    elif provider == "ollama":
        from langchain_openai import ChatOpenAI

        # Ollama Cloud API configuration
        resolved_key = api_key or os.getenv("OLLAMA_API_KEY")
        resolved_model = model_name or os.getenv("OLLAMA_MODEL", "glm-5.1:cloud")

        if not resolved_key:
            raise ValueError("OLLAMA_API_KEY not found. Set it in .env or pass it directly.")

        return ChatOpenAI(
            model=resolved_model,
            base_url="https://ollama.com/v1",
            openai_api_key=resolved_key,
            temperature=temperature,
            request_timeout=120,  # 120s timeout for Ollama Cloud
            max_retries=2,
        )

    else:
        raise ValueError(f"Unsupported provider: '{provider}'. Choose 'gemini', 'openai', or 'ollama'.")


class BaseAgent:
    """
    Base class for all CV evaluation agents.
    Supports OpenAI (ChatGPT) and Google (Gemini) via LangChain.
    """

    def __init__(
        self,
        name: str,
        role: str,
        provider: ProviderType = "gemini",
        model_name: Optional[str] = None,
        temperature: float = 0,
        api_key: Optional[str] = None,
    ):
        self.name = name
        self.role = role
        self.provider = provider
        self.model_name = model_name
        self.temperature = temperature

        self.llm: BaseChatModel = create_llm(
            provider=provider,
            model_name=model_name,
            temperature=temperature,
            api_key=api_key,
        )

        logger.info(f"[{self.name}] Initialized with provider='{provider}', model='{self.model_name or 'default'}'")

    def _build_messages(self, prompt: str) -> list:
        """
        Build the message list for the LLM.
        Gemini uses convert_system_message_to_human, so SystemMessage is safe for OpenAI
        and handled automatically for Gemini.
        """
        messages = []
        if self.role:
            messages.append(SystemMessage(content=self.role))
        messages.append(HumanMessage(content=prompt))
        return messages

    def _extract_json_from_response(self, text: str) -> str:
        """Extract JSON from LLM response, handling markdown code blocks."""
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

        return text.strip()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((json.JSONDecodeError, ValidationError)),
        reraise=True,
    )
    def _call_llm_with_retry(self, prompt: str, output_model: Type[T]) -> T:
        """Call LLM with retry logic for JSON parsing failures."""
        logger.info(f"[{self.name}] Calling {self.provider} LLM...")
    
        messages = self._build_messages(prompt)
        response = self.llm.invoke(messages)
        raw_text = response.content
    
        logger.debug(f"[{self.name}] Raw response:\n{raw_text}")
    
        json_str = self._extract_json_from_response(raw_text)
    
        # --- JSON parse ---
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.warning(f"[{self.name}] JSON parse error: {e}. Asking LLM to fix...")
            fix_prompt = (
                f"Le texte suivant devait être un JSON valide mais contient des erreurs. "
                f"Corrige-le et renvoie UNIQUEMENT le JSON valide :\n\n{json_str}"
            )
            fix_response = self.llm.invoke([HumanMessage(content=fix_prompt)])
            json_str = self._extract_json_from_response(fix_response.content)
            data = json.loads(json_str)  # raises → retry
    
        # --- Pydantic validation ---
        try:
            result = output_model.model_validate(data)
        except ValidationError as e:
            # Log exactly which fields are wrong
            logger.warning(
                f"[{self.name}] Pydantic ValidationError:\n{e}\n"
                f"Data received:\n{json.dumps(data, indent=2, ensure_ascii=False)}"
            )
            # Send schema + errors back to LLM for self-correction
            schema = json.dumps(output_model.model_json_schema(), indent=2, ensure_ascii=False)
            fix_prompt = (
                f"Le JSON suivant ne respecte pas le schéma attendu.\n\n"
                f"SCHÉMA:\n{schema}\n\n"
                f"JSON REÇU:\n{json.dumps(data, indent=2, ensure_ascii=False)}\n\n"
                f"ERREURS DE VALIDATION:\n{str(e)}\n\n"
                f"Renvoie UNIQUEMENT un JSON corrigé qui respecte exactement le schéma."
            )
            fix_response = self.llm.invoke([HumanMessage(content=fix_prompt)])
            json_str = self._extract_json_from_response(fix_response.content)
            data = json.loads(json_str)
            result = output_model.model_validate(data)  # raises ValidationError → retry
    
        logger.info(f"[{self.name}] Successfully parsed and validated output.")
        return result

    def run(self, **kwargs) -> Any:
        """Override in subclasses."""
        raise NotImplementedError("Subclasses must implement run()")
