"""Current group-scoped bulk projections. No provider calls or read-side writes."""
from contextlib import contextmanager
from decimal import Decimal
import json
from sqlalchemy import select, text
from fastapi.encoders import jsonable_encoder
from pydantic import ValidationError
from app.auth.models import User
from app.core.database import session, now
from app.game_accounts import lifecycle
from app.game_accounts.models import Account, Registration, Configuration, Activity, Character, NameClaim, CharacterRoleSummary
from app.game_accounts.power_success import RolePowerSuccess
from app.game_accounts.profile_schemas import RoleSummary
from app.game_accounts.support import authorize, fail, cursor_encode, cursor_decode
from app.groups import features, service as groups, http_service, admissions, admission_core
from app.groups.models import Group, GroupMembership
from app.groups.admission_models import GroupJoinSubject, GroupJoinRelation
from app.groups.feature_models import GroupActivityHead, SubjectCharacterReference
from app.raid_rooms.application_display import _level

PROFILE = 'group-display-1'
MAX_RESPONSE_BYTES = 1024 * 1024


@contextmanager
def snapshot(principal):
    with session() as db, db.begin():
        db.connection(execution_options={'isolation_level': 'REPEATABLE READ'})
        db.execute(text('SET TRANSACTION READ ONLY'))
        uid = authorize(db, principal)
        features.ready(db)
        yield db, uid, now(db)


def bounded(value):
    if len(json.dumps(jsonable_encoder(value), ensure_ascii=False).encode()) > MAX_RESPONSE_BYTES:
        fail('SERVICE_UNAVAILABLE', 503)
    return value


def paginate(principal, path, rows, evidence, limit, cursor, **scope):
    revision = lifecycle.digest(jsonable_encoder([evidence, rows]))
    binding = dict(path=path, actor=str(principal[0].id), session=str(principal[1].id),
                   profile=PROFILE, limit=limit, **scope)
    offset = cursor_decode(cursor, binding, revision) if cursor else 0
    if offset > len(rows):
        fail('INVALID_REQUEST', 400)
    following = offset + limit
    return rows[offset:following], (cursor_encode(dict(scope=binding, revision=revision, offset=following))
        if following < len(rows) else None), revision


def empty_role():
    return dict(combat_power=None, source='unavailable', trust=None, observed_at=None,
                saved_at=None, power_revision=None, analysis=None, reason='ROLE_ANALYSIS_UNAVAILABLE')


def absent(reason):
    return dict(character_id=None, state='unavailable', reason=reason, item_level=None,
        item_level_source='unavailable', summary_fetched_at=None, dealer=empty_role(), support=empty_role())


def load(db, users):
    """Load eligible characters and role facts once, across all requested members."""
    rows = list(db.execute(select(Registration, Account, Configuration, Character, NameClaim.revision)
        .join(Account, Account.id == Registration.account_id)
        .join(User, User.id == Registration.user_id)
        .join(Configuration, (Configuration.account_id == Account.id) & (Configuration.user_id == Registration.user_id))
        .join(Activity, Activity.settings_id == Configuration.id)
        .join(Character, (Character.id == Activity.character_id) & (Character.account_id == Account.id))
        .join(NameClaim, (NameClaim.server_name == Character.server_name) &
            (NameClaim.character_name == Character.character_name) & (NameClaim.character_id == Character.id))
        .where(Registration.user_id.in_(users), User.status == 'active', Registration.deleted_at.is_(None),
            Account.owner_id == Registration.user_id, Account.verified_at.is_not(None),
            Configuration.ended_at.is_(None), Character.status == 'confirmed', Character.lifecycle_state == 'active')))
    specs = character_specs(db, [(reg.user_id, account, char) for reg, account, _, char, _ in rows])
    found, evidence = {}, []
    for reg, account, config, char, claim_revision in rows:
        found[(reg.user_id, char.id)] = (char, account, specs[(reg.user_id, char.id)])
        evidence.append([reg.id, reg.version, account.id, account.ownership_revision, account.roster_revision,
            config.id, config.version, char.id, char.lifecycle_revision, claim_revision])
    evidence.sort(key=lambda v: str(v))
    return found, evidence


