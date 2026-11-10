"""Allowlisted internal failure metadata; never log provider/user input."""
import json
import logging
import math
import uuid

STAGES = frozenset(('provider_init', 'siblings_transport', 'siblings_schema',
                    'before_armory', 'armory_transport', 'armory_profile',
                    'armory_equipment', 'equipment_receipt'))
REASONS = frozenset(('UPSTREAM_UNAVAILABLE', 'UPSTREAM_INVALID_RESPONSE',
                     'UPSTREAM_RESPONSE_TOO_LARGE', 'UPSTREAM_NOT_CONFIGURED',
                     'UPSTREAM_BUSY', 'LOSTARK_KEY_REJECTED', 'UPSTREAM_RATE_LIMITED'))
DETAILS = frozenset(('content_type', 'body_deadline', 'body_size', 'json_decode',
                     'body_shape', 'transport_timeout', 'transport_connection', 'transport_other'))


def milliseconds(value):
    if type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 86400000:
        return round(value, 3)
    return None


def record(error):
    request_id = str(uuid.uuid4())
    timings = getattr(error, 'diagnostic_timings', {})
    if not isinstance(timings, dict):
        timings = {}
    data = dict(request_id=request_id,
                stage=error.diagnostic_stage if getattr(error, 'diagnostic_stage', None) in STAGES else 'unknown',
                reason=error.reason if error.reason in REASONS else 'unknown',
                detail=error.diagnostic_reason if error.diagnostic_reason in DETAILS else None,
                upstream_status=error.http_status if type(error.http_status) is int and 100 <= error.http_status <= 599 else None,
                elapsed_ms=milliseconds(getattr(error, 'diagnostic_elapsed_ms', None)),
                stage_ms={stage: milliseconds(timings[stage]) for stage in sorted(STAGES) if stage in timings})
    logging.getLogger(__name__).warning('Provider failure %s', json.dumps(data, sort_keys=True),
        extra={'safe_event': 'provider_failure', 'safe_fields': data})
    return request_id
