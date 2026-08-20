"""LLM client abstraction.

Production note: agents should depend on this interface instead of importing an SDK directly.
"""

import logging
import os
from dataclasses import dataclass

from multi_agent_research_lab.core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LLMResponse:
    content: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None


class LLMClient:
    """Provider-agnostic LLM client supporting Google Gemini and OpenAI."""

    def __init__(self, model: str | None = None, api_key: str | None = None) -> None:
        self.settings = get_settings()
        self.api_key = (
            api_key
            or self.settings.gemini_api_key
            or self.settings.google_api_key
            or os.getenv("GEMINI_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
            or self.settings.openai_api_key
            or os.getenv("OPENAI_API_KEY")
        )
        self.model = (
            model
            or self.settings.gemini_model
            or os.getenv("GEMINI_MODEL")
            or self.settings.openai_model
            or "gemini-2.5-flash"
        )

    def complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        """Return a model completion."""
        # Use Google GenAI / Gemini
        if self.api_key and (
            self.settings.gemini_api_key
            or self.settings.google_api_key
            or "gemini" in self.model.lower()
            or "gemma" in self.model.lower()
            or not self.settings.openai_api_key
        ):
            return self._complete_gemini(system_prompt, user_prompt)
        elif self.settings.openai_api_key:
            return self._complete_openai(system_prompt, user_prompt)
        else:
            return self._complete_gemini(system_prompt, user_prompt)

    def _complete_gemini(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        """Call Gemini API via langchain-google-genai or google-genai SDK."""
        # Try google-genai or google.generativeai or langchain_google_genai
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.api_key)
            config = types.GenerateContentConfig(
                system_instruction=system_prompt if system_prompt else None,
                temperature=0.3,
            )
            response = client.models.generate_content(
                model=self.model,
                contents=user_prompt,
                config=config,
            )
            content = response.text or ""
            input_tokens = None
            output_tokens = None
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                input_tokens = response.usage_metadata.prompt_token_count
                output_tokens = response.usage_metadata.candidates_token_count

            cost = 0.0
            if input_tokens:
                cost += (input_tokens / 1_000_000) * 0.075
            if output_tokens:
                cost += (output_tokens / 1_000_000) * 0.30

            return LLMResponse(
                content=content,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost if (input_tokens or output_tokens) else None,
            )
        except Exception as exc:
            logger.info("Retrying with langchain-google-genai...")
            try:
                from langchain_core.messages import HumanMessage, SystemMessage
                from langchain_google_genai import ChatGoogleGenerativeAI

                llm = ChatGoogleGenerativeAI(
                    model=self.model,
                    google_api_key=self.api_key,
                    temperature=0.3,
                )
                messages = []
                if system_prompt:
                    messages.append(SystemMessage(content=system_prompt))
                messages.append(HumanMessage(content=user_prompt))
                res = llm.invoke(messages)
                content = str(res.content)
                return LLMResponse(content=content)
            except Exception as e2:
                logger.error(f"Failed to generate completion from Gemini: {e2}")
                raise e2 from exc

    def _complete_openai(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        """Call OpenAI API."""
        from openai import OpenAI

        client = OpenAI(api_key=self.settings.openai_api_key)
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        response = client.chat.completions.create(
            model=self.settings.openai_model,
            messages=messages,
            temperature=0.3,
        )
        content = response.choices[0].message.content or ""
        input_tokens = response.usage.prompt_tokens if response.usage else None
        output_tokens = response.usage.completion_tokens if response.usage else None
        cost = 0.0
        if input_tokens:
            cost += (input_tokens / 1_000_000) * 0.15
        if output_tokens:
            cost += (output_tokens / 1_000_000) * 0.60

        return LLMResponse(
            content=content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost if (input_tokens or output_tokens) else None,
        )
