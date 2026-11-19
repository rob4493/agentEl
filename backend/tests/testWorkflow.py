import json
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.meaningValidator import extractFacts, validateMeaning
from app.providers.ollamaProvider import OllamaProvider
from app.providers.modelProvider import ProviderUnavailable
from app.emailSchemas import EmailRequest

fixture = json.loads((Path(__file__).resolve().parents[2] / "evaluation/fixtures/stagingEmail.json").read_text())
client = TestClient(app)

def testHealth():
    assert client.get("/api/health").json()["semanticValidation"] == "unavailable"

@pytest.mark.parametrize("draft", ["", " " , "x" * 20001])
def testInputLimits(draft):
    assert client.post("/api/improve", json={**fixture, "originalDraft": draft}).status_code == 422

def testMockContract():
    response = client.post("/api/improve", json=fixture)
    assert response.status_code == 200
    result = response.json()
    assert result["isMock"] is True
    assert result["validation"]["status"] == "reviewRequired"
    assert result["validation"]["semanticStatus"] == "unavailable"
    assert result["analysis"]["facts"]
    assert all(fact["sourcePassage"] in fixture["originalDraft"] for fact in result["analysis"]["facts"])

def testStableEvidence():
    first = extractFacts(fixture["originalDraft"])
    assert first == extractFacts(fixture["originalDraft"])
    assert len({fact.factId for fact in first.facts}) == len(first.facts)

@pytest.mark.parametrize("old,new", [
    ("deployed to staging", "deployed to production"),
    ("remain unresolved", "are resolved"),
    ("no confirmed resolution date", "a confirmed resolution date of November 20, 2026"),
    ("Intermittent CSV export timeouts for datasets exceeding 25,000 rows remain unresolved.", ""),
    ("November 18, 2026", "November 19, 2026"),
    ("25,000", "50,000"),
    ("no confirmed resolution date", "a guaranteed resolution"),
])
def testDeliberateChanges(old,new):
    result = validateMeaning(fixture["originalDraft"], fixture["originalDraft"].replace(old,new))
    assert any(finding.category == "sourcePassageChanged" for finding in result.findings)

def testUnsupportedAchievement():
    result = validateMeaning(fixture["originalDraft"], fixture["originalDraft"] + "\nWe also doubled performance.")
    assert any(finding.category == "unsupportedOrReworded" for finding in result.findings)

def testNumericalAndDeadlineReports():
    result = validateMeaning(fixture["originalDraft"], fixture["originalDraft"].replace("November 18", "December 19"))
    assert {"numericalChange", "deadlineChange"}.issubset({finding.category for finding in result.findings})

def testUnchangedStillRequiresHumanReview():
    result = validateMeaning(fixture["originalDraft"], fixture["originalDraft"])
    assert not result.findings
    assert result.status == "reviewRequired"

def testOllamaFailure():
    provider = OllamaProvider("http://127.0.0.1:11434", "qwen3:4b")
    with patch("app.providers.ollamaProvider.openLocalRequest", side_effect=URLError("offline")):
        with pytest.raises(ProviderUnavailable):
            provider.improve(EmailRequest(**fixture))

def testApiProviderFailure(monkeypatch):
    monkeypatch.setenv("COMMUNICATION_PROVIDER", "ollama")
    with patch("app.providers.ollamaProvider.openLocalRequest", side_effect=URLError("offline")):
        assert client.post("/api/improve", json=fixture).status_code == 503

def testRemoteProviderRejected():
    with pytest.raises(ValueError):
        OllamaProvider("https://example.com", "qwen3:4b")

def testRedirectRejected():
    from app.providers.ollamaProvider import LocalOnlyRedirectHandler
    with pytest.raises(ProviderUnavailable):
        LocalOnlyRedirectHandler().redirect_request(None, None, 307, "redirect", {}, "https://example.com")

def testAnalysisAndValidationEndpoints():
    assert client.post("/api/analyze", json=fixture).json()["facts"]
    response = client.post("/api/validate", json={"originalDraft":fixture["originalDraft"], "improvedDraft":fixture["originalDraft"]})
    assert response.status_code == 200
    assert response.json()["semanticStatus"] == "unavailable"