def character_specs(db, characters):
    """Bulk stored facts for caller-authorized characters; no activity/access gate here."""
    ids = {char.id for _, _, char in characters}
    users = {uid for uid, _, _ in characters}
    heads = {(v.user_id, v.character_id, v.ownership_revision, v.role): v for v in db.scalars(
        select(CharacterRoleSummary).where(CharacterRoleSummary.user_id.in_(users), CharacterRoleSummary.character_id.in_(ids)))} if ids else {}
    successes = {(v.user_id, v.character_id, v.ownership_revision, v.role): v for v in db.scalars(
        select(RolePowerSuccess).where(RolePowerSuccess.user_id.in_(users), RolePowerSuccess.character_id.in_(ids)))} if ids else {}
    found = {}
    for uid, account, char in characters:
        roles = {}
        for role in ('dealer', 'support'):
            out = empty_role()
            key = (uid, char.id, account.ownership_revision, role)
            head, success = heads.get(key), successes.get(key)
            if head is not None:
                try:
                    summary = RoleSummary.model_validate(head.summary)
                    if summary.observed_lifecycle_revision == char.lifecycle_revision:
                        out['analysis'] = dict(version=head.version, saved_at=head.saved_at, analyzed_at=summary.analyzed_at,
                            integrity_status=summary.integrity_status, issues=summary.model_dump(mode='json')['issues'])
                        out['reason'] = None
                except (ValidationError, TypeError, ValueError):
                    out['reason'] = 'ROLE_ANALYSIS_INVALID'
            if success is not None:
                try:
                    saved = RoleSummary.model_validate(success.source_summary)
                    if saved.observed_lifecycle_revision == char.lifecycle_revision and _level(success.combat_power) is not None:
                        out.update(combat_power=success.combat_power, source='stored_role_success', trust='client_submitted',
                            observed_at=success.observed_at, saved_at=success.source_saved_at, power_revision=success.power_revision)
                except (ValidationError, TypeError, ValueError):
                    out['reason'] = 'ROLE_ANALYSIS_INVALID'
            roles[role] = out
        level = _level(char.summary.get('item_level'))
        has_power = any(v['combat_power'] is not None for v in roles.values())
        has_analysis = any(v['analysis'] is not None for v in roles.values())
        state = 'available' if level is not None and has_power else 'partial' if level is not None or has_power or has_analysis else 'unavailable'
        reason = None if state == 'available' else 'CHARACTER_DATA_UNAVAILABLE' if level is None else 'ROLE_ANALYSIS_UNAVAILABLE'
        spec = dict(character_id=char.id, state=state, reason=reason, item_level=level,
            item_level_source='stored_character_summary' if level is not None else 'unavailable',
            summary_fetched_at=char.fetched_at, **roles)
        found[(uid, char.id)] = spec
    return found


def member_rows(db, gid):
    return list(db.scalars(select(GroupMembership).where(GroupMembership.group_id == gid,
        GroupMembership.ended_at.is_(None)).order_by(GroupMembership.joined_at, GroupMembership.id)))


def members(principal, gid, limit, cursor):
    with snapshot(principal) as (db, uid, stamp):
        group = groups.group(db, gid); own = groups.member(db, uid, group)
        members = member_rows(db, gid)
        loaded, evidence = load(db, {m.user_id for m in members})
        rows = [dict(membership_id=m.id, role='leader' if m.id == group.leader_membership_id else 'member',
            revision=m.revision, display=groups.display(m.display), joined_at=m.joined_at, is_me=m.user_id == uid,
            character_spec=loaded[(m.user_id, m.character_id)][2] if (m.user_id, m.character_id) in loaded else
                absent('CHARACTER_NOT_CURRENTLY_ELIGIBLE' if m.character_id else 'CHARACTER_REFERENCE_UNAVAILABLE')) for m in members]
        items, following, revision = paginate(principal, 'group-members', rows,
            [group.revision, group.members_revision, own.id, own.revision, evidence], limit, cursor, group_id=str(gid))
        return bounded(dict(profile=PROFILE, evaluated_at=stamp, snapshot_revision=revision,
            group_id=gid, group_revision=group.revision, members_revision=group.members_revision, items=items, next_cursor=following))


def activity(principal, gid, mid, limit, cursor):
    with snapshot(principal) as (db, uid, stamp):
        group = groups.group(db, gid); own = groups.member(db, uid, group)
        target = db.get(GroupMembership, mid)
        if target is None or target.group_id != gid or target.ended_at is not None:
            fail('GROUP_TARGET_UNAVAILABLE', 404)
        loaded, evidence = load(db, {target.user_id})
        rows = [dict(character_id=c.id, display=admission_core.display(c), character_spec=spec) for c, _, spec in loaded.values()]
        rows.sort(key=lambda r: (r['character_spec']['item_level'] is None,
            -Decimal(r['character_spec']['item_level'] or '0'), str(r['character_id'])))
        items, following, revision = paginate(principal, 'group-activity', rows,
            [group.revision, group.members_revision, own.id, own.revision, target.id, target.revision, evidence],
            limit, cursor, group_id=str(gid), membership_id=str(mid))
        return bounded(dict(group_id=gid, membership_id=mid, group_revision=group.revision,
            members_revision=group.members_revision, evaluated_at=stamp, snapshot_revision=revision, items=items, next_cursor=following))


