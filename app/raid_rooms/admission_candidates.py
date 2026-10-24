"""Bulk own-character candidates in one read-only snapshot; no provider/writes."""
from collections import Counter
import hashlib
import hmac
import json
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from app.core.config import settings
from app.game_accounts.models import Account, Registration, Configuration, Activity, Character, NameClaim
from app.game_accounts.support import fail, cursor_decode, cursor_encode
from app.raid_rooms import admission_eligibility as eligibility, cycle_commands as commands
from app.raid_rooms import cycle_lifecycle as life
from app.raid_rooms.cycle_creation import scope
from app.raid_rooms.admission_candidate_schemas import AdmissionCandidatePage

MAX_RESPONSE_BYTES = 1024 * 1024


def mac(value):
    raw = json.dumps(jsonable_encoder(value),sort_keys=True,separators=(',',':')).encode()
    return hmac.new(settings.recovery_key(), b'admission-character-candidates-2\0'+raw, hashlib.sha256).hexdigest()


def source(db, uid):
    return list(db.execute(select(Registration, Account, Configuration, Character, NameClaim)
        .join(Account, Account.id == Registration.account_id)
        .join(Configuration, (Configuration.account_id == Account.id) & (Configuration.user_id == uid))
        .join(Activity, Activity.settings_id == Configuration.id)
        .join(Character, (Character.id == Activity.character_id) & (Character.account_id == Account.id))
        .join(NameClaim, (NameClaim.character_id == Character.id) & (NameClaim.server_name == Character.server_name) & (NameClaim.character_name == Character.character_name))
        .where(Registration.user_id == uid, Registration.deleted_at.is_(None), Account.owner_id == uid,
            Account.verified_at.is_not(None), Configuration.ended_at.is_(None), Character.status == 'confirmed',
            Character.lifecycle_state == 'active').order_by(Character.id)))


def replacement(db, uid, target):
    cm = life.actual_member(db,target,uid,states=('participating',))
    if cm is None:
        fail('WEEKLY_PARTICIPANT_REQUIRED',403)
    owned = life.assignments(db,target,cm)
    if not owned or any(a.state != 'active' for a in owned):
        fail('ROUND_NOT_ACTIVE')
    owned.sort(key=lambda a: str(a.item_id))
    return cm, owned


def actor_value(cm, owned):
    if cm is None:
        return None
    return dict(membership_id=cm.membership_id,cycle_member_id=cm.id,cycle_member_revision=cm.revision,
        assignments=[dict(assignment_id=a.id,revision=a.revision,item_id=a.item_id,round_id=a.round_id,
            character_id=a.character_id,selected_role=a.selected_role,party_no=a.party_no,slot_no=a.slot_no) for a in owned])


def get(principal, rid, key, intent, limit=50, cursor=None):
    if intent not in ('apply','change_character') or type(limit) is not int or not 1 <= limit <= 100:
        fail('INVALID_REQUEST',400)
    with commands.base.snapshot(principal) as (db,uid,stamp):
        room,target = commands.resolve(db,uid,rid,key,stamp)
        if intent == 'apply' and target.settings_snapshot['admission_mode'] != 'leader_only':
            fail('ADMISSION_MODE_CHANGED')
        cm, owned = replacement(db,uid,target) if intent == 'change_character' else (None,[])
        actor = actor_value(cm,owned)
        rows = source(db,uid)
        bundle = eligibility.load(db,uid,target,[c.id for _,_,_,c,_ in rows],owned=owned)
        eligible = []; exclusions = Counter(); source_facts = []
        seen = set()
        for registration,account,configuration,character,claim in rows:
            if character.id in seen:
                fail('CHARACTER_DATA_UNAVAILABLE')
            seen.add(character.id)
            source_facts.append([eligibility.facts(v) for v in (registration,account,configuration,character,claim)])
            values = {r: eligibility.evaluate(bundle,character,account.ownership_revision,r) for r in ('dealer','support')}
            if any(v['allowed'] for v in values.values()):
                eligible.append(dict(character_id=character.id,registration_id=registration.id,
                    server_name=character.server_name,character_name=character.character_name,
                    class_name=character.summary['class_name'],item_level=format(eligibility.decimal(character.summary.get('item_level')),'f'),
                    roles={r:{k:v[k] for k in ('supported','allowed','reason','comparison')} for r,v in values.items()}))
            else:
                failed = [v for v in values.values() if v['supported']]
                v = min(failed,key=lambda v:(eligibility.REASONS.index(v['reason']),
                    0 if v['comparison']['state']=='missing' else 1))
                detail = v['comparison']['state'] if v['reason']=='COMBAT_POWER_REQUIRED' else None
                exclusions[v['reason'],detail] += 1
        summary = [dict(reason=r,detail=d,character_count=n) for (r,d),n in sorted(exclusions.items(),key=lambda x:str(x[0]))]
        current_scope = scope(stamp,key,target)
        stable_scope = {k:v for k,v in current_scope.items() if k!='server_now'}
        token = mac(['snapshot',uid,principal[1].id,room.id,intent,stable_scope,actor,eligibility.facts(room),
            source_facts,eligibility.evidence(bundle),eligibility.POLICY])
        binding = mac(['cursor',uid,principal[1].id,room.id,key,intent,eligibility.POLICY])
        offset = cursor_decode(cursor,binding,token) if cursor is not None else 0
        if offset > len(eligible):
            fail('INVALID_REQUEST',400)
        page = eligible[offset:offset+limit]; following = offset+len(page)
        result = AdmissionCandidatePage.model_validate(dict(scope=current_scope,data=dict(room_id=rid,intent=intent,
            eligibility_policy_version=eligibility.POLICY,actor=actor,evaluated_at=stamp,
            catalog_version=commands.raids.catalog().catalog_version,snapshot_token=token,
            raw_candidate_count=len(rows),eligible_candidate_count=len(eligible),exclusion_summary=summary,items=page,
            next_cursor=cursor_encode(dict(scope=binding,revision=token,offset=following)) if following<len(eligible) else None))).model_dump(mode='json')
        if len(json.dumps(result,ensure_ascii=False,separators=(',',':')).encode()) > MAX_RESPONSE_BYTES:
            fail('RESPONSE_TOO_LARGE',413)
        return result
