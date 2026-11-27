"""Synthetic credentials only; no real access codes or stored hashes in source."""
from dataclasses import replace
from concurrent.futures import ThreadPoolExecutor
import asyncio
from datetime import datetime,timezone
import json
from threading import Event
import pytest
from fastapi.testclient import TestClient
from app.main import createApp
from app.betaSecurity import BetaSettings,BetaBoundary,BetaControl
from app.betaCodes import updateCodes
from app.providers.ollamaProvider import OllamaProvider

origin='https://ritmoagent.netlify.app'


@pytest.fixture
def betaData(tmp_path,monkeypatch):
    monkeypatch.setattr('app.betaCodes.secrets.token_urlsafe',lambda size:'x'*43)
    path=tmp_path/'codes.json'
    first=updateCodes(path,'create','reviewer01')
    second=updateCodes(path,'create','reviewer02')
    return path,first,second


def clientFor(data,**settings):
    return TestClient(createApp(replace(BetaSettings(enabled=True,origins=(origin,),codeFile=str(data[0])),**settings)))


def auth(token):return {'Authorization':'Bearer '+token,'Origin':origin}


def testAllApiEndpointsRequireCode(betaData):
    with clientFor(betaData) as client:
        for route in ['/api/health','/api/analyze','/api/improve','/api/validate','/api/adaptResponse','/api/adaptResponse/validate','/api/review','/api/readerAnalysis']:
            method=client.get if route.endswith('health') else client.post
            response=method(route)
            assert response.status_code==401
            assert response.headers['cache-control']=='no-store'


def testIndividualRevocationAndExpiry(betaData):
    path,first,second=betaData
    with clientFor(betaData) as client:
        verified=client.get('/api/health',headers=auth(first))
        assert verified.status_code==200 and verified.json()['betaAccessVerified'] is True
        updateCodes(path,'revoke','reviewer01')
        assert client.get('/api/health',headers=auth(first)).status_code==401
        assert client.get('/api/health',headers=auth(second)).status_code==200
        data=json.loads(path.read_text());data['codes'][1]['expiresAt']='2000-01-01T00:00:00+00:00';path.write_text(json.dumps(data))
        assert client.get('/api/health',headers=auth(second)).status_code==401


def testMissingStoreFailsClosed(betaData):
    with clientFor(betaData) as client:
        betaData[0].unlink()
        response=client.get('/api/health',headers=auth(betaData[1]))
        assert response.status_code==503
        assert str(betaData[0]) not in response.text and betaData[1] not in response.text


