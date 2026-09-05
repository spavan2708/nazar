import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from schemas.semantic import SemanticProviderOutput, SemanticSignal
from schemas.signals import SignalCode
from services.llm import provider as provider_module
from services.llm.config import (
    get_llm_settings,
    get_provider_status,
    load_backend_env,
)
from services.llm.provider import MockSemanticProvider, configured_provider
from services.llm.smoke_test import run_smoke_test


class LLMConfigurationTests(unittest.TestCase):
    def test_dotenv_loads_without_overriding_process_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            env_path = Path(directory) / ".env"
            env_path.write_text(
                "LLM_ENABLED=true\n"
                "LLM_API_KEY=file-key\n"
                "LLM_MODEL=file-model\n"
                "LLM_BASE_URL=https://provider.example/v1\n"
            )
            with patch.dict(os.environ, {"LLM_MODEL": "shell-model"}, clear=True):
                load_backend_env(env_path)
                settings = get_llm_settings()

                self.assertTrue(settings.configured)
                self.assertEqual(settings.api_key, "file-key")
                self.assertEqual(settings.model, "shell-model")

    def test_disabled_llm_has_no_provider(self):
        settings = get_llm_settings({"LLM_ENABLED": "false"})

        self.assertFalse(settings.enabled)
        self.assertFalse(settings.configured)

    def test_enabled_llm_with_missing_key_is_unavailable_and_logs_safely(self):
        environment = {
            "LLM_ENABLED": "true",
            "LLM_API_KEY": "",
            "LLM_MODEL": "test-model",
            "LLM_BASE_URL": "https://provider.example/v1",
        }
        provider_module._last_configuration_warning = None
        with patch.dict(os.environ, environment, clear=True):
            with self.assertLogs(provider_module.logger, level="WARNING") as logs:
                result = configured_provider()

        self.assertIsNone(result)
        self.assertIn("LLM_API_KEY", logs.output[0])
        self.assertNotIn("secret", logs.output[0])

    def test_invalid_timeout_is_unavailable(self):
        settings = get_llm_settings(
            {
                "LLM_ENABLED": "true",
                "LLM_API_KEY": "secret-value",
                "LLM_MODEL": "test-model",
                "LLM_BASE_URL": "https://provider.example/v1",
                "LLM_TIMEOUT_SECONDS": "not-a-number",
            }
        )

        self.assertFalse(settings.configured)
        self.assertIn("positive number", settings.error)

    def test_provider_status_never_contains_api_key(self):
        secret = "super-secret-provider-key"
        status = get_provider_status(
            {
                "LLM_ENABLED": "true",
                "LLM_API_KEY": secret,
                "LLM_MODEL": "configured-model",
                "LLM_BASE_URL": "https://provider.example/v1",
            }
        )

        serialized = json.dumps(status)
        self.assertEqual(status["configured"], True)
        self.assertNotIn("api_key", status)
        self.assertNotIn(secret, serialized)

    def test_smoke_test_uses_mock_without_network(self):
        mock_provider = MockSemanticProvider(
            output=SemanticProviderOutput(
                risk_score=0.9,
                intent="credential_theft",
                tactics=["verification_pretext"],
                requested_actions=["share_verification_code"],
                signals=[
                    SemanticSignal(
                        code=SignalCode.OTP_REQUEST,
                        confidence=0.95,
                    )
                ],
                is_safety_warning=False,
                explanation="The sender requests a verification code.",
            )
        )

        result = run_smoke_test(mock_provider)

        self.assertEqual(mock_provider.call_count, 1)
        self.assertTrue(result["available"])
        self.assertTrue(result["is_mock"])
        self.assertNotIn("api_key", result)
        self.assertEqual(result["signals"][0]["code"], "OTP_REQUEST")


if __name__ == "__main__":
    unittest.main()
