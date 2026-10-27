"""F2-A isolated PostgreSQL reads, authorization, cursor and snapshot boundaries."""
import uuid
from datetime import timedelta
import pytest
from sqlalchemy import event, select, text
from app.core.database import session, now, engine
from app.game_accounts.models import Account, Activity, Character, CharacterRoleSummary, Registration
from app.raid_rooms import queries as q, service, policies
from app.raid_rooms.models import Room, Round, Membership, Application
from app.raid_rooms.commands import Admission
from app.member_limits.service import Limits
from tests.test_raid_room_foundation import (people, worlds, create, create_command, join, admission,
    recover, membership_command, selection, denied, decision)
from tests.test_group_foundation import actor
from tests.test_member_limits import change


@pytest.fixture(autouse=True)
def enabled_candidate_admissions(monkeypatch):
    monkeypatch.setenv("RAID_ROOM_ADMISSIONS_ENABLED", "true")


def rid(w, **kwargs):
    return uuid.UUID(create(w, **kwargs)[1]['room_id'])


def context(w, room, **kwargs):
    return q.admission_context(actor(w['uid']), room, character_id=uuid.UUID(w['ids'][0]),
                              selected_role='dealer', party_no=1, intent='join', **kwargs)


def test_public_summary_allowlist_and_private_access(people):
    a, b = people('a'), people('b')
    room = rid(a)
    out = q.room_summary(room)
    assert out['member_count'] == 1 and out['leader_display']['character_name'] == 'sample-0'
    assert not {'members', 'applications', 'policy_snapshot', 'user_id', 'character_id', 'build'} & out.keys()
    assert str(a['uid']) not in str(out)
    denied('ROOM_MEMBERSHIP_REQUIRED', q.room_detail, actor(b['uid']), room)
    detail = q.room_detail(actor(a['uid']), room)
    assert detail['members'][0]['is_me'] and detail['members'][0]['status'] == 'valid'
    assert 'user_id' not in str(detail) and 'registration_id' not in str(detail)
    assert detail['permissions']['end']['allowed']
    assert not detail['permissions']['complete']['allowed']


def test_all_reads_are_database_read_only_without_row_locks(people):
    a, b = people('a'), people('b')
    room = rid(a, command=create_command(a, mode='leader_only'))
    aid = uuid.UUID(join(b, room, applying=True)[1]['application_id'])
    statements = []
    def capture(conn, cursor, statement, *args):
        statements.append(statement.upper())
    event.listen(engine(), 'before_cursor_execute', capture)
    try:
        q.room_list(); q.room_summary(room); q.room_detail(actor(a['uid']), room)
        q.management(actor(a['uid']), room); q.memberships(actor(a['uid']))
        q.applications(actor(b['uid'])); q.applications(actor(a['uid']), room_id=room)
        q.application(actor(b['uid']), aid)
        q.admission_context(actor(b['uid']), room, character_id=uuid.UUID(b['ids'][1]),
                            selected_role='support', party_no=1, intent='apply')
    finally:
        event.remove(engine(), 'before_cursor_execute', capture)
    assert not any(s.lstrip().startswith(('INSERT ', 'UPDATE ', 'DELETE ')) or 'FOR UPDATE' in s for s in statements)
    assert statements.count('SET TRANSACTION READ ONLY') == 9


def test_context_drives_real_atomic_join_with_explicit_policy(people):
    a, b = people('a'), people('b')
    room = rid(a)
    out = context(b, room)
    assert out['eligibility'] == {'allowed': True, 'reason': None}
    sel = out['selection']
    command = Admission(selection=sel, expected_room_revision=out['room_revision'],
        expected_round_revision=out['round_revision'], expected_members_revision=out['members_revision'],
        expected_policy_snapshot=out['policy_snapshot'], expected_cycle_key=out['cycle_key'],
        expected_catalog_version=out['catalog_version'])
    assert service.admit(actor(b['uid']), room, uuid.uuid4(), command, policy=policies.public_finite)[0] == 200
    assert q.room_summary(room)['member_count'] == 2
    assert q.memberships(actor(b['uid']))['items'][0]['room_id'] == str(room)
    assert context(b, room)['eligibility']['reason'] == 'ROOM_MEMBER_EXISTS'


