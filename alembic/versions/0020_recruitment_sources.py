"""Additional recruitment sources and atomically retained P1 successful power.

Preserve existing tables, unknown application origins and nullable P1 heads.
No scheduling, reservations or personal settings are fabricated by migration.
"""
from datetime import datetime
import re
from alembic import op
from sqlalchemy import text

revision = '0020_recruitment_sources'
down_revision = '0019_integrated_recruitment'
branch_labels = None
depends_on = None

TABLES = ('recruitment_personal_availability', 'character_role_power_successes', 'recruitment_applications', 'recruitment_schedule_groups', 'recruitment_settings', 'recruitment_availability_submissions', 'recruitment_continuation_choices', 'recruitment_item_settings', 'recruitment_opening_events', 'recruitment_participations', 'recruitment_schedule_proposals', 'recruitment_session_bindings', 'recruitment_proposal_responses', 'recruitment_proposal_targets', 'recruitment_schedule_alternatives', 'recruitment_reservations', 'recruitment_segment_duration_evidence')

DDL = (
    """CREATE TABLE recruitment_personal_availability (
	user_id UUID NOT NULL,
	revision INTEGER NOT NULL,
	timezone VARCHAR(16) NOT NULL,
	intervals JSONB NOT NULL,
	normalized_intervals JSONB NOT NULL,
	saved_at TIMESTAMP WITH TIME ZONE NOT NULL,
	record_created_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp(),
	record_updated_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp(),
	PRIMARY KEY (user_id),
	CHECK (revision>=1 AND timezone='Asia/Seoul'),
	CHECK (jsonb_typeof(intervals)='array' AND jsonb_typeof(normalized_intervals)='array'),
	FOREIGN KEY(user_id) REFERENCES users (id)
)""",
    """CREATE TABLE character_role_power_successes (
	user_id UUID NOT NULL,
	character_id UUID NOT NULL,
	ownership_revision INTEGER NOT NULL,
	role VARCHAR(16) NOT NULL,
	power_revision INTEGER NOT NULL,
	combat_power VARCHAR(32) NOT NULL,
	observed_at TIMESTAMP WITH TIME ZONE NOT NULL,
	source_summary_version INTEGER NOT NULL,
	source_saved_at TIMESTAMP WITH TIME ZONE NOT NULL,
	source_summary JSONB NOT NULL,
	record_created_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp(),
	record_updated_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp(),
	PRIMARY KEY (user_id, character_id, ownership_revision, role),
	FOREIGN KEY(user_id, character_id, ownership_revision, role) REFERENCES character_role_summaries (user_id, character_id, ownership_revision, role) ON DELETE CASCADE,
	CHECK (ownership_revision>=1 AND power_revision>=2 AND source_summary_version>=1 AND role IN ('dealer','support')),
	CHECK (combat_power ~ '^[0-9]+([.][0-9]+)?$'),
	CHECK (jsonb_typeof(source_summary)='object')
)""",
    """CREATE TABLE recruitment_applications (
	id UUID NOT NULL,
	room_id UUID NOT NULL,
	user_id UUID NOT NULL,
	revision INTEGER NOT NULL,
	selection JSONB NOT NULL,
	targets JSONB NOT NULL,
	display JSONB NOT NULL,
	build JSONB,
	origin_state VARCHAR(16) NOT NULL,
	origin_scope VARCHAR(8),
	origin_group_id UUID,
	state VARCHAR(16) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
	ended_at TIMESTAMP WITH TIME ZONE,
	record_created_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp(),
	record_updated_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp(),
	PRIMARY KEY (id),
	CHECK (revision>=1 AND jsonb_typeof(targets)='array'),
	CHECK ((origin_state='known' AND origin_scope IS NOT NULL AND origin_scope IN ('public','group') AND (origin_scope<>'group' OR origin_group_id IS NOT NULL)) OR (origin_state='legacy_unknown' AND origin_scope IS NULL AND origin_group_id IS NULL)),
	CHECK (state IN ('pending','accepted','rejected','withdrawn','expired','cancelled') AND expires_at>created_at),
	CHECK ((state='pending' AND ended_at IS NULL) OR (state<>'pending' AND ended_at IS NOT NULL)),
	FOREIGN KEY(room_id) REFERENCES recruitment_rooms (id),
	FOREIGN KEY(user_id) REFERENCES users (id),
	FOREIGN KEY(origin_group_id) REFERENCES groups (id)
)""",
    """CREATE TABLE recruitment_schedule_groups (
	id UUID NOT NULL,
	room_id UUID NOT NULL,
	cycle_key DATE NOT NULL,
	client_key VARCHAR(64) NOT NULL,
	revision INTEGER NOT NULL,
	occurrence_mode VARCHAR(8) NOT NULL,
	planning_mode VARCHAR(16) NOT NULL,
	day_scope VARCHAR(24) NOT NULL,
	required BOOLEAN NOT NULL,
	auto_additional_members INTEGER,
	selected_session_id UUID,
	record_created_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp(),
	record_updated_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp(),
	PRIMARY KEY (id),
	UNIQUE (room_id, id),
	UNIQUE (room_id, cycle_key, client_key),
	CHECK (revision>=1 AND EXTRACT(DOW FROM cycle_key)=3),
	CHECK (occurrence_mode IN ('one_of','each') AND planning_mode IN ('unscheduled','manual','coordinated')),
	CHECK (day_scope IN ('selected_weekdays','any_current_cycle')),
	CHECK (day_scope<>'any_current_cycle' OR (planning_mode='coordinated' AND occurrence_mode='one_of')),
	CHECK ((planning_mode='coordinated' AND auto_additional_members IS NOT NULL AND auto_additional_members BETWEEN 1 AND 7) OR (planning_mode<>'coordinated' AND auto_additional_members IS NULL)),
	CHECK (occurrence_mode='one_of' OR selected_session_id IS NULL),
	FOREIGN KEY(room_id) REFERENCES recruitment_rooms (id)
)""",
    """CREATE TABLE recruitment_settings (
	room_id UUID NOT NULL,
	revision INTEGER NOT NULL,
	continuation_revision INTEGER NOT NULL,
	admission_mode VARCHAR(16) NOT NULL,
	experience_level VARCHAR(24),
	combat_input_mode VARCHAR(8) NOT NULL,
	dealer_min VARCHAR(32),
	support_min VARCHAR(32),
	continuation_enabled BOOLEAN DEFAULT false NOT NULL,
	auto_open_enabled BOOLEAN DEFAULT false NOT NULL,
	auto_open_effective_cycle DATE,
	record_created_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp(),
	record_updated_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp(),
	PRIMARY KEY (room_id),
	CHECK (revision>=1 AND continuation_revision>=1),
	CHECK (admission_mode IN ('leader_only','direct_join')),
	CHECK (experience_level IS NULL OR experience_level IN ('tryLevel','clearExp','multiClearExp','semiExperienced','experienced')),
	CHECK (combat_input_mode IN ('shared','per_role')),
	CHECK (dealer_min IS NULL OR dealer_min ~ '^[0-9]+([.][0-9]+)?$'),
	CHECK (support_min IS NULL OR support_min ~ '^[0-9]+([.][0-9]+)?$'),
	CHECK (combat_input_mode<>'shared' OR dealer_min IS NOT DISTINCT FROM support_min),
	CHECK (NOT auto_open_enabled OR (continuation_enabled AND auto_open_effective_cycle IS NOT NULL)),
	CHECK (auto_open_effective_cycle IS NULL OR EXTRACT(DOW FROM auto_open_effective_cycle)=3),
	FOREIGN KEY(room_id) REFERENCES recruitment_rooms (id)
)""",
    """CREATE TABLE recruitment_availability_submissions (
	membership_id UUID NOT NULL,
	room_id UUID NOT NULL,
	user_id UUID NOT NULL,
	revision INTEGER NOT NULL,
	source_personal_revision INTEGER NOT NULL,
	intervals JSONB NOT NULL,
	normalized_intervals JSONB NOT NULL,
	submitted_at TIMESTAMP WITH TIME ZONE NOT NULL,
	record_created_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp(),
	record_updated_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp(),
	PRIMARY KEY (membership_id),
	FOREIGN KEY(room_id, membership_id, user_id) REFERENCES recruitment_memberships (room_id, id, user_id),
	CHECK (revision>=1 AND source_personal_revision>=1),
	CHECK (jsonb_typeof(intervals)='array' AND jsonb_typeof(normalized_intervals)='array')
)""",
    """CREATE TABLE recruitment_continuation_choices (
	id UUID NOT NULL,
	room_id UUID NOT NULL,
	item_id UUID NOT NULL,
	membership_id UUID NOT NULL,
	user_id UUID NOT NULL,
	character_id UUID NOT NULL,
	raid_id VARCHAR(64) NOT NULL,
	selected_role VARCHAR(8) NOT NULL,
	ownership_revision INTEGER NOT NULL,
	target_cycle DATE NOT NULL,
	revision INTEGER NOT NULL,
	state VARCHAR(8) NOT NULL,
	blocked_reason VARCHAR(64),
	ended_at TIMESTAMP WITH TIME ZONE,
	record_created_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp(),
	record_updated_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp(),
	PRIMARY KEY (id),
	FOREIGN KEY(room_id, item_id, raid_id) REFERENCES recruitment_items (room_id, id, raid_id),
	FOREIGN KEY(room_id, membership_id, user_id) REFERENCES recruitment_memberships (room_id, id, user_id),
	CHECK (revision>=1 AND ownership_revision>=1 AND EXTRACT(DOW FROM target_cycle)=3 AND selected_role IN ('dealer','support')),
	CHECK ((state IN ('selected','blocked') AND ended_at IS NULL) OR (state IN ('released','replaced') AND ended_at IS NOT NULL)),
	CHECK ((state='blocked' AND blocked_reason IS NOT NULL) OR (state<>'blocked' AND blocked_reason IS NULL)),
	FOREIGN KEY(character_id) REFERENCES game_characters (id)
)""",
    """CREATE TABLE recruitment_item_settings (
	item_id UUID NOT NULL,
	room_id UUID NOT NULL,
	revision INTEGER NOT NULL,
	difficulty_id VARCHAR(64) NOT NULL,
	catalog_version VARCHAR(64) NOT NULL,
	duration_minutes INTEGER,
	duration_policy_version VARCHAR(64) NOT NULL,
	record_created_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp(),
	record_updated_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp(),
	PRIMARY KEY (item_id),
	FOREIGN KEY(room_id, item_id) REFERENCES recruitment_items (room_id, id),
	CHECK (revision>=1),
	CHECK (duration_minutes IS NULL OR (duration_minutes BETWEEN 10 AND 1440 AND mod(duration_minutes,5)=0))
)""",
    """CREATE TABLE recruitment_opening_events (
	id UUID NOT NULL,
	room_id UUID NOT NULL,
	item_id UUID NOT NULL,
	target_cycle DATE NOT NULL,
	mode VARCHAR(16) NOT NULL,
	settings_revision INTEGER NOT NULL,
	authorized_effective_at TIMESTAMP WITH TIME ZONE NOT NULL,
	search_floor_at TIMESTAMP WITH TIME ZONE NOT NULL,
	processed_at TIMESTAMP WITH TIME ZONE,
	state VARCHAR(16) NOT NULL,
	blocked_reason VARCHAR(64),
	record_created_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp(),
	record_updated_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp(),
	PRIMARY KEY (id),
	FOREIGN KEY(room_id, item_id) REFERENCES recruitment_items (room_id, id),
	UNIQUE (room_id, item_id, target_cycle, mode),
	CHECK (settings_revision>=1 AND EXTRACT(DOW FROM target_cycle)=3 AND mode IN ('scheduled_auto','manual')),
	CHECK (search_floor_at=authorized_effective_at+interval '30 minutes'),
	CHECK (mode<>'scheduled_auto' OR authorized_effective_at=((target_cycle+time '06:00') AT TIME ZONE 'Asia/Seoul')),
	CHECK (state IN ('scheduled','applied','blocked','cancelled') AND (state<>'applied' OR processed_at IS NOT NULL)),
	CHECK ((state='blocked' AND blocked_reason IS NOT NULL) OR (state<>'blocked' AND blocked_reason IS NULL))
)""",
    """CREATE TABLE recruitment_participations (
	id UUID NOT NULL,
	room_id UUID NOT NULL,
	session_id UUID NOT NULL,
	membership_id UUID NOT NULL,
	user_id UUID NOT NULL,
	revision INTEGER NOT NULL,
	state VARCHAR(8) NOT NULL,
	confirmation_state VARCHAR(24) NOT NULL,
	confirmed_schedule_revision INTEGER,
	confirmed_at TIMESTAMP WITH TIME ZONE,
	record_created_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp(),
	record_updated_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp(),
	PRIMARY KEY (id),
	UNIQUE (session_id, membership_id),
	UNIQUE (room_id, id, session_id, membership_id, user_id),
	FOREIGN KEY(room_id, session_id) REFERENCES recruitment_sessions (room_id, id),
	FOREIGN KEY(room_id, membership_id, user_id) REFERENCES recruitment_memberships (room_id, id, user_id),
	CHECK (revision>=1 AND state IN ('active','ended') AND confirmation_state IN ('not_required','confirmation_pending','confirmed')),
	CHECK ((confirmation_state='confirmed' AND confirmed_at IS NOT NULL AND confirmed_schedule_revision IS NOT NULL AND confirmed_schedule_revision>=1) OR (confirmation_state<>'confirmed' AND confirmed_at IS NULL AND confirmed_schedule_revision IS NULL))
)""",
    """CREATE TABLE recruitment_schedule_proposals (
	id UUID NOT NULL,
	room_id UUID NOT NULL,
	creator_membership_id UUID NOT NULL,
	revision INTEGER NOT NULL,
	proposal_plan_revision INTEGER NOT NULL,
	created_from_plan_revision INTEGER NOT NULL,
	state VARCHAR(16) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	record_created_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp(),
	record_updated_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp(),
	PRIMARY KEY (id),
	UNIQUE (room_id, id),
	FOREIGN KEY(room_id, creator_membership_id) REFERENCES recruitment_memberships (room_id, id),
	CHECK (revision>=1 AND proposal_plan_revision>=1 AND created_from_plan_revision>=1),
	CHECK (state IN ('pending','applied','cancelled','obsolete'))
)""",
    """CREATE TABLE recruitment_session_bindings (
	session_id UUID NOT NULL,
	room_id UUID NOT NULL,
	group_id UUID NOT NULL,
	required BOOLEAN NOT NULL,
	record_created_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp(),
	record_updated_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp(),
	PRIMARY KEY (session_id),
	UNIQUE (room_id, group_id, session_id),
	FOREIGN KEY(room_id, session_id) REFERENCES recruitment_sessions (room_id, id),
	FOREIGN KEY(room_id, group_id) REFERENCES recruitment_schedule_groups (room_id, id)
)""",
    """CREATE TABLE recruitment_proposal_responses (
	proposal_id UUID NOT NULL,
	membership_id UUID NOT NULL,
	membership_generation INTEGER NOT NULL,
	proposal_plan_revision INTEGER NOT NULL,
	room_id UUID NOT NULL,
	revision INTEGER NOT NULL,
	response VARCHAR(8) NOT NULL,
	responded_at TIMESTAMP WITH TIME ZONE,
	record_created_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp(),
	record_updated_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp(),
	PRIMARY KEY (proposal_id, membership_id, membership_generation, proposal_plan_revision),
	FOREIGN KEY(room_id, proposal_id) REFERENCES recruitment_schedule_proposals (room_id, id),
	FOREIGN KEY(room_id, membership_id) REFERENCES recruitment_memberships (room_id, id),
	CHECK (membership_generation>=1 AND proposal_plan_revision>=1 AND revision>=1),
	CHECK (response IN ('pending','accept','reject','left')),
	CHECK ((response='pending' AND responded_at IS NULL) OR (response IN ('accept','reject') AND responded_at IS NOT NULL) OR response='left')
)""",
    """CREATE TABLE recruitment_proposal_targets (
	proposal_id UUID NOT NULL,
	session_id UUID NOT NULL,
	room_id UUID NOT NULL,
	base_schedule_revision INTEGER NOT NULL,
	proposed_segments JSONB NOT NULL,
	record_created_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp(),
	record_updated_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp(),
	PRIMARY KEY (proposal_id, session_id),
	FOREIGN KEY(room_id, proposal_id) REFERENCES recruitment_schedule_proposals (room_id, id),
	FOREIGN KEY(room_id, session_id) REFERENCES recruitment_sessions (room_id, id),
	CHECK (base_schedule_revision>=1 AND jsonb_typeof(proposed_segments)='array')
)""",
    """CREATE TABLE recruitment_schedule_alternatives (
	id UUID NOT NULL,
	room_id UUID NOT NULL,
	group_id UUID NOT NULL,
	client_key VARCHAR(64) NOT NULL,
	weekday INTEGER NOT NULL,
	start_minute INTEGER,
	latest_start_minute INTEGER,
	item_order JSONB NOT NULL,
	session_id UUID,
	record_created_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp(),
	record_updated_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp(),
	PRIMARY KEY (id),
	UNIQUE (group_id, client_key),
	FOREIGN KEY(room_id, group_id) REFERENCES recruitment_schedule_groups (room_id, id),
	FOREIGN KEY(room_id, group_id, session_id) REFERENCES recruitment_session_bindings (room_id, group_id, session_id),
	CHECK (weekday BETWEEN 1 AND 7),
	CHECK (start_minute IS NULL OR (start_minute BETWEEN 0 AND 1439 AND mod(start_minute,5)=0)),
	CHECK (latest_start_minute IS NULL OR latest_start_minute BETWEEN 0 AND 1439),
	CHECK (jsonb_typeof(item_order)='array')
)""",
    """CREATE TABLE recruitment_reservations (
	id UUID NOT NULL,
	room_id UUID NOT NULL,
	participation_id UUID NOT NULL,
	session_id UUID NOT NULL,
	membership_id UUID NOT NULL,
	user_id UUID NOT NULL,
	assignment_id UUID NOT NULL,
	item_id UUID NOT NULL,
	round_id UUID NOT NULL,
	segment_id UUID NOT NULL,
	schedule_revision INTEGER NOT NULL,
	starts_at TIMESTAMP WITH TIME ZONE NOT NULL,
	ends_at TIMESTAMP WITH TIME ZONE NOT NULL,
	released_at TIMESTAMP WITH TIME ZONE,
	released_reason VARCHAR(32),
	record_created_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp(),
	record_updated_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp(),
	PRIMARY KEY (id),
	UNIQUE (participation_id, segment_id, schedule_revision),
	FOREIGN KEY(room_id, participation_id, session_id, membership_id, user_id) REFERENCES recruitment_participations (room_id, id, session_id, membership_id, user_id),
	FOREIGN KEY(room_id, assignment_id, membership_id, user_id, item_id, round_id) REFERENCES recruitment_assignments (room_id, id, membership_id, user_id, item_id, round_id),
	FOREIGN KEY(room_id, segment_id, session_id, item_id, round_id) REFERENCES recruitment_segments (room_id, id, session_id, item_id, round_id),
	CHECK (schedule_revision>=1 AND starts_at<ends_at AND ends_at-starts_at<=interval '24 hours'),
	CHECK ((released_at IS NULL AND released_reason IS NULL) OR (released_at IS NOT NULL AND released_reason IS NOT NULL))
)""",
    """CREATE TABLE recruitment_segment_duration_evidence (
	segment_id UUID NOT NULL,
	room_id UUID NOT NULL,
	session_id UUID NOT NULL,
	item_id UUID NOT NULL,
	round_id UUID NOT NULL,
	item_settings_revision INTEGER NOT NULL,
	duration_policy_version VARCHAR(64) NOT NULL,
	record_created_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp(),
	record_updated_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp(),
	PRIMARY KEY (segment_id),
	FOREIGN KEY(room_id, segment_id, session_id, item_id, round_id) REFERENCES recruitment_segments (room_id, id, session_id, item_id, round_id),
	CHECK (item_settings_revision>=1)
)""",
    """CREATE UNIQUE INDEX uq_recruitment_pending_application ON recruitment_applications (room_id, user_id) WHERE state='pending'""",
    """CREATE UNIQUE INDEX uq_recruitment_current_choice ON recruitment_continuation_choices (user_id, character_id, raid_id, target_cycle) WHERE ended_at IS NULL""",
    """CREATE UNIQUE INDEX uq_recruitment_room_item_choice ON recruitment_continuation_choices (room_id, user_id, item_id, target_cycle) WHERE ended_at IS NULL""",
    """CREATE UNIQUE INDEX uq_recruitment_applied_opening ON recruitment_opening_events (room_id, item_id, target_cycle) WHERE state='applied'""",
    """CREATE INDEX ix_recruitment_user_active_reservations ON recruitment_reservations (user_id, starts_at) WHERE released_at IS NULL""",
    """CREATE UNIQUE INDEX uq_recruitment_active_participation_segment ON recruitment_reservations (participation_id, segment_id) WHERE released_at IS NULL""",
    """ALTER TABLE recruitment_schedule_groups ADD CONSTRAINT fk_schedule_group_selected_session FOREIGN KEY(room_id, id, selected_session_id) REFERENCES recruitment_session_bindings (room_id, group_id, session_id) DEFERRABLE INITIALLY DEFERRED""",
)


