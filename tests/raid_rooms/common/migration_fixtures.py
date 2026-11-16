"""Frozen pre-cutover SQL rows for migration tests, never an executable old app."""
import json
import uuid
from datetime import timedelta
from sqlalchemy import text
from app.core.database import session, now
from app.raids import service as raids


def legacy_room(leader, starts_at, ends_at, *, index=0, peers=(), ended=False):
    rid,round_id,mid=uuid.uuid4(),uuid.uuid4(),uuid.uuid4()
    with session() as db,db.begin():
        at=now(db)
        common=dict(rid=rid,round=round_id,mid=mid,at=at,ended=at if ended else None)
        db.execute(text('''INSERT INTO raid_rooms
            (id,round_id,leader_membership_id,title,scope,group_id,creation_scope,creation_group_id,
             admission_mode,revision,members_revision,applications_revision,created_at,ended_at)
            VALUES (:rid,:round,:mid,'synthetic migration','public',NULL,'public',NULL,'direct_join',1,1,1,:at,:ended)'''),common)
        db.execute(text('''INSERT INTO raid_room_rounds
            (id,room_id,raid_id,difficulty_id,catalog_version,cycle_key,party_count,revision,starts_at,ends_at,created_at,ended_at)
            VALUES (:round,:rid,'horizon_cathedral','stage1',:catalog,CAST(:cycle AS date),1,1,:starts,:ends,:at,:ended)'''),
            common|dict(catalog=raids.catalog().catalog_version,cycle=raids.cycle(at).cycle_key,starts=starts_at,ends=ends_at))
        for slot,w in enumerate((leader,*peers),1):
            cid=uuid.UUID(w['ids'][index])
            display=dict(server_name='synthetic-server',character_name='synthetic-'+str(slot),class_name='synthetic-class-'+str(slot))
            db.execute(text('''INSERT INTO raid_room_memberships
                (id,room_id,round_id,user_id,character_id,selected_role,party_no,slot_no,display,build,
                 ownership_revision,lifecycle_revision,revision,joined_at,ended_at)
                VALUES (:id,:rid,:round,:uid,:cid,'dealer',1,:slot,CAST(:display AS jsonb),NULL,1,1,1,:at,:ended)'''),
                common|dict(id=mid if slot==1 else uuid.uuid4(),uid=w['uid'],cid=cid,slot=slot,display=json.dumps(display)))
    return rid


def sql_roster():
    """Minimal historical storage facts; no auth/provider/application execution."""
    from app.auth.models import User
    from app.game_accounts.models.models import Account,Character
    uid,cid=uuid.uuid4(),uuid.uuid4()
    with session() as db,db.begin():
        at=now(db)
        db.add(User(id=uid,status='active',created_at=at,updated_at=at,last_login_at=at));db.flush()
        account=Account(owner_id=uid,verified_at=at);db.add(account);db.flush()
        db.add(Character(id=cid,account_id=account.id,server_name='synthetic-history',character_name='synthetic-history',
            summary={},fetched_at=at,confirmed_at=at))
    return uid,cid


def sql_group(uid,cid):
    from app.groups.models import Group,GroupMembership
    gid,mid=uuid.uuid4(),uuid.uuid4()
    with session() as db,db.begin():
        at=now(db)
        db.add(Group(id=gid,name='synthetic history',leader_membership_id=mid,representative_character_id=cid,
            representative_user_id=uid,representative_display={},created_at=at));db.flush()
        db.add(GroupMembership(id=mid,group_id=gid,user_id=uid,character_id=cid,display={},joined_at=at))
    return gid
