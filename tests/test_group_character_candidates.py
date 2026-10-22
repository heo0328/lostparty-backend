"""Real restricted PostgreSQL/HTTP; synthetic group candidates only."""
import json
import uuid
from pathlib import Path
import pytest
from sqlalchemy import select, inspect, delete
from app.core.database import session, now
from app.auth.models import User, Session
from app.game_accounts.models import Character, Account, Activity, Registration, NameClaim, CharacterRoleSummary
from app.game_accounts.power_success import capture
from app.groups.models import Group, GroupMembership
from app.raid_rooms import character_candidates as service, cycle_schemas as inputs, cycle_queries
from app.raid_rooms.candidate_schemas import CandidatePage
from tests.test_recruitment_cycle_creation import candidate, ready, sources, imported, people, worlds, denied, preflight
from tests.test_group_foundation import actor, create
from tests.test_recruitment_cycle_times_http import client
from tests.test_recruitment_cycle_queries import search_request
from tests.test_raid_room_migrations import table_digests
from tests.test_role_summaries import summary


@pytest.fixture
def group_candidates(candidate):
    engine, a, b = candidate
    gid = uuid.UUID(create(a)[1]['group']['group_id'])
    with session() as db, db.begin():
        db.add(GroupMembership(id=uuid.uuid4(), group_id=gid, user_id=b['uid'],
            character_id=uuid.UUID(b['ids'][0]), display=None, revision=1, joined_at=now(db)))
        db.get(Group, gid).members_revision += 1
    return engine, a, b, gid


def context(a, gid):
    return cycle_queries.filters.get_context(actor(a['uid']), [gid])['filter_context_token']


def page(a, gid, **kwargs):
    return service.get(actor(a['uid']), gid, context(a, gid), **kwargs)


def search(a, gid, candidates, member, ids, **kwargs):
    key = preflight(a)['data']['target_cycle_key']
    body = search_request(key, group_ids=[gid], filter_context_token=candidates['filter_context_token'],
        member_conditions=[dict(member_ref=member['member_ref'], character_ids=ids)]).model_dump(mode='json', exclude_unset=True)
    return inputs.Search.model_validate(body | dict(group_character_candidates_token=candidates['candidate_token']) | kwargs)


def test_http_allowlist_page_fragments_and_readonly(group_candidates):
    engine, a, b, gid = group_candidates
    with session() as db, db.begin():
        for w in (a, b):
            for cid, level in zip(w['ids'], ('999.9', '1000.00', '2000')):
                c = db.get(Character, uuid.UUID(cid)); c.summary = c.summary | dict(item_level=level)
    before = table_digests(engine, set(inspect(engine).get_table_names()) - {'alembic_version'})
    pages = []; cursor = None
    with client(a) as http:
        while True:
            params = dict(filter_context_token=context(a, gid), limit=1)
            if cursor: params['cursor'] = cursor
            response = http.get(f'/v2/groups/{gid}/raid-room-character-candidates', params=params)
            assert response.status_code == 200, response.json().get('error')
            assert response.headers['cache-control'] == 'no-store'
            value = response.json(); CandidatePage.model_validate(value); pages.append(value)
            from jsonschema import Draft202012Validator
            from referencing import Registry, Resource
            from referencing.jsonschema import DRAFT202012
            contract=json.loads(Path('docs/design/issue13-group-character-candidates.draft.openapi.json').read_text())
            registry=Registry().with_resource('urn:candidates',Resource.from_contents(contract,default_specification=DRAFT202012))
            Draft202012Validator({'$ref':'urn:candidates#/components/schemas/CandidatePage'},registry=registry,
                format_checker=Draft202012Validator.FORMAT_CHECKER).validate(value)
            cursor = value['next_cursor']
            if not cursor: break
    assert len(pages) == 4 and len({p['candidate_token'] for p in pages}) == 1
    for first, last in ((pages[0], pages[1]), (pages[2], pages[3])):
        x, y = first['groups'][0], last['groups'][0]
        assert x['member_ref'] == y['member_ref']
        assert not x['continues_from_previous'] and x['continues_on_next']
        assert y['continues_from_previous'] and not y['continues_on_next']
        assert x['characters'][0]['item_level'] == '1000.00'
        assert y['characters'][0]['item_level'] == '999.9'
    raw = json.dumps(pages)
    assert not any(field in raw for field in ('user_id', 'account_id', 'registration_id', 'source_summary'))
    assert table_digests(engine, set(inspect(engine).get_table_names()) - {'alembic_version'}) == before


