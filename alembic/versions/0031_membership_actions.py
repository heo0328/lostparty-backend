"""Add explicit leadership recovery and immutable membership action evidence."""
from alembic import op
from sqlalchemy import inspect
revision = '0031_membership_actions'
down_revision = '0030_completion_corrections'
branch_labels = None
depends_on = None


def upgrade():
    # Preserve ended CM identities across a same-T rejoin. No row is rewritten.
    name=next(v['name'] for v in inspect(op.get_bind()).get_unique_constraints('recruitment_cycle_members')
        if v['column_names']==['cycle_id','generation','membership_id'])
    op.drop_constraint(name,'recruitment_cycle_members',type_='unique')
    assignment_name=next(v['name'] for v in inspect(op.get_bind()).get_unique_constraints('recruitment_assignments')
        if v['column_names']==['round_id','membership_id'])
    op.drop_constraint(assignment_name,'recruitment_assignments',type_='unique')
    op.execute("CREATE UNIQUE INDEX uq_recruitment_current_assignment ON recruitment_assignments(round_id,membership_id) WHERE state <> 'left' AND state <> 'legacy_ended'")
    op.execute("CREATE UNIQUE INDEX uq_recruitment_current_cycle_member ON recruitment_cycle_members(cycle_id,generation,membership_id) WHERE state <> 'cancelled' AND state <> 'removed'")
    op.execute("""CREATE TABLE recruitment_leadership_recovery (
        cycle_id UUID NOT NULL, generation INTEGER NOT NULL, state VARCHAR(24) NOT NULL,
        reason VARCHAR(64), remaining_review_reasons JSONB NOT NULL, revision INTEGER NOT NULL,
        record_created_at TIMESTAMPTZ DEFAULT clock_timestamp(),record_updated_at TIMESTAMPTZ DEFAULT clock_timestamp(),
        PRIMARY KEY(cycle_id,generation),
        FOREIGN KEY(cycle_id,generation) REFERENCES recruitment_cycle_generations(cycle_id,generation),
        CHECK(generation>=1 AND revision>=1 AND state IN ('active','pending_review','review_remaining','closed') AND jsonb_typeof(remaining_review_reasons)='array'))""")
    op.execute("""CREATE TABLE recruitment_membership_action_audit (
        id UUID PRIMARY KEY,room_id UUID NOT NULL REFERENCES recruitment_rooms(id),
        actor_membership_id UUID NOT NULL REFERENCES recruitment_memberships(id),user_id UUID NOT NULL REFERENCES users(id),
        command_id UUID NOT NULL,action VARCHAR(32) NOT NULL,evidence JSONB NOT NULL,effective_at TIMESTAMPTZ NOT NULL,
        record_created_at TIMESTAMPTZ DEFAULT clock_timestamp(),record_updated_at TIMESTAMPTZ DEFAULT clock_timestamp(),
        UNIQUE(user_id,command_id),CHECK(action IN ('leave_target','leave_all','dissolve_led_targets','recover_leadership') AND jsonb_typeof(evidence)='object'))""")
    for table in ('recruitment_leadership_recovery','recruitment_membership_action_audit'):
        op.execute(f'CREATE TRIGGER record_timestamps_before_write BEFORE INSERT OR UPDATE ON {table} FOR EACH ROW EXECUTE FUNCTION maintain_record_timestamps()')
    op.execute('CREATE TRIGGER membership_action_immutable BEFORE UPDATE OR DELETE ON recruitment_membership_action_audit FOR EACH ROW EXECUTE FUNCTION protect_cycle_decision()')


def downgrade():
    raise RuntimeError('Preserve membership action and recovery evidence')