def upgrade():
    # Ownership aliases let new compound FKs bind a reservation to the exact
    # segment, assignment and member without changing any legacy source rows.
    op.create_unique_constraint('uq_assignment_reservation_owner', 'recruitment_assignments',
        ['room_id','id','membership_id','user_id','item_id','round_id'])
    op.create_unique_constraint('uq_segment_reservation_owner', 'recruitment_segments',
        ['room_id','id','session_id','item_id','round_id'])
    op.create_unique_constraint('uq_item_choice_raid', 'recruitment_items', ['room_id','id','raid_id'])
    for statement in DDL:
        op.execute(statement)
    for name in TABLES:
        if name != 'recruitment_applications':
            _timestamp_trigger(name)
    op.execute("""
        INSERT INTO recruitment_settings
        (room_id,revision,continuation_revision,admission_mode,experience_level,
         combat_input_mode,dealer_min,support_min,continuation_enabled,auto_open_enabled)
        SELECT n.id,1,1,o.admission_mode,NULL,'shared',NULL,NULL,false,false
        FROM recruitment_rooms n JOIN raid_rooms o ON n.id=o.id
    """)
    # No per-application origin was recorded by F1: do not infer a public
    # exception from the room's current or creation visibility.
    op.execute("""
        INSERT INTO recruitment_applications
        (id,room_id,user_id,revision,selection,targets,display,build,
         origin_state,origin_scope,origin_group_id,state,created_at,expires_at,
         ended_at,record_created_at,record_updated_at)
        SELECT a.id,a.room_id,a.user_id,a.revision,a.selection,
               jsonb_build_array(jsonb_build_object('item_id',q.item_id,
                   'round_id',a.round_id,'party_no',a.selection->'party_no')),
               a.display,a.build,'legacy_unknown',NULL,NULL,a.state,
               a.created_at,a.expires_at,a.ended_at,a.record_created_at,a.record_updated_at
        FROM raid_room_applications a JOIN recruitment_rounds q
        ON q.room_id=a.room_id AND q.id=a.round_id
    """)
    _backfill_power()
    _protect_history()
    _timestamp_trigger('recruitment_applications')


