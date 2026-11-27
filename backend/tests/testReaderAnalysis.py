"""Internal demonstration policy; source verification is not semantic verification."""
from io import BytesIO
import json
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from app.main import app
from app.readerAnalysis import ReaderRequest,ReaderReport,ReaderObservation,ReaderResult,analyzeReader,readerModelSchema
from app.providers.ollamaProvider import OllamaProvider

client=TestClient(app)


class ReaderStub:
    def __init__(self,report):self.report=report
    def analyzeReader(self,request):return self.report


def observe(style,characteristic,excerpt):
    return ReaderObservation(style=style,characteristic=characteristic,excerpt=excerpt)


def analyze(email,observations,primary=None,uncertainty='mixed'):
    report=ReaderReport(primaryStyle=primary,uncertainty=uncertainty,observations=observations)
    return analyzeReader(ReaderRequest(receivedEmail=email),ReaderStub(report))


@pytest.mark.parametrize('style,characteristic,parts',[
    ('Expressive','vision',['Imagine a brighter courtyard.','Picture the possibilities.','Approve the plan.']),
    ('Amiable','empathy',['I know the change is difficult.','I care about the impact on you.','Approve the plan.']),
    ('Driver','actions',['Choose option B.','Approve the order.','I know this affects you.']),
    ('Analytical','structure',['Which scope applies?','What depends on approval?','I know this affects you.']),
])
def testSupportedDemonstrationForEveryStyleDoesNotPublishAggregation(style,characteristic,parts,caplog):
    caplog.set_level('DEBUG',logger='app.readerAnalysis')
    other=observe('Amiable','empathy',parts[2]) if style in {'Driver','Analytical'} else observe('Driver','actions',parts[2])
    email=' '.join(parts)
    result=analyze(email,[observe(style,characteristic,parts[0]),observe(style,characteristic,parts[1]),other],primary=None,uncertainty='insufficientEvidence')
    assert result.primaryStyle==style and result.uncertainty=='tentative'
    assert result.uncertaintyReason is None and len(result.observations)==3
    public=result.model_dump_json()
    for forbidden in ['majority','2 of 3','matching characteristics','confidence','acceptedStyleCounts','modelPrimaryStyle','decisionMethod','observations invalid']:
        assert forbidden.lower() not in public.lower()
    diagnostics=caplog.records[-1].readerDiagnostics
    assert diagnostics['modelPrimaryStyle'] is None and diagnostics['modelUncertainty']=='insufficientEvidence'
    assert diagnostics['validatedPrimaryStyle']==style
    assert email not in caplog.text and all(p not in caplog.text for p in parts)


@pytest.mark.parametrize('size',[0,1])
def testIncompleteEvidenceIsInconclusiveEvenIfTheModelProposedAStyle(size):
    parts=['Choose B.','Approve it.','Send the order.']
    result=analyze(' '.join(parts),[observe('Driver','actions',p) for p in parts[:size]],'Driver','tentative')
    assert result.primaryStyle is None and result.uncertainty=='insufficientEvidence'
    assert len(result.observations)==size and 'model' not in result.explanation.lower()


def testAllDistinctStylesRemainInconclusive():
    result=analyze('Imagine it. Choose B. Which version?',[
        observe('Expressive','vision','Imagine it.'),observe('Driver','actions','Choose B.'),observe('Analytical','structure','Which version?')])
    assert result.primaryStyle is None


def testApplicationDecisionIsSeparateFromWrongRawModelDecision(caplog):
    caplog.set_level('DEBUG',logger='app.readerAnalysis')
    result=analyze('Choose B. Approve it. I can help.',[
        observe('Driver','actions','Choose B.'),observe('Driver','actions','Approve it.'),observe('Amiable','teamwork','I can help.')],'Expressive','mixed')
    assert result.primaryStyle=='Driver' and result.uncertainty=='tentative'
    info=caplog.records[-1].readerDiagnostics
    assert info['modelPrimaryStyle']=='Expressive' and info['validatedPrimaryStyle']=='Driver'
    assert 'Expressive' not in result.explanation