def blocked(principal, gid, limit, cursor):
    with snapshot(principal) as (db, uid, stamp):
        group = groups.group(db, gid); own = admission_core.leader(db, uid, group)
        subjects = list(db.scalars(select(GroupJoinSubject).where(GroupJoinSubject.group_id == gid,
            GroupJoinSubject.blocked_at.is_not(None)).order_by(GroupJoinSubject.created_at.desc(), GroupJoinSubject.id.desc())))
        references = {r.subject_id: r for r in db.scalars(select(SubjectCharacterReference).where(SubjectCharacterReference.group_id == gid))}
        loaded, evidence = load(db, {s.user_id for s in subjects})
        rows = []
        for subject in subjects:
            ref = references.get(subject.id)
            entry = loaded.get((subject.user_id, ref.character_id)) if ref else None
            valid = entry is not None and (entry[1].ownership_revision, entry[0].lifecycle_revision) == (ref.ownership_revision, ref.lifecycle_revision)
            rows.append({**admissions.subject_output(subject), 'character_spec': entry[2] if valid else
                absent('CHARACTER_NOT_CURRENTLY_ELIGIBLE' if ref else 'CHARACTER_REFERENCE_UNAVAILABLE')})
        items, following, revision = paginate(principal, 'group-blocked', rows,
            [group.revision, group.members_revision, own.id, own.revision, evidence], limit, cursor, group_id=str(gid))
        return bounded(dict(profile=PROFILE, evaluated_at=stamp, snapshot_revision=revision, items=items, next_cursor=following))


def detail(db, group, own, stamp):
    head = db.get(GroupActivityHead, group.id)
    value = http_service.detail(db, group, own)
    value.update(last_activity_at=head.last_activity_at if head else None)
    revision = lifecycle.digest(jsonable_encoder(value))
    return dict(value, profile=PROFILE, evaluated_at=stamp, snapshot_revision=revision)


def my_groups(principal, limit=None, cursor=None, gid=None):
    with snapshot(principal) as (db, uid, stamp):
        if gid is not None:
            group = groups.group(db, gid)
            return detail(db, group, groups.member(db, uid, group), stamp)
        values = list(db.scalars(select(Group).join(GroupMembership, GroupMembership.group_id == Group.id).where(
            Group.ended_at.is_(None), GroupMembership.user_id == uid, GroupMembership.ended_at.is_(None))
            .order_by(Group.created_at.desc(), Group.id.desc())))
        rows = [detail(db, g, groups.member(db, uid, g), stamp) for g in values]
        # Evaluation time is not a mutable cursor fact.
        stable = [{k: v for k, v in r.items() if k != 'evaluated_at'} for r in rows]
        items, following, revision = paginate(principal, 'my-groups', stable, [], limit, cursor)
        for item in items: item['evaluated_at'] = stamp
        return bounded(dict(profile=PROFILE, evaluated_at=stamp, snapshot_revision=revision,
            directory_revision=http_service.directory_revision(db), items=items, next_cursor=following))


def counts(principal, gid=None):
    with snapshot(principal) as (db, uid, stamp):
        if gid is not None:
            group = groups.group(db, gid); admission_core.leader(db, uid, group)
            led = [gid]
        else:
            led = list(db.scalars(select(Group.id).join(GroupMembership, GroupMembership.id == Group.leader_membership_id)
                .where(Group.ended_at.is_(None), GroupMembership.user_id == uid, GroupMembership.ended_at.is_(None)).order_by(Group.id)))
        rows = list(db.scalars(select(GroupJoinRelation).join(Group, Group.id == GroupJoinRelation.group_id)
            .where(Group.ended_at.is_(None), GroupJoinRelation.state == 'pending',
                ((GroupJoinRelation.group_id.in_(led)) | (GroupJoinRelation.target_user_id == uid))).order_by(GroupJoinRelation.id)))
        rows = [r for r in rows if (gid is None or r.group_id == gid) and admission_core.relation_state(db, r, stamp) == 'pending']
        received = {r.id for r in rows if r.kind == 'invitation' and r.target_user_id == uid}
        sent = {r.id for r in rows if r.kind == 'application' and r.target_user_id == uid}
        managed = {r.id for r in rows if r.kind == 'application' and r.group_id in led}
        invitations = {r.id for r in rows if r.kind == 'invitation' and r.group_id in led}
        revision = lifecycle.digest(jsonable_encoder([uid, led, [[r.id, r.revision, r.state] for r in rows]]))
        result = dict(evaluated_at=stamp, counts_revision=revision, valid_until=min((r.expires_at for r in rows), default=None))
        if gid is not None:
            return dict(result, group_id=gid, group_revision=group.revision, members_revision=group.members_revision,
                pending_applications=len(managed), pending_invitations=len(invitations), action_required=len(managed))
        return dict(result, received_invitations=len(received), sent_applications=len(sent),
            managed_applications=len(managed), managed_invitations=len(invitations), action_required=len(received | managed))
