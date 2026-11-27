import json
from io import BytesIO
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
from app.emailSchemas import EmailRequest
from app.providers.ollamaProvider import OllamaProvider

client = TestClient(app)
def contextRequest(goal="Request a decision", draft="We reviewed the proposed changes."):
    return {"originalDraft":draft,"audience":{"group":"Custom complete group","communicationObjectives":goal,"technicalBackground":"Known background","preferences":"Short paragraphs","requiredDetails":""}}

def testMissingDecisionStopsBeforeProviderAndAcceptsBoundAnswer():
    request = contextRequest()
    analysis = client.post('/api/analyze',json=request).json()
    question = analysis['ambiguities'][0]
    assert question['question'] == 'What decision are you asking the recipients to make?'
    with patch('app.providers.mockProvider.MockProvider.improve') as generate:
        assert client.post('/api/improve',json=request).status_code == 409
        generate.assert_not_called()
    request['clarifications']=[{**{key:question[key] for key in ['ambiguityId','sourcePassage']},'answer':'Please approve the proposed changes.'}]
    assert client.post('/api/analyze',json=request).json()['ambiguities'] == []
    request['audience']['communicationObjectives']='Request a decision about budget'
    assert client.post('/api/analyze',json=request).status_code == 422

def testConcreteDecisionAndNondecisionGoalsNeedNoExtraQuestion():
    for goal,draft in [('Request a decision','Please approve the proposed changes.'),('Request a decision','Please decide whether to release version 2.4.1.'),('Share an update','We reviewed the proposed changes.')]:
        result=client.post('/api/analyze',json=contextRequest(goal,draft)).json()
        assert result['ambiguities'] == []
        assert result['facts']
        assert result['confirmedContext'] == []

def testStructuredContextReachesOllamaUnchanged():
    request=EmailRequest(**contextRequest('My exact custom objective','Version 2.4.1 is in staging.'))
    response={'done':True,'message':{'role':'assistant','content':'Version 2.4.1 is in staging.'}}
    with patch('app.providers.ollamaProvider.openLocalRequest',return_value=BytesIO(json.dumps(response).encode())) as send:
        OllamaProvider('http://127.0.0.1:11434','localModel').improve(request)
    payload=json.loads(send.call_args.args[0].data)
    assert json.loads(payload['messages'][1]['content']) == request.model_dump()
    assert 'not evidence of a decision' in payload['messages'][0]['content']
    assert 'Example only' not in payload['messages'][1]['content']

def testApiPassesAllContextToProvider(monkeypatch):
    monkeypatch.setenv('COMMUNICATION_PROVIDER','mock')
    request=contextRequest('Share an update','Version 2.4.1 is in staging.')
    request['audience']['requiredDetails']='Retain version 2.4.1'
    with patch('app.providers.mockProvider.MockProvider.improve',return_value=request['originalDraft']) as generate:
        response=client.post('/api/improve',json=request)
    assert response.status_code == 200
    assert generate.call_args.args[0].model_dump() == EmailRequest(**request).model_dump()
