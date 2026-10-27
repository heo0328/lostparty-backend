"""Prove an ended actual participation before creating a fresh writer identity."""
from dataclasses import dataclass
from sqlalchemy import select,text
from app.game_accounts.support import fail
from app.raid_rooms.cycle_models import CycleMember,CycleAssignment,ParticipationEvent
from app.raid_rooms.integrated_models import RecruitmentMembership as Member,RecruitmentAssignment as Assignment

HEAD='0033_reapplication_history'


@dataclass
class Reentry:
    member: object
    event: object
    assignments: tuple

    def evidence(self):
        return [str(self.member.id),self.member.revision,self.member.state,str(self.event.id),
                [[str(a.id),a.revision,a.state,str(a.round_id)] for a in self.assignments]]


def resolve(db,target,persistent):
    if persistent is None:return None
    if 'admission_history_head' not in db.info:
        db.info['admission_history_head']=db.scalar(text('SELECT version_num FROM public.alembic_version'))
    head=db.info['admission_history_head']
    if head not in ('0031_membership_actions','0032_beta_recruitment',HEAD):return None
    cm=db.scalar(select(CycleMember).where(CycleMember.cycle_id==target.id,CycleMember.generation==target.generation,
        CycleMember.membership_id==persistent.id).order_by(CycleMember.joined_order.desc().nullslast(),CycleMember.id.desc()))
    if cm is None or cm.state not in ('cancelled','removed'):return None
    if cm.ended_at is None or cm.user_id!=persistent.user_id or cm.room_id!=target.room_id:fail('TARGET_CONTEXT_STALE')
    event=db.scalar(select(ParticipationEvent).where(ParticipationEvent.cycle_member_id==cm.id,
        ParticipationEvent.member_revision==cm.revision,ParticipationEvent.action==cm.state))
    rows=list(db.scalars(select(Assignment).join(CycleAssignment,CycleAssignment.assignment_id==Assignment.id).where(
        CycleAssignment.cycle_member_id==cm.id,CycleAssignment.cycle_id==target.id,CycleAssignment.generation==target.generation,
        CycleAssignment.membership_id==persistent.id,CycleAssignment.user_id==persistent.user_id).order_by(Assignment.id)))
    if event is None or not rows or any(a.state not in ('left','completed') or a.ended_at is None for a in rows):fail('TARGET_CONTEXT_STALE')
    recorded={v.get('id') for v in event.evidence.get('assignments',[])}
    if recorded!={str(a.id) for a in rows}:fail('TARGET_CONTEXT_STALE')
    if any(a.state=='completed' for a in rows) and head!=HEAD:
        fail('RECRUITMENT_COMMAND_NOT_READY',503)
    return Reentry(cm,event,tuple(rows))


def for_user(db,uid,target):
    member=db.scalar(select(Member).where(Member.room_id==target.room_id,Member.user_id==uid,Member.ended_at.is_(None)))
    return resolve(db,target,member)
