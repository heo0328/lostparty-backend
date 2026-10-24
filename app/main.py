import os
import asyncio
from contextlib import asynccontextmanager, suppress
from typing import Literal
import psycopg
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.auth.router import router
from app.auth.cleanup import run
from app.game_accounts.router import router as game_router
from app.game_accounts.lifecycle_router import router as lifecycle_router
from app.game_accounts.profile_router import router as profile_router, preferences_router, presentation_router
from app.core.errors import register
from app.core.game_policy import DEFAULT_MIN_ITEM_LEVEL
from app.member_settings.router import router as settings_router
from app.lostark_keys.router import router as lostark_keys_router
from app.raids.router import router as raid_router
from app.raid_weekly.router import router as raid_weekly_router
from app.groups.router import router as groups_router
from app.groups.admission_router import router as group_admissions_router
from app.ownership_disputes.router import router as ownership_disputes_router
from app.ownership_disputes.worker import run as run_ownership_worker
from app.game_accounts.bootstrap_router import router as bootstrap_router
from app.raid_rooms.admission_router import router as recruitment_router
from app.raid_rooms.availability_router import router as availability_router
from app.raid_rooms.schedule_router import router as schedule_router
from app.raid_rooms.continuation_router import router as continuation_router
from app.raid_rooms.completion_router import router as completion_router
from app.raid_rooms.management_router import router as recruitment_management_router
from app.raid_rooms.search_router import router as recruitment_search_router
from app.raid_rooms.member_router import router as recruitment_reads_router
from app.raid_rooms.worker import run as run_recruitment_worker
from app.raid_rooms.weekly_summary_router import router as weekly_summary_router


@asynccontextmanager
async def lifespan(app):
    from app.core.database import session
    from app.raid_rooms.readiness import require_active
    with session() as db:require_active(db)
    task = asyncio.create_task(run())
    ownership_task = asyncio.create_task(run_ownership_worker())
    recruitment_task = asyncio.create_task(run_recruitment_worker())
    yield
    task.cancel()
    ownership_task.cancel()
    recruitment_task.cancel()
    with suppress(asyncio.CancelledError):
        await task
    with suppress(asyncio.CancelledError):
        await ownership_task
    with suppress(asyncio.CancelledError):
        await recruitment_task


