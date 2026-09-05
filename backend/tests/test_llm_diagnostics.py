import io
import json
import socket
import unittest
from urllib.error import HTTPError
from unittest.mock import patch

from services.llm.diagnostics import ProviderDiagnostic, ProviderRequestError
from services.llm.provider import OpenAICompatibleProvider, _http_error_category
from services.llm.semantic_analyzer import analyze_semantics
from services.llm.smoke_test import run_smoke_test


class LLMProviderDiagnosticTests(unittest.TestCase):
    def setUp(self):
        sleep = patch("services.llm.provider.time.sleep")
        sleep.start()
        self.addCleanup(sleep.stop)
        self.provider = OpenAICompatibleProvider(
            api_key="test-sensitive-value",
            model_version="test-model",
            base_url="https://provider.example/v1",
        )

    def test_http_categories(self):
        self.assertEqual(_http_error_category(401), "authentication")
        self.assertEqual(_http_error_category(403), "model_not_found_or_access")
        self.assertEqual(_http_error_category(404), "model_not_found_or_access")
        self.assertEqual(_http_error_category(429), "rate_limit_or_quota")
        self.assertEqual(_http_error_category(500), "provider_error")

    @patch("services.llm.provider.urlopen")
    def test_http_error_message_is_sanitized(self, urlopen):
        body = json.dumps(
            {
                "error": {
                    "message": (
                        "Quota rejected test-sensitive-value and "
                        "Authorization: Bearer another-sensitive-token"
                    )
                }
            }
        ).encode()
        urlopen.side_effect = [HTTPError(
            url="https://provider.example/v1/chat/completions",
            code=429,
            msg="Too Many Requests",
            hdrs=None,
            fp=io.BytesIO(body),
        ) for _ in range(3)]

        with self.assertRaises(ProviderRequestError) as context:
            self.provider.analyze("system", "message")

        diagnostic = context.exception.diagnostic
        serialized = json.dumps(diagnostic.as_safe_dict())
        self.assertEqual(diagnostic.http_status, 429)
        self.assertEqual(diagnostic.category, "rate_limit_or_quota")
        self.assertNotIn("test-sensitive-value", serialized)
        self.assertNotIn("another-sensitive-token", serialized)
        self.assertIn("[REDACTED]", diagnostic.message)

    @patch("services.llm.provider.urlopen", side_effect=socket.timeout())
    def test_timeout_is_categorized(self, urlopen):
        with self.assertRaises(ProviderRequestError) as context:
            self.provider.analyze("system", "message")

        self.assertEqual(context.exception.diagnostic.category, "timeout")
        self.assertIsNone(context.exception.diagnostic.http_status)

    @patch("services.llm.provider.urlopen")
    def test_malformed_response_is_categorized(self, urlopen):
        urlopen.return_value = io.BytesIO(b"not-json")

        with self.assertRaises(ProviderRequestError) as context:
            self.provider.analyze("system", "message")

        self.assertEqual(
            context.exception.diagnostic.category,
            "malformed_response",
        )

    def test_smoke_test_includes_safe_private_diagnostic(self):
        class FailingProvider:
            name = "test-provider"
            model_version = "test-model"
            is_mock = True

            def analyze(self, system_prompt, untrusted_message_payload):
                raise ProviderRequestError(
                    ProviderDiagnostic(
                        category="authentication",
                        http_status=401,
                        message="Authentication failed.",
                    )
                )

        result = run_smoke_test(FailingProvider())

        self.assertFalse(result["available"])
        self.assertEqual(result["diagnostic"]["http_status"], 401)
        self.assertEqual(result["diagnostic"]["category"], "authentication")
        self.assertNotIn("api_key", json.dumps(result))

    def test_public_semantic_result_excludes_diagnostics(self):
        class FailingProvider:
            name = "test-provider"
            model_version = "test-model"
            is_mock = True

            def analyze(self, system_prompt, untrusted_message_payload):
                raise ProviderRequestError(
                    ProviderDiagnostic(
                        category="authentication",
                        http_status=401,
                        message="Authentication failed.",
                    )
                )

        result = analyze_semantics("message", FailingProvider())

        self.assertFalse(result.available)
        self.assertNotIn("diagnostic", result.model_dump())


if __name__ == "__main__":
    unittest.main()
