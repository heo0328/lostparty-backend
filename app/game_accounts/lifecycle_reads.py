"""V2 read-only current-state/history projections. No provider or DB writes."""
from sqlalchemy import select
from app.core.database import session
from app.game_accounts.models import Character, CharacterRetirement, CharacterHistoryHead
from app.game_accounts import service, lifecycle
from app.game_accounts.power_service import overlay
from app.game_accounts.support import authorize, cursor_encode, cursor_decode


def characters(principal, rid, limit, cursor):
    with session() as db, db.begin():
        db.connection(execution_options={'isolation_level': 'REPEATABLE READ'})
        uid=authorize(db,principal)
        registration=service.reg(db,uid,rid)
        account,state=service.ownership(db,uid,registration)
        settings=service.settings_out(db,uid,registration)
        scope=f'lifecycle-characters:{uid}:{rid}'
        revision=lifecycle.digest((lifecycle.registration_stamp(db,registration),settings['settings_version']))
        offset=cursor_decode(cursor,scope,revision) if cursor else 0
        items=[]
        if account and state=='owned':
            rows=list(db.scalars(select(Character).where(Character.account_id==account.id,
                Character.lifecycle_state!='retired').order_by(Character.server_name,Character.character_name,Character.id)))
            for c in rows:
                items.append(current_item(db, uid, registration, c))
        else:
            items = [preview_item(db, uid, registration, row) for row in registration.preview]
        following=offset+limit
        return dict(registration_id=registration.id,game_account_id=account.id if account else None,
            is_main=registration.is_main,registration_version=registration.version,ownership_status=state,
            ownership_revision=account.ownership_revision if account else None,
            roster_revision=account.roster_revision if account else registration.version,settings=settings,
            items=items[offset:following],next_cursor=cursor_encode(dict(scope=scope,revision=revision,offset=following)) if following<len(items) else None,
            server_fetched_at=registration.fetched_at)


def current_item(db, uid, registration, character, *, candidates=None, at=None):
    c = character
    usable = lifecycle.usable(db, c)
    status = 'suspect' if c.status != 'confirmed' or c.lifecycle_state == 'suspect' else 'active'
    blocked = None if usable else 'CHARACTER_UNUSABLE' if status == 'suspect' else 'IDENTITY_CONFLICT'
    item = dict(c.summary, character_id=c.id, roster_status=c.status,
                summary_fetched_at=c.fetched_at, last_confirmed_at=c.confirmed_at, requires_refresh=not usable,
                eligible=usable, power_fetched_at=c.power_fetched_at, lifecycle_state=status,
                lifecycle_revision=c.lifecycle_revision, usable=usable, blocked_reason=blocked)
    item.update(overlay(db, uid, item, lifecycle.power_scope(registration, c), candidates=candidates, at=at))
    return item


def preview_item(db, uid, registration, row):
    item = dict(row, character_id=None, roster_status='preview', summary_fetched_at=registration.fetched_at,
                last_confirmed_at=None, requires_refresh=True, eligible=False, power_fetched_at=None,
                lifecycle_state='preview', lifecycle_revision=None, usable=False, blocked_reason='OWNERSHIP_REQUIRED')
    item.update(overlay(db, uid, item, lifecycle.power_scope(registration)))
    return item


def retirements(principal, limit, cursor):
    with session() as db, db.begin():
        db.connection(execution_options={'isolation_level': 'REPEATABLE READ'})
        uid=authorize(db,principal)
        head=db.get(CharacterHistoryHead,uid)
        revision=head.revision if head else 1
        scope=f'character-retirements:{uid}'
        offset=cursor_decode(cursor,scope,revision) if cursor else 0
        rows=list(db.scalars(select(CharacterRetirement).where(CharacterRetirement.user_id==uid)
            .order_by(CharacterRetirement.retired_at,CharacterRetirement.id).offset(offset).limit(limit+1)))
        items=[dict(history_id=h.id,character_id=h.character_id,game_account_id=h.account_id,
            server_name=h.server_name,character_name=h.character_name,class_name=h.class_name,
            combat_power=h.combat_power,item_level=h.item_level,power_fetched_at=h.power_fetched_at,
            item_level_fetched_at=h.item_level_fetched_at,retired_at=h.retired_at,
            lifecycle_revision=h.lifecycle_revision) for h in rows[:limit]]
        return dict(items=items,history_revision=revision,
            next_cursor=cursor_encode(dict(scope=scope,revision=revision,offset=offset+limit)) if len(rows)>limit else None)
