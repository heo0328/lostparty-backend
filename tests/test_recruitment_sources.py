"""Restricted-role additive migration and source invariants in tmpfs PostgreSQL."""
import os
import subprocess
import uuid
from datetime import timedelta
import pytest
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import IntegrityError
from app.core.database import session, now
from app.game_accounts.models import CharacterRoleSummary
from app.game_accounts.power_success import RolePowerSuccess
from app.raid_rooms import readiness
from app.raid_rooms.integrated_models import RecruitmentMembership, RecruitmentRound, RecruitmentAssignment, RecruitmentSegment
from app.raid_rooms.source_models import (SOURCE_MODELS, RoomSettings, ScheduleGroup, PersonalAvailability,
    SessionParticipation, TimeReservation, ContinuationChoice, OpeningEvent, RecruitmentApplication)
from app.raid_rooms.models import Application
from tests.test_integrated_recruitment_storage import imported, people, worlds
from tests.test_raid_room_migrations import table_digests
from tests.test_raid_room_foundation import selection
from tests.test_role_summaries import summary


@pytest.fixture
def sources(imported):
    target,rid,second,third,a,b,gid=imported
    with session() as db,db.begin():
        stamp=now(db)
        payload=summary();payload['combat_power']='100.50'
        db.add(CharacterRoleSummary(user_id=a['uid'],character_id=uuid.UUID(a['ids'][0]),ownership_revision=1,
            role='dealer',version=4,summary=payload,saved_at=stamp))
        missing=summary();missing.update(combat_power=None,combat_power_observed_at=None)
        db.add(CharacterRoleSummary(user_id=a['uid'],character_id=uuid.UUID(a['ids'][0]),ownership_revision=1,
            role='support',version=5,summary=missing,saved_at=stamp))
        db.add(CharacterRoleSummary(user_id=b['uid'],character_id=uuid.UUID(b['ids'][0]),ownership_revision=1,
            role='dealer',version=2,summary={'combat_power':'99999'},saved_at=stamp))
        round_id=db.scalar(select(RecruitmentRound.id).where(RecruitmentRound.room_id==second))
        appid=uuid.uuid4()
        db.add(Application(id=appid,room_id=second,round_id=round_id,user_id=b['uid'],
            selection=selection(b,index=1).model_dump(mode='json'),display={'server_name':'test','character_name':'test','class_name':None},
            build=None,state='pending',revision=1,created_at=stamp,expires_at=stamp+timedelta(days=1)))
    old=set(inspect(target).get_table_names())-{'alembic_version'}
    before=table_digests(target,old)
    result=subprocess.run(['alembic','upgrade','0020_recruitment_sources'],env={**os.environ,
        'DATABASE_URL':target.url.render_as_string(hide_password=False)},capture_output=True,text=True,timeout=90)
    assert result.returncode==0,'Isolated R1-B migration failed'
    assert table_digests(target,old)==before
    return target,rid,second,third,a,b,gid,appid


def test_preservation_and_no_fabricated_schedule_or_success(sources):
    target,rid,second,third,a,b,gid,appid=sources
    with session() as db,db.begin():
        db.connection(execution_options={'isolation_level':'REPEATABLE READ'})
        db.execute(text('SET TRANSACTION READ ONLY'))
        readiness.require_ready(db,integrated=True)
        assert db.scalar(select(RolePowerSuccess.combat_power))=='100.50'
        power=db.scalar(select(RolePowerSuccess))
        assert power.source_summary_version==4 and power.power_revision==2
        assert power.record_created_at==power.record_updated_at
        assert power.source_summary['combat_power']==power.combat_power
        app=db.get(RecruitmentApplication,appid)
        assert app.origin_state=='legacy_unknown' and app.origin_scope is None and app.origin_group_id is None
        assert app.build is None and app.targets[0]['round_id']==str(db.get(Application,appid).round_id)
        for settings in db.scalars(select(RoomSettings)):
            assert settings.experience_level is None and not settings.auto_open_enabled
            assert settings.dealer_min is None and settings.support_min is None
        for model in SOURCE_MODELS:
            if model not in (RoomSettings,RecruitmentApplication):
                assert db.scalar(text('SELECT count(*) FROM '+model.__tablename__))==0
        for model in SOURCE_MODELS+(RolePowerSuccess,):
            columns={col['name']:col for col in inspect(db.connection()).get_columns(model.__tablename__)}
            assert set(columns)==set(model.__table__.columns.keys())
            for col in model.__table__.columns:
                assert columns[col.name]['nullable']==col.nullable
                assert str(columns[col.name]['type'].compile(dialect=target.dialect))==str(col.type.compile(dialect=target.dialect))