@pytest.mark.parametrize('bad',[
    observe('Driver','actions','Invented quote.'),
    observe('Driver','empathy','Send the order.'),
])
def testInvalidEvidenceDoesNotContribute(bad,caplog):
    caplog.set_level('DEBUG',logger='app.readerAnalysis')
    result=analyze('Choose B. Approve it. Send the order.',[observe('Driver','actions','Choose B.'),observe('Driver','actions','Approve it.'),bad],'Driver','tentative')
    assert result.primaryStyle=='Driver' and len(result.observations)==2
    assert 'left out' in ' '.join(result.limitations)
    assert 'invalid observation(s)' not in ' '.join(result.limitations)


@pytest.mark.parametrize('style,key',[('Driver','actions'),('Amiable','teamwork')])
def testSamePassageRelabeledDoesNotBecomeDistinctEvidence(style,key,caplog):
    caplog.set_level('DEBUG',logger='app.readerAnalysis')
    result=analyze('Choose B. Approve it.',[
        observe('Driver','actions','Choose B.'),observe(style,key,'Choose B.'),observe('Driver','actions','Approve it.')])
    assert result.primaryStyle=='Driver' and len(result.observations)==2
    assert caplog.records[-1].readerDiagnostics['duplicateObservations']==1


def testOverlappingEvidenceDoesNotCountAsIndependent(caplog):
    caplog.set_level('DEBUG',logger='app.readerAnalysis')
    result=analyze('Please choose B today. Approve it.',[
        observe('Driver','actions','Please choose B today.'),observe('Driver','directness','choose B'),observe('Driver','actions','Approve it.')])
    assert result.primaryStyle=='Driver' and len(result.observations)==2
    assert caplog.records[-1].readerDiagnostics['overlappingObservations']==1


@pytest.mark.parametrize('email,quote,expected,corrections',[
    ('We work together.','We work together.','We work together.',0),
    ('We work together.','"We work together."','We work together.',1),
    ('She said "We work together." today.','"We work together."','"We work together."',0),
    ('We work "together" today.','"We work "together" today."','We work "together" today.',1),
    ('We work\n together.','"We work\n together."','We work\n together.',1),
])
def testExactAndNarrowWrapperVerificationUnchanged(email,quote,expected,corrections,caplog):
    caplog.set_level('DEBUG',logger='app.readerAnalysis')
    report=ReaderReport(primaryStyle='Amiable',uncertainty='tentative',observations=[observe('Amiable','teamwork',quote)])
    result=analyzeReader(ReaderRequest(receivedEmail=email),ReaderStub(report))
    assert result.observations[0].excerpt==expected and report.observations[0].excerpt==quote
    assert caplog.records[-1].readerDiagnostics['quotationWrapperCorrections']==corrections
    assert quote not in caplog.text and email not in caplog.text


@pytest.mark.parametrize('quote',[
    '"We collaborate."','"We work together!"','"We together."','"An absent excerpt."','""We work together.""','“We work together.”',
    "'We work together.'",' "We work together." ','"we work together."','"We  work together."','"We work\ntogether."','"We ... together."','" "',
])
def testParaphrasePunctuationCaseWhitespaceAndExtraWrappersStillRejected(quote):
    result=analyze('We work together.',[observe('Amiable','teamwork',quote)])
    assert result.primaryStyle is None and result.observations==[]


def testConflictingBadEvidenceDiagnosticsStayPrivate(caplog):
    caplog.set_level('DEBUG',logger='app.readerAnalysis')
    invalid=observe('Driver','empathy','PRIVATE invented quote')
    result=analyze('Private email source.',[invalid,invalid])
    info=caplog.records[-1].readerDiagnostics
    assert info['invalidQuotations']==1 and info['incompatiblePairings']==1 and info['duplicateObservations']==1
    assert 'PRIVATE' not in caplog.text and 'Private email source.' not in caplog.text
    assert not any(str(n)+' invalid' in ' '.join(result.limitations) for n in range(4))


