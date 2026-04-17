"""
Base agent class for all CV evaluation agents.
Supports multiple LLM providers: OpenAI (ChatGPT), Google (Gemini) via LangChain,
and free/local Ollama via custom wrapper.
"""

import json
import re
import os
import logging
from typing import Any, Dict, Optional, Type, TypeVar, Literal, Iterator
from pydantic import BaseModel, ValidationError
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, BaseMessage
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.outputs import ChatResult, ChatGeneration
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

ProviderType = Literal["gemini", "openai", "ollama"]


# ------------------------------------------------------------
# Ollama Chat Model Wrapper (using official ollama package)
# ------------------------------------------------------------
class OllamaChatModel(BaseChatModel):
    """
    Custom wrapper for Ollama using the official 'ollama' Python client.
    Compatible with LangChain's BaseChatModel interface.
    Supports both local (no API key) and cloud (with Bearer token) modes.
    """
    model: str = "llama3.2"
    temperature: float = 0.0
    api_key: Optional[str] = None

    def __init__(self, model: str, temperature: float, api_key: Optional[str] = None, **kwargs):
        super().__init__(model=model, temperature=temperature, api_key=api_key, **kwargs)
        from ollama import Client
        if api_key:
            # Cloud mode
            self._client = Client(
                host="https://ollama.com",
                headers={"Authorization": f"Bearer {api_key}"}
            )
            logger.info("OllamaChatModel: using cloud mode with API key")
        else:
            # Local mode
            self._client = Client(host="http://localhost:11434")
            logger.info("OllamaChatModel: using local mode (no API key)")

    def _convert_messages_to_ollama(self, messages: list[BaseMessage]) -> list[dict]:
        """Convert LangChain messages to Ollama format."""
        ollama_messages = []
        for msg in messages:
            if isinstance(msg, SystemMessage):
                role = "system"
            elif isinstance(msg, HumanMessage):
                role = "user"
            elif isinstance(msg, AIMessage):
                role = "assistant"
            else:
                role = "user"
            ollama_messages.append({"role": role, "content": msg.content})
        return ollama_messages

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: Optional[list[str]] = None,
        run_manager = None,
        **kwargs,
    ) -> ChatResult:
        ollama_messages = self._convert_messages_to_ollama(messages)
        try:
            response = self._client.chat(
                model=self.model,
                messages=ollama_messages,
                stream=False,
                options={"temperature": self.temperature}
            )
            content = response["message"]["content"]
        except Exception as e:
            logger.error(f"Ollama chat error: {e}")
            raise
        message = AIMessage(content=content)
        generation = ChatGeneration(message=message)
        return ChatResult(generations=[generation])

    def _stream(
        self,
        messages: list[BaseMessage],
        stop: Optional[list[str]] = None,
        run_manager = None,
        **kwargs,
    ) -> Iterator[ChatGeneration]:
        """Streaming mode (optional)."""
        ollama_messages = self._convert_messages_to_ollama(messages)
        try:
            stream = self._client.chat(
                model=self.model,
                messages=ollama_messages,
                stream=True,
                options={"temperature": self.temperature}
            )
            for chunk in stream:
                if "message" in chunk and "content" in chunk["message"]:
                    content = chunk["message"]["content"]
                    message = AIMessage(content=content)
                    yield ChatGeneration(message=message)
                    if run_manager:
                        run_manager.on_llm_new_token(content)
        except Exception as e:
            logger.error(f"Ollama stream error: {e}")
            raise

    @property
    def _llm_type(self) -> str:
        return "ollama-custom"


# ------------------------------------------------------------
# Factory function for LLM creation
# ------------------------------------------------------------
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
            convert_system_message_to_human=True,
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
        )

    elif provider == "ollama":
        resolved_model = model_name or os.getenv("OLLAMA_MODEL", "llama3.2")
        # Use our custom wrapper
        return OllamaChatModel(
            model=resolved_model,
            temperature=temperature,
            api_key=api_key,   # None for local, actual key for cloud
        )

    else:
        raise ValueError(f"Unsupported provider: '{provider}'. Choose 'gemini', 'openai' or 'ollama'.")


# ------------------------------------------------------------
# BaseAgent class (unchanged except for the use of create_llm)
# ------------------------------------------------------------
class BaseAgent:
    """
    Base class for all CV evaluation agents.
    Supports OpenAI (ChatGPT), Google (Gemini) and Ollama (local/cloud) via custom wrapper.
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
    
        # JSON parse
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
            data = json.loads(json_str)
    
        # Pydantic validation
        try:
            result = output_model.model_validate(data)
        except ValidationError as e:
            logger.warning(
                f"[{self.name}] Pydantic ValidationError:\n{e}\n"
                f"Data received:\n{json.dumps(data, indent=2, ensure_ascii=False)}"
            )
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
            result = output_model.model_validate(data)
    
        logger.info(f"[{self.name}] Successfully parsed and validated output.")
        return result

    def run(self, **kwargs) -> Any:
        raise NotImplementedError("Subclasses must implement run()")
