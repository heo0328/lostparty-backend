"""Explicit schema boundary and provenance writes; no inferred legacy references."""
from sqlalchemy import text
from app.game_accounts.support import fail
from app.groups.feature_models import SubjectCharacterReference

HEAD = '0034_group_features'


def enabled(db):
    return list(db.scalars(text('SELECT version_num FROM public.alembic_version'))) == [HEAD]


def ready(db):
    if not enabled(db):
        fail('GROUP_FEATURE_NOT_READY', 503)


def remember(db, subject, character, account):
    if not enabled(db):
        return
    reference = db.get(SubjectCharacterReference, subject.id)
    if reference is None:
        reference = SubjectCharacterReference(subject_id=subject.id, group_id=subject.group_id, user_id=subject.user_id)
        db.add(reference)
    reference.character_id = character.id
    reference.ownership_revision = account.ownership_revision
    reference.lifecycle_revision = character.lifecycle_revision


def group_state(db, gid):
    """Public retained link metadata; never grants access to a linked group."""
    from app.groups.models import Group
    if gid is None:
        return None
    row = db.get(Group, gid)
    return dict(group_id=gid, name=row.name if row else None,
        state='unavailable' if row is None else 'ended' if row.ended_at is not None else 'active')
