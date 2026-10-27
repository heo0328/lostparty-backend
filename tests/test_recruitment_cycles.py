"""W1: restricted LOGIN migrations, preservation, target isolation and durable ACKs."""
import os
import subprocess
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import IntegrityError, DBAPIError
from app.core.database import session, now
from app.game_accounts.support import GameError
from app.raid_rooms import cycles, readiness, continuation, admission_service
from app.raid_rooms.cycle_models import (CYCLE_MODELS, RoomCycle, CycleGeneration,
    CycleMember, CycleRound, CycleAssignment, CycleOpening, CycleDirectoryHead, ParticipationEvent, LegacyCycleEvidence)
from app.raid_rooms.integrated_models import (RecruitmentRoom as Room, RecruitmentRound as Round,
    RecruitmentMembership as Member, RecruitmentItem as Item, RecruitmentAssignment as Assignment,
    RecruitmentSession as RaidSession, RecruitmentSegment as Segment)
from app.raid_rooms.source_models import (OpeningEvent, AvailabilitySubmission, RecruitmentApplication,
    ScheduleGroup, SessionBinding, ContinuationChoice)
from app.raid_rooms.weekly_links import WeeklyOccupancy
from app.raid_weekly.models import WeeklyState
from app.raids.service import cycle as actual_cycle
from tests.test_recruitment_participation import ready, sources, imported, people, worlds, make_room, admit
from tests.test_raid_room_migrations import table_digests
from tests.test_group_foundation import actor


def upgrade(target):
    result = subprocess.run(['alembic', 'upgrade', '0024_recruitment_cycles'], env={**os.environ,
        'DATABASE_URL': target.url.render_as_string(hide_password=False)}, capture_output=True, timeout=90)
    assert result.returncode == 0, 'Restricted-role W1 migration failed'


def next_rounds(db, rid, key):
    original = list(db.scalars(select(Round).where(Round.room_id == rid)))
    for old in original:
        db.add(Round(id=uuid.uuid4(), room_id=rid, item_id=old.item_id, cycle_key=key,
            difficulty_id=old.difficulty_id, catalog_version=old.catalog_version,
            game_party_size=old.game_party_size, revision=1, state='active', created_at=now(db)))
    db.flush()