def test_offpage_selection_valid_even_when_no_matching_rooms(group_candidates):
    _, a, b, gid = group_candidates
    first = page(a, gid, limit=1); all_items = page(a, gid)
    member = all_items['groups'][-1]; cid = member['characters'][-1]['character_id']
    assert cid not in {c['character_id'] for g in first['groups'] for c in g['characters']}
    response = cycle_queries.search(actor(a['uid']), search(a, gid, first, member, [cid]))
    assert response['data']['items'] == []
    denied('INVALID_REQUEST', cycle_queries.search, actor(a['uid']), search(a, gid, first, member, [cid, str(uuid.uuid4())]))
    other = all_items['groups'][0]['characters'][0]['character_id']
    denied('INVALID_REQUEST', cycle_queries.search, actor(a['uid']), search(a, gid, first, member, [other]))


@pytest.mark.parametrize('change', ['activity', 'ownership', 'status', 'lifecycle', 'claim', 'registration', 'level'])
def test_candidate_change_invalidates_cursor_and_selection(group_candidates, change):
    _, a, b, gid = group_candidates
    old = page(a, gid, limit=1); member = page(a, gid)['groups'][0]
    cid = uuid.UUID(member['characters'][0]['character_id'])
    with session() as db, db.begin():
        char = db.get(Character, cid); account = db.get(Account, char.account_id)
        if change == 'activity': db.execute(delete(Activity).where(Activity.character_id == cid))
        elif change == 'ownership': account.owner_id = None; account.ownership_revision += 1
        elif change == 'status': char.status = 'suspect'
        elif change == 'lifecycle': char.lifecycle_state = 'retired'; char.lifecycle_revision += 1
        elif change == 'claim': db.delete(db.get(NameClaim, (char.server_name, char.character_name)))
        elif change == 'registration':
            row = db.scalar(select(Registration).where(Registration.account_id == account.id)); row.deleted_at = now(db)
        else: char.summary = char.summary | dict(item_level='1777.7')
    denied('CURSOR_STALE', service.get, actor(a['uid']), gid, old['filter_context_token'], 1, old['next_cursor'])
    # Build the original selection without fetching preflight after ownership changes.
    from app.raids.service import cycle
    with session() as db: key = cycle(now(db)).cycle_key
    body = search_request(key, group_ids=[gid], filter_context_token=old['filter_context_token'],
        member_conditions=[dict(member_ref=member['member_ref'], character_ids=[cid])]).model_dump(mode='json', exclude_unset=True)
    old_request = inputs.Search.model_validate(body | dict(group_character_candidates_token=old['candidate_token']))
    denied('GROUP_CHARACTER_CANDIDATES_STALE', cycle_queries.search, actor(a['uid']), old_request)
    fresh = page(a, gid)
    request = inputs.Search.model_validate(body | dict(group_character_candidates_token=fresh['candidate_token']))
    if change == 'level': assert cycle_queries.search(actor(a['uid']), request)['data']['items'] == []
    else: denied('INVALID_REQUEST', cycle_queries.search, actor(a['uid']), request)


def test_access_context_cursor_session_and_empty_marker(group_candidates):
    _, a, b, gid = group_candidates
    first = page(a, gid, limit=1)
    denied('INVALID_REQUEST', service.get, actor(b['uid']), gid, context(b, gid), 1, first['next_cursor'])
    denied('INVALID_REQUEST', service.get, actor(a['uid']), gid, context(a, gid), 2, first['next_cursor'])
    with session() as db, db.begin():
        db.execute(delete(Activity).where(Activity.settings_id == a['cid']))
    empty = page(a, gid)
    assert sum(not g['characters'] for g in empty['groups']) == 1
    with session() as db, db.begin():
        db.scalar(select(GroupMembership).where(GroupMembership.group_id == gid, GroupMembership.user_id == b['uid'])).ended_at = now(db)
        db.get(Group, gid).members_revision += 1
    denied('FILTER_CONTEXT_STALE', service.get, actor(a['uid']), gid, first['filter_context_token'])
    denied('GROUP_NOT_FOUND', service.get, actor(b['uid']), gid, first['filter_context_token'])


