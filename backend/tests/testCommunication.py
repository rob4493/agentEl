import json
from pathlib import Path
from unittest.mock import patch
from io import BytesIO
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.emailSchemas import EmailRequest, ValidationRequest, Clarification, SemanticReport
from app.factExtractor import extractFacts
from app.ambiguityChecker import findAmbiguities
from app.meaningValidator import validateMeaning
from app.semanticReview import reviewMeaning
from app.providers.ollamaProvider import OllamaProvider
from app.providers.modelProvider import ProviderUnavailable

fixtureRoot = Path(__file__).resolve().parents[2] / "evaluation/fixtures"
fixtureData = json.loads((fixtureRoot / "communicationScenarios.json").read_text())
scenarios = fixtureData["scenarios"]
client = TestClient(app)

def scenarioRequest(scenario):
    original = scenario.get("originalDraft") or json.loads((fixtureRoot / scenario["fixtureFile"]).read_text())["originalDraft"]
    answers = [Clarification(ambiguityId=question.ambiguityId,sourcePassage=question.sourcePassage,answer=scenario["clarificationAnswers"][question.category]) for question in findAmbiguities(original)]
    return EmailRequest(originalDraft=original,audience=fixtureData["audience"],clarifications=answers)

@pytest.mark.parametrize("scenario", scenarios, ids=[scenario["scenarioId"] for scenario in scenarios])
def testDeliberateScenarioErrors(scenario):
    request = scenarioRequest(scenario)
    result = validateMeaning(request.originalDraft,scenario["incorrectDraft"],request.audience,request.clarifications)
    assert set(scenario["expectedCategories"]).issubset({finding.category for finding in result.findings})
    assert all(finding.reviewMethod == "deterministic" for finding in result.findings)

@pytest.mark.parametrize("scenario", scenarios, ids=[scenario["scenarioId"] for scenario in scenarios])
def testCorrectScenarioKeepsCoreFacts(scenario):
    request = scenarioRequest(scenario)
    result = validateMeaning(request.originalDraft,scenario["correctDraft"],request.audience,request.clarifications)
    # Conservative wording warnings are retained; targeted warnings should not reject these known correct samples.
    assert not set(scenario["expectedCategories"]) & {finding.category for finding in result.findings}
    assert result.status == "reviewRequired"

def testAmbiguityBlocksInferenceAndRetainsEvidence(monkeypatch):
    monkeypatch.setenv("COMMUNICATION_PROVIDER", "mock")
    request = {"originalDraft":"We need to circle back on the logistics plan before EOD.","audience":{"group":"Team"}}
    with patch("app.providers.mockProvider.MockProvider.improve") as model:
        analysis = client.post("/api/analyze", json=request).json()
        response = client.post("/api/improve", json=request)
        assert response.status_code == 409
        assert {question["category"] for question in analysis["ambiguities"]} == {"requestedAction","deadline"}
        assert all(question["sourcePassage"] in request["originalDraft"] for question in analysis["ambiguities"])
        model.assert_not_called()
    request["clarifications"] = [{"ambiguityId":question["ambiguityId"],"sourcePassage":question["sourcePassage"],"answer":"Discuss the plan." if question["category"] == "requestedAction" else "November 20, 2026 at 17:00 America/New_York."} for question in analysis["ambiguities"]]
    response = client.post("/api/improve", json=request)
    assert response.status_code == 200
    assert response.json()["analysis"]["confirmedContext"][0]["origin"] == "userConfirmedContext"

def testChangedSourceRejectsStaleClarification():
    original = "We need to circle back on the logistics plan."
    question = findAmbiguities(original)[0]
    response = client.post("/api/improve", json={"originalDraft":"Please review the plan.","audience":{"group":"Team"},"clarifications":[{"ambiguityId":question.ambiguityId,"sourcePassage":question.sourcePassage,"answer":"Discuss the plan."}]})
    assert response.status_code == 422