def test_context_is_not_reservation_and_rechecks_after_limit_change(people):
    a, b = people('a'), people('b')
    room = rid(a)
    before = context(b, room)
    change(b['uid'], Limits(15, 5, 0))
    assert context(b, room)['eligibility']['reason'] == 'MEMBER_RAID_LIMIT_REACHED'
    sel = before['selection']
    cmd = admission(b, room).model_copy(update={'selection': selection(b).model_copy(
        update={'expected_limits_revision': sel['expected_limits_revision']})})
    denied('POLICY_CONTEXT_CHANGED', service.admit, actor(b['uid']), room, uuid.uuid4(), cmd,
           policy=policies.public_finite)
    assert q.memberships(actor(b['uid']))['items'] == []


def test_foreign_and_inactive_character_context(people):
    a, b = people('a'), people('b')
    room = rid(a)
    denied('CHARACTER_NOT_FOUND', q.admission_context, actor(b['uid']), room,
           character_id=uuid.UUID(a['ids'][0]), selected_role='dealer', party_no=1, intent='join')
    out = q.admission_context(actor(b['uid']), room, character_id=uuid.UUID(b['ids'][2]),
                             selected_role='dealer', party_no=1, intent='join')
    assert out['eligibility']['reason'] == 'ACTIVITY_SELECTION_REQUIRED'
    with session() as db, db.begin():
        c = db.get(Character, uuid.UUID(b['ids'][0])); c.summary = {**c.summary, 'item_level': '100'}
    assert context(b, room)['eligibility']['reason'] == 'RAID_ITEM_LEVEL_REQUIRED'


def test_role_party_mode_and_overlap_conditions(people):
    a, b = people('a'), people('b')
    room = rid(a)
    assert q.admission_context(actor(b['uid']), room, character_id=uuid.UUID(b['ids'][0]),
        selected_role='dealer', party_no=2, intent='join')['eligibility']['reason'] == 'ROOM_COMPOSITION_CONFLICT'
    assert q.admission_context(actor(b['uid']), room, character_id=uuid.UUID(b['ids'][0]),
        selected_role='dealer', party_no=1, intent='apply')['eligibility']['reason'] == 'ROOM_FEATURE_UNSUPPORTED'
    other = rid(b)
    assert context(b, room)['eligibility']['reason'] in ('WEEKLY_ALREADY_PARTICIPATING', 'SCHEDULE_CONFLICT')
    assert other != room


def test_full_room_still_allows_pending_without_slot_or_limit_reservation(people):
    a, b, c, d, e = [people(x) for x in 'abcde']
    room = rid(a)
    join(b, room); join(c, room); join(d, room, admission(d, room, role='support'))
    assert context(e, room)['eligibility']['reason'] == 'ROOM_FULL'
    with session() as db, db.begin():
        db.get(Room, room).admission_mode = 'leader_only'
    change(e['uid'], Limits(15, 5, 0))
    out = q.admission_context(actor(e['uid']), room, character_id=uuid.UUID(e['ids'][0]),
                            selected_role='dealer', party_no=1, intent='apply')
    assert out['eligibility']['allowed']
    assert join(e, room, applying=True)[0] == 201
    assert q.memberships(actor(e['uid']))['items'] == []


def test_public_cursor_filters_tampering_and_other_actor(people):
    a, b = people('a'), people('b')
    rid(a); rid(b)
    first = q.room_list(limit=1)
    token = first['next_cursor']
    assert token and len(q.room_list(limit=1, cursor=token)['items']) == 1
    denied('INVALID_REQUEST', q.room_list, limit=1, cursor=token+'x')
    denied('INVALID_REQUEST', q.room_list, limit=2, cursor=token)
    denied('INVALID_REQUEST', q.room_list, actor(a['uid']), limit=1, cursor=token)
    denied('INVALID_REQUEST', q.room_list, difficulty_id='stage1')
    for limit in [True, 0, 51, '1']:
        denied('INVALID_REQUEST', q.room_list, limit=limit)