def test_power_success_provenance_and_lifecycle_boundary(group_candidates):
    _, a, b, gid = group_candidates
    cid = uuid.UUID(a['ids'][0])
    with session() as db, db.begin():
        head = CharacterRoleSummary(user_id=a['uid'], character_id=cid, ownership_revision=1,
            role='dealer', version=2, summary=summary(), saved_at=now(db))
        db.add(head); db.flush(); capture(db, head)
    value = next(c for g in page(a, gid)['groups'] for c in g['characters'] if c['character_id'] == str(cid))
    assert value['dealer']['value'] == '12345.00' and value['dealer']['trust'] == 'client_submitted'
    assert value['support']['source'] == 'unavailable' and value['support']['value'] is None
    with session() as db, db.begin():
        head = db.get(CharacterRoleSummary,(a['uid'],cid,1,'dealer'))
        head.version += 1
        head.summary = head.summary | dict(combat_power=None,combat_power_observed_at=None)
        capture(db,head)
    retained = next(c for g in page(a, gid)['groups'] for c in g['characters'] if c['character_id'] == str(cid))
    assert retained['dealer'] == value['dealer']
    with session() as db, db.begin(): db.get(Character, cid).lifecycle_revision += 1
    value = next(c for g in page(a, gid)['groups'] for c in g['characters'] if c['character_id'] == str(cid))
    assert value['dealer']['source'] == 'unavailable'


def test_different_session_and_disabled_member(group_candidates):
    _, a, b, gid = group_candidates
    original = actor(a['uid']); first = page(a,gid,limit=1)
    with session() as db, db.begin():
        old = db.get(Session,original[1].id)
        new = Session(user_id=a['uid'],remember_me=False,created_at=now(db),
            absolute_expires_at=old.absolute_expires_at,idle_expires_at=old.idle_expires_at)
        db.add(new);db.flush();new_id=new.id
    with session() as db: alternate = (db.get(User,a['uid']),db.get(Session,new_id))
    denied('INVALID_REQUEST',service.get,alternate,gid,context(a,gid),1,first['next_cursor'])
    assert service.get(alternate,gid,context(a,gid))['candidate_token']!=first['candidate_token']
    with session() as db, db.begin(): db.get(User,b['uid']).status='disabled'
    assert len(page(a,gid)['groups'])==1
    denied('CURSOR_STALE',service.get,original,gid,first['filter_context_token'],1,first['next_cursor'])


def test_strict_http_input_and_payload_limit(group_candidates, monkeypatch):
    _, a, _, gid = group_candidates
    p = dict(filter_context_token=context(a, gid))
    with client(a) as http:
        path = f'/v2/groups/{gid}/raid-room-character-candidates'
        for update in (dict(limit=0), dict(limit=101), dict(cursor=''), dict(extra='x'), dict(filter_context_token='x'*64)):
            assert http.get(path, params=p | update).status_code == 400
        assert http.get(path, params=list(p.items()) * 2).status_code == 400
        monkeypatch.setattr(service, 'MAX_RESPONSE_BYTES', 10)
        assert http.get(path, params=p).status_code == 413
        key = preflight(a)['data']['target_cycle_key']
        body = search_request(key).model_dump(mode='json', exclude_unset=True)
        for token in (None, '', 'x'*64, True):
            assert http.post('/v2/raid-rooms/search', json=body | dict(group_character_candidates_token=token)).status_code == 400


def test_actual_bearer_authentication_and_foreign_group(group_candidates, people):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.core.errors import register
    from app.main import no_store
    from app.raid_rooms.cycle_router import router
    _, a, b, gid = group_candidates
    outsider = people('candidate-outsider')
    app = FastAPI(); register(app); app.include_router(router); app.middleware('http')(no_store)
    path = f'/v2/groups/{gid}/raid-room-character-candidates'
    with TestClient(app) as http:
        params = dict(filter_context_token=context(a, gid))
        assert http.get(path, params=params).status_code == 401
        assert http.get(path, params=params, headers={'Authorization':'Bearer invalid'}).status_code == 401
        assert http.get(path, params=params, headers=a['headers']).status_code == 200
        assert http.get(path, params=params, headers=outsider['headers']).status_code == 404
        with session() as db,db.begin(): db.get(User,b['uid']).status='disabled'
        assert http.get(path,params=dict(filter_context_token=context(a,gid)),headers=b['headers']).status_code==403
        with session() as db,db.begin():
            db.scalar(select(Session).where(Session.user_id==a['uid'])).revoked_at=now(db)
        assert http.get(path,params=params,headers=a['headers']).status_code==401


