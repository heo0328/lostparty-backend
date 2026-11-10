"""Internal batch evidence preparation; no public batch endpoint is installed."""
import copy
import hashlib
import json
import uuid
from datetime import date
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from sqlalchemy import inspect, select

from app.core.database import session, now
from app.game_accounts.common.support import GameError
from app.game_accounts.rosters.lifecycle import digest
from app.raid_rooms.common import beta_profile
from app.raid_rooms.outcomes import batch_snapshot as snapshot
from app.raid_rooms.models.cycle_models import RoomCycle, CycleAssignment, CycleRound
from app.raid_rooms.models.integrated_models import RecruitmentAssignment as Assignment
from app.raid_rooms.models.integrated_models import RecruitmentRound as Round
from app.raid_rooms.models.integrated_models import RecruitmentItem as Item
from tests.raid_rooms.admissions.test_reapplication_history import reapplication_ready
from tests.raid_rooms.admissions.test_reapplication_history import beta, current, candidate, ready
from tests.raid_rooms.admissions.test_reapplication_history import sources, imported, people, worlds
from tests.raid_rooms.admissions.test_reapplication_history import setup_reentry
from tests.raid_rooms.admissions.test_reapplication_history import context, admission_request, commands, actor
from tests.raid_rooms.common.test_raid_room_migrations import table_digests


ARTIFACTS = Path('docs/features/recruitment/completion-and-records/examples')


def row_for(db, rid, key):
    return db.scalar(select(RoomCycle).where(RoomCycle.room_id == rid,
        RoomCycle.cycle_key == date.fromisoformat(key)))


def values(obj):
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}


def clone_completed(db, source, *, round_id=None, character_id=None):
    stamp = now(db)
    body = values(source)
    body.update(id=uuid.uuid4(), state='completed', ended_at=stamp,
                build={'completion_source': 'manual', 'completed_at': stamp.isoformat()})
    if round_id is not None:
        body['round_id'] = round_id
    if character_id is not None:
        body['character_id'] = character_id
    completed = Assignment(**body)
    db.add(completed)
    db.flush()
    link = values(db.get(CycleAssignment, source.id))
    link.update(assignment_id=completed.id, round_id=completed.round_id)
    db.add(CycleAssignment(**link))
    db.flush()
    return completed


def test_reentry_large_history_stream_scope_digest_and_no_writes(reapplication_ready):
    engine,a,b,alt,rid,c,n,old_cm,old=setup_reentry(reapplication_ready,'direct_join')
    with beta_profile.using():
        ctx=context(alt,rid,c)
        assert commands.admit(actor(a['uid']),rid,uuid.uuid4(),admission_request(ctx))[0]==200
    with session() as db,db.begin():
        row=row_for(db,rid,c)
        source=db.get(Assignment,uuid.UUID(next(x for x in old['assignments'] if x['state']=='completed')['assignment_id']))
        # Historical non-current rounds and multiple character identities do not
        # consume any current slot or become a qualification input.
        old_round=values(db.get(Round,source.round_id))
        old_round.update(id=uuid.uuid4(),state='completed',ended_at=now(db))
        db.add(Round(**old_round));db.flush()
        round_link=values(db.get(CycleRound,source.round_id))
        round_link.update(round_id=old_round['id'],is_current=False)
        db.add(CycleRound(**round_link));db.flush()
        for i in range(257):
            clone_completed(db,source,round_id=old_round['id'] if i%2 else None,
                            character_id=uuid.UUID(a['ids'][i%2]))
        other=next(x for x in snapshot.active_assignments(db,row) if x.user_id==b['uid'])
        clone_completed(db,other)
        next_row=row_for(db,rid,n)
        next_source=snapshot.active_assignments(db,next_row,user_id=a['uid'])[0]
        clone_completed(db,next_source)
    tables=set(inspect(engine).get_table_names())
    before=table_digests(engine,tables)
    with session() as db:
        row=row_for(db,rid,c)
        personal=snapshot.preserved_completed(db,row,user_id=a['uid'])
        party=snapshot.preserved_completed(db,row)
        assert personal['assignment_count']==258
        assert party['assignment_count']==259
        assert sum(x['assignment_count'] for x in party['raids'])==259
        active=snapshot.active_assignments(db,row,user_id=a['uid'])
        assert len(active)==1 and {x.character_id for x in active}=={uuid.UUID(alt['ids'][0])}
        assert len(snapshot.active_assignments(db,row))==2
        # Independently assemble the documented evidence, including ended member
        # identities. Digest must match the existing project canonical encoder.
        proof=[]
        for assn,link in db.execute(select(Assignment,CycleAssignment).join(CycleAssignment,
            CycleAssignment.assignment_id==Assignment.id).where(CycleAssignment.cycle_id==row.id,
            CycleAssignment.generation==row.generation,CycleAssignment.user_id==a['uid'],
            Assignment.state=='completed').order_by(Assignment.id)):
            rd=db.get(Round,assn.round_id);item=db.get(Item,assn.item_id)
            proof.append(dict(assignment=values(assn),binding=values(link),raid_id=item.raid_id,
                round={k:getattr(rd,k) for k in ('id','item_id','cycle_key','difficulty_id','catalog_version')}))
        assert personal['digest']==digest(proof)
        for group in personal['raids']:
            assert group['digest']==digest([p for p in proof if p['raid_id']==group['raid_id']])
        assert len(json.dumps(personal))<2048
        assert snapshot.preserved_completed(db,row,user_id=uuid.uuid4())==dict(
            assignment_count=0,digest=digest([]),raids=[])
    assert table_digests(engine,tables)==before