def testRawSchemaOnlyRequestsCompactFields():
    schema=readerModelSchema()
    assert set(schema['properties'])=={'primaryStyle','uncertainty','observations'}
    assert set(schema['$defs']['ReaderObservation']['properties'])=={'style','characteristic','excerpt'}
    assert schema['properties']['observations']['maxItems']==3
    assert ReaderResult.model_json_schema()['properties']['observations']['maxItems']==3
    with pytest.raises(ValidationError):
        ReaderReport(primaryStyle=None,uncertainty='mixed',observations=[observe('Driver','actions','x')]*4)


def testQuotationAccuracyDoesNotProveStyleInterpretation():
    result=analyze('Thanks. See you tomorrow. Goodbye.',[
        observe('Amiable','warmth','Thanks.'),observe('Amiable','teamwork','See you tomorrow.'),observe('Driver','actions','Goodbye.')])
    assert result.primaryStyle=='Amiable'  # Demonstration labels can still be semantically weak.
    assert 'may be incorrect' in ' '.join(result.limitations)


def testMockAndEndpointInputErrorsRemainHonest(monkeypatch):
    monkeypatch.setenv('COMMUNICATION_PROVIDER','mock')
    assert client.post('/api/readerAnalysis',json={'receivedEmail':'   '}).status_code==422
    response=client.post('/api/readerAnalysis',json={'receivedEmail':'Synthetic email.'})
    assert response.status_code==503 and 'no fabricated analysis' in response.json()['detail']


def testActualTransportHasCompactSchemaSeparateEmailAndNoSettingsChange(monkeypatch):
    monkeypatch.setenv('COMMUNICATION_PROVIDER','ollama')
    email='Choose B. Approve it. I can help.';sent=[]
    report={'primaryStyle':'Amiable','uncertainty':'mixed','observations':[
        {'style':'Driver','characteristic':'actions','excerpt':'Choose B.'},
        {'style':'Driver','characteristic':'actions','excerpt':'Approve it.'},
        {'style':'Amiable','characteristic':'teamwork','excerpt':'I can help.'}]}
    def capture(request):
        sent.append(json.loads(request.data))
        return BytesIO(json.dumps({'done':True,'message':{'role':'assistant','content':json.dumps(report)}}).encode())
    with patch('app.providers.ollamaProvider.openLocalRequest',capture):response=client.post('/api/readerAnalysis',json={'receivedEmail':email})
    assert response.status_code==200 and response.json()['primaryStyle']=='Driver'
    payload=sent[0];assert payload['format']==readerModelSchema()
    assert payload['messages'][1]=={'role':'user','content':json.dumps({'receivedEmail':email},separators=(',',':'))}
    assert email not in payload['messages'][0]['content']
    assert 'options' not in payload and payload['think'] is False and payload['stream'] is False
    assert 'acceptedStyleCounts' not in response.text and 'Mixed characteristics' not in response.text


def testOversizedModelReportFailsSafelyInsteadOfChoosingConvenientEvidence(monkeypatch):
    monkeypatch.setenv('COMMUNICATION_PROVIDER','ollama')
    value={'primaryStyle':'Driver','uncertainty':'tentative','observations':[{'style':'Driver','characteristic':'actions','excerpt':'Choose B.'}]*4}
    wire={'done':True,'message':{'role':'assistant','content':json.dumps(value)}}
    with patch('app.providers.ollamaProvider.openLocalRequest',return_value=BytesIO(json.dumps(wire).encode())):
        response=client.post('/api/readerAnalysis',json={'receivedEmail':'Choose B.'})
    assert response.status_code==503 and 'invalid structured output' in response.json()['detail']
    assert '4 validation' not in response.text and 'at most' not in response.text


@pytest.mark.parametrize('style,key',[('Expressive','vision'),('Amiable','empathy'),('Driver','actions'),('Analytical','structure')])
def testTwoAcceptedObservationsSupportStyleWithoutThird(style,key):
    result=analyze('First source passage. Second source passage.',[observe(style,key,'First source passage.'),observe(style,key,'Second source passage.')])
    assert result.primaryStyle==style and result.uncertainty=='tentative'


def testTwoDifferentStylesRemainInconclusive():
    result=analyze('Choose B. I can help.',[observe('Driver','actions','Choose B.'),observe('Amiable','teamwork','I can help.')])
    assert result.primaryStyle is None