@pytest.fixture
def migrated(ready):
    engine, a, b, source = ready
    rid = make_room(a, bundle=True)
    admit(a, rid)
    admit(b, rid)
    key, request = uuid.uuid4(), {'synthetic': 'original-ack'}
    ack = admission_service.execute(actor(a['uid']), 'w1-preserve', key, request,
        lambda db, uid, stamp: (200, dict(command_id=key, outcome='noop', executed_at=stamp, revisions=[])))
    with session() as db, db.begin():
        stamp = now(db)
        current = datetime.fromisoformat(actual_cycle(stamp).cycle_key).date()
        next_rounds(db, rid, current + timedelta(days=7))
        member = db.scalar(select(Member).where(Member.room_id == rid, Member.user_id == a['uid']))
        db.add(AvailabilitySubmission(membership_id=member.id, room_id=rid, user_id=a['uid'], revision=1,
            source_personal_revision=1, intervals=[], normalized_intervals=[], submitted_at=stamp))
        item = db.scalar(select(Item).where(Item.room_id == rid).order_by(Item.id))
        event_id = uuid.uuid4()
        db.add(OpeningEvent(id=event_id, room_id=rid, item_id=item.id, target_cycle=current, mode='manual',
            settings_revision=1, authorized_effective_at=stamp, search_floor_at=stamp+timedelta(minutes=30),
            processed_at=stamp, state='applied'))
        rounds = list(db.scalars(select(Round).where(Round.room_id == rid, Round.cycle_key == current+timedelta(days=7))))
        app_id = uuid.uuid4()
        db.add(RecruitmentApplication(id=app_id, room_id=rid, user_id=b['uid'], revision=1,
            selection={}, targets=[dict(round_id=str(r.id), item_id=str(r.item_id)) for r in rounds], display={},
            build=None, origin_state='legacy_unknown', origin_scope=None, origin_group_id=None,
            state='pending', created_at=stamp, expires_at=stamp+timedelta(hours=1)))
        for bad_targets in ([], [{'round_id':'malformed','item_id':str(item.id)}]):
            db.add(RecruitmentApplication(id=uuid.uuid4(),room_id=rid,user_id=b['uid'],revision=1,
                selection={},targets=bad_targets,display={},build=None,origin_state='legacy_unknown',
                state='rejected',created_at=stamp,expires_at=stamp+timedelta(hours=1),ended_at=stamp))
        # A future choice alone must not open a cycle, restore consent or enrol.
        assignment = db.scalar(select(Assignment).where(Assignment.membership_id==member.id,
            Assignment.item_id==item.id))
        db.add(ContinuationChoice(id=uuid.uuid4(),room_id=rid,item_id=item.id,membership_id=member.id,
            user_id=a['uid'],character_id=assignment.character_id,raid_id=item.raid_id,selected_role='dealer',
            ownership_revision=1,target_cycle=current+timedelta(days=14),revision=1,state='selected'))
        current_rounds = list(db.scalars(select(Round).where(Round.room_id==rid,Round.cycle_key==current).order_by(Round.item_id)))
        next_by_item = {r.item_id:r for r in rounds}
        for label,group_key,segment_rounds in (
            ('mixed',current,[current_rounds[0],next_by_item[current_rounds[1].item_id]]),
            ('mismatched',current,rounds),
            ('verified',current+timedelta(days=7),rounds),
        ):
            groupid,sid = uuid.uuid4(),uuid.uuid4()
            db.add(ScheduleGroup(id=groupid,room_id=rid,cycle_key=group_key,client_key=label,revision=1,
                occurrence_mode='one_of',planning_mode='unscheduled',day_scope='selected_weekdays',required=True))
            db.add(RaidSession(id=sid,room_id=rid,revision=1,schedule_revision=1,state='unconfirmed',created_at=stamp))
            db.flush()
            db.add(SessionBinding(session_id=sid,room_id=rid,group_id=groupid,required=True))
            for number,rd in enumerate(segment_rounds,1):
                db.add(Segment(id=uuid.uuid4(),room_id=rid,session_id=sid,item_id=rd.item_id,round_id=rd.id,
                    ordinal=number,duration_minutes=10,duration_source='explicit'))
    old = set(inspect(engine).get_table_names()) - {'alembic_version'}
    before = table_digests(engine, old)
    upgrade(engine)
    assert table_digests(engine, old) == before
    return engine, a, b, rid, current, key, request, ack, event_id, app_id


def explicit(db, rid, key, *, generation=1):
    """Test-only promotion with explicit new authority; never a migration default."""
    row = db.scalar(select(RoomCycle).where(RoomCycle.room_id == rid, RoomCycle.cycle_key == key))
    row.provenance, row.settings_snapshot = 'explicit', {'admission_mode': 'direct_join'}
    row.generation = generation
    db.add(CycleGeneration(cycle_id=row.id, generation=generation, state='review_required',
        leader_cycle_member_id=None, leadership_revision=1, next_join_order=1, opened_at=now(db)))
    db.flush()
    for link in db.scalars(select(CycleRound).where(CycleRound.cycle_id == row.id)):
        link.generation, link.is_current = generation, True
    db.flush()
    return row


