import errno
import json
import random
import logging
import re
import socket
import ssl
import time
from http.client import IncompleteRead, RemoteDisconnected
from dataclasses import dataclass, field
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import ValidationError

from schemas.semantic import SemanticProviderOutput
from services.llm.config import get_llm_settings
from services.llm.diagnostics import ProviderDiagnostic, ProviderRequestError


logger = logging.getLogger(__name__)
_last_configuration_warning: str | None = None


@dataclass
class OpenAICompatibleProvider:
    api_key: str = field(repr=False)
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
        try:
            provider_response = self._request_json(request)
            content = provider_response["choices"][0]["message"]["content"]
            return SemanticProviderOutput.model_validate_json(content)
        except HTTPError as error:
            message = _safe_http_error_message(error, self.api_key)
            raise ProviderRequestError(
                ProviderDiagnostic(
                    category=_http_error_category(error.code),
                    http_status=error.code,
                    message=message,
                )
            ) from error
        except (TimeoutError, socket.timeout) as error:
            raise ProviderRequestError(
                ProviderDiagnostic(
                    category="timeout",
                    message="The provider request timed out.",
                )
            ) from error
        except (URLError, OSError, IncompleteRead) as error:
            if isinstance(getattr(error, "reason", error), (TimeoutError, socket.timeout)):
                category = "timeout"
                message = "The provider request timed out."
            else:
                category = "network_error"
                message = "The provider could not be reached."
            raise ProviderRequestError(
                ProviderDiagnostic(category=category, message=message)
            ) from error
        except (ValueError, KeyError, IndexError, TypeError, UnicodeError, ValidationError) as error:
            raise ProviderRequestError(
                ProviderDiagnostic(
                    category="malformed_response",
                    message="The provider returned an invalid structured response.",
                )
            ) from error


    def _request_json(self, request: Request) -> dict:
        # Share the configured timeout across attempts and backoff. urllib's
        # timeout remains a socket-operation timeout, not a hard wall-clock cap.
        deadline = time.monotonic() + self.timeout_seconds
        for attempt in range(3):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError()
            try:
                with urlopen(request, timeout=remaining) as response:
                    raw = response.read(128 * 1024 + 1)
                    if len(raw) > 128 * 1024:
                        raise ValueError("Provider response exceeds limit")
                    return json.loads(raw)
            except (URLError, OSError, IncompleteRead) as error:
                if attempt == 2 or not _is_transient(error):
                    raise
                delay = 0.25 * (2 ** attempt) + random.uniform(0, 0.1)
                if deadline - time.monotonic() <= delay:
                    raise
                # Release intermediate HTTP responses without reading/logging
                # provider bodies. The final error keeps the safe diagnostics.
                if isinstance(error, HTTPError):
                    error.close()
                time.sleep(delay)
        raise AssertionError("Unreachable retry state")


def _is_transient(error: Exception) -> bool:
    if isinstance(error, HTTPError):
        return error.code in {429, 500, 502, 503, 504}
    reason = error.reason if isinstance(error, URLError) else error
    # TLS/certificate and unknown URL failures are not assumed temporary.
    if isinstance(reason, ssl.SSLError):
        return False
    if isinstance(reason, socket.gaierror):
        return reason.errno == socket.EAI_AGAIN
    if isinstance(reason, (TimeoutError, ConnectionError, RemoteDisconnected, IncompleteRead)):
        return True
    return isinstance(reason, OSError) and reason.errno in {
        errno.ECONNRESET, errno.ECONNREFUSED, errno.ECONNABORTED,
        errno.ETIMEDOUT, errno.EHOSTUNREACH, errno.ENETUNREACH, errno.EPIPE,
    }


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
    global _last_configuration_warning

    settings = get_llm_settings()
    if settings.error and settings.error.startswith("LLM_ENABLED"):
        if settings.error != _last_configuration_warning:
            logger.warning("LLM semantic analysis unavailable: %s", settings.error)
            _last_configuration_warning = settings.error
        return None
    if not settings.enabled:
        return None
    if not settings.configured:
        if settings.error != _last_configuration_warning:
            logger.warning("LLM semantic analysis unavailable: %s", settings.error)
            _last_configuration_warning = settings.error
        return None

    _last_configuration_warning = None
    assert settings.api_key is not None
    assert settings.model is not None
    assert settings.base_url is not None
    return OpenAICompatibleProvider(
        api_key=settings.api_key,
        model_version=settings.model,
        base_url=settings.base_url,
        timeout_seconds=settings.timeout_seconds,
    )


def _http_error_category(status_code: int) -> str:
    if status_code == 401:
        return "authentication"
    if status_code in {403, 404}:
        return "model_not_found_or_access"
    if status_code == 408:
        return "timeout"
    if status_code == 429:
        return "rate_limit_or_quota"
    if 500 <= status_code <= 599:
        return "provider_error"
    return "invalid_request"


def _safe_http_error_message(error: HTTPError, api_key: str) -> str:
    fallback = f"Provider request failed with HTTP {error.code}."
    try:
        body = error.read(16_384).decode("utf-8", errors="replace")
        payload = json.loads(body)
        message = payload.get("error", {}).get("message")
        if not isinstance(message, str) or not message.strip():
            return fallback
        return _redact(message, api_key)
    except (AttributeError, json.JSONDecodeError, OSError, TypeError):
        return fallback
    finally:
        error.close()


def _redact(message: str, api_key: str) -> str:
    sanitized = message.replace(api_key, "[REDACTED]") if api_key else message
    sanitized = re.sub(
        r"(?i)authorization\s*:\s*bearer\s+\S+|bearer\s+\S+",
        "[REDACTED]",
        sanitized,
    )
    sanitized = re.sub(r"\bsk-[A-Za-z0-9_-]+", "[REDACTED]", sanitized)
    sanitized = " ".join(sanitized.split())
    return sanitized[:500]
