"""Export the unmounted R2 contract without publishing it in production OpenAPI."""
from fastapi import FastAPI
from app.raid_rooms.availability_router import router


def draft_openapi():
    candidate = FastAPI(title='LostParty recruitment availability draft')
    candidate.include_router(router)
    schema = candidate.openapi()
    for operations in schema['paths'].values():
        for operation in operations.values():
            operation['responses'].pop('422', None)
            for status, response in operation['responses'].items():
                headers = response.setdefault('headers', {})
                headers['Cache-Control'] = {'schema': {'type': 'string', 'const': 'no-store'}}
                if status == '401':
                    headers['WWW-Authenticate'] = {'schema': {'type': 'string', 'const': 'Bearer'}}
                if status == '409':
                    headers['Retry-After'] = {'description': 'REQUEST_IN_PROGRESS only',
                        'schema': {'type': 'integer', 'const': 2}}
    for key in ('HTTPValidationError', 'ValidationError'):
        schema['components']['schemas'].pop(key, None)
    schema['x-availability-policy'] = {
        'activation': 'unmounted R2 draft; integrated activation and canonical OpenAPI merge at R5',
        'timezone': 'Asia/Seoul', 'week_origin': 'ISO Monday 00:00',
        'body_bytes': 32768, 'interval_count': 'bounded by encoded request bytes; no separate arbitrary row cap',
        'interval_minutes': 'positive, at most 1440; 5-minute alignment',
        'personal_version': 'unset 1; first saved empty/nonempty 2; ordered raw change only increments',
        'submission': 'explicit snapshot; same source version is noop; GET and personal save never copy',
        'writes': 'current verified registration required; room copy requires current membership and ready active room',
        'reads': 'authenticated personal history accessible after unlink; room submission restricted to current member',
        'replay': 'original ACK after current auth and membership; resource CAS not rechecked; never reapplied',
        'warnings': 'schedule mismatch and busy warnings belong to R3 schedule/participation views; no schedule writes here',
    }
    return schema
