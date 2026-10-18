"""Additive ownership disputes; fixed DDL independent of future ORM changes."""
from alembic import op

revision = '0015_ownership_disputes'
down_revision = '0014_group_admissions'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('CREATE TABLE ownership_dispute_heads (\n\taccount_id UUID NOT NULL, \n\tgeneration INTEGER NOT NULL, \n\tsequence INTEGER NOT NULL, \n\tPRIMARY KEY (account_id), \n\tCHECK (generation >= 1 AND sequence >= 0), \n\tFOREIGN KEY(account_id) REFERENCES game_accounts (id)\n)')
    op.execute('CREATE TABLE ownership_member_heads (\n\tuser_id UUID NOT NULL, \n\tproof_revision INTEGER NOT NULL, \n\tdispute_revision INTEGER NOT NULL, \n\tPRIMARY KEY (user_id), \n\tCHECK (proof_revision >= 1 AND dispute_revision >= 1), \n\tFOREIGN KEY(user_id) REFERENCES users (id)\n)')
    op.execute("CREATE TABLE ownership_control_proofs (\n\tid UUID NOT NULL, \n\tactor_id UUID NOT NULL, \n\tpurpose VARCHAR(16) NOT NULL, \n\tsource VARCHAR(24) NOT NULL, \n\tregistration_id UUID, \n\tsource_registration_id UUID, \n\tdispute_id UUID, \n\tcandidate_id UUID, \n\tlookup_name VARCHAR(64) NOT NULL, \n\tversion INTEGER NOT NULL, \n\tstatus VARCHAR(16) NOT NULL, \n\toutcome VARCHAR(24) NOT NULL, \n\tresult_code VARCHAR(64), \n\tidentity_snapshot JSONB NOT NULL, \n\tbaseline JSONB, \n\tslots JSONB NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\texpires_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tended_at TIMESTAMP WITH TIME ZONE, \n\tPRIMARY KEY (id), \n\tCHECK (purpose IN ('claim','defense') AND source IN ('direct_input','registration','dispute_defense')), \n\tCHECK (status IN ('pending','passed','expired','cancelled','invalidated') AND outcome IN ('none','verified','dispute_opened','defended','blocked') AND version >= 1), \n\tCHECK (expires_at > created_at AND ((status='pending' AND ended_at IS NULL) OR (status<>'pending' AND ended_at IS NOT NULL))), \n\tFOREIGN KEY(actor_id) REFERENCES users (id), \n\tFOREIGN KEY(registration_id) REFERENCES game_account_registrations (id), \n\tFOREIGN KEY(source_registration_id) REFERENCES game_account_registrations (id), \n\tFOREIGN KEY(candidate_id) REFERENCES game_accounts (id)\n)")
    op.execute('CREATE INDEX ix_ownership_control_proofs_actor_id ON ownership_control_proofs (actor_id)')
    op.execute('CREATE INDEX ix_ownership_control_proofs_expires_at ON ownership_control_proofs (expires_at)')
    op.execute("CREATE TABLE ownership_disputes (\n\tid UUID NOT NULL, \n\taccount_id UUID NOT NULL, \n\towner_id UUID NOT NULL, \n\tchallenger_id UUID NOT NULL, \n\townership_revision INTEGER NOT NULL, \n\tgeneration INTEGER NOT NULL, \n\tsequence INTEGER NOT NULL, \n\tslot INTEGER NOT NULL, \n\tproof_id UUID NOT NULL, \n\tversion INTEGER NOT NULL, \n\tstate VARCHAR(24) NOT NULL, \n\treason VARCHAR(64), \n\tstarted_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tdeadline TIMESTAMP WITH TIME ZONE NOT NULL, \n\tresolved_at TIMESTAMP WITH TIME ZONE, \n\tnext_retry_at TIMESTAMP WITH TIME ZONE, \n\tlease_until TIMESTAMP WITH TIME ZONE, \n\tlease_generation INTEGER NOT NULL, \n\tPRIMARY KEY (id), \n\tCHECK (slot BETWEEN 1 AND 3 AND ownership_revision >= 1 AND generation >= 1 AND sequence >= 1 AND version >= 1 AND lease_generation >= 0 AND owner_id <> challenger_id), \n\tCHECK (state IN ('defending','defended','transferred','cancelled','invalidated','review_required')), \n\tCHECK (deadline = started_at + interval '24 hours' AND ((state IN ('defending','review_required') AND resolved_at IS NULL) OR (state NOT IN ('defending','review_required') AND resolved_at IS NOT NULL))), \n\tUNIQUE (account_id, sequence), \n\tFOREIGN KEY(account_id) REFERENCES game_accounts (id), \n\tFOREIGN KEY(owner_id) REFERENCES users (id), \n\tFOREIGN KEY(challenger_id) REFERENCES users (id), \n\tUNIQUE (proof_id), \n\tFOREIGN KEY(proof_id) REFERENCES ownership_control_proofs (id)\n)")
    op.execute('CREATE INDEX ix_ownership_disputes_account_id ON ownership_disputes (account_id)')
    op.execute('CREATE INDEX ix_ownership_disputes_challenger_id ON ownership_disputes (challenger_id)')
    op.execute('CREATE INDEX ix_ownership_disputes_deadline ON ownership_disputes (deadline)')
    op.execute("CREATE UNIQUE INDEX uq_dispute_live_actor ON ownership_disputes (account_id, challenger_id) WHERE state IN ('defending','review_required')")
    op.execute("CREATE UNIQUE INDEX uq_dispute_live_slot ON ownership_disputes (account_id, slot) WHERE state IN ('defending','review_required')")
    op.execute('CREATE TABLE ownership_dispute_events (\n\tid UUID NOT NULL, \n\tdispute_id UUID NOT NULL, \n\trevision INTEGER NOT NULL, \n\tkind VARCHAR(64) NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (dispute_id, revision), \n\tCHECK (revision >= 1), \n\tFOREIGN KEY(dispute_id) REFERENCES ownership_disputes (id)\n)')
    op.execute('ALTER TABLE ownership_control_proofs ADD CONSTRAINT fk_proof_dispute FOREIGN KEY(dispute_id) REFERENCES ownership_disputes(id)')


def downgrade():
    raise RuntimeError('Preserve ownership dispute history; use a forward correction')