def add_next_bundle(db, rid, current, uid):
    membership = db.scalar(select(Member).where(Member.room_id == rid, Member.user_id == uid))
    assignments = list(db.scalars(select(Assignment).join(Round, Round.id == Assignment.round_id)
        .where(Assignment.membership_id == membership.id, Round.cycle_key == current)))
    for old in assignments:
        rd = db.scalar(select(Round).where(Round.item_id == old.item_id, Round.cycle_key == current+timedelta(days=7)))
        item = db.get(Item, old.item_id)
        stamp = now(db)
        fields = {c.name: getattr(old, c.name) for c in Assignment.__table__.columns
                  if c.name not in ('record_created_at', 'record_updated_at')}
        fields.update(id=uuid.uuid4(), round_id=rd.id, joined_at=stamp)
        assignment = Assignment(**fields)
        db.add(assignment)
        db.add(WeeklyState(user_id=uid, character_id=old.character_id, raid_id=item.raid_id,
            cycle_key=rd.cycle_key, revision=2, active_party_id=rid, active_difficulty_id=rd.difficulty_id,
            joined_at=stamp, updated_at=stamp))
        db.flush()
        db.add(WeeklyOccupancy(user_id=uid, character_id=old.character_id, raid_id=item.raid_id,
            cycle_key=rd.cycle_key, room_id=rid, item_id=old.item_id, round_id=rd.id,
            assignment_id=assignment.id, joined_at=stamp))
    db.flush()
    return membership


def test_migration_preserves_all_sources_and_unknowns(migrated):
    engine, a, b, rid, current, key, request, ack, event_id, app_id = migrated
    with session() as db, db.begin():
        db.execute(text('SET TRANSACTION READ ONLY'))
        readiness.require_ready(db, integrated=True)
        assert db.scalar(text('SELECT NOT rolsuper FROM pg_roles WHERE rolname=current_user'))
        rows = list(db.scalars(select(RoomCycle).where(RoomCycle.room_id == rid)))
        assert {r.cycle_key for r in rows} == {current, current+timedelta(days=7)}
        assert all(r.state == 'review_required' and r.generation is None and r.settings_snapshot is None for r in rows)
        assert db.scalar(select(CycleGeneration)) is None
        assert db.scalar(select(ParticipationEvent)) is None
        assert db.scalar(text('SELECT count(*) FROM recruitment_cycle_submissions')) == 0
        assert db.scalar(text("SELECT count(*) FROM recruitment_cycle_members WHERE state<>'review_required' OR joined_order IS NOT NULL")) == 0
        opening = db.scalar(select(CycleOpening).where(CycleOpening.legacy_event_id == event_id))
        assert opening.generation is None and opening.state == 'review_required'
        evidence = db.get(LegacyCycleEvidence, ('application', app_id))
        assert db.get(RoomCycle, evidence.cycle_id).cycle_key == current+timedelta(days=7)
        submission = db.scalar(select(LegacyCycleEvidence).where(LegacyCycleEvidence.room_id == rid,
            LegacyCycleEvidence.source_kind == 'submission'))
        assert submission.cycle_id is None
        application_evidence = list(db.scalars(select(LegacyCycleEvidence).where(
            LegacyCycleEvidence.room_id==rid,LegacyCycleEvidence.source_kind=='application')))
        assert len(application_evidence)==3 and sum(e.cycle_id is None for e in application_evidence)==2
        session_evidence = list(db.scalars(select(LegacyCycleEvidence).where(
            LegacyCycleEvidence.room_id==rid,LegacyCycleEvidence.source_kind=='session')))
        assert len(session_evidence)==3 and sum(e.cycle_id is None for e in session_evidence)==2
        for model in CYCLE_MODELS:
            table = model.__table__
            columns = {c['name']: c for c in inspect(db.connection()).get_columns(table.name)}
            assert set(columns) == set(table.columns.keys())
    # The original callback must not execute again, even after the schema change.
    result = admission_service.execute(actor(a['uid']), 'w1-preserve', key, request,
        lambda *args: pytest.fail('original ACK must precede mutation revalidation'))
    assert result == ack


