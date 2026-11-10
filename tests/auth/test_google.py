import json
import time
import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from app.auth import google,tokens
from app.core.config import settings
from app.core.errors import AuthError

@pytest.fixture
def proof(monkeypatch):
    key,_=tokens.configured_keys()
    public=key.public_key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    class Response:
        status=200
        data=json.dumps({'test':public}).encode()
    google._local.request=lambda *args,**kwargs:Response()
    nonce=tokens.secret()
    def issue(**changes):
        claims={'iss':'https://accounts.google.com','aud':settings.google_audience,'sub':'subject','iat':int(time.time()),'exp':int(time.time())+300,'nonce':nonce}
        claims.update(changes)
        return jwt.encode(claims,key,algorithm='RS256',headers={'kid':'test'}),tokens.digest(nonce)
    return issue


def test_signed_proof(proof):
    token,nonce=proof()
    assert google.verify_google(token,nonce)=='subject'

@pytest.mark.parametrize('changes',[{'iss':'attacker'},{'aud':'other'},{'exp':1},{'iat':int(time.time())+3600},{'nonce':'wrong'},{'sub':''},{'azp':'unknown-client'}])
def test_bad_claims(proof,changes):
    token,nonce=proof(**changes)
    with pytest.raises(AuthError) as e:google.verify_google(token,nonce)
    assert e.value.code=='GOOGLE_PROOF_INVALID'


def test_signature(proof):
    token,nonce=proof()
    pieces=token.split('.')
    signature=pieces[-1]
    pieces[-1]=('A' if signature[0]!='A' else 'B')+signature[1:]
    with pytest.raises(AuthError):google.verify_google('.'.join(pieces),nonce)


def test_provider_failure(proof):
    from google.auth.exceptions import TransportError
    def fail(*args,**kwargs):raise TransportError('offline')
    token,nonce=proof()
    google._local.request=fail
    with pytest.raises(AuthError) as e:google.verify_google(token,nonce)
    assert e.value.code=='AUTH_PROVIDER_UNAVAILABLE' and e.value.status==503


def test_rejection_log_contains_no_token_or_claims(proof,caplog):
    token,nonce=proof(azp='private-diagnostic-client')
    with pytest.raises(AuthError):google.verify_google(token,nonce)
    assert 'stage=azp_allowlist' in caplog.text
    assert token not in caplog.text
    assert 'private-diagnostic-client' not in caplog.text
    assert nonce not in caplog.text


def test_confirmed_debug_azp_only(proof,monkeypatch):
    from dataclasses import replace
    debug='574337852234-pje249p14id708ieg1t4q6fa9tmljih5.apps.googleusercontent.com'
    monkeypatch.setattr(google,'settings',replace(settings,google_azp=(debug,)))
    token,nonce=proof(azp=debug)
    assert google.verify_google(token,nonce)=='subject'
    token,nonce=proof(azp='unregistered.apps.googleusercontent.com')
    with pytest.raises(AuthError) as e:google.verify_google(token,nonce)
    assert e.value.code=='GOOGLE_PROOF_INVALID'
    token,nonce=proof(azp=debug,aud='wrong-audience')
    with pytest.raises(AuthError):google.verify_google(token,nonce)
