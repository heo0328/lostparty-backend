"""Owner-only revision-bound correction, including past weeks and inactive records."""
import uuid
from datetime import datetime, timedelta
from sqlalchemy import select, text
from fastapi.encoders import jsonable_encoder
from app.core.database import session
from app.game_accounts.models import Account, Character, Registration
from app.game_accounts.support import fail
from app.game_accounts.lifecycle import digest
from app.raid_weekly.models import WeeklyState
from app.raid_weekly.service import parse_cycle
from app.raid_rooms import cycles, command_context as opaque, admission_service as base
from app.raid_rooms.cycle_creation import permission
from app.raid_rooms.completion_correction_models import CompletionCorrection
from app.raid_rooms import completion_correction_schemas as schema
from app.raids import service as raids


def ready(db):
    if list(db.scalars(text('SELECT version_num FROM alembic_version')))not in (['0030_completion_corrections'],['0031_membership_actions']):
        fail('RECRUITMENT_COMMAND_NOT_READY',503)


def read(db,uid,cid,raid,key,stamp):
    ready(db);target=parse_cycle(key);current=raids.cycle(stamp)
    if target>parse_cycle(current.cycle_key) or not isinstance(raid,str) or not 1<=len(raid)<=64:fail('INVALID_REQUEST',400)
    character=db.get(Character,cid)
    if character is None or db.scalar(select(Registration.id).where(Registration.user_id==uid,
            Registration.account_id==character.account_id,Registration.deleted_at.is_(None))) is None:fail('CHARACTER_NOT_FOUND',404)
    account=db.get(Account,character.account_id)
    if account.owner_id!=uid or account.verified_at is None:fail('OWNERSHIP_REQUIRED',403)
    state=db.get(WeeklyState,(uid,cid,raid,target))
    if state is None and not any(r.raid_id==raid for r in raids.catalog().raids):fail('RAID_NOT_FOUND',404)
    sources=[]
    if state and state.manual_completed_at:sources.append(dict(source='manual',completed_at=state.manual_completed_at,difficulty_id=state.manual_difficulty_id,party_id=None))
    if state and state.party_completed_at:sources.append(dict(source='party',completed_at=state.party_completed_at,difficulty_id=state.party_difficulty_id,party_id=state.completed_party_id))
    data=dict(character_id=cid,raid_id=raid,target_cycle_key=key,weekly_revision=state.revision if state else 1,
        ownership_revision=account.ownership_revision,lifecycle_revision=character.lifecycle_revision,completion_sources=sources,
        permission=permission(None if sources else 'COMPLETION_NOT_FOUND'),confirmation=None)
    binding=digest(jsonable_encoder([uid,current.cycle_key,data]))
    return data,binding,state,current


def context(principal,cid,raid,key):
    with base.snapshot(principal) as (db,uid,stamp):
        data,binding,_,current=read(db,uid,cid,raid,key,stamp)
        if data['permission']['allowed']:
            expires=min(stamp+timedelta(seconds=120),current.ends_at)
            token=opaque.seal(dict(flow='completion-correction',actor=str(uid),character=str(cid),raid=raid,target=key,
                current=current.cycle_key,digest=binding,expires=expires.isoformat()))
            data['confirmation']=dict(context_token=token,issued_at=stamp,expires_at=expires)
        return schema.CorrectionContext.model_validate(dict(server_now=stamp,current_cycle_key=current.cycle_key,data=data)).model_dump(mode='json')


def execute(principal,cid,raid,command,data):
    body=data.model_dump(mode='json')
    def run(db,uid,stamp):
        value,binding,state,current=read(db,uid,cid,raid,body['target_cycle_key'],stamp)
        if body['expected_cycle_key']!=current.cycle_key:fail('CYCLE_CHANGED')
        for expected,field in [('expected_weekly_revision','weekly_revision'),('expected_ownership_revision','ownership_revision'),('expected_lifecycle_revision','lifecycle_revision')]:
            if body[expected]!=value[field]:fail('REVISION_CONFLICT')
        token=opaque.unseal(body['correction_context_token'])
        if (token.get('flow'),token.get('actor'),token.get('character'),token.get('raid'),token.get('target'))!=('completion-correction',str(uid),str(cid),raid,body['target_cycle_key']):fail('CONTEXT_INVALID',400)
        try:expires=datetime.fromisoformat(token['expires'])
        except (KeyError,TypeError,ValueError):fail('CONTEXT_INVALID',400)
        if token.get('current')!=current.cycle_key:fail('CYCLE_CHANGED')
        if stamp>=expires:fail('COMMAND_CONTEXT_EXPIRED')
        if token.get('digest')!=binding:fail('COMPLETION_CONTEXT_CHANGED')
        if not value['completion_sources']:fail('COMPLETION_NOT_FOUND')
        if state.revision>=2147483647:fail('REVISION_CONFLICT')
        correction=uuid.uuid4()
        db.add(CompletionCorrection(id=correction,user_id=uid,character_id=cid,raid_id=raid,cycle_key=state.cycle_key,
            command_id=command,before_revision=state.revision,after_revision=state.revision+1,sources=jsonable_encoder(value['completion_sources']),effective_at=stamp))
        state.manual_completed_at=state.manual_difficulty_id=None
        state.party_completed_at=state.completed_party_id=state.party_difficulty_id=None
        state.revision+=1;state.updated_at=stamp
        result=schema.CorrectionResult.model_validate(dict(server_now=stamp,current_cycle_key=current.cycle_key,
            data=dict(command_id=command,outcome='applied',correction_id=correction,character_id=cid,raid_id=raid,
                target_cycle_key=body['target_cycle_key'],weekly_revision=state.revision,completion_sources=[],participation_restored=False))).model_dump(mode='json')
        db.flush()
        def final(current_stamp):
            if current_stamp>=expires:fail('COMMAND_CONTEXT_EXPIRED')
        return 200,result,final
    return cycles.execute(principal,'correct-weekly',command,dict(character_id=str(cid),raid_id=raid,body=body),run)
