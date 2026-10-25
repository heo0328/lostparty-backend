"""Read-only minimum schema/privilege checks prepared for the F3 startup boundary.

This is not a migration runner or a substitute for migration regression tests.
No production lifespan calls this module before activation is agreed.
"""
import re
from sqlalchemy import inspect, text, UniqueConstraint, CheckConstraint
from app.game_accounts.support import fail
from app.raid_rooms.models import Room, Round, Membership, Application, DirectoryHead, MemberHead

REVISION = '0018_room_application_build'
# Known additive source revisions; legacy F2 schema/semantics stay intact.
SUPPORTED_REVISIONS = (REVISION, '0019_integrated_recruitment', '0020_recruitment_sources', '0021_recruitment_weekly_links','0022_recruitment_schedule_heads','0023_recruitment_resume','0024_recruitment_cycles','0025_cycle_admissions','0026_cycle_lifecycle','0027_cycle_consents','0028_cycle_planning','0029_cycle_outcomes','0030_completion_corrections','0031_membership_actions','0032_beta_recruitment')
MODELS = (Room, Round, Membership, Application, DirectoryHead, MemberHead)


def normalized(value):
    value = re.sub(r'::(?:text|character varying)', '', str(value).lower())
    return re.sub(r'[\s()"]', '', value)


def require(value):
    if not value:
        fail('SERVICE_UNAVAILABLE', 503)


