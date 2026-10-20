"""R1 additive source model; legacy candidates and application DB stay untouched.

DDL is frozen here rather than importing evolving application model definitions.
Legacy schedules are evidence requiring review, never implicit reservations.
"""
from alembic import op

revision = '0019_integrated_recruitment'
down_revision = '0018_room_application_build'
branch_labels = None
depends_on = None

DDL = (
    """CREATE TABLE recruitment_rooms (
	id UUID NOT NULL,
	leader_membership_id UUID NOT NULL,
	title VARCHAR(60) NOT NULL,
	scope VARCHAR(8) NOT NULL,
	group_id UUID,
	app_capacity INTEGER NOT NULL,
	revision INTEGER NOT NULL,
	members_revision INTEGER NOT NULL,
	plan_revision INTEGER NOT NULL,
	migration_state VARCHAR(24) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	ended_at TIMESTAMP WITH TIME ZONE,
	record_created_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp(),
	record_updated_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp(),
	PRIMARY KEY (id),
	CHECK (scope IN ('public','group') AND (scope<>'group' OR group_id IS NOT NULL)),
	CHECK (char_length(title) BETWEEN 1 AND 60),
	CHECK (app_capacity IN (4,8) AND revision>=1 AND members_revision>=1 AND plan_revision>=1),
	CHECK (migration_state IN ('ready','legacy_review_required')),
	FOREIGN KEY(group_id) REFERENCES groups (id)
)""",
    """CREATE TABLE recruitment_items (
	id UUID NOT NULL,
	room_id UUID NOT NULL,
	raid_id VARCHAR(64) NOT NULL,
	revision INTEGER NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	record_created_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp(),
	record_updated_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp(),
	PRIMARY KEY (id),
	UNIQUE (room_id, id),
	UNIQUE (room_id, raid_id),
	CHECK (revision>=1),
	FOREIGN KEY(room_id) REFERENCES recruitment_rooms (id)
)""",
    """CREATE TABLE recruitment_memberships (
	id UUID NOT NULL,
	room_id UUID NOT NULL,
	user_id UUID NOT NULL,
	revision INTEGER NOT NULL,
	joined_at TIMESTAMP WITH TIME ZONE NOT NULL,
	ended_at TIMESTAMP WITH TIME ZONE,
	record_created_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp(),
	record_updated_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp(),
	PRIMARY KEY (id),
	UNIQUE (room_id, id),
	UNIQUE (room_id, id, user_id),
	CHECK (revision>=1),
	FOREIGN KEY(room_id) REFERENCES recruitment_rooms (id),
	FOREIGN KEY(user_id) REFERENCES users (id)
)""",
    """CREATE TABLE recruitment_sessions (
	id UUID NOT NULL,
	room_id UUID NOT NULL,
	revision INTEGER NOT NULL,
	schedule_revision INTEGER NOT NULL,
	state VARCHAR(24) NOT NULL,
	starts_at TIMESTAMP WITH TIME ZONE,
	ends_at TIMESTAMP WITH TIME ZONE,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	record_created_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp(),
	record_updated_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp(),
	PRIMARY KEY (id),
	UNIQUE (room_id, id),
	CHECK (revision>=1 AND schedule_revision>=1),
	CHECK (state IN ('unconfirmed','confirmed','finished','cancelled','legacy_review_required')),
	CHECK ((starts_at IS NULL AND ends_at IS NULL) OR (starts_at IS NOT NULL AND ends_at IS NOT NULL AND starts_at<ends_at)),
	CHECK (state<>'confirmed' OR (starts_at IS NOT NULL AND ends_at IS NOT NULL AND ends_at-starts_at<=interval '24 hours')),
	FOREIGN KEY(room_id) REFERENCES recruitment_rooms (id)
)""",
    """CREATE TABLE recruitment_rounds (
	id UUID NOT NULL,
	room_id UUID NOT NULL,
	item_id UUID NOT NULL,
	cycle_key DATE NOT NULL,
	difficulty_id VARCHAR(64) NOT NULL,
	catalog_version VARCHAR(64) NOT NULL,
	game_party_size INTEGER NOT NULL,
	revision INTEGER NOT NULL,
	state VARCHAR(24) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	ended_at TIMESTAMP WITH TIME ZONE,
	record_created_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp(),
	record_updated_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp(),
	PRIMARY KEY (id),
	UNIQUE (room_id, item_id, id),
	FOREIGN KEY(room_id, item_id) REFERENCES recruitment_items (room_id, id),
	CHECK (EXTRACT(DOW FROM cycle_key)=3 AND game_party_size IN (4,8) AND revision>=1),
	CHECK (state IN ('active','completed','stopped_incomplete','legacy_ended'))
)""",
    """CREATE TABLE recruitment_assignments (
	id UUID NOT NULL,
	room_id UUID NOT NULL,
	item_id UUID NOT NULL,
	round_id UUID NOT NULL,
	membership_id UUID NOT NULL,
	user_id UUID NOT NULL,
	character_id UUID NOT NULL,
	selected_role VARCHAR(8) NOT NULL,
	party_no INTEGER NOT NULL,
	slot_no INTEGER NOT NULL,
	ownership_revision INTEGER NOT NULL,
	lifecycle_revision INTEGER NOT NULL,
	display JSONB NOT NULL,
	build JSONB,
	revision INTEGER NOT NULL,
	state VARCHAR(24) NOT NULL,
	joined_at TIMESTAMP WITH TIME ZONE NOT NULL,
	ended_at TIMESTAMP WITH TIME ZONE,
	record_created_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp(),
	record_updated_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp(),
	PRIMARY KEY (id),
	UNIQUE (round_id, membership_id),
	FOREIGN KEY(room_id, item_id, round_id) REFERENCES recruitment_rounds (room_id, item_id, id),
	FOREIGN KEY(room_id, membership_id, user_id) REFERENCES recruitment_memberships (room_id, id, user_id),
	CHECK (selected_role IN ('dealer','support') AND party_no BETWEEN 1 AND 2 AND slot_no BETWEEN 1 AND 4),
	CHECK (revision>=1 AND ownership_revision>=1 AND lifecycle_revision>=1),
	CHECK ((state='active' AND ended_at IS NULL) OR (state IN ('completed','left','stopped_incomplete','legacy_ended') AND ended_at IS NOT NULL)),
	FOREIGN KEY(user_id) REFERENCES users (id),
	FOREIGN KEY(character_id) REFERENCES game_characters (id)
)""",
    """CREATE TABLE recruitment_segments (
	id UUID NOT NULL,
	room_id UUID NOT NULL,
	session_id UUID NOT NULL,
	item_id UUID NOT NULL,
	round_id UUID NOT NULL,
	ordinal INTEGER NOT NULL,
	duration_minutes INTEGER,
	duration_source VARCHAR(24) NOT NULL,
	starts_at TIMESTAMP WITH TIME ZONE,
	ends_at TIMESTAMP WITH TIME ZONE,
	record_created_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp(),
	record_updated_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp(),
	PRIMARY KEY (id),
	UNIQUE (session_id, ordinal),
	UNIQUE (session_id, item_id),
	FOREIGN KEY(room_id, session_id) REFERENCES recruitment_sessions (room_id, id),
	FOREIGN KEY(room_id, item_id, round_id) REFERENCES recruitment_rounds (room_id, item_id, id),
	CHECK (ordinal>=1),
	CHECK (duration_source IN ('explicit','difficulty_default','legacy_review_required')),
	CHECK ((duration_minutes IS NOT NULL AND duration_minutes BETWEEN 10 AND 1440 AND mod(duration_minutes,5)=0) OR (duration_minutes IS NULL AND duration_source='legacy_review_required')),
	CHECK ((starts_at IS NULL AND ends_at IS NULL) OR (starts_at IS NOT NULL AND ends_at IS NOT NULL AND starts_at<ends_at)),
	CHECK (duration_minutes IS NULL OR starts_at IS NULL OR ends_at-starts_at=duration_minutes*interval '1 minute')
)""",
    """CREATE UNIQUE INDEX uq_recruitment_current_user ON recruitment_memberships (room_id, user_id) WHERE ended_at IS NULL""",
    """CREATE UNIQUE INDEX uq_recruitment_active_slot ON recruitment_assignments (round_id, party_no, slot_no) WHERE state='active'""",
    """ALTER TABLE recruitment_rooms ADD CONSTRAINT fk_recruitment_leader FOREIGN KEY(id, leader_membership_id) REFERENCES recruitment_memberships (room_id, id) DEFERRABLE INITIALLY DEFERRED""",
)


