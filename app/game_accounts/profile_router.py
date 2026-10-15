from uuid import UUID
from fastapi import APIRouter, Request
from fastapi.encoders import jsonable_encoder
from fastapi.routing import APIRoute
from app.game_accounts.router import Principal, Key
from app.game_accounts.schemas import GameErrorOut
from app.game_accounts import profiles, presentation, profile_schemas as s
from app.game_accounts.support import fail


class ProfileRoute(APIRoute):
    body_limit = 32768

    def get_route_handler(self):
        handler = super().get_route_handler()

        async def bounded(request: Request):
            if request.query_params:
                fail('INVALID_REQUEST', 400)
            # Bound the body before FastAPI JSON parsing, including chunked input.
            body = bytearray()
            async for chunk in request.stream():
                if request.method == 'GET' and chunk:
                    fail('INVALID_REQUEST', 400)
                if len(body) + len(chunk) > self.body_limit:
                    fail('REQUEST_TOO_LARGE', 413)
                body.extend(chunk)
            request._body = bytes(body)
            return await handler(request)
        return bounded


router = APIRouter(prefix='/v2/me/characters', tags=['character-profiles'], route_class=ProfileRoute)
common = {status: {'model': GameErrorOut} for status in (400, 401, 403, 404, 409, 413, 503)}


@router.get('/{character_id}/personal-profile', response_model=s.PersonalProfileOut, responses=common)
def get(character_id: UUID, principal: Principal):
    return profiles.get(principal, character_id)


@router.put('/{character_id}/role-summaries/{role}', response_model=s.RoleSummaryOut, responses=common)
def put(character_id: UUID, role: s.Role, data: s.RoleSummaryIn, principal: Principal, key: Key):
    _, body = profiles.put(principal, character_id, role, key, jsonable_encoder(data))
    return body


class PreferencesRoute(ProfileRoute):
    body_limit = 4096


preferences_router = APIRouter(prefix='/v2/me/characters', tags=['character-profiles'], route_class=PreferencesRoute)
presentation_router = APIRouter(prefix='/v2/me/game-accounts', tags=['character-profiles'], route_class=PreferencesRoute)


@preferences_router.put('/{character_id}/personal-preferences', response_model=s.PersonalPreferencesOut, responses=common)
def put_preferences(character_id: UUID, data: s.PersonalPreferencesIn, principal: Principal, key: Key):
    _, body = profiles.put_preferences(principal, character_id, key, jsonable_encoder(data))
    return body


@presentation_router.get('/{registration_id}/presentation-settings', response_model=s.PresentationOut, responses=common)
def get_presentation(registration_id: UUID, principal: Principal):
    return presentation.get(principal, registration_id)


@presentation_router.put('/{registration_id}/presentation-settings', response_model=s.PresentationOut, responses=common)
def put_presentation(registration_id: UUID, data: s.PresentationIn, principal: Principal, key: Key):
    _, body = presentation.put(principal, registration_id, key, jsonable_encoder(data))
    return body
