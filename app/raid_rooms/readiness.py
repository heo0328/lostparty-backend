"""Read-only minimum schema/privilege checks prepared for the F3 startup boundary.

This is not a migration runner or a substitute for migration regression tests.
No production lifespan calls this module before activation is agreed.
"""
import re
from sqlalchemy import inspect, text, UniqueConstraint, CheckConstraint
from app.game_accounts.support import fail
from app.raid_rooms.models import Room, Round, Membership, Application, DirectoryHead, MemberHead

REVISION = '0018_room_application_build'
MODELS = (Room, Round, Membership, Application, DirectoryHead, MemberHead)


def normalized(value):
    value = re.sub(r'::(?:text|character varying)', '', str(value).lower())
    return re.sub(r'[\s()"]', '', value)


def require(value):
    if not value:
        fail('SERVICE_UNAVAILABLE', 503)


def require_ready(db):
    """Inspect the caller's transaction and effective DB role, without any writes.

    SQL/privilege failures propagate to the existing 503 boundary. Unknown migration
    heads require explicit compatibility review instead of a guessed >= comparison.
    """
    schema = inspect(db.connection())
    require(schema.has_table('alembic_version', schema='public'))
    require(list(db.scalars(text('SELECT version_num FROM public.alembic_version'))) == [REVISION])
    for model in MODELS:
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
            if fk.deferrable:
                require(matches[0]['options'].get('deferrable') is True)
                require(matches[0]['options'].get('initially') == fk.initially)
        unique = {tuple(v['column_names']) for v in schema.get_unique_constraints(name, schema='public')}
        for constraint in table.constraints:
            if isinstance(constraint, UniqueConstraint):
                require(tuple(c.name for c in constraint.columns) in unique)
        # Expressions are covered by domain/DDL tests; startup catches missing checks.
        require(len(schema.get_check_constraints(name, schema='public')) >=
                sum(isinstance(c, CheckConstraint) for c in table.constraints))
        indexes = {v['name']: v for v in schema.get_indexes(name, schema='public')}
        for index in table.indexes:
            actual = indexes.get(index.name)
            require(actual is not None)
            require(actual['column_names'] == [c.name for c in index.columns])
            require(bool(actual['unique']) == bool(index.unique))
            where = index.dialect_options['postgresql'].get('where')
            if where is not None:
                require(normalized(actual.get('dialect_options', {}).get('postgresql_where', '')) == normalized(where))
        for privilege in ('SELECT', 'INSERT', 'UPDATE'):
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
    require({m.__tablename__ for m in MODELS} <= enabled)
    head = db.get(DirectoryHead, 1)
    require(head is not None and head.revision >= 1)
