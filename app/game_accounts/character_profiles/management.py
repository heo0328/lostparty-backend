"""Atomic own-account activity, representative and movable-subset ordering."""
import hashlib
import json
from decimal import Decimal, InvalidOperation, localcontext
from uuid import UUID
from sqlalchemy import select, delete, tuple_, text
from pydantic import ValidationError
from app.core.database import session, now
from app.game_accounts.common.support import authorize, fail, reserve, commit_result, release
from app.game_accounts.character_profiles.representative import owned
from app.game_accounts.rosters.service import config
from app.game_accounts.models.models import Character, NameClaim, Configuration, Activity, CharacterPersonalPreferences as Preferences
from app.game_accounts.schemas.management_schemas import ManagementContext
POLICY='character-management-1'

def level(raw):
    if not isinstance(raw,str) or not raw.strip() or len(raw)>128:return None
    try:
        with localcontext() as ctx:
            ctx.prec=128
            v=Decimal(raw)
            if not v.is_finite() or v<0:return None
            if v==0:return '0'
            if v.adjusted()>63 or v.adjusted() < -128:return None
            result=format(v.normalize(),'f')
            return result if len(result)<=64 else None
    except (InvalidOperation,ValueError):return None

def sort_key(row):
    rank=row['display_order'];lev=row['item_level']
    return (rank is None,rank or 0,lev is None,Decimal(lev).copy_negate() if lev is not None else 0,
            row['character_name'].encode('utf-16-be'),row['character_id'])