def test_missing_target_and_common_authority_reads_do_not_write(migrated):
    engine, a, b, rid, current, *_ = migrated
    with session() as db, db.begin():
        db.execute(text('SET TRANSACTION READ ONLY'))
        stamp = now(db)
        value, missing = cycles.resolve(db, uuid.uuid4(), current.isoformat(), stamp)
        assert missing is None
        assert cycles.directory_revision(db, current) == 1
        assert db.get(CycleDirectoryHead, current) is None
        authority = cycles.common_authority_cycle(db, rid, stamp)
        assert authority.cycle_key == current and authority.state == 'review_required'
        assert cycles.common_authority_cycle(db, uuid.uuid4(), stamp) is None


@pytest.mark.parametrize('utc,key,phase,playable', [
    ('2026-10-20T20:59:59+00:00','2026-10-14','current',True),
    ('2026-10-20T21:00:00+00:00','2026-10-21','current',False),
    ('2026-10-21T00:59:59+00:00','2026-10-21','current',False),
    ('2026-10-21T01:00:00+00:00','2026-10-21','current',True),
    ('2026-10-21T01:00:00+00:00','2026-10-28','future',False),
])
def test_six_and_ten_hour_boundaries(utc,key,phase,playable):
    stamp = datetime.fromisoformat(utc)
    assert cycles.target(stamp,key).phase == phase
    if playable:
        assert cycles.require_playable(stamp,key).key.isoformat() == key
    else:
        with pytest.raises(GameError, match='TARGET_NOT_PLAYABLE'):
            cycles.require_playable(stamp,key)


@pytest.mark.parametrize('key', ['2026-11-04','2026-10-14','2026-10-22','20261021','invalid',None])
def test_invalid_and_out_of_window_target(key):
    with pytest.raises(GameError):
        cycles.target(datetime(2026,10,21,1,tzinfo=timezone.utc),key)


def test_bundle_join_isolated_leaders_orders_quota_and_event(migrated):
    engine, a, b, rid, current, *_ = migrated
    with session() as db, db.begin():
        c = explicit(db, rid, current)
        n = explicit(db, rid, current+timedelta(days=7))
        am = db.scalar(select(Member).where(Member.room_id == rid, Member.user_id == a['uid']))
        ac = cycles.record_bundle_join(db,c.id,am.id,uuid.uuid4(),now(db))
        bm = add_next_bundle(db,rid,current,b['uid'])
        bn = cycles.record_bundle_join(db,n.id,bm.id,uuid.uuid4(),now(db))
        assert ac.joined_order == bn.joined_order == 1
        assert db.get(CycleGeneration,(c.id,1)).leader_cycle_member_id == ac.id
        assert db.get(CycleGeneration,(n.id,1)).leader_cycle_member_id == bn.id
        c_before = (c.revision,c.members_revision,c.plan_revision)
        assert cycles.record_bundle_join(db,n.id,bm.id,uuid.uuid4(),now(db)).id == bn.id
        assert c_before == (c.revision,c.members_revision,c.plan_revision)
        assert db.scalar(select(ParticipationEvent).where(ParticipationEvent.cycle_member_id == bn.id)).action == 'joined'
        assert db.scalar(text('SELECT count(*) FROM recruitment_memberships WHERE room_id=:rid'), {'rid':rid}) == 2
        assert cycles.directory_revision(db,current) == cycles.directory_revision(db,current+timedelta(days=7)) == 2
        assert db.scalar(text('SELECT count(*) FROM recruitment_cycle_assignments WHERE room_id=:rid'),{'rid':rid})==4


def test_bundle_failure_leaves_order_and_sources_unchanged(migrated):
    engine, a, b, rid, current, *_ = migrated
    with session() as db, db.begin():
        n = explicit(db,rid,current+timedelta(days=7))
        bm = db.scalar(select(Member).where(Member.room_id == rid, Member.user_id == b['uid']))
        with pytest.raises(GameError, match='TARGET_BUNDLE_INCOMPLETE'), db.begin_nested():
            cycles.record_bundle_join(db,n.id,bm.id,uuid.uuid4(),now(db))
        assert db.get(CycleGeneration,(n.id,1)).next_join_order == 1
        assert db.scalar(select(ParticipationEvent)) is None


