"""Source-fixture and targeted warning regressions, not semantic-accuracy proofs."""
import json
from pathlib import Path
import pytest
from app.emailSchemas import Finding
from app.composeAdaptation import ComposeReport,ComposeValidationRequest,composeInstructions,validateAdaptedResponse
from app.composePreservation import reviewAdaptationFidelity,timeMarkers


cases=json.loads((Path(__file__).parent/'fixtures'/'composeFidelityCases.json').read_text(encoding='utf-8'))['cases']
byId={case['id']:case for case in cases}


def check(original,adapted):
    return validateAdaptedResponse(ComposeValidationRequest(originalDraft=original,improvedDraft=adapted))


@pytest.mark.parametrize('case',cases,ids=lambda case:case['id'])
def testOriginalFixtureStaysUnchangedWithNoAddedFidelityWarnings(case):
    original=case['originalDraft']
    result=check(original,original)
    assert not result.findings
    assert result.status=='reviewRequired' and result.semanticStatus=='unavailable'
    assert original==case['originalDraft']
    assert 'Subject: Re:' in original and original.endswith('Morgan')


@pytest.mark.parametrize('caseId,source,replacement,category',[
    ('atlas','40 people','41 people','numericalChange'),
    ('atlas','80%','85%','numericalChange'),
    ('atlas',"I'm planning to send",'I will send','unsupportedCommitment'),
    ('atlas','December 4','December 5','deadlineChange'),
    ('schedule','The new schedule started last Monday. ','','timingChanged'),
    ('schedule','Two team members','Several team members','quantityChanged'),
    ('schedule',"We haven't agreed",'We have agreed','decisionStatusChanged'),
    ('schedule',"I'm planning to share",'I will share','unsupportedCommitment'),
    ('schedule',"I'm planning to share an update with everyone after the meeting.",'','sourcePassageChanged'),
    ('vendor','$4,800','$4,900','numericalChange'),
    ('vendor',"I haven't booked anything yet",'I have booked everything','decisionStatusChanged'),
    ('vendor','I can send you the complete quote','Please approve the complete quote','offerChangedToRequirement'),
    ('vendor'," if you'd like to review it",'','conditionChanged'),
    ('vendor','3:00 PM','4:00 PM','timingChanged'),
    ('vendor','Thanks,\nMorgan','','senderIdentityChanged'),
])
def testTargetedSourceMutationIsFlaggedWithoutChangingDraft(caseId,source,replacement,category):
    original=byId[caseId]['originalDraft'];adapted=original.replace(source,replacement)
    assert original!=adapted
    result=check(original,adapted)
    assert category in {finding.category for finding in result.findings}
    assert result.status=='reviewRequired' and result.semanticStatus=='unavailable'
    assert byId[caseId]['originalDraft']==original


@pytest.mark.parametrize('original,adapted,category',[
    ('I plan to send the report.','The report will be sent.','commitmentStrengthChanged'),
    ('I plan to send the report.','The report is scheduled for delivery.','commitmentStrengthChanged'),
    ('I can send the report.','I have sent the report.','commitmentStrengthChanged'),
    ('I will send the report.','I plan to send the report.','commitmentStrengthChanged'),
    ('The results are preliminary.','The results are final.','decisionStatusChanged'),
    ('Please review the export issue.','Please review the critical export issue.','addedSeverity'),
    ('We have three prototypes.','We have prototypes.','quantityChanged'),
    ("I can send the file if you'd like.",'If you approve, I can send the file.','conditionChanged'),
])
def testAdditionalBoundedWarnings(original,adapted,category):
    assert category in {finding.category for finding in reviewAdaptationFidelity(original,adapted,[])}


@pytest.mark.parametrize('original,adapted',[
    ('Two team members need support.','2 team members need support.'),
    ('Two team members need support.','Both team members need support.'),
    ('I plan to send the report.','I am planning to send the report.'),
    ('I will send the report.','The report will be sent.'),
    ('We support one another.','We work as one team.'),
    ('I reviewed both vendor options.','I reviewed the vendor options.'),
    ('I plan to send the report.','I plan to send the report; I will also bring the draft.'),
    ('Could you confirm the quote?','Please confirm the quote?'),
])
def testOrdinaryRephrasingDoesNotAddNewHeuristicWarnings(original,adapted):
    # Existing general wording warnings remain; do not add a new semantic claim.
    assert reviewAdaptationFidelity(original,adapted,[])==[]


def testEquivalentClockFormattingDoesNotAddTimingWarning():
    assert timeMarkers('Thursday at 3:00 PM')==timeMarkers('Thursday at 3 PM')


def testExistingCommitmentWarningIsNotDuplicatedAndIsNotRemoved():
    source='I plan to send the report.';output='I will send the report.'
    existing=[Finding(category='unsupportedCommitment',severity='warning',explanation='Review this commitment.',sourceEvidence=source,generatedText=output)]
    assert reviewAdaptationFidelity(source,output,existing)==[]
    assert len(existing)==1 and existing[0].category=='unsupportedCommitment'


def testRequestedAdjustmentSchemaMatchesExistingRuntimeBounds():
    item=ComposeReport.model_json_schema()['properties']['styleAdjustments']['items']
    assert item['minLength']==1 and item['maxLength']==240 and item['pattern']==r'\S'


@pytest.mark.parametrize('style',['Analytical','Amiable','Driver','Expressive'])
def testPrioritizedContractUsesOnlySelectedGuidanceAndNoRegressionAnswers(style):
    prompt=composeInstructions(style)
    assert [prompt.index(f'Priority {index}') for index in range(1,6)]==sorted(prompt.index(f'Priority {index}') for index in range(1,6))
    assert 'BOTH directions' in prompt and 'complete, usable' in prompt
    assert 'Never add content from it' in prompt and 'subordinate to meaning preservation' in prompt
    for case in cases:
        assert case['originalDraft'] not in prompt
    for privateToken in ['Project Atlas','Northstar','Morgan','Taylor','Showcase']:
        assert privateToken not in prompt
