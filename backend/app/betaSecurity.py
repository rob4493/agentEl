"""Opt-in private-beta boundary. Never stores email bodies or plaintext codes."""
from collections import deque
import asyncio
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import hmac
import ipaddress
import json
import logging
import os
from pathlib import Path
import re
from threading import BoundedSemaphore, Lock
from time import monotonic
from urllib.parse import urlparse
from fastapi import HTTPException
from .providers.ollamaProvider import OllamaProvider

inferencePaths={'/api/improve','/api/adaptResponse','/api/readerAnalysis','/api/review'}
betaContext=ContextVar('betaContext',default=None)
logger=logging.getLogger(__name__)


def envFlag(name,default='false'):
    value=os.getenv(name,default).lower()
    if value not in {'true','false'}:raise ValueError(f'{name} must be true or false')
    return value=='true'


@dataclass(frozen=True)
class BetaSettings:
    enabled: bool=False
    origins: tuple[str,...]=('http://localhost:5173','http://127.0.0.1:5173')
    codeFile: str=''
    maxRequestBytes: int=262144
    requestsPerMinute: int=60
    inferencesPerMinute: int=4
    failedAuthPerMinute: int=10
    maxRequests: int=8
    trustCloudflareIp: bool=False

    @classmethod
    def fromEnvironment(cls):
        if not envFlag('BETA_ENABLED'):return cls()
        origins=tuple(x.strip() for x in os.getenv('BETA_ALLOWED_ORIGINS','https://ritmoagent.netlify.app').split(',') if x.strip())
        if not origins:raise ValueError('Beta requires explicit allowed origins')
        for origin in origins:
            parsed=urlparse(origin)
            if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment or '*' in origin:
                raise ValueError('Beta origins must be exact HTTPS origins without paths or wildcards')
        if os.getenv('COMMUNICATION_PROVIDER')!='ollama':raise ValueError('Beta requires the explicitly configured local Ollama provider')
        OllamaProvider(os.getenv('OLLAMA_BASE_URL','http://127.0.0.1:11434'),os.getenv('OLLAMA_MODEL','qwen3.5:4b'))
        codeFile=os.getenv('BETA_CODE_FILE','')
        if not codeFile:raise ValueError('Beta requires a private access-code file')
        def integer(name,default,maximum):
            value=int(os.getenv(name,str(default)))
            if not 1<=value<=maximum:raise ValueError(f'Invalid {name}')
            return value
        settings=cls(True,origins,codeFile,integer('BETA_MAX_REQUEST_BYTES',262144,2097152),
            integer('BETA_REQUESTS_PER_MINUTE',60,1000),integer('BETA_INFERENCES_PER_MINUTE',4,60),
            integer('BETA_FAILED_AUTH_PER_MINUTE',10,100),integer('BETA_MAX_REQUESTS',8,32),envFlag('BETA_TRUST_CLOUDFLARE_IP'))
        readCodes(codeFile)  # Fail startup closed; never silently fall back to local-open mode.
        return settings


def readCodes(filename):
    try:
        with Path(filename).open('rb') as handle:content=handle.read(65537)
        if len(content)>65536:raise ValueError('Too large')
        data=json.loads(content)
        if set(data)!={'version','codes'} or type(data.get('version')) is not int or data['version']!=1 or not isinstance(data.get('codes'),list) or len(data['codes'])>128:raise ValueError('Invalid store')
        seen=set()
        for code in data['codes']:
            if set(code)!={'codeId','tokenHash','enabled','expiresAt'} or not re.fullmatch(r'[A-Za-z0-9_-]{3,48}',code['codeId']) or code['codeId'] in seen:raise ValueError('Invalid identity')
            if not re.fullmatch(r'[a-f0-9]{64}',code['tokenHash']) or type(code['enabled']) is not bool:raise ValueError('Invalid verifier')
            expiry=datetime.fromisoformat(code['expiresAt'])
            if expiry.tzinfo is None:raise ValueError('Expiry requires timezone')
            seen.add(code['codeId'])
        return data
    except (OSError,ValueError,TypeError,KeyError,AttributeError) as error:
        raise ValueError('Beta access configuration unavailable') from error


class WindowLimits:
    def __init__(self):self.windows={};self.lock=Lock()
    def admit(self,key,limit):
        now=monotonic()
        with self.lock:
            for stale in [k for k,v in self.windows.items() if not v or v[-1]<=now-60]:del self.windows[stale]
            if key not in self.windows and len(self.windows)>=4096:return False
            times=self.windows.setdefault(key,deque())
            while times and times[0]<=now-60:times.popleft()
            if len(times)>=limit:return False
            times.append(now);return True


class BetaControl:
    def __init__(self,settings):
        self.settings=settings
        self.requests=BoundedSemaphore(settings.maxRequests)
        self.inference=BoundedSemaphore(1)
        self.limits=WindowLimits()
        self.failedAuthLimits=WindowLimits()

    def authenticate(self,authorization):
        if not authorization or len(authorization)>200 or authorization[:7].lower()!='bearer ':return None
        token=authorization[7:]
        if not re.fullmatch(r'[A-Za-z0-9_-]{3,48}\.[A-Za-z0-9_-]{43}',token):return None
        identity=token.split('.',1)[0]
        data=readCodes(self.settings.codeFile)
        matched=next((entry for entry in data['codes'] if entry['codeId']==identity),None)
        candidate=hashlib.sha256(token.encode()).hexdigest()
        valid=hmac.compare_digest(candidate,matched['tokenHash'] if matched else '0'*64)
        if not valid or not matched or not matched['enabled'] or datetime.fromisoformat(matched['expiresAt'])<=datetime.now(timezone.utc):return None
        return identity


