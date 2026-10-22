"""Private snapshot/restore audit helper. Raw rows and keys are never printed.

The coordinator captures this helper's private protocol rather than forwarding
it to logs. It runs against the source with READ ONLY and an exported snapshot,
or against explicitly disposable restore databases. No migration is run here.
"""
import hashlib
from collections import Counter
from datetime import timedelta
import json
import os
from pathlib import Path
import sys
import tarfile
from sqlalchemy import inspect,text,select
from app.core.database import session


def fingerprint(db):
    schema=inspect(db.connection());result={}
    for name in sorted(schema.get_table_names(schema='public')):
        quoted=db.bind.dialect.identifier_preparer.quote(name)
        hashes=sorted(hashlib.sha256(row.encode()).digest() for row in db.scalars(text(
            f'SELECT row_to_json(t)::text FROM public.{quoted} AS t')))
        columns=[dict(name=c['name'],type=str(c['type']),nullable=c['nullable'],default=c.get('default'))
            for c in schema.get_columns(name,schema='public')]
        result[name]=dict(rows=len(hashes),sha256=hashlib.sha256(b''.join(hashes)).hexdigest(),columns=columns)
    return result


def sequences(db):
    schema=inspect(db.connection());result={}
    for name in sorted(schema.get_sequence_names(schema='public')):
        quoted=db.bind.dialect.identifier_preparer.quote(name)
        row=db.execute(text(f'SELECT last_value,is_called FROM public.{quoted}')).one()
        result[name]=dict(last_value=row[0],is_called=row[1])
    return result


def database_profile(db):
    return dict(db.execute(text("SELECT pg_encoding_to_char(encoding) AS encoding,datcollate AS collation,datctype AS ctype FROM pg_database WHERE datname=current_database()")).mappings().one())