def _timestamp_trigger(name):
    op.execute(f'CREATE TRIGGER record_timestamps_before_write BEFORE INSERT OR UPDATE ON {name} '
               'FOR EACH ROW EXECUTE FUNCTION maintain_record_timestamps()')


def _utc(value):
    if not isinstance(value, str) or not re.fullmatch(
            r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?(?:Z|\+00:00)', value):
        raise ValueError('Unproven legacy timestamp')
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def _valid_success(payload):
    """Frozen P1 v1 validation. Invalid/null history is not a successful value."""
    keys = {'source','analysis_rules_version','analyzed_at','combat_power','item_level',
            'combat_power_observed_at','item_level_observed_at','integrity_status',
            'catalog_version','issues','observed_lifecycle_revision'}
    if not isinstance(payload, dict) or set(payload) != keys:
        return False
    try:
        if payload['source'] != 'flutter_analysis':
            return False
        for key in ('analysis_rules_version','catalog_version'):
            value = payload[key]
            if value is None and key == 'catalog_version':
                continue
            if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9._-]{1,64}',value):
                return False
        _utc(payload['analyzed_at'])
        for key in ('combat_power','item_level'):
            value, observed = payload[key], payload[key+'_observed_at']
            if value is None and observed is None:
                continue
            if not isinstance(value,str) or not re.fullmatch(r'[0-9]+(?:\.[0-9]+)?',value) or len(value)>32:
                return False
            _utc(observed)
        version=payload['observed_lifecycle_revision']
        if type(version) is not int or not 1<=version<=2147483647:
            return False
        issues=payload['issues']
        if not isinstance(issues,list) or len(issues)>20:
            return False
        pairs=[]
        for issue in issues:
            if not isinstance(issue,dict) or set(issue)!={'code','severity'}:
                return False
            if not isinstance(issue['code'],str) or not re.fullmatch(r'[A-Z0-9_]{1,64}',issue['code']):
                return False
            if issue['severity'] not in ('warning','error'):
                return False
            pairs.append((issue['code'],issue['severity']))
        if len(set(pairs))!=len(pairs):
            return False
        status=payload['integrity_status']; errors=any(severity=='error' for _,severity in pairs)
        if status not in ('clean','review','error','unavailable'):
            return False
        if ((status=='clean' and issues) or (status=='review' and (not issues or errors))
                or (status=='error' and not errors) or (status=='unavailable' and errors)):
            return False
        return payload['combat_power'] is not None
    except (ValueError,TypeError,OverflowError):
        return False


