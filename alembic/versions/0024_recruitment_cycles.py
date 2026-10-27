"""Add shadow two-cycle storage; preserve all old rows and unknown provenance.

No runtime cutover: 0023 worker/HTTP activation rejects this head. This migration
must not run on a live database before v2 and its worker are ready together.
"""
import uuid
from alembic import op
from sqlalchemy import text

revision = '0024_recruitment_cycles'
down_revision = '0023_recruitment_resume'
branch_labels = depends_on = None

TABLES = (
    'recruitment_room_cycles', 'recruitment_cycle_generations',
    'recruitment_cycle_members', 'recruitment_cycle_rounds',
    'recruitment_cycle_assignments',
    'recruitment_cycle_directory_heads', 'recruitment_cycle_submissions',
    'recruitment_cycle_openings', 'recruitment_participation_events',
    'recruitment_legacy_cycle_evidence',
)


def upgrade():
    # Frozen DDL deliberately independent of evolving application metadata.
    op.execute('''CREATE TABLE recruitment_room_cycles (
        id UUID PRIMARY KEY, room_id UUID NOT NULL REFERENCES recruitment_rooms(id),
        cycle_key DATE NOT NULL, state VARCHAR(24) NOT NULL, generation INTEGER,
        revision INTEGER NOT NULL, settings_revision INTEGER NOT NULL,
        members_revision INTEGER NOT NULL, plan_revision INTEGER NOT NULL,
        settings_snapshot JSONB, provenance VARCHAR(24) NOT NULL, created_at TIMESTAMPTZ NOT NULL,
        UNIQUE(room_id,cycle_key), UNIQUE(room_id,cycle_key,id), UNIQUE(room_id,id),
        CHECK(EXTRACT(DOW FROM cycle_key)=3 AND revision>=1 AND settings_revision>=1 AND members_revision>=1 AND plan_revision>=1),
        CHECK(state IN ('open','closed','review_required') AND (generation IS NULL OR generation>=1)),
        CHECK(provenance IN ('explicit','legacy_unknown') AND (state='review_required' OR (generation IS NOT NULL AND provenance='explicit' AND settings_snapshot IS NOT NULL)))
    )''')
    op.execute('CREATE INDEX ix_recruitment_cycle_directory ON recruitment_room_cycles(cycle_key,state,room_id)')
    op.execute('''CREATE TABLE recruitment_cycle_generations (
        cycle_id UUID NOT NULL REFERENCES recruitment_room_cycles(id), generation INTEGER NOT NULL,
        state VARCHAR(24) NOT NULL, leader_cycle_member_id UUID,
        leadership_revision INTEGER NOT NULL, next_join_order BIGINT,
        opened_at TIMESTAMPTZ NOT NULL, closed_at TIMESTAMPTZ,
        PRIMARY KEY(cycle_id,generation),
        CHECK(generation>=1 AND leadership_revision>=1 AND (next_join_order IS NULL OR next_join_order>=1)),
        CHECK(state IN ('open','completed','stopped','cancelled','review_required')),
        CHECK((state='open' AND leader_cycle_member_id IS NOT NULL AND closed_at IS NULL) OR (state<>'open')),
        CHECK(state<>'cancelled' OR (leader_cycle_member_id IS NULL AND closed_at IS NOT NULL))
    )''')
    op.execute('''ALTER TABLE recruitment_room_cycles ADD CONSTRAINT fk_room_cycle_generation
        FOREIGN KEY(id,generation) REFERENCES recruitment_cycle_generations(cycle_id,generation)
        DEFERRABLE INITIALLY DEFERRED''')
    op.execute('''CREATE TABLE recruitment_cycle_members (
        id UUID PRIMARY KEY, room_id UUID NOT NULL, cycle_id UUID NOT NULL, generation INTEGER,
        membership_id UUID NOT NULL, user_id UUID NOT NULL, state VARCHAR(24) NOT NULL,
        revision INTEGER NOT NULL, joined_order BIGINT, joined_at TIMESTAMPTZ, ended_at TIMESTAMPTZ,
        UNIQUE(cycle_id,generation,id), UNIQUE(cycle_id,generation,membership_id),
        UNIQUE(cycle_id,generation,joined_order), UNIQUE(room_id,cycle_id,generation,id,membership_id,user_id),
        FOREIGN KEY(room_id,cycle_id) REFERENCES recruitment_room_cycles(room_id,id),
        FOREIGN KEY(cycle_id,generation) REFERENCES recruitment_cycle_generations(cycle_id,generation),
        FOREIGN KEY(room_id,membership_id,user_id) REFERENCES recruitment_memberships(room_id,id,user_id),
        CHECK(revision>=1 AND (generation IS NULL OR generation>=1) AND (joined_order IS NULL OR joined_order>=1)),
        CHECK(state IN ('participating','completed','stopped','cancelled','removed','review_required')),
        CHECK(state='review_required' OR (generation IS NOT NULL AND joined_order IS NOT NULL AND joined_at IS NOT NULL)),
        CHECK(state<>'participating' OR ended_at IS NULL),
        CHECK(state NOT IN ('cancelled','removed') OR ended_at IS NOT NULL)
    )''')
    op.execute('''CREATE UNIQUE INDEX uq_recruitment_unknown_cycle_member ON recruitment_cycle_members(cycle_id,membership_id) WHERE generation IS NULL''')
    op.execute('''ALTER TABLE recruitment_cycle_generations ADD CONSTRAINT fk_cycle_generation_leader
        FOREIGN KEY(cycle_id,generation,leader_cycle_member_id) REFERENCES recruitment_cycle_members(cycle_id,generation,id)
        DEFERRABLE INITIALLY DEFERRED''')
    op.execute('''CREATE TABLE recruitment_cycle_rounds (
        round_id UUID PRIMARY KEY, room_id UUID NOT NULL, item_id UUID NOT NULL,
        cycle_key DATE NOT NULL, cycle_id UUID NOT NULL, generation INTEGER, is_current BOOLEAN NOT NULL,
        UNIQUE(room_id,cycle_id,generation,round_id),
        FOREIGN KEY(room_id,item_id,round_id,cycle_key) REFERENCES recruitment_rounds(room_id,item_id,id,cycle_key),
        FOREIGN KEY(room_id,cycle_key,cycle_id) REFERENCES recruitment_room_cycles(room_id,cycle_key,id),
        FOREIGN KEY(cycle_id,generation) REFERENCES recruitment_cycle_generations(cycle_id,generation),
        CHECK((generation IS NULL OR generation>=1) AND (generation IS NOT NULL OR NOT is_current))
    )''')
    op.execute('''CREATE UNIQUE INDEX uq_recruitment_current_cycle_item ON recruitment_cycle_rounds(cycle_id,generation,item_id) WHERE is_current''')
    op.execute('''CREATE TABLE recruitment_cycle_assignments (
        assignment_id UUID PRIMARY KEY, room_id UUID NOT NULL, cycle_id UUID NOT NULL,
        generation INTEGER NOT NULL, cycle_member_id UUID NOT NULL, membership_id UUID NOT NULL,
        user_id UUID NOT NULL, item_id UUID NOT NULL, round_id UUID NOT NULL,
        FOREIGN KEY(room_id,assignment_id,membership_id,user_id,item_id,round_id)
            REFERENCES recruitment_assignments(room_id,id,membership_id,user_id,item_id,round_id),
        FOREIGN KEY(room_id,cycle_id,generation,round_id)
            REFERENCES recruitment_cycle_rounds(room_id,cycle_id,generation,round_id),
        FOREIGN KEY(room_id,cycle_id,generation,cycle_member_id,membership_id,user_id)
            REFERENCES recruitment_cycle_members(room_id,cycle_id,generation,id,membership_id,user_id)
    )''')
    op.execute('''CREATE TABLE recruitment_cycle_directory_heads (
        cycle_key DATE PRIMARY KEY, revision BIGINT NOT NULL,
        CHECK(EXTRACT(DOW FROM cycle_key)=3 AND revision>=1)
    )''')
    op.execute('''CREATE TABLE recruitment_cycle_submissions (
        cycle_member_id UUID PRIMARY KEY, room_id UUID NOT NULL, cycle_id UUID NOT NULL,
        generation INTEGER NOT NULL, membership_id UUID NOT NULL, user_id UUID NOT NULL,
        revision INTEGER NOT NULL, source_personal_revision INTEGER NOT NULL,
        intervals JSONB NOT NULL, normalized_intervals JSONB NOT NULL, submitted_at TIMESTAMPTZ NOT NULL,
        FOREIGN KEY(room_id,cycle_id,generation,cycle_member_id,membership_id,user_id)
            REFERENCES recruitment_cycle_members(room_id,cycle_id,generation,id,membership_id,user_id),
        CHECK(revision>=1 AND source_personal_revision>=1 AND jsonb_typeof(intervals)='array' AND jsonb_typeof(normalized_intervals)='array')
    )''')
    op.execute('''CREATE TABLE recruitment_cycle_openings (
        id UUID PRIMARY KEY, room_id UUID NOT NULL, cycle_id UUID NOT NULL, generation INTEGER,
        item_id UUID NOT NULL, legacy_event_id UUID UNIQUE REFERENCES recruitment_opening_events(id),
        command_id UUID, mode VARCHAR(24) NOT NULL, state VARCHAR(24) NOT NULL,
        effective_at TIMESTAMPTZ NOT NULL, evidence JSONB NOT NULL,
        FOREIGN KEY(room_id,cycle_id) REFERENCES recruitment_room_cycles(room_id,id),
        FOREIGN KEY(room_id,item_id) REFERENCES recruitment_items(room_id,id),
        FOREIGN KEY(cycle_id,generation) REFERENCES recruitment_cycle_generations(cycle_id,generation),
        UNIQUE(cycle_id,generation,item_id,mode),
        CHECK(mode IN ('open','reopen','legacy_manual','legacy_scheduled_auto') AND state IN ('applied','cancelled','review_required')),
        CHECK((state='review_required' AND legacy_event_id IS NOT NULL) OR (generation IS NOT NULL AND command_id IS NOT NULL AND legacy_event_id IS NULL AND mode IN ('open','reopen')))
    )''')
    op.execute('''CREATE UNIQUE INDEX uq_recruitment_cycle_opening ON recruitment_cycle_openings(cycle_id,generation,item_id) WHERE state='applied' ''')
    op.execute('''CREATE TABLE recruitment_participation_events (
        id UUID PRIMARY KEY, room_id UUID NOT NULL, cycle_id UUID NOT NULL,
        generation INTEGER NOT NULL, cycle_member_id UUID NOT NULL, membership_id UUID NOT NULL,
        user_id UUID NOT NULL, command_id UUID NOT NULL, action VARCHAR(24) NOT NULL,
        member_revision INTEGER NOT NULL, effective_at TIMESTAMPTZ NOT NULL, evidence JSONB NOT NULL,
        FOREIGN KEY(room_id,cycle_id,generation,cycle_member_id,membership_id,user_id)
            REFERENCES recruitment_cycle_members(room_id,cycle_id,generation,id,membership_id,user_id),
        UNIQUE(cycle_member_id,member_revision), UNIQUE(cycle_member_id,command_id,action),
        CHECK(member_revision>=1 AND action IN ('joined','cancelled','removed','completed','stopped','character_changed') AND jsonb_typeof(evidence)='object')
    )''')
    op.execute('''CREATE TABLE recruitment_legacy_cycle_evidence (
        source_kind VARCHAR(24) NOT NULL, source_id UUID NOT NULL,
        room_id UUID NOT NULL REFERENCES recruitment_rooms(id), cycle_id UUID,
        reason VARCHAR(64) NOT NULL, evidence JSONB NOT NULL,
        PRIMARY KEY(source_kind,source_id),
        FOREIGN KEY(room_id,cycle_id) REFERENCES recruitment_room_cycles(room_id,id),
        CHECK(source_kind IN ('assignment','session','application','submission','proposal','resume','choice') AND jsonb_typeof(evidence)='object')
    )''')
    for name in TABLES:
        op.execute(f'''ALTER TABLE {name}
            ADD COLUMN record_created_at TIMESTAMPTZ DEFAULT clock_timestamp(),
            ADD COLUMN record_updated_at TIMESTAMPTZ DEFAULT clock_timestamp()''')
        op.execute(f'''CREATE TRIGGER record_timestamps_before_write BEFORE INSERT OR UPDATE ON {name}
            FOR EACH ROW EXECUTE FUNCTION maintain_record_timestamps()''')
    # These are audit sources. Corrections are new events, never rewritten history.
    op.execute('''CREATE FUNCTION reject_recruitment_event_mutation() RETURNS trigger
        LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Recruitment source events are immutable'; END $$''')
    for name in ('recruitment_participation_events', 'recruitment_cycle_openings', 'recruitment_legacy_cycle_evidence'):
        op.execute(f'''CREATE TRIGGER immutable_recruitment_source BEFORE UPDATE OR DELETE ON {name}
            FOR EACH ROW EXECUTE FUNCTION reject_recruitment_event_mutation()''')
    backfill()


