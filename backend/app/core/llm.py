import json
import os
from typing import Optional
from openai import OpenAI
from app.core.config import Settings


class LLMClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = OpenAI(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key or "sk-no-key",
        )

    def chat_completion(
        self,
        prompt: str,
        system: Optional[str] = None,
        response_format: Optional[dict] = None,
    ) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        kwargs = {
            "model": self.settings.llm_model,
            "messages": messages,
            "temperature": self.settings.llm_temperature,
            "max_tokens": self.settings.llm_max_tokens,
        }
        if response_format:
            kwargs["response_format"] = response_format

        resp = self.client.chat.completions.create(**kwargs)
        return resp.choices[0].message.content

    def chat_completion_json(self, prompt: str, system: Optional[str] = None) -> dict:
        content = self.chat_completion(
            prompt,
            system=system,
            response_format={"type": "json_object"},
        )
        return json.loads(content)
