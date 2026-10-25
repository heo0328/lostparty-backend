"""Request-scoped opt-in; legacy commands keep their exact old payload/namespace."""
from contextlib import contextmanager
from contextvars import ContextVar
from app.game_accounts.support import fail

PROFILE='beta-recruitment-1'
_state=ContextVar('beta_recruitment_request',default=None)
_raw_body=ContextVar('beta_recruitment_raw_body',default=None)


def enabled():
    return _state.get() is not None


def query():
    return _state.get() or {}


@contextmanager
def using(parameters=None):
    token=_state.set(dict(parameters or {}))
    try:yield
    finally:_state.reset(token)


def check_marker(token):
    if (token.get('contract_profile')==PROFILE)!=enabled():
        fail('CONTEXT_INVALID',400)


def marker():
    return {'contract_profile':PROFILE} if enabled() else {}


def body(data):
    return data.model_dump(mode='json',exclude_unset=enabled())


@contextmanager
def request_scope(parameters):
    token=_state.set(None if parameters is None else dict(parameters))
    raw_token=_raw_body.set(None)
    try:yield
    finally:
        _state.reset(token)
        _raw_body.reset(raw_token)


def request_model(data,legacy,beta):
    if enabled():
        from pydantic import ValidationError
        try:return beta.model_validate(data.model_dump(mode='json',exclude_unset=True))
        except ValidationError:fail('INVALID_REQUEST',400)
    if type(data) is beta:
        fail('INVALID_REQUEST',400)
    return data


def capture_body(value):
    _raw_body.set(value)


def raw_body(fallback):
    value=_raw_body.get()
    return fallback if value is None else value