def backfill():
    """Classify actual FK evidence only; no inferred order/leader/consent/settings.

Even a single historical Round does not prove its opening generation. Store its
actual date, retaining unknown generation rather than fabricating generation 1.
Opening/choice dates alone are not proof of an opened RoomCycle.
    """
    bind = op.get_bind()
    pairs = bind.execute(text('''SELECT room_id,cycle_key,min(created_at) AS created_at
        FROM recruitment_rounds GROUP BY room_id,cycle_key''')).mappings().all()
    for pair in pairs:
        bind.execute(text('''INSERT INTO recruitment_room_cycles
            (id,room_id,cycle_key,state,generation,revision,settings_revision,members_revision,plan_revision,settings_snapshot,provenance,created_at)
            VALUES (:id,:room_id,:cycle_key,'review_required',NULL,1,1,1,1,NULL,'legacy_unknown',:created_at)'''), dict(pair, id=uuid.uuid4()))
    op.execute('''INSERT INTO recruitment_cycle_rounds(round_id,room_id,item_id,cycle_key,cycle_id,generation,is_current)
        SELECT r.id,r.room_id,r.item_id,r.cycle_key,c.id,NULL,false
        FROM recruitment_rounds r JOIN recruitment_room_cycles c USING(room_id,cycle_key)''')
    members = bind.execute(text('''SELECT DISTINCT a.room_id,t.cycle_id,a.membership_id,a.user_id
        FROM recruitment_assignments a JOIN recruitment_cycle_rounds t ON t.round_id=a.round_id''')).mappings().all()
    for member in members:
        bind.execute(text('''INSERT INTO recruitment_cycle_members
            (id,room_id,cycle_id,generation,membership_id,user_id,state,revision,joined_order,joined_at,ended_at)
            VALUES (:id,:room_id,:cycle_id,NULL,:membership_id,:user_id,'review_required',1,NULL,NULL,NULL)'''), dict(member, id=uuid.uuid4()))
    op.execute('''INSERT INTO recruitment_legacy_cycle_evidence(source_kind,source_id,room_id,cycle_id,reason,evidence)
        SELECT 'assignment',a.id,a.room_id,t.cycle_id,'generation_and_interval_unknown',
               jsonb_build_object('round_id',a.round_id,'membership_id',a.membership_id,'state',a.state)
        FROM recruitment_assignments a JOIN recruitment_cycle_rounds t ON t.round_id=a.round_id''')
    # Session dates must agree across BOTH the binding and every segment Round.
    op.execute('''INSERT INTO recruitment_legacy_cycle_evidence(source_kind,source_id,room_id,cycle_id,reason,evidence)
        SELECT 'session',s.id,s.room_id,
            CASE WHEN count(DISTINCT t.cycle_id)=1 AND bool_and(g.cycle_key=t.cycle_key)
                       AND count(seg.id)>0 AND count(t.round_id)=count(seg.id)
                 THEN (array_agg(t.cycle_id))[1] ELSE NULL END,
            'legacy_confirmation_not_reconstructed',jsonb_build_object('state',s.state)
        FROM recruitment_sessions s
        LEFT JOIN recruitment_session_bindings b ON b.session_id=s.id AND b.room_id=s.room_id
        LEFT JOIN recruitment_schedule_groups g ON g.id=b.group_id AND g.room_id=s.room_id
        LEFT JOIN recruitment_segments seg ON seg.session_id=s.id AND seg.room_id=s.room_id
        LEFT JOIN recruitment_cycle_rounds t ON t.round_id=seg.round_id AND t.room_id=s.room_id
        GROUP BY s.id''')
    # Compare JSON IDs as text, so malformed/foreign/missing IDs remain review.
    op.execute('''INSERT INTO recruitment_legacy_cycle_evidence(source_kind,source_id,room_id,cycle_id,reason,evidence)
        SELECT 'application',a.id,a.room_id,
            CASE WHEN jsonb_array_length(a.targets)>0 AND count(t.round_id)=jsonb_array_length(a.targets)
                       AND count(DISTINCT t.cycle_id)=1 THEN (array_agg(t.cycle_id))[1] ELSE NULL END,
            'legacy_target_generation_unknown',jsonb_build_object('state',a.state)
        FROM recruitment_applications a
        LEFT JOIN LATERAL jsonb_array_elements(a.targets) j ON true
        LEFT JOIN recruitment_cycle_rounds t ON t.round_id::text=j->>'round_id'
             AND t.item_id::text=j->>'item_id' AND t.room_id=a.room_id
        GROUP BY a.id''')
    # The old submission is membership-wide and has no proven submission cycle.
    op.execute('''INSERT INTO recruitment_legacy_cycle_evidence(source_kind,source_id,room_id,cycle_id,reason,evidence)
        SELECT 'submission',membership_id,room_id,NULL,'submission_cycle_unknown',
            jsonb_build_object('revision',revision,'source_personal_revision',source_personal_revision)
        FROM recruitment_availability_submissions''')
    op.execute('''INSERT INTO recruitment_legacy_cycle_evidence(source_kind,source_id,room_id,cycle_id,reason,evidence)
        SELECT 'choice',id,room_id,NULL,'choice_is_not_actual_participation',
            jsonb_build_object('target_cycle',target_cycle,'state',state)
        FROM recruitment_continuation_choices''')
    for kind, table in (('proposal', 'recruitment_schedule_proposals'), ('resume', 'recruitment_resume_proposals')):
        op.execute(f'''INSERT INTO recruitment_legacy_cycle_evidence(source_kind,source_id,room_id,cycle_id,reason,evidence)
            SELECT '{kind}',id,room_id,NULL,'proposal_target_generation_unknown',jsonb_build_object('state',state)
            FROM {table}''')
    # Only events with an existing, FK-proven cycle receive a shadow reference.
    op.execute('''INSERT INTO recruitment_cycle_openings
        (id,room_id,cycle_id,generation,item_id,legacy_event_id,command_id,mode,state,effective_at,evidence)
        SELECT e.id,e.room_id,c.id,NULL,e.item_id,e.id,NULL,'legacy_'||e.mode,
               'review_required',e.authorized_effective_at,
               jsonb_build_object('state',e.state,'settings_revision',e.settings_revision,'processed_at',e.processed_at)
        FROM recruitment_opening_events e JOIN recruitment_room_cycles c ON c.room_id=e.room_id AND c.cycle_key=e.target_cycle''')


def downgrade():
    raise RuntimeError('Preserve cycle, membership and source evidence; destructive downgrade unsupported')