def test_bigint_exhaustion_has_no_wrap_or_partial_mutation(migrated):
    engine, a, b, rid, current, *_ = migrated
    with session() as db, db.begin():
        c = explicit(db,rid,current)
        gen = db.get(CycleGeneration,(c.id,1))
        gen.next_join_order = cycles.MAX_JOIN_ORDER
        db.flush()
        am = db.scalar(select(Member).where(Member.room_id == rid, Member.user_id == a['uid']))
        ac = cycles.record_bundle_join(db,c.id,am.id,uuid.uuid4(),now(db))
        assert str(ac.joined_order) == '9223372036854775807'
        bm = db.scalar(select(Member).where(Member.room_id == rid, Member.user_id == b['uid']))
        before = c.revision
        with pytest.raises(GameError, match='JOIN_ORDER_EXHAUSTED'), db.begin_nested():
            cycles.record_bundle_join(db,c.id,bm.id,uuid.uuid4(),now(db))
        assert gen.next_join_order is None and c.revision == before


def test_old_worker_and_api_activation_reject_shadow_head(migrated):
    engine, a, b, rid, *_ = migrated
    names = set(inspect(engine).get_table_names())-{'alembic_version'}
    before = table_digests(engine,names)
    for worker in (continuation.process_due, lambda: continuation.process_room(rid)):
        with pytest.raises(GameError, match='SERVICE_UNAVAILABLE'):
            worker()
    with session() as db, pytest.raises(GameError, match='SERVICE_UNAVAILABLE'):
        readiness.require_active(db)
    assert table_digests(engine,names) == before


def test_cycle_round_and_leadership_foreign_keys(migrated):
    engine, a, b, rid, current, *_ = migrated
    with session() as db, db.begin():
        c = explicit(db,rid,current)
        n = explicit(db,rid,current+timedelta(days=7))
        am = db.scalar(select(Member).where(Member.room_id == rid, Member.user_id == a['uid']))
        ac = cycles.record_bundle_join(db,c.id,am.id,uuid.uuid4(),now(db))
        cid,nid,memberid = c.id,n.id,ac.id
    with engine.begin() as connection:
        with pytest.raises(IntegrityError), connection.begin_nested():
            connection.execute(text('UPDATE recruitment_cycle_generations SET leader_cycle_member_id=:member WHERE cycle_id=:nid'),dict(member=memberid,nid=nid))
            connection.execute(text('SET CONSTRAINTS fk_cycle_generation_leader IMMEDIATE'))
        with pytest.raises(IntegrityError), connection.begin_nested():
            connection.execute(text('UPDATE recruitment_cycle_rounds SET cycle_id=:nid WHERE cycle_id=:cid'),dict(nid=nid,cid=cid))
        with pytest.raises(IntegrityError), connection.begin_nested():
            connection.execute(text('UPDATE recruitment_cycle_rounds SET generation=NULL,is_current=true WHERE cycle_id=:cid'),dict(cid=cid))
    with session() as db:
        c = db.get(RoomCycle,cid)
        foreign_round = db.scalar(select(CycleRound.round_id).where(CycleRound.cycle_id == nid))
        with pytest.raises(GameError, match='TARGET_CONTEXT_STALE'):
            cycles.require_current_round(db,c,foreign_round)