def _backfill_power():
    db=op.get_bind()
    rows=db.execute(text('''SELECT user_id,character_id,ownership_revision,role,
                                  version,saved_at,summary FROM character_role_summaries'''))
    # Existing head is the only proven snapshot. Never reconstruct an absent
    # older success, borrow another role, or inspect historical maximum values.
    while batch:=rows.fetchmany(200):
        for row in batch:
            if not _valid_success(row.summary):
                continue
            import json
            db.execute(text('''INSERT INTO character_role_power_successes
                (user_id,character_id,ownership_revision,role,power_revision,
                 combat_power,observed_at,source_summary_version,source_saved_at,source_summary)
                VALUES (:u,:c,:o,:role,2,:power,:observed,:version,:saved,CAST(:summary AS jsonb))'''),
                dict(u=row.user_id,c=row.character_id,o=row.ownership_revision,role=row.role,
                     power=row.summary['combat_power'],observed=_utc(row.summary['combat_power_observed_at']),
                     version=row.version,saved=row.saved_at,summary=json.dumps(row.summary)))


def downgrade():
    raise RuntimeError('Preserve recruitment and power success history; use a forward correction')


def _protect_history():
    op.execute("""
        CREATE FUNCTION protect_recruitment_opening() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF (NEW.id,NEW.room_id,NEW.item_id,NEW.target_cycle,NEW.mode,
                NEW.settings_revision,NEW.authorized_effective_at,NEW.search_floor_at)
                IS DISTINCT FROM
               (OLD.id,OLD.room_id,OLD.item_id,OLD.target_cycle,OLD.mode,
                OLD.settings_revision,OLD.authorized_effective_at,OLD.search_floor_at) THEN
                RAISE EXCEPTION 'Opening event authority is immutable' USING ERRCODE='23514';
            END IF;
            RETURN NEW;
        END; $$
    """)
    op.execute('CREATE TRIGGER protect_opening_before_update BEFORE UPDATE ON recruitment_opening_events '
               'FOR EACH ROW EXECUTE FUNCTION protect_recruitment_opening()')
    op.execute("""
        CREATE FUNCTION protect_role_power_success() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF (to_jsonb(NEW)-'record_created_at'-'record_updated_at') IS NOT DISTINCT FROM
               (to_jsonb(OLD)-'record_created_at'-'record_updated_at') THEN
                RETURN NEW;
            END IF;
            IF (NEW.user_id,NEW.character_id,NEW.ownership_revision,NEW.role) IS DISTINCT FROM
               (OLD.user_id,OLD.character_id,OLD.ownership_revision,OLD.role)
               OR NEW.power_revision<>OLD.power_revision+1
               OR (NEW.observed_at,NEW.source_summary_version)<=(OLD.observed_at,OLD.source_summary_version) THEN
                RAISE EXCEPTION 'Power success must advance observation/version atomically' USING ERRCODE='23514';
            END IF;
            RETURN NEW;
        END; $$
    """)
    op.execute('CREATE TRIGGER protect_power_before_update BEFORE UPDATE ON character_role_power_successes '
               'FOR EACH ROW EXECUTE FUNCTION protect_role_power_success()')
