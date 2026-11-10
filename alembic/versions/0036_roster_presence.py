"""Record positive roster observations without retiring or relinking characters."""
from alembic import op

revision = '0036_roster_presence'
down_revision = '0035_cycle_group_policy'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('''CREATE TABLE character_roster_transitions (
        id UUID PRIMARY KEY,
        character_id UUID NOT NULL REFERENCES game_characters(id),
        account_id UUID NOT NULL REFERENCES game_accounts(id),
        owner_id UUID NOT NULL REFERENCES users(id),
        ownership_revision INTEGER NOT NULL,
        from_revision INTEGER NOT NULL,
        to_revision INTEGER NOT NULL,
        state VARCHAR(16) NOT NULL,
        source_usable BOOLEAN NOT NULL,
        observed_at TIMESTAMPTZ NOT NULL,
        record_created_at TIMESTAMPTZ DEFAULT clock_timestamp(),
        record_updated_at TIMESTAMPTZ DEFAULT clock_timestamp(),
        UNIQUE(character_id,ownership_revision,to_revision),
        CHECK(state IN ('missing','present') AND from_revision>0
            AND to_revision>=from_revision AND ownership_revision>0))''')
    op.execute('CREATE INDEX ix_character_roster_transitions_character_id ON character_roster_transitions(character_id)')
    op.execute('''CREATE TRIGGER record_timestamps_before_write BEFORE INSERT OR UPDATE
        ON character_roster_transitions FOR EACH ROW EXECUTE FUNCTION maintain_record_timestamps()''')
    op.execute('''CREATE TABLE roster_participation_recoveries (
        id UUID PRIMARY KEY, cycle_id UUID NOT NULL REFERENCES recruitment_room_cycles(id),
        generation INTEGER NOT NULL, evidence JSONB NOT NULL, observed_at TIMESTAMPTZ NOT NULL,
        record_created_at TIMESTAMPTZ DEFAULT clock_timestamp(),
        record_updated_at TIMESTAMPTZ DEFAULT clock_timestamp(),
        FOREIGN KEY(cycle_id,generation) REFERENCES recruitment_cycle_generations(cycle_id,generation),
        CHECK(generation>0 AND jsonb_typeof(evidence)='object'))''')
    op.execute('''CREATE TRIGGER record_timestamps_before_write BEFORE INSERT OR UPDATE
        ON roster_participation_recoveries FOR EACH ROW EXECUTE FUNCTION maintain_record_timestamps()''')
    op.execute('''CREATE TABLE roster_participation_capabilities (
        id UUID PRIMARY KEY, cycle_id UUID NOT NULL, generation INTEGER NOT NULL,
        created_at TIMESTAMPTZ NOT NULL,
        record_created_at TIMESTAMPTZ DEFAULT clock_timestamp(),
        record_updated_at TIMESTAMPTZ DEFAULT clock_timestamp(),
        UNIQUE(cycle_id,generation), CHECK(generation>0),
        FOREIGN KEY(cycle_id,generation) REFERENCES recruitment_cycle_generations(cycle_id,generation))''')
    op.execute('''CREATE FUNCTION protect_roster_observation() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN RAISE EXCEPTION 'roster observation evidence is immutable'; END $$''')
    for table in ('character_roster_transitions', 'roster_participation_recoveries', 'roster_participation_capabilities'):
        op.execute(f'''CREATE TRIGGER roster_observation_immutable BEFORE UPDATE OR DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION protect_roster_observation()''')


def downgrade():
    raise RuntimeError('Preserve roster observation evidence; use a forward migration')