def key_manifest():
    root=Path(os.environ.get('AUTH_SECRET_DIR','/run/secrets'))
    result={}
    for p in sorted(root.rglob('*')):
        if p.is_symlink():raise RuntimeError('Symlinks are not supported in key backup')
        if p.is_file():result[p.relative_to(root).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
    if not {'jwt.pem','recovery.key'}<=set(result):raise RuntimeError('Required keys missing')
    return result


def aggregate(db):
    result={}
    for name,column in [('recruitment_rooms','migration_state'),('recruitment_assignments','state'),
            ('recruitment_memberships','ended_at'),('recruitment_rounds','state')]:
        expression="CASE WHEN ended_at IS NULL THEN 'active' ELSE 'ended' END" if column=='ended_at' else column
        result[name]=dict(db.execute(text(f'SELECT {expression}, count(*) FROM {name} GROUP BY 1')).all())
    return result


def extract_keys(archive):
    root=Path(os.environ.get('AUTH_SECRET_DIR','/run/secrets'));root.mkdir(mode=0o700,parents=True,exist_ok=True)
    with tarfile.open(archive,'r:') as source:
        for member in source:
            path=Path(member.name)
            if member.issym() or member.islnk() or not member.isfile() or path.is_absolute() or '..' in path.parts:
                raise RuntimeError('Unsafe key archive member')
            target=root/path;target.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
            with target.open('xb') as out:out.write(source.extractfile(member).read())
            target.chmod(0o600)



def projections(db,legacy=False):
    base=dict(category='all',admission_scope=None,group_ids=[],filter_context_token=None,
        member_conditions=[],raid_ids=[],difficulty_ids=[],limit=50,cursor=None)
    from app.raid_rooms.search_router import Search
    if legacy:
        from app.raid_rooms import search
        return dict(public_v1_items=len(search.search(None,Search.model_validate(base))['items']))
    from app.core.database import now
    from app.raids import service as raids
    from app.raid_rooms import cycle_queries,cycle_wire,cycle_lists,cycle_member_reads,cycle_common
    current=raids.cycle(now(db)).cycle_key
    from datetime import date
    n=(date.fromisoformat(current)+timedelta(days=7)).isoformat()
    public={}
    for label,key in [('C',current),('N',n)]:
        page=cycle_queries.search(None,cycle_wire.InputContract3PostV2RaidRoomsSearch.model_validate(base|dict(target_cycle_key=key)))
        public[label]=len(page['data']['items'])
    from app.auth.models import User,Session
    from app.auth.service import active
    from app.core.errors import AuthError
    from app.raid_rooms.integrated_models import RecruitmentMembership as Member
    principals={}
    for user,auth in db.execute(select(User,Session).join(Session,Session.user_id==User.id)):
        try:active(user,auth,now(db))
        except AuthError:continue
        principals.setdefault(user.id,(user,auth))
    counts=Counter();states=Counter();plans=Counter();leave=Counter()
    for uid,principal in principals.items():
        for label,key in [('C',current),('N',n)]:
            page=cycle_lists.memberships(principal,key,limit=50)['data']['items']
            counts[label]+=len(page)
            for item in page:states[item['target_participation_state']]+=1
        for mid,rid in db.execute(select(Member.id,Member.room_id).where(Member.user_id==uid,Member.ended_at.is_(None))):
            try:cycle_member_reads.plan(principal,rid,current);plans['available']+=1
            except AuthError as error:plans[error.code]+=1
            try:
                ctx=cycle_common.get(principal,rid,'leave')['data']
                leave['allowed' if ctx['permission']['allowed'] else ctx['permission']['reason']]+=1
                if not ctx['impact_cycles']:leave['zero_impact_contexts']+=1
            except AuthError as error:leave[error.code]+=1
    phases=dict(db.execute(text("""SELECT CASE WHEN cycle_key=CAST(:c AS date) THEN 'C'
        WHEN cycle_key=CAST(:n AS date) THEN 'N' ELSE 'outside_C_N' END,count(*)
        FROM recruitment_room_cycles GROUP BY 1"""),dict(c=current,n=n)).all())
    return dict(public_items=public,eligible_session_users=len(principals),membership_items=dict(counts),
        membership_states=dict(states),current_plan_results=dict(plans),leave_context_results=dict(leave),cycle_phase_counts=phases,
        scope='read-only service projections using existing valid sessions; no JWT/command/provider/device test')


def main():
    mode=sys.argv[1]
    if mode=='keys':
        root=Path(os.environ.get('AUTH_SECRET_DIR','/run/secrets'))
        key_manifest()
        with tarfile.open(fileobj=sys.stdout.buffer,mode='w|') as archive:
            for p in sorted(root.rglob('*')):
                if p.is_file():archive.add(p,arcname=p.relative_to(root).as_posix(),recursive=False)
        return
    if mode=='extract':extract_keys(sys.argv[2]);return
    with session() as db,db.begin():
        db.connection(execution_options={'isolation_level':'REPEATABLE READ'});db.execute(text('SET TRANSACTION READ ONLY'))
        if mode=='snapshot':
            snapshot=db.scalar(text('SELECT pg_export_snapshot()'))
            result=dict(snapshot=snapshot,revision=list(db.scalars(text('SELECT version_num FROM alembic_version'))),
                tables=fingerprint(db),sequences=sequences(db),database_profile=database_profile(db),keys=key_manifest(),aggregate=aggregate(db))
            print(json.dumps(result),flush=True)
            if sys.stdin.readline().strip()!='complete':raise RuntimeError('Snapshot coordinator interrupted')
            if key_manifest()!=result['keys']:raise RuntimeError('Keys changed during backup')
        elif mode=='status':
            print(json.dumps(dict(revision=list(db.scalars(text('SELECT version_num FROM alembic_version'))),keys=key_manifest())))
        elif mode=='audit':
            print(json.dumps(dict(revision=list(db.scalars(text('SELECT version_num FROM alembic_version'))),
                tables=fingerprint(db),sequences=sequences(db),database_profile=database_profile(db),keys=key_manifest(),aggregate=aggregate(db))))
        elif mode=='prepared':
            from app.raid_rooms import readiness,cycle_worker
            readiness.require_two_cycle_active(db)
            from app.main import create_two_cycle_app
            assert len(create_two_cycle_app().openapi()['paths'])==167
            result=dict(revision=list(db.scalars(text('SELECT version_num FROM alembic_version'))),
                restricted_login=bool(db.scalar(text('SELECT current_user=session_user AND NOT rolsuper AND NOT rolcreatedb AND NOT rolcreaterole FROM pg_roles WHERE rolname=current_user'))),
                database_owner=bool(db.scalar(text('SELECT pg_get_userbyid(datdba)=current_user FROM pg_database WHERE datname=current_database()'))),
                cycles=dict(db.execute(text('SELECT state, count(*) FROM recruitment_room_cycles GROUP BY state')).all()),
                provenance=dict(db.execute(text('SELECT provenance, count(*) FROM recruitment_room_cycles GROUP BY provenance')).all()),
                unknown_generations=db.scalar(text('SELECT count(*) FROM recruitment_room_cycles WHERE generation IS NULL')),
                members=dict(db.execute(text('SELECT state, count(*) FROM recruitment_cycle_members GROUP BY state')).all()),
                evidence=dict(db.execute(text('SELECT source_kind, count(*) FROM recruitment_legacy_cycle_evidence GROUP BY source_kind')).all()),
                explicit_cycles=db.scalar(text("SELECT count(*) FROM recruitment_room_cycles WHERE provenance='explicit'")),
                executable_members=db.scalar(text("SELECT count(*) FROM recruitment_cycle_members WHERE state='participating'")),
                new_consents=db.scalar(text('SELECT count(*) FROM recruitment_cycle_consents')))
            print(json.dumps(result))
        elif mode in ('projections','old_projections'):
            print(json.dumps(projections(db,legacy=mode=='old_projections')))
        elif mode=='worker':
            from app.raid_rooms.cycle_worker import process_due
            process_due();print(json.dumps(dict(processed=True)))
        elif mode=='legacy':
            from app.raid_rooms import readiness
            from app.main import app,health
            readiness.require_active(db)
            assert health()=={'status':'ok','database':'ok'}
            print(json.dumps(dict(paths=len(app.openapi()['paths']),revision=list(db.scalars(text('SELECT version_num FROM alembic_version'))))))
        else:raise RuntimeError('Unknown helper mode')


if __name__=='__main__':main()