def upgrade():
    for statement in DDL:
        op.execute(statement)
    _import_legacy()
    for name in ('recruitment_rooms', 'recruitment_items', 'recruitment_rounds',
                 'recruitment_memberships', 'recruitment_assignments',
                 'recruitment_sessions', 'recruitment_segments'):
        op.execute(f'CREATE TRIGGER record_timestamps_before_write BEFORE INSERT OR UPDATE ON {name} '
                   'FOR EACH ROW EXECUTE FUNCTION maintain_record_timestamps()')


def _import_legacy():
    # The transaction and deferred leader FK preserve complete room ownership.
    # IDs of rooms/rounds/memberships are retained; new item IDs are deterministic.
    op.execute("""
        INSERT INTO recruitment_rooms
        (id,leader_membership_id,title,scope,group_id,app_capacity,revision,
         members_revision,plan_revision,migration_state,created_at,ended_at,
         record_created_at,record_updated_at)
        SELECT r.id,r.leader_membership_id,r.title,r.scope,r.group_id,q.party_count*4,
               r.revision,r.members_revision,1,'legacy_review_required',r.created_at,r.ended_at,
               r.record_created_at,r.record_updated_at
        FROM raid_rooms r JOIN raid_room_rounds q ON q.room_id=r.id AND q.id=r.round_id
    """)
    op.execute("""
        INSERT INTO recruitment_items
        (id,room_id,raid_id,revision,created_at,record_created_at,record_updated_at)
        SELECT md5(room_id::text || ':' || raid_id)::uuid,room_id,raid_id,1,
               min(created_at),min(record_created_at),max(record_updated_at)
        FROM raid_room_rounds GROUP BY room_id,raid_id
    """)
    op.execute("""
        INSERT INTO recruitment_rounds
        (id,room_id,item_id,cycle_key,difficulty_id,catalog_version,game_party_size,
         revision,state,created_at,ended_at,record_created_at,record_updated_at)
        SELECT id,room_id,md5(room_id::text || ':' || raid_id)::uuid,cycle_key,
               difficulty_id,catalog_version,party_count*4,revision,
               CASE WHEN ended_at IS NULL THEN 'active' ELSE 'legacy_ended' END,
               created_at,ended_at,record_created_at,record_updated_at
        FROM raid_room_rounds
    """)
    op.execute("""
        INSERT INTO recruitment_memberships
        (id,room_id,user_id,revision,joined_at,ended_at,record_created_at,record_updated_at)
        SELECT id,room_id,user_id,revision,joined_at,ended_at,record_created_at,record_updated_at
        FROM raid_room_memberships
    """)
    op.execute("""
        INSERT INTO recruitment_assignments
        (id,room_id,item_id,round_id,membership_id,user_id,character_id,selected_role,
         party_no,slot_no,ownership_revision,lifecycle_revision,display,build,revision,state,
         joined_at,ended_at,record_created_at,record_updated_at)
        SELECT m.id,m.room_id,q.item_id,m.round_id,m.id,m.user_id,m.character_id,
               m.selected_role,m.party_no,m.slot_no,m.ownership_revision,m.lifecycle_revision,m.display,m.build,
               m.revision,CASE WHEN m.ended_at IS NULL THEN 'active' ELSE 'legacy_ended' END,
               m.joined_at,m.ended_at,m.record_created_at,m.record_updated_at
        FROM raid_room_memberships m JOIN recruitment_rounds q
        ON q.room_id=m.room_id AND q.id=m.round_id
    """)
    op.execute("""
        INSERT INTO recruitment_sessions
        (id,room_id,revision,schedule_revision,state,starts_at,ends_at,created_at,
         record_created_at,record_updated_at)
        SELECT id,room_id,1,1,'legacy_review_required',starts_at,ends_at,created_at,
               record_created_at,record_updated_at FROM raid_room_rounds
    """)
    op.execute("""
        INSERT INTO recruitment_segments
        (id,room_id,session_id,item_id,round_id,ordinal,duration_minutes,duration_source,
         starts_at,ends_at,record_created_at,record_updated_at)
        SELECT q.id,q.room_id,q.id,md5(q.room_id::text || ':' || q.raid_id)::uuid,q.id,1,
               CASE WHEN d.minutes BETWEEN 10 AND 1440 AND mod(d.minutes,5)=0
                    THEN d.minutes::integer ELSE NULL END,
               CASE WHEN d.minutes BETWEEN 10 AND 1440 AND mod(d.minutes,5)=0
                    THEN 'explicit' ELSE 'legacy_review_required' END,
               q.starts_at,q.ends_at,q.record_created_at,q.record_updated_at
        FROM raid_room_rounds q
        CROSS JOIN LATERAL (SELECT extract(epoch FROM q.ends_at-q.starts_at)/60 AS minutes) d
    """)
    # No existing WeeklyState, application snapshot or idempotency result is changed.


def downgrade():
    raise RuntimeError('Preserve integrated recruitment history; use a forward correction')
