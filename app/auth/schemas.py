import base64
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, StringConstraints, AfterValidator, Strict


def canonical(value):
    try:
        raw = base64.urlsafe_b64decode(value + "=")
        if len(raw) != 32 or base64.urlsafe_b64encode(raw).decode().rstrip("=") != value:
            raise ValueError()
    except Exception:
        raise ValueError("Expected canonical 32-byte base64url") from None
    return value


Secret = Annotated[str, StringConstraints(strict=True, min_length=43, max_length=43, pattern=r"^[A-Za-z0-9_-]{43}$"), AfterValidator(canonical)]
Digest = Annotated[str, StringConstraints(strict=True, min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")]
Token = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=16384)]


class DTO(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ChallengeIn(DTO):
    transaction_secret_hash: Digest


class ChallengeOut(DTO):
    transaction_id: UUID
    nonce: Secret
    expires_at: datetime


class GoogleIn(DTO):
    transaction_id: UUID
    transaction_secret: Secret
    google_id_token: Token
    remember_me: Annotated[bool, Strict()]


class RefreshIn(DTO):
    refresh_token: Secret
    refresh_request_id: Secret


class LogoutIn(DTO):
    refresh_token: Secret


class UserOut(DTO):
    id: UUID
    status: Literal["active", "disabled"]
    created_at: datetime


class SessionOut(DTO):
    id: UUID
    remember_me: bool
    created_at: datetime
    absolute_expires_at: datetime
    idle_expires_at: datetime
    expires_at: datetime


class Tokens(DTO):
    token_type: Literal["Bearer"]
    access_token: Token
    access_expires_at: datetime
    refresh_token: Secret
    refresh_expires_at: datetime
    session: SessionOut


class LoginOut(Tokens):
    user: UserOut
    is_new_user: bool


class ErrorDetail(DTO):
    code: Literal["INVALID_REQUEST", "AUTH_TRANSACTION_INVALID", "AUTH_TRANSACTION_EXPIRED",
                  "AUTH_TRANSACTION_CONSUMED", "GOOGLE_PROOF_INVALID", "AUTH_PROVIDER_UNAVAILABLE",
                  "ACCESS_INVALID", "ACCESS_EXPIRED", "SESSION_EXPIRED", "SESSION_REVOKED",
                  "ACCOUNT_DISABLED", "REFRESH_INVALID", "REFRESH_EXPIRED", "REFRESH_REUSED",
                  "REFRESH_RECOVERY_EXPIRED", "REFRESH_RECOVERY_LIMITED", "REFRESH_RESULT_SUPERSEDED",
                  "RATE_LIMITED", "SERVICE_UNAVAILABLE"]
    message: str
    request_id: UUID


class ErrorOut(DTO):
    error: ErrorDetail
