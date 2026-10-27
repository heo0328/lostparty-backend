"""Append target planning evidence without rewriting existing schedule sources."""
from alembic import op
import sqlalchemy as sa
revision='0028_cycle_planning'
down_revision='0027_cycle_consents'
branch_labels=depends_on=None


def upgrade():
    # Multi-session votes can authorize more than one participation per command.
    old=[c['name'] for c in sa.inspect(op.get_bind()).get_unique_constraints('recruitment_cycle_consents')
        if c['column_names']==['user_id','command_id']]
    if len(old)!=1:raise RuntimeError('Expected single-participation consent uniqueness')
    op.drop_constraint(old[0],'recruitment_cycle_consents',type_='unique')
    op.create_unique_constraint('uq_cycle_consent_command_part','recruitment_cycle_consents',['user_id','command_id','participation_id'])
    op.create_unique_constraint('uq_cycle_alternative_owner','recruitment_schedule_alternatives',['group_id','id'])
    clocks='record_created_at TIMESTAMPTZ DEFAULT clock_timestamp(),record_updated_at TIMESTAMPTZ DEFAULT clock_timestamp()'
    definitions={
        'recruitment_cycle_proposals':"""proposal_id UUID PRIMARY KEY,room_id UUID NOT NULL,cycle_id UUID NOT NULL,generation INTEGER NOT NULL,content JSONB NOT NULL,
            UNIQUE(room_id,cycle_id,generation,proposal_id),
            FOREIGN KEY(room_id,proposal_id) REFERENCES recruitment_schedule_proposals(room_id,id),
            FOREIGN KEY(room_id,cycle_id) REFERENCES recruitment_room_cycles(room_id,id),
            FOREIGN KEY(cycle_id,generation) REFERENCES recruitment_cycle_generations(cycle_id,generation),
            CHECK(jsonb_typeof(content)='array')""",
        'recruitment_cycle_votes':"""id UUID PRIMARY KEY,room_id UUID NOT NULL,cycle_id UUID NOT NULL,generation INTEGER NOT NULL,
            proposal_id UUID NOT NULL,cycle_member_id UUID NOT NULL,membership_id UUID NOT NULL,user_id UUID NOT NULL,
            member_revision INTEGER NOT NULL,revision INTEGER NOT NULL,command_id UUID NOT NULL,response VARCHAR(8) NOT NULL,effective_at TIMESTAMPTZ NOT NULL,
            FOREIGN KEY(room_id,cycle_id,generation,proposal_id) REFERENCES recruitment_cycle_proposals(room_id,cycle_id,generation,proposal_id),
            FOREIGN KEY(room_id,cycle_id,generation,cycle_member_id,membership_id,user_id) REFERENCES recruitment_cycle_members(room_id,cycle_id,generation,id,membership_id,user_id),
            UNIQUE(proposal_id,cycle_member_id,revision),UNIQUE(proposal_id,user_id,command_id),
            CHECK(member_revision>=1 AND revision>=1 AND response IN ('accept','reject'))""",
        'recruitment_cycle_schedule_events':"""id UUID PRIMARY KEY,room_id UUID NOT NULL,cycle_id UUID NOT NULL,generation INTEGER NOT NULL,
            actor_id UUID NOT NULL REFERENCES users(id),command_id UUID NOT NULL,kind VARCHAR(32) NOT NULL,effective_at TIMESTAMPTZ NOT NULL,evidence JSONB NOT NULL,
            FOREIGN KEY(room_id,cycle_id) REFERENCES recruitment_room_cycles(room_id,id),
            FOREIGN KEY(cycle_id,generation) REFERENCES recruitment_cycle_generations(cycle_id,generation),
            CHECK(kind IN ('groups_edited','initial_confirmed','proposal_created','proposal_applied','proposal_obsolete') AND jsonb_typeof(evidence)='object')""",
        'recruitment_cycle_alternatives':"""alternative_id UUID PRIMARY KEY,group_id UUID NOT NULL,edition INTEGER NOT NULL,client_key VARCHAR(64) NOT NULL,
            FOREIGN KEY(group_id,alternative_id) REFERENCES recruitment_schedule_alternatives(group_id,id),
            UNIQUE(group_id,edition,client_key),CHECK(edition>=1)""",
    }
    for table,definition in definitions.items():
        op.execute(f'CREATE TABLE {table} ({definition},{clocks})')
        op.execute(f'CREATE TRIGGER record_timestamps_before_write BEFORE INSERT OR UPDATE ON {table} FOR EACH ROW EXECUTE FUNCTION maintain_record_timestamps()')
        op.execute(f'CREATE TRIGGER cycle_planning_immutable BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION protect_cycle_decision()')


def downgrade():raise RuntimeError('Preserve planning/vote/consent history')