@pytest.mark.parametrize('sql',[
    "UPDATE recruitment_settings SET experience_level='unknown' WHERE room_id=:room",
    "UPDATE recruitment_settings SET dealer_min='1',support_min='2' WHERE room_id=:room",
    "UPDATE recruitment_settings SET auto_open_enabled=true WHERE room_id=:room",
])
def test_settings_constraints_rollback(sources,sql):
    target,rid,*_=sources
    with target.begin() as c:
        with pytest.raises(IntegrityError),c.begin_nested():c.execute(text(sql),{'room':rid})
        assert c.scalar(text('SELECT experience_level FROM recruitment_settings WHERE room_id=:room'),{'room':rid}) is None


def group_row(room,cycle,**changes):
    values=dict(id=uuid.uuid4(),room_id=room,cycle_key=cycle,client_key='test',revision=1,
        occurrence_mode='one_of',planning_mode='coordinated',day_scope='any_current_cycle',required=True,
        auto_additional_members=1,selected_session_id=None)
    return ScheduleGroup(**(values|changes))


def test_auto_zero_and_unlimited_days_cannot_become_manual(sources):
    target,rid,*_=sources
    with session() as db,db.begin():
        cycle=db.scalar(select(RecruitmentRound.cycle_key).where(RecruitmentRound.room_id==rid))
        for changes in ({'auto_additional_members':0},{'planning_mode':'manual','auto_additional_members':None}):
            with pytest.raises(IntegrityError),db.begin_nested():
                db.add(group_row(rid,cycle,**changes));db.flush()
        db.add(group_row(rid,cycle));db.flush()


def test_edit_intervals_remain_distinct_from_normalized_intervals(sources):
    target,rid,second,third,a,*_=sources
    raw=[{'weekday':3,'start':'23:00','end':'03:30','end_day_offset':1}]
    normalized=[{'start_minute':4260,'end_minute':4530}]
    with session() as db,db.begin():
        db.add(PersonalAvailability(user_id=a['uid'],revision=2,timezone='Asia/Seoul',
            intervals=raw,normalized_intervals=normalized,saved_at=now(db)))
    with session() as db:
        row=db.get(PersonalAvailability,a['uid'])
        assert row.intervals==raw and row.normalized_intervals==normalized


def test_reservations_are_bound_to_the_exact_person_and_segment(sources):
    target,rid,second,third,a,b,*_=sources
    with session() as db,db.begin():
        member=db.scalar(select(RecruitmentMembership).where(RecruitmentMembership.room_id==rid,RecruitmentMembership.user_id==a['uid']))
        assignment=db.scalar(select(RecruitmentAssignment).where(RecruitmentAssignment.membership_id==member.id))
        segment=db.scalar(select(RecruitmentSegment).where(RecruitmentSegment.room_id==rid))
        part=SessionParticipation(id=uuid.uuid4(),room_id=rid,session_id=segment.session_id,membership_id=member.id,
            user_id=a['uid'],revision=1,state='active',confirmation_state='confirmed',confirmed_schedule_revision=1,confirmed_at=now(db))
        db.add(part);db.flush()
        fields=dict(room_id=rid,participation_id=part.id,session_id=segment.session_id,membership_id=member.id,user_id=a['uid'],
            assignment_id=assignment.id,item_id=assignment.item_id,round_id=assignment.round_id,segment_id=segment.id,
            schedule_revision=1,starts_at=segment.starts_at,ends_at=segment.ends_at)
        for changes in ({'user_id':b['uid']},{'room_id':second}):
            with pytest.raises(IntegrityError),db.begin_nested():
                db.add(TimeReservation(id=uuid.uuid4(),**(fields|changes)));db.flush()
        first=TimeReservation(id=uuid.uuid4(),**fields);db.add(first);db.flush()
        with pytest.raises(IntegrityError),db.begin_nested():
            db.add(TimeReservation(id=uuid.uuid4(),**(fields|{'schedule_revision':2})));db.flush()
        first.released_at=now(db);first.released_reason='schedule_changed';db.flush()
        db.add(TimeReservation(id=uuid.uuid4(),**(fields|{'schedule_revision':2})));db.flush()


