"""Exact R2-C draft, separate from the unchanged production contract."""
from fastapi import FastAPI
from app.raid_rooms.admission_router import router
from app.raid_rooms.availability_contract import decorate


def draft_openapi():
    app=FastAPI(title='LostParty integrated recruitment admission draft')
    app.include_router(router)
    schema=app.openapi();decorate(schema)
    schema['x-recruitment-admission-policy']={
        'activation':'unmounted; canonical OpenAPI and main integration at R5',
        'implemented':'unscheduled creation, join, apply, approve, reject, withdraw, contexts, own plan and scoped application review',
        'pending_scheduling':'nonempty schedule_groups, sessions or schedule targets never succeed; R3 integration required',
        'pending_commands':'plan leave/transfer/end disabled until their implementation',
        'selection_token':'67 ASCII characters: s1. plus HMAC-SHA256 hex; opaque actor/action/cycle/source-version binding; no readable private payload',
        'selection_lifetime':'current cycle and exact source snapshot; server key rotation invalidates old contexts; no independent arbitrary TTL',
        'bounds':{'body_bytes':32768,'query_bytes':32768,'items':'unique raid IDs within current authoritative catalog'},
        'application_expiry':'current cycle end; pending GET evaluates expiry without writes; approve checks final DB clock',
        'approval':'current leader; applicant source CAS is server-owned; original ownership/lifecycle lifetime must match',
        'origin':'server-stored public admission origin survives group return; never granted to legacy_unknown or new outside group applications',
        'ack':'original actor/operation/key/body success before new context/expiry checks; no reapplication; current auth still required',
        'duration_policy':{'version':'difficulty-duration-v1','normal':10,'hard':20,'nightmare':30,'stage1':10,'stage2':20,'stage3':30},
        'privacy':'review never exposes another member ownership/weekly CAS or selection token; required nullable comparison when unavailable',
    }
    return schema