def test_event_immutability_and_generation_opening_uniqueness(migrated):
    engine, a, b, rid, current, *_ = migrated
    with session() as db, db.begin():
        c = explicit(db,rid,current)
        am = db.scalar(select(Member).where(Member.room_id == rid, Member.user_id == a['uid']))
        cycles.record_bundle_join(db,c.id,am.id,uuid.uuid4(),now(db))
        item = db.scalar(select(Item).where(Item.room_id == rid))
        for gen in (1,2):
            if gen == 2:
                db.add(CycleGeneration(cycle_id=c.id,generation=2,state='review_required',
                    leadership_revision=1,next_join_order=1,opened_at=now(db)))
                db.flush()
            db.add(CycleOpening(id=uuid.uuid4(),room_id=rid,cycle_id=c.id,generation=gen,item_id=item.id,
                mode='open' if gen == 1 else 'reopen',state='applied',command_id=uuid.uuid4(),effective_at=now(db),evidence={}))
        db.flush()
        with pytest.raises(IntegrityError), db.begin_nested():
            db.add(CycleOpening(id=uuid.uuid4(),room_id=rid,cycle_id=c.id,generation=2,item_id=item.id,
                mode='open',state='applied',command_id=uuid.uuid4(),effective_at=now(db),evidence={}))
            db.flush()
    for statement in ('UPDATE recruitment_participation_events SET action=action',
                      'DELETE FROM recruitment_participation_events',
                      'UPDATE recruitment_cycle_openings SET state=state'):
        with engine.begin() as connection, pytest.raises(DBAPIError):
            connection.execute(text(statement))


def test_durable_replay_before_changed_week_context_or_authority(migrated,monkeypatch):
    engine,a,b,rid,current,*_ = migrated
    key = uuid.uuid4()
    payload = {'target_cycle_key':current.isoformat(),'context_token':'synthetic-old-context'}
    result = cycles.execute(actor(a['uid']),'w1-test',key,payload,
        lambda db,uid,stamp:(200,dict(outcome='applied',command_id=key,
            scope=dict(current_cycle_key=current.isoformat(),server_now=stamp),room_revision=7,affected_cycle_keys=[])))
    with session() as db,db.begin():
        room=db.get(Room,rid)
        room.leader_membership_id=db.scalar(select(Member.id).where(Member.room_id==rid,Member.user_id==b['uid']))
        room.revision+=1
    monkeypatch.setattr(cycles,'actual_cycle',lambda *args:pytest.fail('replay must precede current-week validation'))
    assert cycles.execute(actor(a['uid']),'w1-test',key,payload,
        lambda *args: pytest.fail('expired context/week/authority revalidation must follow replay')) == result
    with pytest.raises(GameError, match='IDEMPOTENCY_CONFLICT'):
        cycles.execute(actor(a['uid']),'w1-test',key,dict(payload,context_token='changed'),lambda *args:None)


def test_directory_upsert_does_not_return_cached_revision(migrated):
    engine,a,b,rid,current,*_=migrated
    with session() as db,db.begin():
        cycles.touch_directory(db,current)
        cached=db.get(CycleDirectoryHead,current)
        assert cached.revision==cycles.directory_revision(db,current)==2
        cycles.touch_directory(db,current)
        assert cycles.directory_revision(db,current)==3
        assert cycles.directory_revision(db,current+timedelta(days=7))==1


def test_concurrent_join_orders_are_serialized(migrated):
    engine,a,b,rid,current,*_ = migrated
    with session() as db, db.begin():
        c = explicit(db,rid,current)
        cid = c.id
        mids = list(db.scalars(select(Member.id).where(Member.room_id == rid)))
    def register(mid):
        with session() as db,db.begin():
            return cycles.record_bundle_join(db,cid,mid,uuid.uuid4(),now(db)).joined_order
    with ThreadPoolExecutor(max_workers=2) as pool:
        orders = list(pool.map(register,mids))
    assert sorted(orders) == [1,2]
    with session() as db:
        gen = db.get(CycleGeneration,(cid,1))
        assert gen.next_join_order == 3
        assert db.get(CycleMember,gen.leader_cycle_member_id).joined_order == 1


