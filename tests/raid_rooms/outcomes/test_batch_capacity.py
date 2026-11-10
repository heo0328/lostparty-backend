"""Synthetic 8x5 source boundary; does not widen product creation capacity policy."""
import uuid
from sqlalchemy import select
import pytest
from app.core.database import session,now
from app.game_accounts.models.models import Character
from app.raid_rooms.models.cycle_models import CycleRound,CycleAssignment,CycleMember
from app.raid_rooms.models.integrated_models import RecruitmentAssignment as Assignment
from app.raid_rooms.models.integrated_models import RecruitmentItem as Item
from app.raid_rooms.models.integrated_models import RecruitmentRound as Round
from app.raid_rooms.models.source_models import ItemSettings
from app.raid_rooms.models.weekly_links import WeeklyOccupancy
from app.raid_weekly.models import WeeklyState
from tests.raid_rooms.outcomes.test_batch_snapshot import values
from tests.raid_rooms.outcomes.test_batch_completion import (
    presence_db,policy_db,group_beta,beta,current,candidate,ready,sources,imported,people,worlds,
    bundle,profiles,beta_join,row_for,rounds,context,execute,valid,service,
)


def expand_fixture(a,b,rid,key,people,monkeypatch):
    extra=[people('batch-eight-'+str(i)) for i in range(6)]
    with profiles():beta_join(b,rid,key)
    original=service.life.raids.catalog()
    template=next(r for r in original.raids if r.raid_id=='horizon_cathedral')
    synthetic=[template.model_copy(update=dict(raid_id='batch-synthetic-'+str(i),display_name='합성 레이드'+str(i))) for i in range(3)]
    catalog=original.model_copy(update=dict(raids=tuple(r.model_copy(update=dict(party_size=8,party_count=2,required_support_count=2,max_dealer_count_per_class=2)) for r in (*original.raids,*synthetic))))
    monkeypatch.setattr(service.life.raids,'catalog',lambda:catalog)
    with session() as db,db.begin():
        row=row_for(db,rid,key);stamp=now(db)
        db.get(service.commands.Room,rid).app_capacity=8
        row.settings_snapshot={**row.settings_snapshot,'app_capacity':8}
        pairs=service.life.admission.rounds(db,row)
        first_item,first_round=pairs[0]
        settings=db.get(ItemSettings,first_item.id)
        template_assignment=db.scalar(select(Assignment).where(Assignment.round_id==first_round.id,Assignment.user_id==a['uid'],Assignment.state=='active'))
        template_body=values(template_assignment)
        for raid in synthetic:
            item=Item(**(values(first_item)|dict(id=uuid.uuid4(),raid_id=raid.raid_id)));db.add(item);db.flush()
            saved=values(settings);saved.update(item_id=item.id);db.add(ItemSettings(**saved))
            rd=Round(**(values(first_round)|dict(id=uuid.uuid4(),item_id=item.id,
                difficulty_id=raid.difficulties[0].difficulty_id,game_party_size=raid.party_size)))
            db.add(rd);db.flush()
            cr=values(db.get(CycleRound,first_round.id));cr.update(round_id=rd.id,item_id=item.id)
            db.add(CycleRound(**cr));db.flush()
        for _,rd in service.life.admission.rounds(db,row):rd.game_party_size=8
        base_member=service.life.actual_member(db,row,a['uid'])
        for index,w in enumerate(extra,3):
            mid=uuid.uuid4();db.add(service.life.Member(id=mid,room_id=rid,user_id=w['uid'],revision=1,joined_at=stamp));db.flush()
            cm=values(base_member);cm.update(id=uuid.uuid4(),user_id=w['uid'],membership_id=mid,joined_order=index)
            db.add(CycleMember(**cm));db.flush()
        db.get(service.CycleGeneration,(row.id,row.generation)).next_join_order=9
        worlds_by_uid={w['uid']:w for w in [a,b,*extra]}
        members=list(db.scalars(select(CycleMember).where(CycleMember.cycle_id==row.id,CycleMember.generation==row.generation)))
        for cm in members:
            w=worlds_by_uid[cm.user_id];cid=uuid.UUID(w['ids'][0])
            char=db.get(Character,cid);char.summary={**char.summary,'item_level':'9999'}
            for item,rd in service.life.admission.rounds(db,row):
                existing=db.scalar(select(Assignment.id).where(Assignment.round_id==rd.id,Assignment.membership_id==cm.membership_id,Assignment.state=='active'))
                if existing:continue
                position=cm.joined_order-1
                assn=Assignment(**(template_body|dict(id=uuid.uuid4(),item_id=item.id,round_id=rd.id,
                    user_id=cm.user_id,membership_id=cm.membership_id,character_id=cid,
                    party_no=position//4+1,slot_no=position%4+1,joined_at=stamp,
                    selected_role='support' if position in (3,7) else 'dealer')))
                db.add(assn);db.flush()
                db.add(CycleAssignment(assignment_id=assn.id,room_id=rid,cycle_id=row.id,generation=row.generation,
                    cycle_member_id=cm.id,membership_id=cm.membership_id,user_id=cm.user_id,item_id=item.id,round_id=rd.id))
                weekly=WeeklyState(user_id=cm.user_id,character_id=cid,raid_id=item.raid_id,cycle_key=row.cycle_key,
                    revision=1,active_party_id=rid,active_difficulty_id=rd.difficulty_id,joined_at=stamp,updated_at=stamp)
                db.add(weekly);db.flush()
                db.add(WeeklyOccupancy(user_id=cm.user_id,character_id=cid,raid_id=item.raid_id,cycle_key=row.cycle_key,
                    room_id=rid,item_id=item.id,round_id=rd.id,assignment_id=assn.id,joined_at=stamp));db.flush()


@pytest.mark.parametrize('selected_count',[3,5])
def test_eight_by_five_atomic_whole_and_partial(presence_db,people,monkeypatch,selected_count):
    _,a,b=presence_db;rid,c,n=bundle(a)
    expand_fixture(a,b,rid,c,people,monkeypatch)
    ids=rounds(rid,c);assert len(ids)==5
    ctx=context(a,rid,c,ids[:selected_count]);valid('PartyContext',ctx)
    impact=ctx['data']['impact']
    assert len(impact['completed_assignment_ids'])==8*selected_count
    assert len(impact['preserved_active_assignment_ids'])==8*(5-selected_count)
    assert len(ctx['data']['display']['assignments'])==40
    ack=execute(a,rid,ctx)[1];valid('PartyAck',ack)
    assert ack['data']['impact']==impact
    assert ack['data']['state']['target_state']==('closed' if selected_count==5 else 'open')