def test_public_cursor_ignores_private_applications_but_stales_on_visible_limits(people):
    a, b, c = [people(x) for x in 'abc']
    room = rid(a, command=create_command(a, mode='leader_only'))
    rid(b)
    token = q.room_list(limit=1)['next_cursor']
    join(c, room, applying=True)
    assert q.room_list(limit=1, cursor=token)['items']
    change(a['uid'], Limits(15, 5, 0))
    denied('CURSOR_STALE', q.room_list, limit=1, cursor=token)


def test_personal_cursor_stales_on_other_members_room_change(people):
    a, b = people('a'), people('b')
    first = rid(a)
    second = rid(a, command=create_command(a, offset=3, selection=selection(a, index=1)))
    token = q.memberships(actor(a['uid']), limit=1)['next_cursor']
    join(b, first)
    denied('CURSOR_STALE', q.memberships, actor(a['uid']), limit=1, cursor=token)
    assert second != first


def test_application_visibility_leadership_transfer_and_cursor_authorization(people):
    a, b, c, d = [people(x) for x in 'abcd']
    room = rid(a, command=create_command(a, mode='leader_only'))
    aid = uuid.UUID(join(b, room, applying=True)[1]['application_id'])
    cid = uuid.UUID(join(c, room, applying=True)[1]['application_id'])
    denied('ROOM_APPLICATION_NOT_FOUND', q.application, actor(d['uid']), aid)
    assert q.applications(actor(d['uid']))['items'] == []
    token = q.applications(actor(a['uid']), room_id=room, limit=1)['next_cursor']
    assert token
    service.decide(actor(a['uid']), aid, uuid.uuid4(), decision(aid), approve=True,
                   policy=policies.public_finite)
    recover(a, room, 'transfer', membership_command(a, room, b))
    denied('ROOM_LEADER_REQUIRED', q.applications, actor(a['uid']), room_id=room, limit=1, cursor=token)
    denied('ROOM_APPLICATION_NOT_FOUND', q.application, actor(a['uid']), cid)
    assert q.application(actor(b['uid']), cid)['permissions']['approve']['allowed']
    assert q.application(actor(c['uid']), cid)['permissions']['withdraw']['allowed']
    assert 'expected_ownership_revision' not in str(q.application(actor(b['uid']), cid))


def test_logical_expiry_invalidates_page_without_writes(people, monkeypatch):
    a, b, c = [people(x) for x in 'abc']
    room = rid(a, command=create_command(a, mode='leader_only'))
    ids = [uuid.UUID(join(w, room, applying=True)[1]['application_id']) for w in (b, c)]
    token = q.applications(actor(a['uid']), room_id=room, limit=1)['next_cursor']
    with session() as db:
        expires = max(db.get(Application, i).expires_at for i in ids)
    monkeypatch.setattr(q, 'now', lambda db: expires + timedelta(seconds=1))
    denied('CURSOR_STALE', q.applications, actor(a['uid']), room_id=room, limit=1, cursor=token)
    out = q.applications(actor(b['uid']), state='ended')['items'][0]
    assert out['state'] == 'expired' and out['ended_at'] == out['expires_at']
    with session() as db:
        assert db.get(Application, ids[0]).state == 'pending'


def role_summary(stamp):
    return dict(source='flutter_analysis', analysis_rules_version='test-v1', analyzed_at=stamp.isoformat(),
        combat_power=None, item_level=None, combat_power_observed_at=None, item_level_observed_at=None,
        integrity_status='unavailable', catalog_version=None, issues=[], observed_lifecycle_revision=1)


def test_build_snapshots_are_immutable_and_mark_new_version_stale(people):
    a, b = people('a'), people('b')
    with session() as db, db.begin():
        stamp = now(db)
        for w in (a, b):
            db.add(CharacterRoleSummary(user_id=w['uid'], character_id=uuid.UUID(w['ids'][0]),
                ownership_revision=1, role='dealer', version=4, summary=role_summary(stamp), saved_at=stamp))
    # Reuse server source versions instead of the F1 fixture's fixed role-version=1.
    sel_a = selection(a).model_copy(update={'expected_role_summary_version': 4})
    room = rid(a, command=create_command(a, mode='leader_only', selection=sel_a))
    sel_b = selection(b).model_copy(update={'expected_role_summary_version': 4})
    aid = uuid.UUID(join(b, room, admission(b, room).model_copy(update={'selection': sel_b}), applying=True)[1]['application_id'])
    original = q.room_detail(actor(a['uid']), room)['members'][0]['build']
    assert original['version'] == 4 and not original['stale']
    with session() as db, db.begin():
        for w in (a, b):
            row = db.get(CharacterRoleSummary, (w['uid'], uuid.UUID(w['ids'][0]), 1, 'dealer'))
            row.version = 5
            row.summary = {**row.summary, 'analysis_rules_version': 'new-rules'}
    built = q.room_detail(actor(a['uid']), room)['members'][0]['build']
    app = q.application(actor(b['uid']), aid)['build']
    assert built['version'] == app['version'] == 4 and built['stale'] and app['stale']
    assert built['summary']['analysis_rules_version'] == app['summary']['analysis_rules_version'] == 'test-v1'


