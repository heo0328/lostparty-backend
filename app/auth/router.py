from fastapi import APIRouter, Depends, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.auth import schemas, service
from app.core.errors import AuthError
from app.core.rate_limit import check, limits as _limits

router = APIRouter(prefix="/v1")
bearer = HTTPBearer(auto_error=False)


def limit(request, scope, maximum):
    # Single-process local deployment. Do not trust arbitrary proxy headers.
    key = (scope, request.client.host if request.client else "unknown")
    check(key, maximum)


def authenticated(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthError("ACCESS_INVALID")
    return service.principal(credentials.credentials)


common = {code: {"model": schemas.ErrorOut} for code in (400, 401, 403, 429, 503)}


@router.post("/auth/google/challenges", response_model=schemas.ChallengeOut, status_code=201, responses=common)
def challenge(data: schemas.ChallengeIn, request: Request):
    limit(request, "challenge", 30)
    return service.challenge(data)


@router.post("/auth/google", response_model=schemas.LoginOut, responses=common)
def google(data: schemas.GoogleIn, request: Request):
    limit(request, "google", 10)
    return service.login(data)


@router.get("/me", response_model=schemas.UserOut, responses=common)
def me(principal=Depends(authenticated)):
    return principal[0]


@router.get("/auth/session", response_model=schemas.SessionOut, responses=common)
def current_session(principal=Depends(authenticated)):
    return principal[1]


@router.post("/auth/refresh", response_model=schemas.Tokens,
             responses={**common, 409: {"model": schemas.ErrorOut}})
def refresh(data: schemas.RefreshIn, request: Request):
    limit(request, "refresh-ip", 300)
    return service.refresh(data)


@router.post("/auth/logout", status_code=204, responses=common)
def logout(data: schemas.LogoutIn):
    service.logout(data)
    return Response(status_code=204, headers={"Cache-Control": "no-store"})
