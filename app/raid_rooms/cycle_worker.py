"""06:00 rollover closes expired actual targets; it never opens or enrols N."""
import uuid
from sqlalchemy import select
from app.core.database import session,now
from app.game_accounts.support import lock,fail,GameError
from app.raid_rooms import (cycles,cycle_lifecycle as life,cycle_leadership as leadership,
    cycle_outcomes as outcomes,cycle_planning as plan,cycle_schedule as graph)
from app.raid_rooms.cycle_models import RoomCycle,CycleMember,CycleGeneration,LegacyCycleEvidence,CycleSubmission
from app.raid_rooms.cycle_application_models import CycleApplication
from app.raid_rooms.integrated_models import RecruitmentRoom as Room


def process_room(rid):
    with session() as db,db.begin():
        from app.raid_rooms.readiness import require_cycle_worker
        require_cycle_worker(db);lock(db,'game-mutations-v1');stamp=now(db)
        current=cycles.target(stamp,life.raids.cycle(stamp).cycle_key).current
        room=db.get(Room,rid)
        if room is None:return
        for row in db.scalars(select(RoomCycle).where(RoomCycle.room_id==rid,RoomCycle.cycle_key<=current).order_by(RoomCycle.cycle_key)):
            if row.state not in ('open','review_required') or row.generation is None or row.provenance!='explicit':continue
            recovery=None
            if row.state=='review_required':
                from sqlalchemy import text
                if list(db.scalars(text('SELECT version_num FROM alembic_version')))not in (['0031_membership_actions'],['0032_beta_recruitment']):continue
                from app.raid_rooms.membership_action_models import LeadershipRecovery
                recovery=db.get(LeadershipRecovery,(row.id,row.generation))
                if recovery is None:continue
            if row.cycle_key==current:
                from app.raid_rooms import beta_schedule
                beta_schedule.reconcile(db,room,row,stamp)
                if row.state=='review_required':continue
                # N -> C is a label change, with the SAME actual rows/consents.
                # Invalid sources retain their proven seats/leases for review.
                for cm in db.scalars(select(CycleMember).where(CycleMember.cycle_id==row.id,CycleMember.generation==row.generation,CycleMember.state=='participating')):
                    try:life.qualify(db,room,row,cm)
                    except GameError as error:
                        for a in life.assignments(db,row,cm):
                            if db.get(LegacyCycleEvidence,('assignment',a.id)) is None:
                                db.add(LegacyCycleEvidence(source_kind='assignment',source_id=a.id,room_id=rid,cycle_id=row.id,
                                    reason=error.code,evidence=plan.jsonable_encoder(dict(cycle_member_id=cm.id,revision=cm.revision,assignment=life.assignment_snapshot(a)))))
                        row.state='review_required';db.get(CycleGeneration,(row.id,row.generation)).state='review_required'
                        plan.bump(db,row);break
                continue
            command=uuid.uuid4()
            for cm in db.scalars(select(CycleMember).where(CycleMember.cycle_id==row.id,CycleMember.generation==row.generation,CycleMember.state.in_(('participating','review_required') if recovery else ('participating',)))):
                owned=life.assignments(db,row,cm)
                evidence=dict(reason='cycle_closed',assignments=[life.assignment_snapshot(a) for a in owned],participations=leadership.release_parts(db,row,cm,stamp))
                submission=db.get(CycleSubmission,cm.id)
                if submission is not None:evidence['submission']=plan.snapshot(submission);db.delete(submission)
                for a in owned:
                    if a.state=='active':life.admission.core.release_assignment(db,a,stamp);a.state='stopped_incomplete'
                cm.state='stopped';cm.ended_at=stamp;cm.revision+=1;life.event(db,row,cm,command,'stopped',stamp,evidence)
            for _,rd in life.admission.rounds(db,row):
                if rd.state=='active':rd.state='stopped_incomplete';rd.ended_at=stamp;rd.revision+=1
            for sess in graph.sessions(db,row):
                if sess.state in ('confirmed','unconfirmed'):sess.state='cancelled';sess.revision+=1
            outcomes.obsolete(db,row)
            for app in db.scalars(select(CycleApplication).where(CycleApplication.cycle_id==row.id,CycleApplication.generation==row.generation,CycleApplication.state=='pending')):
                app.state='expired';app.ended_at=stamp;app.revision+=1
            row.state='closed';gen=db.get(CycleGeneration,(row.id,row.generation));gen.state='stopped';gen.closed_at=stamp
            if recovery is not None:
                recovery.state='closed';recovery.reason=None;recovery.remaining_review_reasons=[];recovery.revision+=1
            row.members_revision+=1;plan.bump(db,row)
        db.flush()
        if life.raids.cycle(now(db)).cycle_key!=current.isoformat():fail('CYCLE_CHANGED')


def process_due():
    with session() as db:
        from app.raid_rooms.readiness import require_cycle_worker
        require_cycle_worker(db)
        ids=list(db.scalars(select(RoomCycle.room_id).where(RoomCycle.state.in_(('open','review_required'))).distinct().order_by(RoomCycle.room_id)))
    for rid in ids:
        try:process_room(rid)
        except Exception as error:
            from app.core.observability import job_item_failed
            job_item_failed('cycle_rollover', error)