def testRestrictiveCorsAndProtectedMethods(betaData):
    with clientFor(betaData) as client:
        response=client.options('/api/readerAnalysis',headers={'Origin':origin,'Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'authorization,content-type'})
        assert response.status_code==200 and response.headers['access-control-allow-origin']==origin
        assert 'authorization' in response.headers['access-control-allow-headers'].lower()
        assert 'access-control-allow-credentials' not in response.headers
        bad=client.options('/api/health',headers={'Origin':'https://evil.example','Access-Control-Request-Method':'GET'})
        assert bad.status_code==400
        assert client.get('/api/health',headers={**auth(betaData[1]),'Origin':'null'}).status_code==403
        assert client.get('/api/health',headers={**auth(betaData[1]),'Origin':'https://evil.example'}).status_code==403


def testDocsAndInternalPathsNotExposed(betaData):
    with clientFor(betaData) as client:
        for route in ['/docs','/redoc','/openapi.json','/evaluation','/api/generate','/api/pull']:
            assert client.get(route,headers=auth(betaData[1])).status_code==404


def testRequestSizeDeclaredAndStreamed(betaData):
    with clientFor(betaData,maxRequestBytes=64) as client:
        for body in ['x'*65,iter([b'x'*40,b'y'*40])]:
            assert client.post('/api/analyze',headers=auth(betaData[1]),content=body).status_code==413


def testSanitizedValidationErrors(betaData):
    with clientFor(betaData) as client:
        response=client.post('/api/analyze',headers=auth(betaData[1]),json={'originalDraft':{'private':'DO NOT ECHO'},'audience':{}})
        assert response.status_code==422 and 'DO NOT ECHO' not in response.text


def testPerCodeRateLimits(betaData):
    with clientFor(betaData,requestsPerMinute=2) as client:
        assert [client.get('/api/health',headers=auth(betaData[1])).status_code for _ in range(3)]==[200,200,429]
        assert client.get('/api/health',headers=auth(betaData[2])).status_code==200
    with clientFor(betaData,inferencesPerMinute=1) as client:
        assert client.post('/api/readerAnalysis',headers=auth(betaData[1]),json={}).status_code==422
        response=client.post('/api/adaptResponse',headers=auth(betaData[1]),json={})
        assert response.status_code==429 and response.headers['retry-after']


def testFailedAuthDoesNotBlockValidCodesOrTrustSpoofedHeaders(betaData):
    with clientFor(betaData,failedAuthPerMinute=1) as client:
        assert client.get('/api/health',headers={'CF-Connecting-IP':'1.1.1.1'}).status_code==401
        assert client.get('/api/health',headers={'CF-Connecting-IP':'8.8.8.8'}).status_code==429
        assert client.get('/api/health',headers=auth(betaData[1])).status_code==200


def testOneActualInferenceAtATime(betaData,monkeypatch):
    monkeypatch.setenv('COMMUNICATION_PROVIDER','ollama')
    entered=Event();finish=Event()
    def blocked(self,instructions,data,*args,**kwargs):
        entered.set();assert finish.wait(5)
        return json.dumps({'adaptedDraft':json.loads(data)['originalDraft'],'styleAdjustments':[]})
    monkeypatch.setattr(OllamaProvider,'chat',blocked)
    request={'originalDraft':'I can share the plan.','receivedEmail':'','targetStyle':'Driver','audience':{'group':'Team'}}
    with clientFor(betaData) as client,ThreadPoolExecutor(max_workers=2) as pool:
        first=pool.submit(client.post,'/api/adaptResponse',headers=auth(betaData[1]),json=request)
        try:
            assert entered.wait(3)
            busy=client.post('/api/adaptResponse',headers=auth(betaData[2]),json=request)
            assert busy.status_code==503 and busy.headers['retry-after']=='15'
        finally:finish.set()
        assert first.result(timeout=5).status_code==200
        assert client.post('/api/adaptResponse',headers=auth(betaData[2]),json=request).status_code==200


def testRequestCapacityBound(betaData):
    application=createApp(BetaSettings(enabled=True,origins=(origin,),codeFile=str(betaData[0]),maxRequests=1))
    application.state.betaControl.requests.acquire()
    with TestClient(application) as client:
        assert client.get('/api/health',headers=auth(betaData[1])).status_code==503
    application.state.betaControl.requests.release()


def testBodyDeadlineReleasesCapacity(betaData,monkeypatch):
    import app.betaSecurity as security
    actual=asyncio.timeout
    monkeypatch.setattr(security.asyncio,'timeout',lambda seconds:actual(.005))
    control=BetaControl(BetaSettings(enabled=True,origins=(origin,),codeFile=str(betaData[0])))
    messages=[]
    async def unused(*args):raise AssertionError('Slow body must never reach handler')
    async def receive():await asyncio.sleep(1);return {'type':'http.request','body':b''}
    async def send(message):messages.append(message)
    scope={'type':'http','path':'/api/analyze','method':'POST','client':('127.0.0.1',1),'headers':[(b'authorization',('Bearer '+betaData[1]).encode())]}
    asyncio.run(BetaBoundary(unused,control)(scope,receive,send))
    assert messages[0]['status']==408 and control.requests.acquire(blocking=False)
    control.requests.release()


def testBetaStartupValidation(betaData,monkeypatch):
    monkeypatch.setenv('BETA_ENABLED','true');monkeypatch.setenv('COMMUNICATION_PROVIDER','ollama');monkeypatch.setenv('BETA_CODE_FILE',str(betaData[0]))
    monkeypatch.delenv('BETA_ALLOWED_ORIGINS',raising=False)
    assert BetaSettings.fromEnvironment().origins==(origin,)
    for bad in ['*','https://*.netlify.app','http://ritmoagent.netlify.app','https://ritmoagent.netlify.app/']:
        monkeypatch.setenv('BETA_ALLOWED_ORIGINS',bad)
        with pytest.raises(ValueError):BetaSettings.fromEnvironment()
    monkeypatch.setenv('BETA_ALLOWED_ORIGINS',origin);monkeypatch.setenv('COMMUNICATION_PROVIDER','mock')
    with pytest.raises(ValueError):BetaSettings.fromEnvironment()


def testCodeAdministrationStoresOnlyHashesAndRejectsReuse(betaData):
    data=json.loads(betaData[0].read_text())
    assert betaData[1] not in betaData[0].read_text()
    assert all(len(entry['tokenHash'])==64 for entry in data['codes'])
    updateCodes(betaData[0],'revoke','reviewer01')
    with pytest.raises(ValueError):updateCodes(betaData[0],'create','reviewer01')


def testWorkerKeepsInferenceSlotWhenAwaiterCancelled(betaData,monkeypatch):
    from app.betaSecurity import GuardedOllamaProvider
    from fastapi import HTTPException
    control=BetaControl(BetaSettings())
    entered=Event();finish=Event()
    def blocked(*args,**kwargs):
        entered.set();assert finish.wait(3);return 'synthetic'
    monkeypatch.setattr(OllamaProvider,'chat',blocked)
    provider=GuardedOllamaProvider('http://127.0.0.1:11434','qwen3.5:4b',control)
    with ThreadPoolExecutor(max_workers=1) as pool:
        async def scenario():
            awaiting=asyncio.get_running_loop().run_in_executor(pool,provider.chat,'synthetic','{}')
            assert await asyncio.to_thread(entered.wait,2)
            awaiting.cancel()
            try:
                with pytest.raises(HTTPException) as error:provider.chat('synthetic','{}')
                assert error.value.status_code==503
            finally:finish.set()
        asyncio.run(scenario())
    assert control.inference.acquire(blocking=False);control.inference.release()


def testOperatorLockPreventsLostUpdates(betaData):
    path=betaData[0];lock=path.with_name(path.name+'.lock');lock.write_text('synthetic test lock')
    before=path.read_bytes()
    with pytest.raises(FileExistsError):updateCodes(path,'revoke','reviewer01')
    assert path.read_bytes()==before


def testRequestSlotsReleaseAfterRejection(betaData):
    with clientFor(betaData,maxRequestBytes=64,maxRequests=1) as client:
        assert client.post('/api/analyze',headers=auth(betaData[1]),content='x'*65).status_code==413
        assert client.get('/api/health',headers=auth(betaData[1])).status_code==200


def testLocalModeDoesNotClaimBetaVerification():
    with TestClient(createApp(BetaSettings())) as client:
        assert client.get('/api/health').json()['betaAccessVerified'] is False


def testInferenceExceptionReleasesWorkerSlot(monkeypatch):
    from app.betaSecurity import GuardedOllamaProvider
    from app.providers.modelProvider import ProviderUnavailable
    def failed(*args,**kwargs):raise ProviderUnavailable('Synthetic failure')
    monkeypatch.setattr(OllamaProvider,'chat',failed)
    control=BetaControl(BetaSettings())
    provider=GuardedOllamaProvider('http://127.0.0.1:11434','qwen3.5:4b',control)
    with pytest.raises(ProviderUnavailable):provider.chat('synthetic','{}')
    assert control.inference.acquire(blocking=False);control.inference.release()


def testAuthenticatedDeterministicWorkflowAndClarifications(betaData,monkeypatch):
    monkeypatch.setenv('COMMUNICATION_PROVIDER','ollama')
    with clientFor(betaData) as client:
        original='The report remains preliminary.'
        request={'originalDraft':original,'audience':{'group':'Team'}}
        assert client.post('/api/analyze',headers=auth(betaData[1]),json=request).status_code==200
        validation={**request,'improvedDraft':original}
        for path in ['/api/validate','/api/adaptResponse/validate']:
            response=client.post(path,headers=auth(betaData[1]),json=validation)
            assert response.status_code==200 and response.json()['status']=='reviewRequired'
        ambiguous={'originalDraft':'We need to circle back on the logistics plan before EOD.','audience':{'group':'Team'}}
        response=client.post('/api/improve',headers=auth(betaData[1]),json=ambiguous)
        assert response.status_code==409 and response.json()['detail']['code']=='clarificationRequired'