class GuardedOllamaProvider(OllamaProvider):
    def __init__(self,baseUrl,model,control):
        super().__init__(baseUrl,model);self.control=control
    def chat(self,*args,**kwargs):
        if not self.control.inference.acquire(blocking=False):
            raise HTTPException(503,'Beta inference capacity is busy; try again later.',headers={'Retry-After':'15'})
        # This guard is owned by the WORKER, not the HTTP task. Cancellation of
        # a waiting browser cannot release capacity before local inference ends.
        try:return super().chat(*args,**kwargs)
        finally:self.control.inference.release()


def header(scope,name):
    values=[value for key,value in scope.get('headers',[]) if key.lower()==name]
    return values[0].decode('latin-1') if len(values)==1 else None


async def reject(send,status,detail,retry=False):
    headers=[(b'content-type',b'application/json'),(b'cache-control',b'no-store'),(b'x-content-type-options',b'nosniff')]
    if status==401:headers.append((b'www-authenticate',b'Bearer'))
    if retry:headers.append((b'retry-after',b'60'))
    await send({'type':'http.response.start','status':status,'headers':headers})
    await send({'type':'http.response.body','body':json.dumps({'detail':detail}).encode()})


class BetaBoundary:
    def __init__(self,app,control):self.app=app;self.control=control
    async def __call__(self,scope,receive,send):
        if scope['type']!='http':return await self.app(scope,receive,send)
        settings=self.control.settings
        if not settings.enabled:return await self.app(scope,receive,send)
        path=scope['path']
        if not path.startswith('/api/'):return await reject(send,404,'Not found.')
        if scope['method'] not in {'GET','POST'}:return await reject(send,405,'Method not allowed.')
        if len([key for key,_ in scope.get('headers',[]) if key.lower()==b'origin'])>1:return await reject(send,403,'Origin not allowed.')
        origin=header(scope,b'origin')
        if origin is not None and origin not in settings.origins:return await reject(send,403,'Origin not allowed.')
        peer=(scope.get('client') or ('unknown',0))[0]
        # Only enable behind a loopback-only tunnel and --no-proxy-headers.
        if settings.trustCloudflareIp and peer in {'127.0.0.1','::1'}:
            candidate=header(scope,b'cf-connecting-ip')
            try:peer=str(ipaddress.ip_address(candidate))
            except (ValueError,TypeError):pass
        try:identity=self.control.authenticate(header(scope,b'authorization'))
        except ValueError:return await reject(send,503,'Beta access configuration unavailable.')
        if identity is None:
            allowed=self.control.failedAuthLimits.admit(('failedAuth',peer),settings.failedAuthPerMinute)
            return await reject(send,401 if allowed else 429,'A valid beta access code is required.' if allowed else 'Too many attempts; try later.',not allowed)
        if not self.control.limits.admit(('requests',identity),settings.requestsPerMinute):return await reject(send,429,'Beta request limit reached; try later.',True)
        if path in inferencePaths and not self.control.limits.admit(('inferences',identity),settings.inferencesPerMinute):return await reject(send,429,'Beta inference limit reached; try later.',True)
        if not self.control.requests.acquire(blocking=False):return await reject(send,503,'Beta request capacity is busy; try later.',True)
        context=betaContext.set(self.control)
        started=False
        try:
            lengths=[value for key,value in scope.get('headers',[]) if key.lower()==b'content-length']
            if lengths:
                if len(lengths)!=1 or not lengths[0].isdigit():return await reject(send,400,'Invalid request length.')
                if int(lengths[0])>settings.maxRequestBytes:return await reject(send,413,'Request exceeds the beta size limit.')
            content=bytearray()
            try:
                async with asyncio.timeout(10):
                    while True:
                        message=await receive()
                        if message['type']=='http.disconnect':return
                        chunk=message.get('body',b'')
                        if len(content)+len(chunk)>settings.maxRequestBytes:return await reject(send,413,'Request exceeds the beta size limit.')
                        content.extend(chunk)
                        if not message.get('more_body',False):break
            except TimeoutError:return await reject(send,408,'Request upload timed out.')
            used=False
            async def replay():
                nonlocal used
                if not used:
                    used=True;return {'type':'http.request','body':bytes(content),'more_body':False}
                return await receive()
            async def safeSend(message):
                nonlocal started
                if message['type']=='http.response.start':
                    started=True
                    headers=[(k,v) for k,v in message.get('headers',[]) if k.lower()!=b'cache-control']
                    headers.extend([(b'cache-control',b'no-store'),(b'x-content-type-options',b'nosniff')])
                    message={**message,'headers':headers}
                await send(message)
            await self.app(scope,replay,safeSend)
        except Exception as error:
            # No exception repr, request bodies, auth values or model output in responses/logs.
            if not started:await reject(send,500,'Beta request could not be completed.')
            logger.warning('betaRequestFailed type=%s',type(error).__name__)
        finally:
            betaContext.reset(context);self.control.requests.release()