def test_ownership_loss_keeps_old_snapshot_and_recovery(people):
    a, b = people('a'), people('b')
    room = rid(a); join(b, room)
    before = q.room_detail(actor(b['uid']), room)['members'][0]['display']
    with session() as db, db.begin():
        account = db.get(Account, a['aid']); account.owner_id = b['uid']; account.ownership_revision += 1
        c = db.get(Character, uuid.UUID(a['ids'][0])); c.summary = {**c.summary, 'class_name': 'changed'}
    out = q.room_detail(actor(b['uid']), room)
    old = next(m for m in out['members'] if not m['is_me'])
    assert old['display'] == before and old['status'] == 'needs_review'
    assert old['build']['stale']
    assert q.management(actor(a['uid']), room)['permissions']['transfer_leadership']['allowed']
    assert context(b, room)['eligibility']['reason'] == 'ROOM_MEMBER_EXISTS'


def test_history_cleanup_and_same_cycle_ended_summary(people):
    a, b = people('a'), people('b')
    room = rid(a); join(b, room)
    recover(b, room)
    assert q.memberships(actor(b['uid']))['items'] == []
    old = q.memberships(actor(b['uid']), state='ended')['items'][0]
    assert old['end_reason'] == 'left' and old['access_state'] == 'history_only'
    denied('ROOM_MEMBERSHIP_REQUIRED', q.room_detail, actor(b['uid']), room)
    recover(a, room, 'end')
    old = q.memberships(actor(a['uid']), state='ended')['items'][0]
    assert old['end_reason'] == 'room_ended' and old['round_phase'] == 'ended'
    assert q.room_list()['items'] == []
    assert q.room_list(state='ended')['items'][0]['room_id'] == str(room)


def test_group_rooms_do_not_leak_through_public_or_personal_reads(people):
    a = people('a')
    room = rid(a)
    # Group-room fixture only, no enabled group adapter.
    with session() as db, db.begin():
        from app.groups.models import Group, GroupMembership
        stamp = now(db); gid, mid = uuid.uuid4(), uuid.uuid4()
        db.add(Group(id=gid, name='private', revision=1, members_revision=1, leader_membership_id=mid,
            representative_character_id=uuid.UUID(a['ids'][0]), representative_user_id=a['uid'],
            representative_display={}, created_at=stamp)); db.flush()
        db.add(GroupMembership(id=mid, group_id=gid, user_id=a['uid'], character_id=uuid.UUID(a['ids'][0]),
            display={}, revision=1, joined_at=stamp)); db.flush()
        r = db.get(Room, room); r.scope = 'group'; r.group_id = gid
    denied('ROOM_NOT_FOUND', q.room_summary, room)
    denied('ROOM_NOT_FOUND', q.room_detail, actor(a['uid']), room)
    assert q.room_list()['items'] == [] and q.memberships(actor(a['uid']))['items'] == []


def test_cycle_and_schedule_guards_preserve_recovery(people, monkeypatch):
    a, b = people('a'), people('b')
    room = rid(a)
    with session() as db:
        end = db.get(Round, db.get(Room, room).round_id).ends_at
    monkeypatch.setattr(q, 'now', lambda db: end + timedelta(seconds=1))
    assert context(b, room)['eligibility']['reason'] == 'SCHEDULE_CONFLICT'
    assert q.management(actor(a['uid']), room)['permissions']['end']['allowed']
    monkeypatch.setattr(q, 'now', lambda db: end + timedelta(days=7))
    assert q.room_detail(actor(a['uid']), room)['room']['phase'] == 'cycle_closed'
    assert context(b, room)['eligibility']['reason'] == 'CYCLE_CHANGED'


