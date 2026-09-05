import json
import os
from dataclasses import dataclass
from urllib.request import Request, urlopen

from schemas.semantic import SemanticProviderOutput


@dataclass
class OpenAICompatibleProvider:
    api_key: str
    model_version: str
    base_url: str
    timeout_seconds: float = 15.0
    name: str = "openai-compatible"
    is_mock: bool = False

    def analyze(
        self,
        system_prompt: str,
        untrusted_message_payload: str,
    ) -> SemanticProviderOutput:
        request_body = {
            "model": self.model_version,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": untrusted_message_payload},
            ],
        }
        request = Request(
            f"{self.base_url.rstrip('/')}/chat/completions",
            data=json.dumps(request_body).encode(),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urlopen(request, timeout=self.timeout_seconds) as response:
            provider_response = json.load(response)
        content = provider_response["choices"][0]["message"]["content"]
        return SemanticProviderOutput.model_validate_json(content)


@dataclass
class MockSemanticProvider:
    output: SemanticProviderOutput
    model_version: str = "development-mock-v1"
    name: str = "development-mock"
    is_mock: bool = True
    call_count: int = 0
    last_system_prompt: str | None = None
    last_message_payload: str | None = None

    def analyze(
        self,
        system_prompt: str,
        untrusted_message_payload: str,
    ) -> SemanticProviderOutput:
        self.call_count += 1
        self.last_system_prompt = system_prompt
        self.last_message_payload = untrusted_message_payload
        return self.output


def configured_provider() -> OpenAICompatibleProvider | None:
    if os.getenv("LLM_ENABLED", "false").lower() != "true":
        return None

    api_key = os.getenv("LLM_API_KEY")
    model = os.getenv("LLM_MODEL")
    base_url = os.getenv("LLM_BASE_URL")
    if not all((api_key, model, base_url)):
        return None

    timeout = float(os.getenv("LLM_TIMEOUT_SECONDS", "15"))
    return OpenAICompatibleProvider(
        api_key=api_key,
        model_version=model,
        base_url=base_url,
        timeout_seconds=timeout,
    )