def testOrdinaryLanguageDoesNotInterrupt():
    assert not findAmbiguities("Please review the logistics plan by November 20, 2026. Thanks for your help.")
    assert not findAmbiguities("Please review the plan before EOD (17:00 America/New_York on November 20, 2026).")

def testSourceCategoriesAndOrigins():
    original = "The authentication bug is resolved. CSV timeouts remain unresolved. We may miss the date. Venue B lacks step-free access. We will deliver on November 20, 2026. Please review the report. Notifications improved."
    result = extractFacts(original)
    categories = {category for fact in result.facts for category in fact.categories}
    assert {"resolvedIssue","unresolvedIssue","technicalFact","uncertainty","risk","accessibility","importantLimitation","commitment","date","requestedAction","accomplishment"}.issubset(categories)
    assert all(fact.sourcePassage in original and fact.origin == "explicitSource" for fact in result.facts)
    assert extractFacts("We need to circle back on the plan.").facts[0].origin == "unknown"

def testChangedUncertaintyAndCausalAddition():
    result = validateMeaning("CSV exports may fail.", "CSV exports are reliable because we upgraded the system.")
    assert {"uncertaintyChanged","unsupportedExplanation"}.issubset({finding.category for finding in result.findings})

def testImprovementIsNotResolution():
    result = validateMeaning("Session-expiration notifications improved.", "Session-expiration notifications are resolved.")
    assert "statusChanged" in {finding.category for finding in result.findings}

def testNegativeResultParaphraseAndStatusHeader():
    negative = validateMeaning("We missed our Q2 target by 15%.","We did not meet our Q2 target. The variance is 15%.")
    assert "negativeInformationChanged" not in {finding.category for finding in negative.findings}
    status = validateMeaning("CSV export timeouts remain unresolved.","The following issue remains unresolved:\n- CSV export timeouts.")
    assert "statusChanged" not in {finding.category for finding in status.findings}
    action = validateMeaning("Please validate the authentication fix.","We request your validation of the authentication fix.")
    assert "changedAction" not in {finding.category for finding in action.findings}

def testUnsupportedAttachmentAndConsequence():
    result = validateMeaning("Please review the sales figures.","Please review the attached sales figures. This means our work is complete.")
    assert {"unsupportedAddition","unsupportedExplanation"}.issubset({finding.category for finding in result.findings})

def testInventedAccomplishmentAndOrdinaryActionParaphrase():
    result = validateMeaning("Please review the performance report.","Please inspect the performance report. We doubled performance.")
    categories = {finding.category for finding in result.findings}
    assert "unsupportedAccomplishment" in categories
    assert "changedAction" not in categories
    negative = validateMeaning("I have not evaluated the creative work.","The creative evaluation has not been completed.")
    assert "unsupportedAccomplishment" not in {finding.category for finding in negative.findings}

def testLongAmbiguousPassageAndVersionKeepEvidence():
    original = "Please circle back on version 2.4.1 " + "with context " * 170 + "before EOD."
    questions = findAmbiguities(original)
    assert len(questions) == 2
    assert all(question.sourcePassage == original for question in questions)

def testConfirmedDeadlineCannotBeOmitted():
    request = scenarioRequest(scenarios[2])
    result = validateMeaning(request.originalDraft,"Please discuss the logistics plan again. A written update is not requested.",request.audience,request.clarifications)
    assert {"deadlineChange","numericalChange"}.issubset({finding.category for finding in result.findings})

def testConfirmedContextNumbersKeepFieldBoundaries():
    request = scenarioRequest(scenarios[2])
    request.clarifications[-1].answer = "November 20, 2026"
    request.audience.requiredDetails = "15%"
    draft = "Please discuss the logistics plan again by November 20, 2026. A written update is not requested. Retain 15%."
    result = validateMeaning(request.originalDraft,draft,request.audience,request.clarifications)
    assert "numericalChange" not in {finding.category for finding in result.findings}