def test_production_policy_blocks_unsupported_round_scope(people):
    a = people('a')
    command = create_command(a)
    with session() as db:
        from types import SimpleNamespace
        round = SimpleNamespace(starts_at=command.schedule.starts_at,
            ends_at=command.schedule.ends_at+timedelta(days=7), cycle_key=command.schedule.starts_at.date())
        room = SimpleNamespace(scope='public', group_id=None)
        denied('SCHEDULE_REVIEW_REQUIRED', policies.public_finite, db, a['uid'], room, round, command.selection, None)


def test_restricted_room_preserves_reject_withdraw_and_recovery_permissions(people):
    a, b = people('a'), people('b')
    room = rid(a, command=create_command(a, mode='leader_only'))
    aid = uuid.UUID(join(b, room, applying=True)[1]['application_id'])
    change(a['uid'], Limits(15, 5, 0))
    out = q.room_detail(actor(a['uid']), room)
    assert out['access']['state'] == 'restricted'
    assert out['access']['issues'][0]['dimension'] == 'raid_rooms'
    assert out['permissions']['approve']['reason'] == 'ROOM_RESTRICTED'
    assert out['permissions']['reject']['allowed'] and out['permissions']['end']['allowed']
    assert q.application(actor(a['uid']), aid)['permissions']['reject']['allowed']
    assert q.application(actor(b['uid']), aid)['permissions']['withdraw']['allowed']
    assert q.admission_context(actor(b['uid']), room, character_id=uuid.UUID(b['ids'][0]),
        selected_role='dealer', party_no=1, intent='apply')['eligibility']['reason'] == 'ROOM_RESTRICTED'


def test_get_does_not_mix_source_snapshots_during_concurrent_limit_change(people):
    a = people('a'); room = rid(a)
    changed = []
    def mutate(conn, cursor, statement, *args):
        if not changed and 'FROM raid_rooms' in statement:
            changed.append(True)
            change(a['uid'], Limits(15, 5, 0))
    event.listen(engine(), 'before_cursor_execute', mutate)
    try:
        out = q.room_detail(actor(a['uid']), room)
    finally:
        event.remove(engine(), 'before_cursor_execute', mutate)
    assert changed and not out['room']['restricted'] and out['access']['state'] == 'normal'
    assert q.room_detail(actor(a['uid']), room)['access']['state'] == 'restricted'


def test_revoked_session_rejected_even_for_public_read_with_supplied_actor(people):
    from app.auth.models import Session
    a = people('a'); room = rid(a); principal = actor(a['uid'])
    with session() as db, db.begin():
        db.get(Session, principal[1].id).revoked_at = now(db)
    denied('SESSION_REVOKED', q.room_summary, room, principal)
    denied('SESSION_REVOKED', q.memberships, principal)
    assert q.room_summary(room)['room_id'] == str(room)


def test_missing_historical_build_metadata_is_unavailable_not_fabricated(people):
    a, b = people('a'), people('b')
    room = rid(a, command=create_command(a, mode='leader_only'))
    aid = uuid.UUID(join(b, room, applying=True)[1]['application_id'])
    with session() as db, db.begin():
        db.get(Application, aid).build = None
        db.scalar(select(Membership).where(Membership.room_id == room)).build = {'legacy': 'summary'}
    denied('SERVICE_UNAVAILABLE', q.application, actor(b['uid']), aid)
    denied('SERVICE_UNAVAILABLE', q.room_detail, actor(a['uid']), room)
    assert q.management(actor(a['uid']), room)['permissions']['end']['allowed']
    assert q.room_summary(room)['member_count'] == 1


def test_public_cursor_becomes_stale_at_week_boundary(people, monkeypatch):
    a, b = people('a'), people('b')
    rid(a); rid(b)
    token = q.room_list(limit=1)['next_cursor']
    with session() as db:
        future = now(db) + timedelta(days=7)
    monkeypatch.setattr(q, 'now', lambda db: future)
    denied('CURSOR_STALE', q.room_list, limit=1, cursor=token)