def test_future_choice_conflict_replacement_and_different_character(sources):
    target,rid,second,third,a,*_=sources
    with session() as db,db.begin():
        rounds={r.room_id:r for r in db.scalars(select(RecruitmentRound))}
        members={m.room_id:m for m in db.scalars(select(RecruitmentMembership).where(RecruitmentMembership.user_id==a['uid']))}
        def choice(room,cid):
            rd=rounds[room]
            return ContinuationChoice(id=uuid.uuid4(),room_id=room,item_id=rd.item_id,membership_id=members[room].id,user_id=a['uid'],
                character_id=uuid.UUID(cid),raid_id='horizon_cathedral',selected_role='dealer',ownership_revision=1,
                target_cycle=rd.cycle_key+timedelta(days=7),revision=1,state='selected')
        first=choice(rid,a['ids'][0]);db.add(first);db.flush()
        with pytest.raises(IntegrityError),db.begin_nested():db.add(choice(second,a['ids'][0]));db.flush()
        different=choice(second,a['ids'][1]);db.add(different);db.flush()
        # Explicitly release both choices before A->B replaces the same item representation.
        stamp=now(db)
        for row in (first,different):
            row.state='replaced';row.ended_at=stamp;row.revision+=1
        db.flush();db.add(choice(second,a['ids'][0]));db.flush()


def test_authoritative_opening_floor_is_immutable_after_delayed_processing(sources):
    target,rid,*_=sources
    with session() as db,db.begin():
        rd=db.scalar(select(RecruitmentRound).where(RecruitmentRound.room_id==rid))
        effective=db.scalar(text("SELECT ((CAST(:cycle AS date)+time '06:00') AT TIME ZONE 'Asia/Seoul')"),{'cycle':rd.cycle_key})
        event=OpeningEvent(id=uuid.uuid4(),room_id=rid,item_id=rd.item_id,target_cycle=rd.cycle_key,mode='scheduled_auto',
            settings_revision=1,authorized_effective_at=effective,search_floor_at=effective+timedelta(minutes=30),state='scheduled')
        db.add(event);db.flush()
        with pytest.raises(IntegrityError),db.begin_nested():
            event.search_floor_at=effective+timedelta(hours=5);db.flush()
        db.refresh(event)
        event.state='applied';event.processed_at=effective+timedelta(hours=5);db.flush()
        assert event.search_floor_at==effective+timedelta(minutes=30)


def test_readiness_rejects_success_fk_that_would_block_existing_retirement(sources):
    from app.game_accounts.support import GameError
    target,*_=sources
    with session() as db,db.begin():
        fk=inspect(db.connection()).get_foreign_keys('character_role_power_successes')[0]
        saved=db.begin_nested()
        try:
            name=fk['name']
            assert all(c.isalnum() or c=='_' for c in name)
            db.execute(text('ALTER TABLE character_role_power_successes DROP CONSTRAINT "'+name+'"'))
            db.execute(text('''ALTER TABLE character_role_power_successes ADD CONSTRAINT plain_power_parent
                FOREIGN KEY (user_id,character_id,ownership_revision,role)
                REFERENCES character_role_summaries (user_id,character_id,ownership_revision,role)'''))
            with pytest.raises(GameError) as error:readiness.require_ready(db,integrated=True)
            assert error.value.code=='SERVICE_UNAVAILABLE'
        finally:saved.rollback()
        readiness.require_ready(db,integrated=True)


def test_applied_duration_evidence_does_not_follow_later_item_settings(sources):
    from app.raid_rooms.source_models import ItemSettings, SegmentDurationEvidence
    from app.raid_rooms.integrated_models import RecruitmentSession
    target,rid,*_=sources
    with session() as db,db.begin():
        rd=db.scalar(select(RecruitmentRound).where(RecruitmentRound.room_id==rid));stamp=now(db)
        settings=ItemSettings(item_id=rd.item_id,room_id=rid,revision=1,difficulty_id=rd.difficulty_id,
            catalog_version=rd.catalog_version,duration_minutes=None,duration_policy_version='synthetic-v1')
        sess=RecruitmentSession(id=uuid.uuid4(),room_id=rid,revision=1,schedule_revision=1,state='unconfirmed',
            starts_at=stamp,ends_at=stamp+timedelta(minutes=10),created_at=stamp)
        db.add_all([settings,sess]);db.flush()
        seg=RecruitmentSegment(id=uuid.uuid4(),room_id=rid,session_id=sess.id,item_id=rd.item_id,round_id=rd.id,
            ordinal=1,duration_minutes=10,duration_source='difficulty_default',starts_at=sess.starts_at,ends_at=sess.ends_at)
        db.add(seg);db.flush()
        evidence=SegmentDurationEvidence(segment_id=seg.id,room_id=rid,session_id=sess.id,item_id=rd.item_id,
            round_id=rd.id,item_settings_revision=1,duration_policy_version='synthetic-v1')
        db.add(evidence);db.flush()
        settings.revision=2;settings.duration_minutes=20;settings.duration_policy_version='synthetic-v2';db.flush()
        db.refresh(evidence);db.refresh(seg)
        assert evidence.item_settings_revision==1 and evidence.duration_policy_version=='synthetic-v1'
        assert seg.duration_minutes==10 and seg.ends_at-seg.starts_at==timedelta(minutes=10)