app = FastAPI(title="LostParty API", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
app.include_router(router)
app.include_router(game_router)
app.include_router(lifecycle_router)
app.include_router(profile_router)
app.include_router(preferences_router)
app.include_router(presentation_router)
app.include_router(settings_router)
app.include_router(lostark_keys_router)
app.include_router(raid_router)
app.include_router(raid_weekly_router)
app.include_router(groups_router)
app.include_router(group_admissions_router)
app.include_router(ownership_disputes_router)
app.include_router(bootstrap_router)
app.include_router(weekly_summary_router)
for recruitment_api in (recruitment_search_router,recruitment_reads_router,recruitment_router,availability_router,
                        schedule_router,continuation_router,completion_router,recruitment_management_router):
    app.include_router(recruitment_api)
register(app)


@app.middleware("http")
async def no_store(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith(("/v1/", "/v2/")):
        response.headers["Cache-Control"] = "no-store"
    return response


_original_openapi = app.openapi
def _decorate_openapi(schema):
    for path, operations in schema["paths"].items():
        if path.startswith(("/v1/", "/v2/")):
            for operation in operations.values():
                operation.get("responses", {}).pop("422", None)
                for status, result in operation.get("responses", {}).items():
                    headers = result.setdefault("headers", {})
                    headers["Cache-Control"] = {"schema": {"type": "string", "const": "no-store"}}
                    if status == "429":
                        headers["Retry-After"] = {"schema": {"type": "integer", "minimum": 1}} if "game-accounts" in operation.get("tags", []) else {"schema": {"type": "integer", "const": 60}}
                    if status == "409" and (set(operation.get("tags", [])) & {"game-accounts", "member-settings", "lostark-keys", "character-profiles", "raid-weekly", "groups"} or any(t.startswith('recruitment-') for t in operation.get('tags',[]))):
                        headers["Retry-After"] = {"description": "REQUEST_IN_PROGRESS only", "schema": {"type": "integer", "const": 2}}
                    if status == "401":
                        headers["WWW-Authenticate"] = {"schema": {"type": "string", "const": "Bearer"}}
    schema.get("components", {}).get("schemas", {}).pop("HTTPValidationError", None)
    schema.get("components", {}).get("schemas", {}).pop("ValidationError", None)
    schema['x-ownership-dispute-policy'] = {
        'max_active_per_account': 3, 'equipment_seconds': 600, 'defense_seconds': 86400,
        'defense': 'same current account/owner revision, explicit usable character selection; success closes the entire cohort',
        'settlement': 'oldest server sequence first; durable database leases; no provider I/O under game mutation lock; transfer and cohort invalidation are atomic',
        'authority': 'server-collected equipment receipts and persisted product dispute policy; not provider permanent identity or completeness evidence',
        'compatibility': 'V1 strict DTO/digests preserved; cross-owner legacy transfer denied; V2 typed proof/dispute restoration',
        'retention': 'automatic V2 evidence/metadata deletion is not enabled; separate explicit data-deletion approval required',
    }
    schema["x-auth-policy"] = {"challenge_seconds": 300, "access_seconds": 600,
                              "remember_absolute_seconds": 2592000, "remember_idle_seconds": 604800,
                              "memory_absolute_seconds": 43200, "memory_idle_seconds": 7200,
                              "recovery_seconds": 60, "recovery_additional_attempts": 2,
                              "recovery_time_origin": "database clock at final write before successful commit"}
    schema['x-game-account-policy'] = {
        'idempotency': {'key': 'UUIDv4', 'scope': 'actor + operation',
                        'hash': 'normalized method/path target/query/body',
                        'result_seconds': 86400, 'tombstone_seconds': 86400,
                        'lease_seconds': 30, 'generation_fencing': True,
                        'in_progress_status': 409, 'retry_after_seconds': 2,
                        'delete_replay': 'same actor saved 204; live row not required',
                        'failure_retry': 'same key/hash after retryable failure or lease expiry',
                        'pending_confirm_replay': 'original observation; new explicit check uses new key'},
        'challenge_seconds': 600, 'representative_cooldown_seconds': 0,
        'first_representative_starts_cooldown': False,
        'activity_selection': {
            'initial_selection_minimum_item_level': str(DEFAULT_MIN_ITEM_LEVEL),
            'validation': 'manual full-settings selection and representative target require current owned usable canonical IDs; no item-level floor; initial Flutter default and raid admission levels are separate',
            'stored': 'no bulk removal or automatic representative replacement; ineligible_character_ids reflects lifecycle/claim eligibility, not item level; level-only drops never trigger needs_reconfiguration; existing state changes only on explicit full-settings save',
            'initial_representative': 'existing explicit full-settings command saves selected UUIDs and representative atomically with CAS; reads/refresh never auto-select; existing representative preserved unless explicitly changed',
            'identity': 'V1 eligible/V2 usable and manual activity eligibility describe lifecycle/claim; item level does not create or revoke manual activity rights',
        },
        'max_registrations': 20, 'max_characters': 200,
        'page_default': 50, 'page_max': 100,
        'preview_seconds': 1800, 'preview_cleanup_grace_seconds': 3600,
        'terminal_challenge_retention_seconds': 86400, 'audit_seconds': 7776000,
        'rate_limits': {'shared_backend': 'PostgreSQL rolling windows',
                        'provider_per_minute': 80, 'provider_scope': 'token HMAC fingerprint', 'start_actor_per_minute': 3,
                        'confirm_actor_per_minute': 12, 'confirm_interval_seconds': 5,
                        'manual_refresh_interval_seconds': 10,
                        'transport_concurrency': '2 per process'},
        'pagination': 'full settings on every page; compare roster/settings/ownership versions across pages',
        'registration_label': {'automatic_value': '', 'post_omitted': 'empty string',
                               'patch_omitted': 'unchanged', 'explicit_null': 'rejected',
                               'normalization': 'trim surrounding whitespace; max 40 characters',
                               'display': 'Flutter calculates 메인 계정 / 부계정 N from current is_main and full registration order',
                               'subaccount_order': 'created_at ascending, registration_id ascending; custom labels count toward numbering',
                               'main_switch': 'labels unchanged; refetch full registration list'},
        'combat_power': {'default_min_item_level': str(DEFAULT_MIN_ITEM_LEVEL), 'max_input_characters': 20,
                         'access': 'current owned registration required; unverified/ownership_lost 403 OWNERSHIP_REQUIRED before credentials/provider and on replay/commit; activity selection not required',
                         'preview': 'retain stored data; unverified/ownership_lost V1/V2 power value/times/reason null, status unknown, stale true; direct preview combat_power null; registration mutation replay hides representative_summary after ownership loss',
                         'replay_access': 'current member/session and owned registration rechecked under game write lock; historical success never bypasses lost ownership',
                         'cache_seconds': 1800, 'failed_retry_seconds': 10,
                         'observation_retention_seconds': 7776000,
                         'request_budget_seconds': 20, 'network_wait_seconds': 19,
                         'budget': 'includes orchestration and in-flight network waits; 1 second reserved for commit; DB statements/locks capped at 500ms; not a hard OS scheduling guarantee',
                         'worker_completion': 'timed-out worker transport may finish; discarded results never write DB',
                         'shared_provider_per_minute': 80, 'provider_scope': 'token HMAC fingerprint', 'concurrency': 2,
                         'identity': 'member + server_name + character_name; no ownership/activity rights',
                         'normal_get': 'read cache only; power_status unknown/available/unavailable/failed',
                         'failure': 'preserve last good value/time; checked_at records latest applied observation; stale=true',
                         'deferred': 'no observation applied; same key replays original result; explicit next batch uses new key',
                         'conflict': 'REVISION_CONFLICT if registration/version/roster/ownership changes; revoked session 401; deleted registration 404',
                         'revisions': 'power-only write never changes registration/roster/ownership/settings revisions'},
        'representative': {
            'path': '/v1/me/game-accounts/{registration_id}/representative',
            'get': 'read-only owned registration, including non-main; coherent version snapshot',
            'put': 'main owned registration; confirmed canonical character already selected in activity',
            'expected': 'registration_version + settings_version + ownership_revision + roster_revision',
            'change': 'representative only; settings_version increments on change; configuration_state and activity preserved',
            'noop': 'all expected revisions and eligibility checked first; version unchanged',
            'cooldown': 'removed for representative PUT and character-settings PUT; next_change_at always null',
            'provider': 'no external calls or credential decryption; no automatic ownership/activity creation',
            'replay': 'original success after current session/registration/ownership checks; current main not required; GET latest',
            'errors': {'MAIN_REGISTRATION_CHANGED': 409, 'REVISION_CONFLICT': 409,
                       'SETTINGS_NOT_CONFIGURED': 409, 'CHARACTER_NOT_FOUND': 404,
                       'CHARACTER_NOT_ACTIVE': 409, 'CHARACTER_UNUSABLE': 409,
                       'OWNERSHIP_REQUIRED': 403, 'REGISTRATION_NOT_FOUND': 404,
                       'SERVICE_UNAVAILABLE': 503},
        },
        'live_evidence': 'server-equipment-removal-v1: uncached parsed siblings/Armory receipts at start and confirm; six baseline slots, random 1-3 removals, unchanged other Name/Grade, pinned target/roster/claims and collection times within server 10-minute challenge; final expiry rollback; new unclaimed accounts may verify; current valid owners cannot start another challenge; unresolved claims issue pending challenge and remain pending after equipment control with ACCOUNT_BINDING_EVIDENCE_PENDING, never live transfer; no client proof input',
        'verification_target': {
            'registration': 'optional target_character server_name/character_name plus required paired expected_registration_version; names strict trimmed 1-64 chars, version strict integer >=1; explicit null/unpaired/direct-input target fields rejected',
            'membership': 'saved registration full preview or current-owned non-retired canonical/current-claim membership before provider; fresh siblings/Armory must match selected server/name; no activity, representative, visibility/count or 1700 filter',
            'legacy': 'registration_id-only retains operational lookup target and exact old normalized request digest; omitted new null defaults do not enter dedup body; direct_input wire unchanged',
            'response': 'VerificationOut eight fields unchanged; original command retains target display context; no new status-query endpoint or journal',
            'errors': {'INVALID_REQUEST': 400, 'REGISTRATION_NOT_FOUND': 404, 'CHARACTER_NOT_FOUND': 404, 'REVISION_CONFLICT': 409, 'IDENTITY_CONFLICT': 409, 'EQUIPMENT_INCOMPLETE': 400, 'ALREADY_VERIFIED': 409},
            'owned': '409 ALREADY_VERIFIED for current owner with valid verified_at; linked registration checked before provider/target-version checks, other starts resolve fresh siblings against one current non-retired claim account and member registration history before Armory and recheck before challenge commit; other members and ownership_lost may challenge; pending confirm rechecks current owner without new audit; completed original-command replay and current GET preserved',
            'unresolved': 'start201 pending; matched equipment confirm200 pending ACCOUNT_BINDING_EVIDENCE_PENDING; control observation time and owner/claim snapshot recorded, GET retains pending code; no ownership/account/registration/activity/claim transfer; cancel/expiry remain terminal',
            'recovery': 'lost start response uses same POST/key/normalized body; saved201 replays without new provider/challenge; REQUEST_IN_PROGRESS/Retry-After retains command; after ID recovery GET current state/time; no reset/new key solely on network failure',
        },
        'registration_restore': {
            'command': 'existing registration POST; same RegistrationOut and 201, no new endpoint or equipment challenge',
            'authority': 'fresh parsed siblings must resolve existing claims to one non-retired canonical account, current owner and verified_at must match member with persisted registration history; ambiguous/foreign/no-anchor observations remain unverified',
            'fencing': 'member/key plus historical registration/account/claim snapshot rechecked under mutation lock after network; changed context returns 409 REVISION_CONFLICT',
            'preserve': 'same account/character IDs, owner, verified_at, ownership and roster revisions; no new ownership audit; new active configuration unconfigured with no automatic activity/representative selection; existing personal data retained',
            'duplicate': 'active same-account registration remains 409 REGISTRATION_EXISTS; deleted registration/key/path never revived or reused',
        },
        'input_name_resolution': 'preview/register/start resolve a unique siblings name using ASCII A-Z case-insensitive input matching only; retain API spelling in new registrations/challenges, Armory requests, receipts and history context; reject ambiguous/missing matches; Armory profile server/name and explicit target/pinned challenge/UUID/claims remain exact; request digests and input cache keys unchanged; no identity merging or stored-data migration',
        'challenge_context': 'pin lookup server/name and roster addresses at start; matched equipment with changed/invalid roster returns ROSTER_EVIDENCE_PENDING; missing old snapshot context or server baseline receipt returns PROVIDER_EVIDENCE_PENDING; live equipment receipts bind target/roster/equipment/time; legacy trusted adapter marker must be boolean True; equality alone never proves ownership/continuity/completeness',
        'live_roster_decrease': 'suspect only; missing/transfer require validated observation criteria',
        'owned_roster_refresh': {
            'source': 'existing refresh command fetches provider siblings; list GETs read saved DB only; API roster is the product membership basis, no unavailable upstream permanent-ID evidence required',
            'scope': 'explicit current owned registration/account/owner and registration/account/claim snapshot; query anchor must be current active confirmed claim; foreign account claims reject atomically',
            'apply': 'same current non-retired claims retain IDs; new unclaimed addresses get new UUID and empty personal data; absent records become suspect; same-owned normal API reappearance restores non-retired currently claimed suspect IDs; retired IDs never revive',
            'lookup_recovery': 'only explicit upstream HTTP404 tries another stored active confirmed anchor in the same account; at most 3 anchors per command; success saves operational lookup name without changing historical verification target, activity or representative; failure retains data and ownership',
            'failure': 'timeout, malformed/empty/duplicate/missing-target roster, key/quota errors or foreign claims do not apply roster or revoke ownership; no fallback on non404; unresolved anchors remain incomplete, never empty success',
            'result': '200 means roster applied; registration.version and account.roster_revision advance, ownership_revision/verified_at unchanged; suspect_count counts unresolved non-retired records; requires_refresh means unresolved suspect records, not command still running; GET latest canonical/settings after command or replay',
            'selection': 'activity/representative IDs preserved; newly added IDs never auto-selected; blocked selected IDs set needs_reconfiguration; recovery does not auto-save settings',
            'startup': 'Flutter member/environment once: owned provider roster refresh then current revisions/canonical list then valid activity targets then detail/build checks; nice-off excludes details, not roster refresh; failures remain incomplete',
        },
        'mutation_locking': 'initial global game transaction advisory lock; no network under lock',
    }
    schema['x-character-lifecycle-policy'] = {
        'migration': '0007 files/isolated validation only; real DB application and API restart require separate approval',
        'identity': 'preserve UUID/FK; name claim is conflict detection, never ownership/account continuity proof',
        'evidence': 'live adapter provides no transfer BindingEvidence; owned roster refresh/explicit registration reauth use internal owner scope and API-list policy separately; unresolved verification now starts pending and confirms pending ACCOUNT_BINDING_EVIDENCE_PENDING without transfer',
        'state': 'active/suspect/retired internally; V1 enum unchanged; retired excluded from operating views',
        'recovery': 'normal scoped current-owned API observation can restore non-retired suspect with its current same-account claim; other recovery requires internal continuity evidence; no retired-ID revival, live retirement or claim release API',
        'cache': 'new scoped tables; canonical member/ID/lifecycle/key version, preview member/registration/version/name/key version',
        'legacy_cache': 'preserved, never copied to new identities; preview refresh begins a new unproven generation',
        'fencing': 'registration/main/ownership/roster/character/claim snapshot before external work and final commit',
        'errors': {'ACCOUNT_BINDING_EVIDENCE_PENDING': 409, 'CHARACTER_UNUSABLE': 409,
                   'IDENTITY_CONFLICT': 409, 'REVISION_CONFLICT': 409},
    }
    schema['x-character-lifecycle-policy']['reads'] = {
        'paths': ['/v2/me/game-accounts/{registration_id}/characters','/v2/me/character-retirements'],
        'write': 'none; no evidence/provider/credential lookup or default/head insertion',
        'preview': 'required null character_id/lifecycle_revision; usable=false; ownership-required reason',
        'usable': 'base current ownership/state/claim eligibility only; activity/raid/schedule validated by final command',
        'retired': 'excluded from operating list/count/summary; history scoped to member at retirement, not current account owner',
        'cursor': 'signed member/path scope and current registration/ownership/roster/claim/settings or member-history revision; stale 409',
        'limit': 'default/max 50; next_cursor always present nullable; history empty revision1 without inserting',
        'observations': 'structure revisions fenced; stored power observations may advance without roster revision',
    }
    schema['x-character-profile-policy'] = {
        'phase': 'P1 role summaries + P2 personal preferences/account presentation and internal retirement cleanup',
        'identity': 'member + canonical character UUID + ownership_revision + role; no name-based inheritance',
        'get': 'read-only coherent snapshot; owned active/suspect with current NameClaim; retired 409',
        'put': 'owned active/confirmed canonical with current NameClaim and expected role/ownership/lifecycle revisions',
        'preference_defaults': {'version': 1, 'preferred_role': None, 'visible': True, 'display_order': None, 'saved_at': None},
        'unset_role': {'version': 1, 'summary': None, 'saved_at': None},
        'version': 'first summary version2; change-only increment; stale expected rejected even for no-op; roles independent',
        'source': 'flutter_analysis; never provider observations, ownership/activity/representative authority, or retirement values',
        'integrity': {'clean': 'no issues', 'review': 'one or more warnings, no errors',
                      'error': 'one or more errors, warnings allowed',
                      'unavailable': 'no errors; zero or more warnings; never infer clean from empty issues'},
        'catalog': 'required nullable opaque ASCII identifier, separate from analysis_rules_version and schema version',
        'timestamps': 'UTC RFC3339; client analysis/observation provenance separate from server saved_at; not conflict ordering',
        'limits': {'put_body_bytes': 32768, 'decimal_string_length': 32, 'issues': 20, 'identifier_length': 64},
        'replay': 'historical ACK after current session/active registration/ownership/NameClaim and same ownership/lifecycle checks; no role version recheck or reapplication',
        'idempotency': 'role-summary operation; actor/key digest includes character/role/body; 30s lease, 24h success + 24h tombstone',
        'pending': 'immutable same-key/body recovery; conservative 24h from first send; stale pending never auto rebased on new version',
        'nice_group': 'existing member bool controls new automatic analysis only; valid old pending and summaries preserved; no new per-character switch',
        'provider': 'no external calls, credential lookup, or nice-group/activity prerequisites for storage',
        'errors': {'INVALID_REQUEST': 400, 'CHARACTER_NOT_FOUND': 404, 'OWNERSHIP_REQUIRED': 403,
                   'CHARACTER_UNUSABLE': 409, 'IDENTITY_CONFLICT': 409, 'REVISION_CONFLICT': 409,
                   'IDEMPOTENCY_CONFLICT': 409, 'IDEMPOTENCY_EXPIRED': 409, 'REQUEST_IN_PROGRESS': 409,
                   'REQUEST_TOO_LARGE': 413, 'SERVICE_UNAVAILABLE': 503},
        'deployment': '0008 additive migration and isolated tests only; real DB/API transition requires separate approval',
    }
    schema['x-character-profile-policy']['personal_preferences'] = {
        'get': 'personal-profile.preferences now reads persisted member/character/ownership-lifetime values; P1 virtual const schema replaced',
        'put': 'strict full preferred_role/visible/display_order + expected preference/ownership/lifecycle versions; 409 for suspect writes',
        'scope': 'rank scoped to member + canonical account ownership lifetime, no cross-account reorder or activity/representative changes',
        'version': 'default version1/no insertion on default no-op; actual change increments only this resource, saved_at UTC',
        'limit_bytes': 4096,
    }
    schema['x-character-profile-policy']['presentation'] = {
        'path': '/v2/me/game-accounts/{registration_id}/presentation-settings',
        'scope': 'member + canonical game_account_id + ownership_revision; registration path is access/version fence',
        'default': {'version': 1, 'visible_count': 6, 'saved_at': None},
        'count': 'strict integer 1..200, not nullable; render min(count, available visible rows) without rewriting stored count',
        'put': 'expected version + registration_version + ownership_revision; independent of settings/activity/representative/main',
        'replay': 'current active owned registration and same ownership lifetime; historical registration_version allowed; never reapply',
        'reregistration': 'same member/account/ownership lifetime can read old settings through new active registration; old path remains 404',
        'unverified': '403 OWNERSHIP_REQUIRED; deleted/other registration 404 REGISTRATION_NOT_FOUND',
        'sort': 'Flutter within account: visible filter, representative first, rank asc/null last, item level desc/null last, name asc, UUID asc; hidden representative stays hidden',
        'limit_bytes': 4096,
    }
    schema['x-character-profile-policy']['retirement_cleanup'] = (
        'internal validated complete retirement transaction deletes role summaries/preferences for retiring UUID across owner lifetimes; '
        'preserves account presentation, other UUIDs and history/FKs; rollback atomic; no live caller or claim-release activation')
    schema['x-character-profile-policy']['deployment'] = '0008/0009 files/isolated tests only; no real DB migration or API transition'
    schema['x-member-settings-policy'] = {
        'scope': 'authenticated member; independent of registration/device/session',
        'default': {'nice_group_auto_refresh_enabled': False, 'version': 1},
        'get': 'read-only; unset returns default without inserting',
        'put': 'explicit strict boolean + expected_version + UUIDv4 Idempotency-Key',
        'version': 'increment on value change only; stale expected_version rejected even for same value',
        'conflict': '409 REVISION_CONFLICT; GET then explicit new decision/key',
        'replay': 'same member/key/body returns original success for 24h; current state requires GET',
        'idempotency': 'existing result/tombstone/lease/generation-fencing policy; REQUEST_IN_PROGRESS 409 Retry-After 2',
        'logout': 'preserves stored preference; GET failure must never trigger default PUT',
        'provider': 'no external Lost Ark calls; no build refresh triggered',
    }
    schema['x-lostark-key-policy'] = {
        'scope': 'authenticated member; app Bearer distinct from PUT token',
        'default': {'configured': False, 'version': 1, 'updated_at': None},
        'metadata': 'configured/version/updated_at only; no token retrieval; GET read-only',
        'validation': 'strict compact JWT format only; PUT no provider call/claims/exp validation',
        'version': 'every new PUT increments; DELETE increments only when configured; stale version rejected',
        'idempotency': 'UUIDv4; HMAC token fingerprint, never raw token; 24h historical metadata replay',
        'credential_errors': {'LOSTARK_KEY_NOT_CONFIGURED': 409, 'LOSTARK_KEY_REJECTED': 409,
                              'LOSTARK_KEY_CHANGED': 409, 'LOSTARK_KEY_UNAVAILABLE': 503},
        'provider_401_403': 'key rejected; never app HTTP401/logout',
        'cache': 'member + credential version; old successful power preserved for GET only',
        'changed': '409; old in-flight observations discarded before final commit; new decision/key',
        'power_failure': 'failed key rejection/upstream rate limit; unstarted items deferred with same reason',
        'quota': '80/min per HMAC token fingerprint shared across members/versions; transport 2/process',
        'quota_limit': 'provider 100/min/client includes local direct calls; server budget is not a guarantee',
        'logout': 'preserves credential; DELETE removes current secret only',
        'fallback': 'none; no environment Lost Ark JWT for REST or diagnostic',
    }
    schema['x-lostark-key-policy']['restore'] = {
        'path': '/v1/me/lostark-api-key/restore', 'method': 'POST',
        'body': 'strict expected_version; read-only; no Idempotency-Key/result storage',
        'response': 'token/version from same locked member credential; no-store; secret response not logged',
        'conflict': 'absent 409 NOT_CONFIGURED; changed 409 CHANGED; unreadable 503 UNAVAILABLE',
        'metadata_get': 'unchanged; no token',
    }
    schema['x-lostark-key-policy']['provider_wait'] = {
        'reset': 'UNIX epoch seconds; valid future <=300s; otherwise observed time +60s',
        'trigger': '429 or successful 200 Remaining=0; successful response stays successful',
        'scope': 'token HMAC fingerprint; deadline max; no extension without new provider observation',
        'late': 'only independent token limiter state; never business/cache/idempotent-success writes',
        'single': 'error retry_after_seconds/retry_at for rate limits; Retry-After matches seconds',
        'batch': 'PowerResult required nullable retry_after_seconds/retry_at; no batch200 Retry-After',
        'retry': 'explicit new command; historical replay keeps original retry_at; no automatic provider retries',
    }
    for path, operations in schema['paths'].items():
        for operation in operations.values():
            if 'game-accounts' in operation.get('tags', []) and '503' in operation.get('responses', {}):
                operation['responses']['503']['headers']['Retry-After'] = {
                    'description': 'UPSTREAM_RATE_LIMITED only', 'schema': {'type': 'integer', 'minimum': 1}}
    schema['x-recruitment-policy']={
        'schema_revision':'0023_recruitment_resume',
        'cycle':'Asia/Seoul Wednesday 06:00; maintenance Wednesday [06:00,10:00)',
        'time':'UTC, 5-minute ticks, positive at most 24h per session; stored authorized opening +30m floor',
        'admission_deadline':'strictly before confirmed start minus 30m; initial threshold and existing participant confirmation are distinct',
        'reservations':'exact active assignment/segment/schedule generation; explicit overlap allowed with warning, automatic candidates avoid busy',
        'votes':'each affected session N1 explicit 1, otherwise max(2,ceil(N/2)); all targets atomic; reads never apply',
        'completion':'personal item manual ledger vs leader item party ledger; preserve other segment times and completed history',
        'continuation':'future choices are not current assignments; auto default off; boundary authority distinct from processed_at',
        'command_context':{'algorithm':'AES-256-GCM','seconds':120,'max_token_bytes':4096,'replay':'original minimal ACK before new token expiry/source validation'},
        'search':'visibility and raid/difficulty/group OR/member AND/within-member character OR, then exact remaining slots OR, member_count ascending/descending (default descending), created_at DESC/id DESC ties, then pagination; cursor binds full normalized conditions and directory/cycle/group generations',
        'bounds':{'request_bytes':32768,'page_max':50,'cursor_max':2048,'candidate_ticks_max':2016},
    }
    return schema
def openapi():return _decorate_openapi(_original_openapi())
app.openapi = openapi

class HealthResponse(BaseModel):
    status: Literal["ok"]
    database: Literal["ok"]

class UnhealthyResponse(BaseModel):
    status: Literal["unhealthy"]
    database: Literal["unavailable"]

def connect():
    return psycopg.connect(host="db", dbname=os.environ["POSTGRES_DB"],
                          user="lostparty_app", password=os.environ["APP_DB_PASSWORD"],
                          connect_timeout=3, options="-c statement_timeout=3000")

@app.get("/health", response_model=HealthResponse,
         responses={503: {"model": UnhealthyResponse, "description": "Database unavailable"}})
def health():
    try:
        with connect() as conn:
            value = conn.execute("SELECT 1").fetchone()[0]
        if value != 1:
            raise RuntimeError("Unexpected health result")
    except (psycopg.Error, RuntimeError) as error:
        from app.core.observability import emit, category
        import logging
        emit("database_error", level=logging.ERROR, category=category(error))
        return JSONResponse(status_code=503, content={"status": "unhealthy", "database": "unavailable"})
    return {"status": "ok", "database": "ok"}


@asynccontextmanager
async def two_cycle_lifespan(application):
    from app.core.database import session
    from app.raid_rooms.readiness import require_two_cycle_active
    from app.raid_rooms.cycle_worker import process_due
    with session() as db:require_two_cycle_active(db)
    tasks=[asyncio.create_task(run()),asyncio.create_task(run_ownership_worker()),
        asyncio.create_task(run_recruitment_worker(process_due))]
    try:yield
    finally:
        for task in tasks:task.cancel()
        for task in tasks:
            with suppress(asyncio.CancelledError):await task


def create_two_cycle_app():
    """Explicit ASGI factory for a verified 0029 cutover; default app stays 0023.

    Preparation only: this factory never migrates DBs or edits deployment config.
    """
    from app.raid_rooms.cycle_router import router as cycle_router
    from fastapi.routing import APIRoute
    from fastapi import APIRouter
    result=FastAPI(title="LostParty API",docs_url=None,redoc_url=None,openapi_url=None,lifespan=two_cycle_lifespan)
    legacy=APIRouter()
    legacy.routes.extend(route for route in app.routes if isinstance(route,APIRoute))
    result.include_router(legacy)
    result.include_router(cycle_router)
    register(result);result.middleware('http')(no_store)
    generate=result.openapi
    def schema():
        value=_decorate_openapi(generate())
        value['x-recruitment-policy'].update(schema_revision='0031_membership_actions',policy_version='two-cycle-contract-4',
            search_semantics='own-target-participation-excluded-v1',
            admission_eligibility=dict(policy_version='admission-eligibility-2',required_schema='0031_membership_actions',
                intents=['apply','change_character'],approval='stored parties; qualification failure keeps pending',
                change='exact own assignment/lease exclusion; original party then opposite party; consent bound to target parties',
                reads='own candidates, bulk read-only, no provider or occupancy writes',
                compatibility='existing write DTOs and original 24h ACK; creation/direct join policy preserved'),
            membership_actions=dict(policy_version='membership-actions-1',required_schema='0031_membership_actions',
                actions=['leave_target','leave_all','dissolve_led_targets','recover_leadership'],
                reader_profile='membership-actions-1',default_reader='legacy shape preserved',
                effects_order='actual C then N; empty effects can end persistent membership',
                compatibility='old cancel/leave/end and D22/E23 retain original operation/pending/24h ACK',
                inactive_features='IF-001: close_weekly/weekly_resume app entry disabled; APIs/history/original pending retained'),
            continuation='Explicit N opening only; 06:00 N becomes C with the same UUID/leader/assignments/consents; no automatic new N',
            compatibility='v1 current-C read adapters; unsafe room writes replay original ACK then CLIENT_UPGRADE_REQUIRED; personal availability/manual completion remain safe')
        return value
    result.openapi=schema
    return result