def test_candidate_token_keeps_actual_target_sql_matching(group_candidates):
    from tests.test_recruitment_cycle_creation import request
    from tests.test_recruitment_cycle_commands import commands, context as admission_context, admission_request
    from app.raid_rooms import cycle_creation
    _,a,b,gid=group_candidates
    room=cycle_creation.create(actor(a['uid']),uuid.uuid4(),request(preflight(a,gid=gid,continuation=True),
        scope='group',group_id=str(gid)))[1]['data']
    rid=uuid.UUID(room['room_id']);c,n=[v['target_cycle_key'] for v in room['created_cycles']]
    commands.admit(actor(b['uid']),rid,uuid.uuid4(),admission_request(admission_context(b,rid,n)))
    candidates=page(a,gid)
    member=next(g for g in candidates['groups'] if str(b['ids'][0]) in {v['character_id'] for v in g['characters']})
    for key,count in ((c,0),(n,1)):
        body=search_request(key,group_ids=[gid],filter_context_token=candidates['filter_context_token'],
            member_conditions=[dict(member_ref=member['member_ref'],character_ids=[b['ids'][0]])]).model_dump(mode='json',exclude_unset=True)
        body['group_character_candidates_token']=candidates['candidate_token']
        response=cycle_queries.search(actor(a['uid']),inputs.Search.model_validate(body))
        assert len(response['data']['items'])==count


@pytest.mark.parametrize('extra',[198,4998])
def test_batch_queries_large_group_roster_and_stable_null_sort(group_candidates, extra):
    from time import perf_counter
    from tests.test_recruitment_cycle_performance import measured
    engine, a, b, gid = group_candidates
    with session() as db, db.begin():
        stamp = now(db)
        for w in (a, b):
            additions=[]
            for i in range(extra):
                c = Character(account_id=w['aid'],server_name='synthetic-large',character_name=f'{w["rid"][:8]}-{i}',
                    summary=dict(class_name=None,item_level='1800.0001' if i%2 else 'bad-value'),fetched_at=stamp,confirmed_at=stamp)
                additions.append(c)
            db.add_all(additions);db.flush()
            for c in additions:
                db.add(NameClaim(server_name=c.server_name,character_name=c.character_name,character_id=c.id))
                db.add(Activity(settings_id=w['cid'],account_id=w['aid'],character_id=c.id))
    principal = actor(a['uid']); token = context(a, gid)
    with measured(engine) as counts:
        start=perf_counter()
        first = service.get(principal,gid,token,100)
        elapsed=1000*(perf_counter()-start)
    assert counts['statements'] <= 10
    assert sum(len(g['characters']) for g in first['groups']) == 100
    assert len(json.dumps(first).encode()) < service.MAX_RESPONSE_BYTES
    report=dict(candidate_count=2*(extra+2),page_limit=100,select_statements=counts['statements'],
        selected_sql_rows=counts['rows'],response_bytes=len(json.dumps(first,ensure_ascii=False,separators=(',',':')).encode()),
        first_page_ms=round(elapsed,3),environment='synthetic isolated restricted PostgreSQL; single sample, not SLO')
    Path(f'/tmp/candidate-perf-{extra}.json').write_text(json.dumps(report))
    if extra>198:
        assert first['next_cursor']
        return
    gathered = []; cursor = None; snapshot_token = first['candidate_token']
    while True:
        result = service.get(principal,gid,token,100,cursor)
        assert result['candidate_token'] == snapshot_token
        gathered.extend((g['member_ref'],c) for g in result['groups'] for c in g['characters'])
        cursor = result['next_cursor']
        if not cursor: break
    assert len(gathered)==400 and len({c['character_id'] for _,c in gathered})==400
    for ref in {ref for ref,_ in gathered}:
        chars=[c for r,c in gathered if r==ref]
        assert chars[0]['item_level']=='1800.0001' and chars[-1]['item_level'] is None
        nulls=[c['character_id'] for c in chars if c['item_level'] is None]
        assert nulls==sorted(nulls)
