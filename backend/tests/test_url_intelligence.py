import io
import logging
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image

from main import app
from schemas.analysis import MLAnalysis
from schemas.semantic import SemanticAnalysis
from schemas.signals import SignalCode
from services.analysis_service import analyze_text
from services import campaign_service
from services.url_intelligence import InvalidURL, analyze_url, extract_url_analysis
from services.text_analyzer import analyze_text as v3


class URLIntelligenceTests(unittest.TestCase):
    def codes(self, url):
        return {indicator.code for indicator in analyze_url(url).indicators}

    def test_normal_https_and_canonicalization(self):
        result = analyze_url("HTTPS://Example.COM:443/help")
        self.assertEqual(result.normalized_url, "https://example.com/help")
        self.assertEqual(result.structural_risk_score, 0)
        self.assertEqual(result.risk_level, "low")
        self.assertIn("does not establish", result.explanation)
        self.assertTrue(analyze_url("example.com").scheme_assumed)
        self.assertEqual(analyze_url("//Example.com/path").normalized_url, "https://example.com/path")
        self.assertEqual(analyze_url("example.com:8443/path").port, 8443)

    def test_http_is_one_indicator_not_phishing_verdict(self):
        result = analyze_url("http://example.com")
        self.assertEqual(result.structural_risk_score, 10)
        self.assertEqual(result.evidence_groups, 1)
        self.assertIn("not enough", result.explanation)
        self.assertIn("NON_HTTPS", self.codes("http://example.com"))

    def test_ip_addresses(self):
        for url in ("https://192.0.2.1", "https://127.0.0.1", "https://[2001:db8::1]/"):
            self.assertIn("IP_ADDRESS_HOST", self.codes(url))
        self.assertEqual(analyze_url("https://[2001:db8::1]/").hostname, "2001:db8::1")

    def test_idn_and_lookalike_flags_do_not_double_count(self):
        result = analyze_url("https://раураl.example/")
        self.assertTrue(result.hostname.startswith("xn--"))
        self.assertEqual(result.structural_risk_score, 25)
        self.assertEqual(result.evidence_groups, 1)
        self.assertIn("MIXED_SCRIPT_HOST", {i.code for i in result.indicators})
        self.assertIn("LOOKALIKE_CHARACTERS", {i.code for i in result.indicators})
        self.assertIn("IDN_HOST", self.codes("https://xn--bcher-kva.example/"))

    def test_depth_credentials_shortener_and_complexity(self):
        self.assertIn("DEEP_HOSTNAME", self.codes("https://a.b.c.d.example.com"))
        self.assertIn("CREDENTIAL_HEAVY_URL", self.codes("https://example.com/login/verify/account/password"))
        self.assertIn("URL_SHORTENER", self.codes("https://bit.ly/demo"))
        self.assertNotIn("URL_SHORTENER", self.codes("https://bit.ly.example.com"))
        self.assertIn("LONG_PATH", self.codes("https://example.com/" + "a" * 201))
        self.assertIn("COMPLEX_QUERY", self.codes("https://example.com/?" + "&".join(f"x{i}=1" for i in range(9))))
        self.assertIn("UNUSUAL_PORT", self.codes("https://example.com:8080/"))
        result = analyze_url("https://name:secret@example.com/")
        self.assertNotIn("secret", result.normalized_url)
        self.assertIn("EMBEDDED_USERINFO", {i.code for i in result.indicators})

    def test_unsupported_and_malformed_urls(self):
        for url in ("javascript:alert(1)", "data:text/html,hello", "file:///etc/passwd", "ftp://example.com", "mailto:a@example.com", "", "hello", "https://", "https://example.com:99999", "https://bad..example", "https://exa mple.com", "https://example.com/%zz", "https://example.com\\evil", "https://example.com\n/path", "http://2130706433", "http://0177.0.0.1", "https://xn--bad.example"):
            with self.subTest(url=url), self.assertRaises(InvalidURL):
                analyze_url(url)

    def test_multiple_bare_and_wrapped_links(self):
        urls, truncated = extract_url_analysis("Compare (https://example.com/help), secure-verify-bank-login.example and https://bit.ly/demo.")
        self.assertEqual([url.hostname for url in urls], ["example.com", "secure-verify-bank-login.example", "bit.ly"])
        self.assertFalse(truncated)
        self.assertEqual(extract_url_analysis("Email user@sub.example.com for help.")[0], [])
        self.assertEqual(extract_url_analysis("Version 1.2.3 was released.")[0], [])
        self.assertEqual(extract_url_analysis("Check example.com.")[0][0].hostname, "example.com")
        self.assertEqual(extract_url_analysis("See [https://example.com] and 'https://example.org'.")[0][0].hostname, "example.com")
        self.assertEqual(extract_url_analysis("пример.рф")[0][0].hostname, "xn--e1afmkfd.xn--p1ai")

    def test_invalid_links_in_text_are_reported_without_breaking(self):
        urls, _ = extract_url_analysis("Avoid javascript:alert(1) and https://example.com/")
        self.assertEqual(len(urls), 2)
        self.assertFalse(urls[0].valid)
        self.assertTrue(urls[1].valid)

    def test_extraction_is_bounded_and_deduplicated(self):
        urls, truncated = extract_url_analysis(" ".join(f"https://site{i}.example" for i in range(25)))
        self.assertEqual(len(urls), 20)
        self.assertTrue(truncated)
        self.assertEqual(len(extract_url_analysis("https://example.com https://example.com")[0]), 1)

    def test_offline_no_network_execution_or_secret_logging(self):
        captured = io.StringIO()
        handler = logging.StreamHandler(captured)
        logging.getLogger().addHandler(handler)
        self.addCleanup(logging.getLogger().removeHandler, handler)
        with patch("socket.getaddrinfo", side_effect=AssertionError("DNS must not run")), patch("socket.socket.connect", side_effect=AssertionError("No connections")), patch("urllib.request.urlopen", side_effect=AssertionError("No HTTP")), patch("subprocess.run", side_effect=AssertionError("No execution")), patch("webbrowser.open", side_effect=AssertionError("No browser")):
            response = TestClient(app).post("/api/analyze/url", json={"url": "http://127.0.0.1:8080/login/verify/account?token=query-secret-value"})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("query-secret-value", captured.getvalue())
        self.assertNotIn("query-secret-value", response.json()["explanation"])

    def test_standalone_errors_are_safe(self):
        response = TestClient(app).post("/api/analyze/url", json={"url": "javascript:query-secret-value"})
        self.assertEqual(response.status_code, 422)
        self.assertNotIn("query-secret-value", response.text)


class URLIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch("services.analysis_service.predict_scam_probability", return_value=MLAnalysis(available=False)))
        self.enterContext(patch("services.analysis_service.analyze_semantics", return_value=SemanticAnalysis(available=False)))

    def test_existing_text_scores_unchanged_without_urls(self):
        for text in ("Hello, let's meet tomorrow.", "Send me your OTP immediately.", "உங்கள் OTP யாரிடமும் பகிர வேண்டாம்."):
            result = analyze_text(text)
            self.assertEqual(result.score, v3(text).score)
            self.assertEqual(result.urls, [])

    def test_url_evidence_reuses_canonical_link_weight(self):
        text = "http://192.0.2.1:8080/"
        self.assertEqual(v3(text).score, 0)
        result = analyze_text(text)
        self.assertEqual(result.score, 35)
        self.assertIn(SignalCode.LINK_REQUEST, result.signal_codes)
        self.assertEqual(result.urls[0].structural_risk_score, 40)
        self.assertEqual(analyze_text("http://example.com/").score, 0)
        self.assertEqual(analyze_text("https://раураl.example/").score, 0)
        self.assertEqual(analyze_text("Beware of http://192.0.2.1:8080/").score, 0)

    def test_message_and_image_results_include_links(self):
        client = TestClient(app)
        text = "See http://192.0.2.1:8080/ and https://example.com/"
        response = client.post("/api/analyze/text", json={"text": text})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["urls"]), 2)
        image = io.BytesIO()
        Image.new("RGB", (10, 10)).save(image, format="PNG")
        with patch("services.image_analysis.ocr_configuration", return_value={"language": "eng"}), patch("services.image_analysis.extract_text", return_value=text):
            response = client.post("/api/analyze/image", files={"file": ("test.png", image.getvalue(), "image/png")})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["analysis"]["urls"]), 2)

    def test_campaign_uses_existing_mechanism(self):
        campaign = campaign_service.create_campaign()
        from schemas.campaign import InteractionRequest
        for _ in range(2):
            result = campaign_service.add_interaction(campaign.campaign_id, InteractionRequest(type="text", content="http://192.0.2.1:8080/"))
        self.assertEqual(result.interactions[0].analysis.score, 35)
        self.assertIn(SignalCode.LINK_REQUEST, result.interactions[0].analysis.signal_codes)
        # Existing formula: 35 + round(35 * .2) + 5 for a second elevated message.
        self.assertEqual(result.campaign_score, 47)


if __name__ == "__main__":
    unittest.main()
