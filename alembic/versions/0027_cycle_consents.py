"""Append a new consent/reservation interval instead of reviving released rows."""
from alembic import op
import sqlalchemy as sa

revision='0027_cycle_consents'
down_revision='0026_cycle_lifecycle'
branch_labels=depends_on=None


def upgrade():
    # No existing rows/columns are rewritten. Live reservation uniqueness remains
    # enforced by uq_recruitment_active_participation_segment from 0020.
    schema=sa.inspect(op.get_bind())
    old=[c['name'] for c in schema.get_unique_constraints('recruitment_reservations')
        if c['column_names']==['participation_id','segment_id','schedule_revision']]
    if len(old)!=1:raise RuntimeError('Expected legacy reservation uniqueness')
    op.drop_constraint(old[0],'recruitment_reservations',type_='unique')
    op.execute('''CREATE FUNCTION protect_reservation_history() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Reservation history is immutable'; END IF;
            IF (to_jsonb(NEW)-'record_created_at'-'record_updated_at') IS NOT DISTINCT FROM
               (to_jsonb(OLD)-'record_created_at'-'record_updated_at') THEN RETURN NEW; END IF;
            IF OLD.released_at IS NOT NULL OR NEW.released_at IS NULL OR
               (to_jsonb(NEW)-'released_at'-'released_reason'-'record_created_at'-'record_updated_at') IS DISTINCT FROM
               (to_jsonb(OLD)-'released_at'-'released_reason'-'record_created_at'-'record_updated_at') THEN
                RAISE EXCEPTION 'Reservation may only be released once';
            END IF;
            RETURN NEW;
        END $$''')
    op.execute('''CREATE TRIGGER reservation_history_before_write BEFORE UPDATE OR DELETE ON recruitment_reservations
        FOR EACH ROW EXECUTE FUNCTION protect_reservation_history()''')
    op.execute('''CREATE TABLE recruitment_cycle_consents (
        id UUID PRIMARY KEY,room_id UUID NOT NULL,cycle_id UUID NOT NULL,generation INTEGER NOT NULL,
        cycle_member_id UUID NOT NULL,membership_id UUID NOT NULL,user_id UUID NOT NULL,
        participation_id UUID NOT NULL,session_id UUID NOT NULL,command_id UUID NOT NULL,
        member_revision INTEGER NOT NULL,participation_revision INTEGER NOT NULL,schedule_revision INTEGER NOT NULL,
        effective_at TIMESTAMPTZ NOT NULL,evidence JSONB NOT NULL,
        UNIQUE(user_id,command_id),UNIQUE(participation_id,participation_revision),
        FOREIGN KEY(room_id,cycle_id,generation,cycle_member_id,membership_id,user_id)
            REFERENCES recruitment_cycle_members(room_id,cycle_id,generation,id,membership_id,user_id),
        FOREIGN KEY(room_id,participation_id,session_id,membership_id,user_id)
            REFERENCES recruitment_participations(room_id,id,session_id,membership_id,user_id),
        FOREIGN KEY(room_id,cycle_id,generation,session_id)
            REFERENCES recruitment_cycle_sessions(room_id,cycle_id,generation,session_id),
        CHECK(member_revision>=1 AND participation_revision>=1 AND schedule_revision>=1 AND jsonb_typeof(evidence)='object'),
        record_created_at TIMESTAMPTZ DEFAULT clock_timestamp(),record_updated_at TIMESTAMPTZ DEFAULT clock_timestamp()
    )''')
    op.execute('''CREATE TRIGGER record_timestamps_before_write BEFORE INSERT OR UPDATE ON recruitment_cycle_consents
        FOR EACH ROW EXECUTE FUNCTION maintain_record_timestamps()''')
    op.execute('''CREATE TRIGGER cycle_consent_immutable BEFORE UPDATE OR DELETE ON recruitment_cycle_consents
        FOR EACH ROW EXECUTE FUNCTION protect_cycle_decision()''')


def downgrade():raise RuntimeError('Preserve consent/reservation history')
