"""Synthetic ownership-result projections; these tests do not approve cleanup policy."""
import os
import subprocess
import uuid
import pytest
from sqlalchemy import select
from app.core.database import session,now
from app.game_accounts.models import Account,Registration,Configuration
from app.game_accounts.service import ownership
from app.groups.models import GroupMembership
from tests.test_group_display import group_features,worlds,add,get,PROFILE


@pytest.mark.parametrize('head',['0034_group_features','0035_cycle_group_policy'])
def test_losing_one_of_three_rosters_keeps_other_activity_and_user_membership(group_features,client,worlds,head):
    engine,viewer,old,gid=group_features
    extra=[worlds('impact-extra-1'),worlds('impact-extra-2')]
    with session() as db,db.begin():
        for w in extra:
            db.get(Account,w['aid']).owner_id=old['uid']
            r=db.get(Registration,uuid.UUID(w['rid']));r.is_main=False;r.user_id=old['uid']
            db.get(Configuration,w['cid']).user_id=old['uid']
    if head=='0035_cycle_group_policy':
        result=subprocess.run(['alembic','upgrade',head],env={**os.environ,'DATABASE_URL':engine.url.render_as_string(hide_password=False)},capture_output=True,timeout=90)
        assert result.returncode==0,'migration failed'
    mid=add(client,viewer,old,gid)
    path=f'/v1/groups/{gid}/members/{mid}/activity-characters'
    before=get(client,viewer,path)
    assert {i['character_id'] for i in before['items']}=={cid for w in [old,*extra] for cid in w['ids'][:2]}
    with session() as db:
        preserved={w['aid']:(db.get(Account,w['aid']).ownership_revision,db.get(Registration,uuid.UUID(w['rid'])).version,db.get(Configuration,w['cid']).version,db.get(Configuration,w['cid']).ended_at) for w in extra}
    # Simulate the already-proven final transfer's authority/configuration result.
    # No active raid is installed and no new dispute cleanup behavior is invoked.
    with session() as db,db.begin():
        account=db.get(Account,old['aid']);account.owner_id=viewer['uid'];account.ownership_revision+=1
        conf=db.get(Configuration,old['cid']);conf.ended_at=now(db);conf.version+=1
    after=get(client,viewer,path)
    assert {i['character_id'] for i in after['items']}=={cid for w in extra for cid in w['ids'][:2]}
    member=next(v for v in get(client,viewer,f'/v1/groups/{gid}/members',**PROFILE)['items'] if v['membership_id']==mid)
    assert member['character_spec']['state']=='unavailable'
    with session() as db:
        assert ownership(db,old['uid'],db.get(Registration,uuid.UUID(old['rid'])))[1]=='ownership_lost'
        membership=db.get(GroupMembership,uuid.UUID(mid));assert membership.user_id==old['uid'] and membership.ended_at is None
        for w in extra:
            assert ownership(db,old['uid'],db.get(Registration,uuid.UUID(w['rid'])))[1]=='owned'
            assert (db.get(Account,w['aid']).ownership_revision,db.get(Registration,uuid.UUID(w['rid'])).version,db.get(Configuration,w['cid']).version,db.get(Configuration,w['cid']).ended_at)==preserved[w['aid']]