def test_new_completion_exclusion_and_rejected_live_corruption(reapplication_ready):
    engine,a,b,alt,rid,c,n,old_cm,old=setup_reentry(reapplication_ready,'direct_join')
    with beta_profile.using():
        commands.admit(actor(a['uid']),rid,uuid.uuid4(),admission_request(context(alt,rid,c)))
    with session() as db,db.begin():
        row=row_for(db,rid,c)
        before=snapshot.preserved_completed(db,row,user_id=a['uid'])
        source=snapshot.active_assignments(db,row,user_id=a['uid'])[0]
        created=clone_completed(db,source)
        assert snapshot.preserved_completed(db,row,user_id=a['uid'])['assignment_count']==before['assignment_count']+1
        assert snapshot.preserved_completed(db,row,user_id=a['uid'],exclude_assignment_ids=[created.id])==before
        created.revision+=1;db.flush()
        changed=snapshot.preserved_completed(db,row,user_id=a['uid'])
        assert changed['digest']!=before['digest']
        db.get(CycleRound,source.round_id).is_current=False;db.flush()
        with pytest.raises(GameError,match='ROOM_REVIEW_REQUIRED'):
            snapshot.active_assignments(db,row,user_id=a['uid'])
        # Synthetic corruption is local to this disposable transaction.
        db.rollback()


def test_unknown_historical_raid_label_does_not_hide_other_errors(monkeypatch):
    def missing(_):raise GameError('RAID_NOT_FOUND',404)
    monkeypatch.setattr(snapshot,'raid_by_id',missing)
    assert snapshot._raid_name('retained-raid')=='retained-raid'
    def broken(_):raise GameError('SERVICE_UNAVAILABLE',503)
    monkeypatch.setattr(snapshot,'raid_by_id',broken)
    with pytest.raises(GameError,match='SERVICE_UNAVAILABLE'):snapshot._raid_name('retained-raid')


def test_v3_examples_and_consumer_delta():
    schema=json.loads((ARTIFACTS/'batch-completion-v3.schema.json').read_text())
    Draft202012Validator.check_schema(schema)
    cases=json.loads((ARTIFACTS/'batch-completion-v3.examples.json').read_text())['examples']
    byname={e['name']:e for e in cases}
    for e in cases:
        definition={**schema,'$ref':'#/$defs/'+e['schema']};definition.pop('oneOf')
        validator=Draft202012Validator(definition,format_checker=FormatChecker())
        validator.validate(e['response'])
        bad=copy.deepcopy(e['response']);bad['extra']=True
        assert not validator.is_valid(bad)
        if e['schema']=='Error':continue
        data=e['response']['data'];history=data['impact']['preserved_completed']
        assert history['assignment_count']==sum(r['assignment_count'] for r in history['raids'])
        assert 'preserved_completed_assignment_ids' not in data['impact']
        if e['schema'].endswith('Context'):
            display=data['display'];assert {x['round_id'] for x in display['rounds']}=={x['round_id'] for x in display['assignments']}
            assert {x['round_id'] for x in display['assignments'] if x['effect']=='complete'}==set(data['round_ids'])
            for key,effect in [('completed_assignment_ids','complete'),('cancelled_assignment_ids','cancel'),('preserved_active_assignment_ids','preserve_active')]:
                assert set(data['impact'][key])=={x['assignment_id'] for x in display['assignments'] if x['effect']==effect}
        else:
            context=byname[e['name'].removesuffix('_ack')+'_context']['response']['data']
            assert data['impact']==context['impact']
            assert data['state']==context['expected_after']['state']
    assert byname['party_partial_context']['response']['data']['impact']['preserved_completed']['assignment_count']>40
    assert byname['personal_leave_context']['response']['data']['impact']['preserved_completed']['assignment_count']>5
