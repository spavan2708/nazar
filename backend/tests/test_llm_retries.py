import io
import json
import logging
import socket
import ssl
import unittest
from urllib.error import HTTPError, URLError
from unittest.mock import patch

from fastapi.testclient import TestClient
from main import app
from services.llm.provider import OpenAICompatibleProvider
from services.llm.semantic_analyzer import analyze_semantics
from services.llm.smoke_test import run_smoke_test


class LLMRetryTests(unittest.TestCase):
    def setUp(self):
        self.provider = OpenAICompatibleProvider(
            api_key="secret-test-key", model_version="test-model",
            base_url="https://provider.example/v1", timeout_seconds=5,
        )
        self.urlopen = self.enterContext(patch("services.llm.provider.urlopen"))
        self.sleep = self.enterContext(patch("services.llm.provider.time.sleep"))
        self.enterContext(patch("services.llm.provider.random.uniform", return_value=0.05))
        self.enterContext(patch("services.llm.provider.time.monotonic", return_value=100))

    def http_error(self, code):
        return HTTPError("https://provider.example/v1", code, "error", None,
            io.BytesIO(json.dumps({"error": {"message":
                "secret-test-key Authorization: Bearer secret-header-token"
            }}).encode()))

    def success(self):
        output = {"risk_score": 0.95, "explanation": "Requests a verification code."}
        return io.BytesIO(json.dumps({"choices": [{"message": {
            "content": json.dumps(output)
        }}]}).encode())

    def test_transient_http_then_success(self):
        for code in (429, 500, 502, 503, 504):
            with self.subTest(code=code):
                self.urlopen.reset_mock()
                self.sleep.reset_mock()
                self.urlopen.side_effect = [self.http_error(code), self.success()]
                result = analyze_semantics("message", self.provider)
                self.assertTrue(result.available)
                self.assertEqual(result.risk_score, 0.95)
                self.assertEqual(self.urlopen.call_count, 2)
                self.sleep.assert_called_once_with(0.3)

    def test_permanent_http_is_not_retried(self):
        for code in (400, 401, 403, 404, 408, 422, 501):
            with self.subTest(code=code):
                self.urlopen.reset_mock()
                self.sleep.reset_mock()
                self.urlopen.side_effect = [self.http_error(code)]
                self.assertFalse(analyze_semantics("message", self.provider).available)
                self.assertEqual(self.urlopen.call_count, 1)
                self.sleep.assert_not_called()

    def test_temporary_network_failures_then_success(self):
        for error in (TimeoutError(), ConnectionResetError(),
                      URLError(socket.timeout()), URLError(ConnectionRefusedError()),
                      URLError(socket.gaierror(socket.EAI_AGAIN, "temporary DNS failure"))):
            with self.subTest(error=type(error)):
                self.urlopen.reset_mock()
                self.urlopen.side_effect = [error, self.success()]
                self.assertTrue(analyze_semantics("message", self.provider).available)
                self.assertEqual(self.urlopen.call_count, 2)

    def test_permanent_network_and_malformed_responses_are_not_retried(self):
        for value in (URLError(ssl.SSLCertVerificationError()), URLError("invalid URL"),
                      io.BytesIO(b"not json"), io.BytesIO(b'{"choices": []}'),
                      io.BytesIO(b'{"choices": [{"message": {"content": "{}"}}]}')):
            with self.subTest(value=type(value)):
                self.urlopen.reset_mock()
                self.sleep.reset_mock()
                self.urlopen.side_effect = [value]
                self.assertFalse(analyze_semantics("message", self.provider).available)
                self.assertEqual(self.urlopen.call_count, 1)
                self.sleep.assert_not_called()

    def test_exhaustion_keeps_public_api_normal_and_private(self):
        self.urlopen.side_effect = [self.http_error(503) for _ in range(3)]
        with patch("services.llm.semantic_analyzer.configured_provider", return_value=self.provider):
            response = TestClient(app).post("/api/analyze/text", json={"text": "Hello there"})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["semantic"]["available"])
        self.assertEqual(self.urlopen.call_count, 3)
        self.assertEqual([c.args[0] for c in self.sleep.call_args_list], [0.3, 0.55])
        for private in ("diagnostic", "retry", "secret-test-key", "Authorization"):
            self.assertNotIn(private, response.text)

    def test_timeout_budget_includes_backoff(self):
        self.urlopen.side_effect = [self.http_error(503), self.success()]
        with patch("services.llm.provider.time.monotonic", side_effect=[100, 100, 100.2, 100.5]):
            self.assertTrue(analyze_semantics("message", self.provider).available)
        self.assertEqual([c.kwargs["timeout"] for c in self.urlopen.call_args_list], [5, 4.5])

    def test_no_retry_when_timeout_budget_is_spent(self):
        self.urlopen.side_effect = [self.http_error(503)]
        with patch("services.llm.provider.time.monotonic", side_effect=[100, 100, 104.9]):
            self.assertFalse(analyze_semantics("message", self.provider).available)
        self.assertEqual(self.urlopen.call_count, 1)
        self.sleep.assert_not_called()

    def test_secrets_are_not_logged_and_smoke_diagnostic_is_safe(self):
        self.urlopen.side_effect = [self.http_error(503) for _ in range(3)]
        captured = io.StringIO()
        handler = logging.StreamHandler(captured)
        logging.getLogger().addHandler(handler)
        self.addCleanup(logging.getLogger().removeHandler, handler)
        result = run_smoke_test(self.provider)
        self.assertFalse(result["available"])
        self.assertEqual(result["diagnostic"]["http_status"], 503)
        self.assertEqual(self.urlopen.call_count, 3)
        for secret in ("secret-test-key", "secret-header-token", "Authorization"):
            self.assertNotIn(secret, captured.getvalue())
            self.assertNotIn(secret, json.dumps(result))
            self.assertNotIn(secret, repr(self.provider))


if __name__ == "__main__":
    unittest.main()