def testExplanationsUseRealObservableEvidence(monkeypatch):
    monkeypatch.setenv("COMMUNICATION_PROVIDER", "mock")
    response = client.post("/api/improve", json={"originalDraft":"Please review the plan.\nThe budget may change.","audience":{"group":"Team","requiredDetails":"Keep budget uncertainty."}}).json()
    assert response["processingMilliseconds"]["preparation"] >= 0
    assert response["analysis"]["confirmedContext"][0]["evidenceSource"] == "audienceContext"
    for change in response["changeDetails"]:
        assert change["sourceEvidence"] in "Please review the plan.\nThe budget may change."
        assert change["requiresHumanReview"] is True

def testMockSemanticReviewIsExplicitlyUnavailable(monkeypatch):
    monkeypatch.setenv("COMMUNICATION_PROVIDER", "mock")
    response = client.post("/api/review",json={"originalDraft":"Please review the plan.","improvedDraft":"Please review the plan."}).json()
    assert response["reviewStatus"] == "unavailable"
    assert response["independent"] is False

def testSemanticEvidenceIsVerified():
    class Reviewer:
        def reviewMeaning(self, request):
            return SemanticReport(findings=[{"category":"inventedPraise","severity":"warning","explanation":"New praise.","generatedText":"Excellent work."},{"category":"criticalOmission","severity":"error","explanation":"Invented evidence.","sourceEvidence":"Not actually in the source."}])
    result = reviewMeaning(ValidationRequest(originalDraft="Please revise the document.", improvedDraft="Excellent work."), Reviewer())
    assert len(result.findings) == 1
    assert result.findings[0].reviewMethod == "semanticModel"
    assert any("Discarded 1" in limitation for limitation in result.limitations)

def testSemanticProviderFailureDoesNotBecomePassedReview():
    class Reviewer:
        def reviewMeaning(self, request):
            raise ProviderUnavailable("offline")
    result = reviewMeaning(ValidationRequest(originalDraft="Please review.",improvedDraft="Please review."), Reviewer())
    assert result.reviewStatus == "unavailable"
    assert not result.independent

def testAllUnsupportedReviewEvidenceIsUnavailable():
    class Reviewer:
        def reviewMeaning(self, request):
            return SemanticReport(findings=[{"category":"criticalOmission","severity":"error","explanation":"Missing.","sourceEvidence":"Fabricated quotation."}])
    result = reviewMeaning(ValidationRequest(originalDraft="Please review the plan.",improvedDraft="Please review the plan."),Reviewer())
    assert result.reviewStatus == "unavailable"

def testGenerationUsesOneInferenceAndNoAutomaticModelReview():
    from app.agentWorkflow import improveEmail
    class Provider:
        name = "test"
        isMock = False
        calls = 0
        def improve(self, request):
            self.calls += 1
            return request.originalDraft
        def reviewMeaning(self, request):
            raise AssertionError("Review must be explicitly requested.")
    provider = Provider()
    result = improveEmail(EmailRequest(originalDraft="Please review the plan.",audience={"group":"Team"}),provider)
    assert provider.calls == 1
    assert result.validation.semanticStatus == "unavailable"

def testOllamaReviewRequestsStructuredJson():
    body = {"done":True,"done_reason":"stop","message":{"role":"assistant","content":"{\"findings\":[]}"}}
    with patch("app.providers.ollamaProvider.openLocalRequest",return_value=BytesIO(json.dumps(body).encode())) as openRequest:
        result = OllamaProvider("http://127.0.0.1:11434","qwen3.5:4b").reviewMeaning(ValidationRequest(originalDraft="Please review.",improvedDraft="Please review."))
        assert not result.findings
        payload = json.loads(openRequest.call_args.args[0].data)
        assert payload["format"]["type"] == "object"
        assert payload["think"] is False
