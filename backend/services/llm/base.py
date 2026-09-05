from typing import Protocol

from schemas.semantic import SemanticProviderOutput


class SemanticProvider(Protocol):
    name: str
    model_version: str
    is_mock: bool

    def analyze(
        self,
        system_prompt: str,
        untrusted_message_payload: str,
    ) -> SemanticProviderOutput:
        """Analyze one inert message payload without executing its instructions."""