def require_ready(db, *, integrated=False):
    """Inspect the caller's transaction and effective DB role, without any writes.

    SQL/privilege failures propagate to the existing 503 boundary. Unknown migration
    heads require explicit compatibility review instead of a guessed >= comparison.
    """
    schema = inspect(db.connection())
    require(schema.has_table('alembic_version', schema='public'))
    versions = list(db.scalars(text('SELECT version_num FROM public.alembic_version')))
    require(len(versions) == 1 and versions[0] in SUPPORTED_REVISIONS)
    models = MODELS
    if integrated:
        require(versions[0] in SUPPORTED_REVISIONS[1:])
        from app.raid_rooms.integrated_models import (
            RecruitmentRoom, RecruitmentItem, RecruitmentRound, RecruitmentMembership,
            RecruitmentAssignment, RecruitmentSession, RecruitmentSegment,
        )
        models += (RecruitmentRoom, RecruitmentItem, RecruitmentRound, RecruitmentMembership,
                   RecruitmentAssignment, RecruitmentSession, RecruitmentSegment)
        if versions[0] in SUPPORTED_REVISIONS[2:]:
            from app.raid_rooms.source_models import SOURCE_MODELS
            from app.game_accounts.power_success import RolePowerSuccess
            models += SOURCE_MODELS + (RolePowerSuccess,)
        if versions[0] in SUPPORTED_REVISIONS[3:]:
            from app.raid_rooms.weekly_links import WeeklyOccupancy
            models += (WeeklyOccupancy,)
        if versions[0] in SUPPORTED_REVISIONS[4:]:
            from app.raid_rooms.schedule_heads import ScheduleHead
            models += (ScheduleHead,)
        if versions[0] in SUPPORTED_REVISIONS[5:]:
            from app.raid_rooms.resume_models import ResumeProposal
            models += (ResumeProposal,)
        if versions[0] in SUPPORTED_REVISIONS[6:]:
            from app.raid_rooms.cycle_models import CYCLE_MODELS
            models += CYCLE_MODELS
        if versions[0] in SUPPORTED_REVISIONS[7:]:
            from app.raid_rooms.cycle_application_models import CYCLE_ADMISSION_MODELS
            models += CYCLE_ADMISSION_MODELS
        if versions[0] in SUPPORTED_REVISIONS[8:]:
            from app.raid_rooms.cycle_lifecycle_models import CYCLE_LIFECYCLE_MODELS
            models += CYCLE_LIFECYCLE_MODELS
        if versions[0] in SUPPORTED_REVISIONS[9:]:
            from app.raid_rooms.cycle_consent_models import CYCLE_CONSENT_MODELS
            models += CYCLE_CONSENT_MODELS
        if versions[0] in SUPPORTED_REVISIONS[10:]:
            from app.raid_rooms.cycle_planning_models import CYCLE_PLANNING_MODELS
            models += CYCLE_PLANNING_MODELS
    if integrated and versions[0] in ('0029_cycle_outcomes','0030_completion_corrections','0031_membership_actions','0032_beta_recruitment'):
        from app.raid_rooms.cycle_outcome_models import CYCLE_OUTCOME_MODELS
        models += CYCLE_OUTCOME_MODELS
    if integrated and versions[0] in ('0030_completion_corrections','0031_membership_actions','0032_beta_recruitment'):
        from app.raid_rooms.completion_correction_models import CompletionCorrection
        models += (CompletionCorrection,)
    if integrated and versions[0] in ('0031_membership_actions','0032_beta_recruitment'):
        from app.raid_rooms.membership_action_models import LeadershipRecovery, MembershipActionAudit
        models += (LeadershipRecovery, MembershipActionAudit)
    if integrated and versions[0]=='0032_beta_recruitment':
        from app.raid_rooms.beta_models import BETA_MODELS
        models += BETA_MODELS
        require(db.scalar(text("SELECT has_sequence_privilege(current_user, 'public.recruitment_beta_number_seq', 'USAGE')")))
    for model in models:
        table = model.__table__
        name = table.name
        require(schema.has_table(name, schema='public'))
        columns = {c['name']: c for c in schema.get_columns(name, schema='public')}
        for column in table.columns:
            actual = columns.get(column.name)
            require(actual is not None)
            require(actual['nullable'] == column.nullable)
            require(str(actual['type'].compile(dialect=db.bind.dialect)) ==
                    str(column.type.compile(dialect=db.bind.dialect)))
        require(schema.get_pk_constraint(name, schema='public')['constrained_columns'] ==
                [c.name for c in table.primary_key.columns])
        actual_fks = schema.get_foreign_keys(name, schema='public')
        for fk in table.foreign_key_constraints:
            target = [e.target_fullname.split('.') for e in fk.elements]
            matches = [v for v in actual_fks if v['constrained_columns'] == [c.name for c in fk.columns]
                       and v['referred_table'] == target[0][-2]
                       and v['referred_columns'] == [parts[-1] for parts in target]
                       and v['referred_schema'] in (None, 'public')]
            require(bool(matches))
            if fk.ondelete:
                require(matches[0]['options'].get('ondelete') == fk.ondelete)
            if fk.deferrable:
                require(matches[0]['options'].get('deferrable') is True)
                require(matches[0]['options'].get('initially') == fk.initially)
        unique = {tuple(v['column_names']) for v in schema.get_unique_constraints(name, schema='public')}
        for constraint in table.constraints:
            if isinstance(constraint, UniqueConstraint):
                if versions[0] in ('0031_membership_actions','0032_beta_recruitment') and name=='recruitment_cycle_members' and tuple(c.name for c in constraint.columns)==('cycle_id','generation','membership_id'):
                    continue  # current/retained CM uniqueness is enforced by the partial index below
                if (versions[0] in SUPPORTED_REVISIONS[10:] and name=='recruitment_cycle_consents' and
                        tuple(c.name for c in constraint.columns)==('user_id','command_id')):
                    require(('user_id','command_id','participation_id') in unique)
                    continue
                if versions[0] in ('0031_membership_actions','0032_beta_recruitment') and name=='recruitment_assignments' and tuple(c.name for c in constraint.columns)==('round_id','membership_id'):
                    continue
                # The model retains this constraint for the 0023 runtime.
                # 0027 keeps live (participation,segment) uniqueness and allows
                # a fresh row after release; old reservation rows are immutable.
                if (versions[0] in SUPPORTED_REVISIONS[9:] and name=='recruitment_reservations' and
                        tuple(c.name for c in constraint.columns)==('participation_id','segment_id','schedule_revision')):
                    continue
                if versions[0]=='0019_integrated_recruitment' and constraint.name in ('uq_assignment_reservation_owner','uq_segment_reservation_owner'):
                    continue
                added_weekly_aliases = {
                    'recruitment_items': ('room_id','id','raid_id'),
                    'recruitment_rounds': ('room_id','item_id','id','cycle_key'),
                    'recruitment_assignments': ('room_id','item_id','round_id','id','user_id','character_id'),
                }
                if (versions[0] not in SUPPORTED_REVISIONS[3:] and
                        tuple(c.name for c in constraint.columns) == added_weekly_aliases.get(name)):
                    continue
                require(tuple(c.name for c in constraint.columns) in unique)
        # Expressions are covered by domain/DDL tests; startup catches missing checks.
        require(len(schema.get_check_constraints(name, schema='public')) >=
                sum(isinstance(c, CheckConstraint) for c in table.constraints))
        indexes = {v['name']: v for v in schema.get_indexes(name, schema='public')}
        for index in table.indexes:
            if index.name in ('uq_recruitment_current_cycle_member','uq_recruitment_current_assignment') and versions[0] not in ('0031_membership_actions','0032_beta_recruitment'):continue
            actual = indexes.get(index.name)
            require(actual is not None)
            require(actual['column_names'] == [c.name for c in index.columns])
            require(bool(actual['unique']) == bool(index.unique))
            where = index.dialect_options['postgresql'].get('where')
            if where is not None:
                require(normalized(actual.get('dialect_options', {}).get('postgresql_where', '')) == normalized(where))
        privileges = ('SELECT','INSERT','UPDATE','DELETE') if name in ('recruitment_weekly_occupancies','recruitment_cycle_submissions') else ('SELECT','INSERT','UPDATE')
        for privilege in privileges:
            require(db.scalar(text('SELECT has_table_privilege(current_user, :name, :privilege)'),
                              dict(name='public.'+name, privilege=privilege)))
    triggers = db.execute(text("""
        SELECT c.relname, t.tgenabled, t.tgtype, f.proname, fn.nspname
        FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid
        JOIN pg_namespace n ON n.oid=c.relnamespace
        JOIN pg_proc f ON f.oid=t.tgfoid JOIN pg_namespace fn ON fn.oid=f.pronamespace
        WHERE n.nspname='public' AND NOT t.tgisinternal
          AND t.tgname='record_timestamps_before_write'
    """)).all()
    enabled = {name for name, mode, kind, function, namespace in triggers
               if mode in ('O', 'A') and kind & 23 == 23
               and function == 'maintain_record_timestamps' and namespace == 'public'}
    require({m.__tablename__ for m in models} <= enabled)
    if versions[0] in SUPPORTED_REVISIONS[9:]:
        guards=set(db.scalars(text("""SELECT tgname FROM pg_trigger
            WHERE NOT tgisinternal AND tgenabled IN ('O','A') AND
            tgrelid IN ('recruitment_reservations'::regclass,'recruitment_cycle_consents'::regclass)""")))
        require({'reservation_history_before_write','cycle_consent_immutable'}<=guards)
    if versions[0] in SUPPORTED_REVISIONS[10:]:
        from app.raid_rooms.cycle_planning_models import CYCLE_PLANNING_MODELS
        guarded=set(db.scalars(text("""SELECT c.relname FROM pg_trigger t
            JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace
            JOIN pg_proc f ON f.oid=t.tgfoid JOIN pg_namespace fn ON fn.oid=f.pronamespace
            WHERE n.nspname='public' AND NOT t.tgisinternal AND t.tgenabled IN ('O','A')
            AND t.tgname='cycle_planning_immutable' AND (t.tgtype & 27)=27
            AND f.proname='protect_cycle_decision' AND fn.nspname='public'""")))
        require({m.__tablename__ for m in CYCLE_PLANNING_MODELS}<=guarded)
    if versions[0] in ('0029_cycle_outcomes','0030_completion_corrections','0031_membership_actions','0032_beta_recruitment'):
        guarded=set(db.scalars(text("""SELECT c.relname FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid
            JOIN pg_namespace n ON n.oid=c.relnamespace JOIN pg_proc f ON f.oid=t.tgfoid
            WHERE n.nspname='public' AND NOT t.tgisinternal AND t.tgenabled IN ('O','A')
            AND t.tgname='cycle_outcome_immutable' AND (t.tgtype & 27)=27 AND f.proname='protect_cycle_decision'""")))
        from app.raid_rooms.cycle_outcome_models import CYCLE_OUTCOME_MODELS
        require({m.__tablename__ for m in CYCLE_OUTCOME_MODELS}<=guarded)
    if versions[0] in ('0030_completion_corrections','0031_membership_actions','0032_beta_recruitment'):
        require(db.scalar(text("SELECT count(*) FROM pg_trigger t JOIN pg_proc f ON f.oid=t.tgfoid WHERE t.tgrelid='raid_completion_corrections'::regclass AND NOT t.tgisinternal AND t.tgenabled IN ('O','A') AND t.tgname='completion_correction_immutable' AND (t.tgtype & 27)=27 AND f.proname='protect_cycle_decision'"))==1)
    if versions[0] in ('0031_membership_actions','0032_beta_recruitment'):
        require(db.scalar(text("SELECT count(*) FROM pg_trigger t JOIN pg_proc f ON f.oid=t.tgfoid WHERE t.tgrelid='recruitment_membership_action_audit'::regclass AND NOT t.tgisinternal AND t.tgenabled IN ('O','A') AND t.tgname='membership_action_immutable' AND (t.tgtype & 27)=27 AND f.proname='protect_cycle_decision'"))==1)
    head = db.get(DirectoryHead, 1)
    require(head is not None and head.revision >= 1)


def require_active(db):
    require(list(db.scalars(text('SELECT version_num FROM public.alembic_version')))==['0023_recruitment_resume'])
    require_ready(db,integrated=True)


def require_legacy_worker(db):
    # The old worker may not auto-enrol or expire proposals on the shadow head.
    require(list(db.scalars(text('SELECT version_num FROM public.alembic_version')))==['0023_recruitment_resume'])


def require_cycle_worker(db):
    require(list(db.scalars(text('SELECT version_num FROM public.alembic_version')))in (['0029_cycle_outcomes'],['0030_completion_corrections'],['0031_membership_actions'],['0032_beta_recruitment']))


def require_two_cycle_active(db):
    require_cycle_worker(db)
    require_ready(db,integrated=True)
