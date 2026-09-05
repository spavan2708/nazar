import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parents[2]
ENV_PATH = BACKEND_DIR / ".env"
PROVIDER_NAME = "openai-compatible"


@dataclass(frozen=True)
class LLMSettings:
    enabled: bool
    configured: bool
    api_key: str | None = field(repr=False)
    model: str | None
    base_url: str | None
    timeout_seconds: float
    error: str | None = None

    def provider_status(self) -> dict:
        return {
            "enabled": self.enabled,
            "configured": self.configured,
            "provider": PROVIDER_NAME if self.enabled else None,
            "model": self.model,
        }


def load_backend_env(path: Path = ENV_PATH) -> bool:
    # override=False preserves real process-environment priority over .env values.
    return load_dotenv(dotenv_path=path, override=False)


def get_llm_settings(environ: Mapping[str, str] | None = None) -> LLMSettings:
    values = environ if environ is not None else os.environ
    enabled_value = values.get("LLM_ENABLED", "false").strip().lower()
    if enabled_value not in {"true", "false", "1", "0", "yes", "no", "on", "off"}:
        return LLMSettings(
            enabled=False,
            configured=False,
            api_key=None,
            model=None,
            base_url=None,
            timeout_seconds=15.0,
            error="LLM_ENABLED must be true or false",
        )

    enabled = enabled_value in {"true", "1", "yes", "on"}
    api_key = values.get("LLM_API_KEY", "").strip() or None
    model = values.get("LLM_MODEL", "").strip() or None
    base_url = values.get("LLM_BASE_URL", "").strip() or None

    try:
        timeout_seconds = float(values.get("LLM_TIMEOUT_SECONDS", "15"))
        if timeout_seconds <= 0:
            raise ValueError
    except ValueError:
        return LLMSettings(
            enabled=enabled,
            configured=False,
            api_key=api_key,
            model=model,
            base_url=base_url,
            timeout_seconds=15.0,
            error="LLM_TIMEOUT_SECONDS must be a positive number",
        )

    if not enabled:
        return LLMSettings(
            enabled=False,
            configured=False,
            api_key=api_key,
            model=model,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
        )

    missing = [
        name
        for name, value in (
            ("LLM_API_KEY", api_key),
            ("LLM_MODEL", model),
            ("LLM_BASE_URL", base_url),
        )
        if value is None
    ]
    if missing:
        return LLMSettings(
            enabled=True,
            configured=False,
            api_key=api_key,
            model=model,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
            error="Missing required LLM configuration: " + ", ".join(missing),
        )

    return LLMSettings(
        enabled=True,
        configured=True,
        api_key=api_key,
        model=model,
        base_url=base_url,
        timeout_seconds=timeout_seconds,
    )


def get_provider_status(environ: Mapping[str, str] | None = None) -> dict:
    return get_llm_settings(environ).provider_status()


load_backend_env()