def test_target_uuid_survives_six_hour_label_change(migrated):
    engine,a,b,rid,current,*_ = migrated
    key = current+timedelta(days=7)
    six = datetime.combine(key,datetime.min.time(),timezone.utc)-timedelta(hours=3)
    with session() as db,db.begin():
        db.execute(text('SET TRANSACTION READ ONLY'))
        before,row_before = cycles.resolve(db,rid,key.isoformat(),six-timedelta(seconds=1))
        after,row_after = cycles.resolve(db,rid,key.isoformat(),six)
        assert before.phase=='future' and after.phase=='current'
        assert row_before.id==row_after.id
        assert row_before.revision==row_after.revision==1
        assert row_before.generation is row_after.generation is None


def test_rejoin_preserves_original_intervals_and_allocates_new_order(migrated):
    engine,a,b,rid,current,*_ = migrated
    with session() as db,db.begin():
        c = explicit(db,rid,current)
        am = db.scalar(select(Member).where(Member.room_id==rid,Member.user_id==a['uid']))
        bm = db.scalar(select(Member).where(Member.room_id==rid,Member.user_id==b['uid']))
        cycles.record_bundle_join(db,c.id,am.id,uuid.uuid4(),now(db))
        member = cycles.record_bundle_join(db,c.id,bm.id,uuid.uuid4(),now(db))
        original = db.scalar(select(ParticipationEvent).where(ParticipationEvent.cycle_member_id==member.id))
        original_id,original_time = original.id,original.effective_at
        member.state,member.ended_at,member.revision='cancelled',now(db),2
        db.add(ParticipationEvent(id=uuid.uuid4(),room_id=rid,cycle_id=c.id,generation=1,cycle_member_id=member.id,
            membership_id=bm.id,user_id=b['uid'],command_id=uuid.uuid4(),action='cancelled',member_revision=2,
            effective_at=member.ended_at,evidence={}))
        db.flush()
        rejoined = cycles.record_bundle_join(db,c.id,bm.id,uuid.uuid4(),now(db))
        assert rejoined.id==member.id and rejoined.joined_order==3 and rejoined.revision==3
        assert db.get(ParticipationEvent,original_id).effective_at==original_time
        assert len(list(db.scalars(select(ParticipationEvent).where(ParticipationEvent.cycle_member_id==member.id))))==3


def test_incomplete_lease_rolls_back_whole_next_bundle(migrated):
    engine,a,b,rid,current,*_ = migrated
    with session() as db,db.begin():
        n = explicit(db,rid,current+timedelta(days=7))
        old = table_digests(engine,('raid_weekly_states','recruitment_weekly_occupancies','recruitment_assignments'))
        with pytest.raises(GameError,match='WEEKLY_OCCUPANCY_CHANGED'),db.begin_nested():
            bm = add_next_bundle(db,rid,current,b['uid'])
            lease = db.scalar(select(WeeklyOccupancy).where(WeeklyOccupancy.room_id==rid,
                WeeklyOccupancy.cycle_key==current+timedelta(days=7)))
            db.delete(lease)
            db.flush()
            cycles.record_bundle_join(db,n.id,bm.id,uuid.uuid4(),now(db))
        assert table_digests(engine,old)==old
        assert db.get(CycleGeneration,(n.id,1)).next_join_order==1
        assert db.scalar(select(ParticipationEvent)) is None


def test_assignment_target_chain_cannot_be_forged(migrated):
    engine,a,b,rid,current,*_ = migrated
    with session() as db,db.begin():
        c,n=explicit(db,rid,current),explicit(db,rid,current+timedelta(days=7))
        am=db.scalar(select(Member).where(Member.room_id==rid,Member.user_id==a['uid']))
        cycles.record_bundle_join(db,c.id,am.id,uuid.uuid4(),now(db))
        binding=db.scalar(select(CycleAssignment).where(CycleAssignment.cycle_id==c.id))
        with pytest.raises(IntegrityError),db.begin_nested():
            binding.cycle_id=n.id
            db.flush()
        with pytest.raises(IntegrityError),db.begin_nested():
            binding.user_id=b['uid']
            db.flush()