def context(db,uid,rid):
    registration,account=owned(db,uid,rid);configuration=config(db,uid,account.id)
    chars=list(db.scalars(select(Character).where(Character.account_id==account.id,Character.lifecycle_state!='retired').order_by(Character.id).limit(1001)))
    if len(chars)>1000:fail('CHARACTER_CONTEXT_TOO_LARGE',413)
    prefs={p.character_id:p for p in db.scalars(select(Preferences).where(Preferences.user_id==uid,Preferences.ownership_revision==account.ownership_revision,Preferences.character_id.in_([c.id for c in chars])))}
    claims={(c.server_name,c.character_name):c.character_id for c in db.scalars(select(NameClaim).where(tuple_(NameClaim.server_name,NameClaim.character_name).in_([(c.server_name,c.character_name) for c in chars])))} if chars else {}
    rows=[]
    for c in chars:
        reason=('CHARACTER_UNUSABLE' if c.lifecycle_state!='active' or c.status!='confirmed' else
                'IDENTITY_CONFLICT' if claims.get((c.server_name,c.character_name))!=c.id else None)
        pref=prefs.get(c.id)
        rows.append(dict(character_id=str(c.id),display_order=pref.display_order if pref else None,
            item_level=level(c.summary.get('item_level')),character_name=c.character_name,usable=reason is None,blocked_reason=reason))
    rows.sort(key=sort_key)
    chosen=list(db.scalars(select(Activity.character_id).where(Activity.settings_id==configuration.id).order_by(Activity.character_id).limit(201))) if configuration else []
    if len(chosen)>200:fail('CHARACTER_CONTEXT_TOO_LARGE',413)
    rep=configuration.representative_id if configuration else None
    refs=set(chosen)|({rep} if rep else set())
    if refs:
        owners=dict(db.execute(select(Character.id,Character.account_id).where(Character.id.in_(refs))).all())
        if any(owners.get(cid)!=account.id for cid in refs):fail('SERVICE_UNAVAILABLE',503)
    fingerprint=[POLICY,str(uid),str(account.id),account.ownership_revision,
        [[r['character_id'],r['display_order'],r['item_level'],r['character_name']] for r in rows]]
    digest=hashlib.sha256(json.dumps(fingerprint,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
    value=dict(scope=dict(registration_id=str(registration.id),game_account_id=str(account.id),registration_version=registration.version,
        settings_version=configuration.version if configuration else 1,ownership_revision=account.ownership_revision,
        roster_revision=account.roster_revision,policy_version=POLICY),data=dict(configuration_state=configuration.state if configuration else 'unconfigured',
        activity_character_ids=[str(c) for c in chosen],representative_character_id=str(rep) if rep else None,
        ordered_all_character_ids=[r['character_id'] for r in rows],order_digest=digest,characters=rows,
        evaluated_at=now(db).isoformat().replace('+00:00','Z')))
    try:value=ManagementContext.model_validate(value).model_dump()
    except ValidationError:fail('SERVICE_UNAVAILABLE',503)
    return value,configuration,account,prefs

def get(principal,rid):
    with session() as db,db.begin():
        db.connection(execution_options={'isolation_level':'REPEATABLE READ'})
        db.execute(text('SET TRANSACTION READ ONLY'))
        return context(db,authorize(db,principal),rid)[0]

def put(principal,rid,key,body):
    ticket,replay=reserve(principal,'character-management-1',key,dict(target=str(rid),body=body))
    if replay:
        with session() as db:owned(db,authorize(db,principal),rid)
        return replay
    try:
        with session() as db,db.begin():
            uid=authorize(db,principal,write=True)
            before,configuration,account,prefs=context(db,uid,rid);scope=before['scope'];data=before['data']
            for name in ('registration_version','settings_version','ownership_revision','roster_revision'):
                if scope[name]!=body['expected_'+name]:fail('REVISION_CONFLICT')
            if data['order_digest']!=body['expected_order_digest']:fail('REVISION_CONFLICT')
            selected=body['activity_character_ids'];rep=body['representative_character_id']
            if not selected:fail('EMPTY_ACTIVITY_SELECTION',400)
            if len(set(selected))!=len(selected):fail('INVALID_REQUEST',400)
            if rep not in selected:fail('REPRESENTATIVE_REQUIRED',400)
            rows={r['character_id']:r for r in data['characters']}
            if any(cid not in rows for cid in selected):fail('CHARACTER_NOT_FOUND',404)
            if any(not rows[cid]['usable'] for cid in selected):fail('CHARACTER_UNUSABLE')
            movable=set(selected)-{rep};baseline=[cid for cid in data['ordered_all_character_ids'] if cid in movable]
            requested=body.get('ordered_character_ids')
            if 'ordered_character_ids' in body and (not isinstance(requested,list) or len(requested)!=len(movable) or set(requested)!=movable):fail('INVALID_REQUEST',400)
            reorder=requested is not None and requested!=baseline
            changed=set(selected)!=set(data['activity_character_ids']) or rep!=data['representative_character_id'] or data['configuration_state']!='configured' or reorder
            if changed:
                if configuration is None:
                    configuration=Configuration(user_id=uid,account_id=account.id);db.add(configuration);db.flush()
                if set(selected)!=set(data['activity_character_ids']):
                    db.execute(delete(Activity).where(Activity.settings_id==configuration.id))
                    db.add_all([Activity(settings_id=configuration.id,account_id=account.id,character_id=UUID(cid)) for cid in selected])
                configuration.representative_id=UUID(rep);configuration.state='configured';configuration.version+=1;configuration.next_change_at=None
                if reorder:
                    iterator=iter(requested)
                    ordered=[next(iterator) if cid in movable else cid for cid in data['ordered_all_character_ids']]
                    saved=now(db)
                    for rank,cid in enumerate(ordered):
                        pref=prefs.get(UUID(cid))
                        if pref is not None and pref.display_order==rank:continue
                        if pref is None:
                            pref=Preferences(user_id=uid,character_id=UUID(cid),ownership_revision=account.ownership_revision,
                                preferred_role=None,visible=True,version=1);db.add(pref)
                        pref.display_order=rank;pref.version+=1;pref.saved_at=saved
            db.flush()
            after=context(db,uid,rid)[0]
            return commit_result(db,ticket,200,after)
    except Exception:
        release(ticket);raise
