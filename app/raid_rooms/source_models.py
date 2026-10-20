"""R1-B persistence only. No router, worker, reservation or default GET writes."""
from sqlalchemy import (Boolean, CheckConstraint, Date, ForeignKey, ForeignKeyConstraint,
                        Index, Integer, String, UniqueConstraint, UUID, text)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import mapped_column
from app.auth.models import Base, pk, stamp


class RoomSettings(Base):
    __tablename__ = 'recruitment_settings'
    room_id = mapped_column(ForeignKey('recruitment_rooms.id'), primary_key=True)
    revision = mapped_column(Integer, nullable=False)
    continuation_revision = mapped_column(Integer, nullable=False)
    admission_mode = mapped_column(String(16), nullable=False)
    experience_level = mapped_column(String(24), nullable=True)
    combat_input_mode = mapped_column(String(8), nullable=False)
    dealer_min = mapped_column(String(32), nullable=True)
    support_min = mapped_column(String(32), nullable=True)
    continuation_enabled = mapped_column(Boolean, nullable=False, server_default=text('false'))
    auto_open_enabled = mapped_column(Boolean, nullable=False, server_default=text('false'))
    auto_open_effective_cycle = mapped_column(Date, nullable=True)
    __table_args__ = (
        CheckConstraint('revision>=1 AND continuation_revision>=1'),
        CheckConstraint("admission_mode IN ('leader_only','direct_join')"),
        CheckConstraint("experience_level IS NULL OR experience_level IN ('tryLevel','clearExp','multiClearExp','semiExperienced','experienced')"),
        CheckConstraint("combat_input_mode IN ('shared','per_role')"),
        CheckConstraint("dealer_min IS NULL OR dealer_min ~ '^[0-9]+([.][0-9]+)?$'"),
        CheckConstraint("support_min IS NULL OR support_min ~ '^[0-9]+([.][0-9]+)?$'"),
        CheckConstraint("combat_input_mode<>'shared' OR dealer_min IS NOT DISTINCT FROM support_min"),
        CheckConstraint('NOT auto_open_enabled OR (continuation_enabled AND auto_open_effective_cycle IS NOT NULL)'),
        CheckConstraint('auto_open_effective_cycle IS NULL OR EXTRACT(DOW FROM auto_open_effective_cycle)=3'),
    )


class ScheduleGroup(Base):
    __tablename__ = 'recruitment_schedule_groups'
    id = pk()
    room_id = mapped_column(ForeignKey('recruitment_rooms.id'), nullable=False)
    cycle_key = mapped_column(Date, nullable=False)
    client_key = mapped_column(String(64), nullable=False)
    revision = mapped_column(Integer, nullable=False)
    occurrence_mode = mapped_column(String(8), nullable=False)
    planning_mode = mapped_column(String(16), nullable=False)
    day_scope = mapped_column(String(24), nullable=False)
    required = mapped_column(Boolean, nullable=False)
    auto_additional_members = mapped_column(Integer, nullable=True)
    selected_session_id = mapped_column(UUID, nullable=True)
    __table_args__ = (
        UniqueConstraint('room_id', 'id'), UniqueConstraint('room_id', 'cycle_key', 'client_key'),
        CheckConstraint('revision>=1 AND EXTRACT(DOW FROM cycle_key)=3'),
        CheckConstraint("occurrence_mode IN ('one_of','each') AND planning_mode IN ('unscheduled','manual','coordinated')"),
        CheckConstraint("day_scope IN ('selected_weekdays','any_current_cycle')"),
        CheckConstraint("day_scope<>'any_current_cycle' OR (planning_mode='coordinated' AND occurrence_mode='one_of')"),
        CheckConstraint("(planning_mode='coordinated' AND auto_additional_members IS NOT NULL AND auto_additional_members BETWEEN 1 AND 7) OR (planning_mode<>'coordinated' AND auto_additional_members IS NULL)"),
        CheckConstraint("occurrence_mode='one_of' OR selected_session_id IS NULL"),
        ForeignKeyConstraint(['room_id', 'id', 'selected_session_id'],
                             ['recruitment_session_bindings.room_id', 'recruitment_session_bindings.group_id', 'recruitment_session_bindings.session_id'],
                             name='fk_schedule_group_selected_session', use_alter=True,
                             deferrable=True, initially='DEFERRED'),
    )


class SessionBinding(Base):
    __tablename__ = 'recruitment_session_bindings'
    session_id = mapped_column(UUID, primary_key=True)
    room_id = mapped_column(UUID, nullable=False)
    group_id = mapped_column(UUID, nullable=False)
    required = mapped_column(Boolean, nullable=False)
    __table_args__ = (
        UniqueConstraint('room_id', 'group_id', 'session_id'),
        ForeignKeyConstraint(['room_id', 'session_id'], ['recruitment_sessions.room_id', 'recruitment_sessions.id']),
        ForeignKeyConstraint(['room_id', 'group_id'], ['recruitment_schedule_groups.room_id', 'recruitment_schedule_groups.id']),
    )


class ScheduleAlternative(Base):
    __tablename__ = 'recruitment_schedule_alternatives'
    id = pk()
    room_id = mapped_column(UUID, nullable=False)
    group_id = mapped_column(UUID, nullable=False)
    client_key = mapped_column(String(64), nullable=False)
    weekday = mapped_column(Integer, nullable=False)
    start_minute = mapped_column(Integer, nullable=True)
    latest_start_minute = mapped_column(Integer, nullable=True)
    item_order = mapped_column(JSONB, nullable=False)
    session_id = mapped_column(UUID, nullable=True)
    __table_args__ = (
        UniqueConstraint('group_id', 'client_key'),
        ForeignKeyConstraint(['room_id', 'group_id'], ['recruitment_schedule_groups.room_id', 'recruitment_schedule_groups.id']),
        ForeignKeyConstraint(['room_id', 'group_id', 'session_id'], ['recruitment_session_bindings.room_id', 'recruitment_session_bindings.group_id', 'recruitment_session_bindings.session_id']),
        CheckConstraint('weekday BETWEEN 1 AND 7'),
        CheckConstraint('start_minute IS NULL OR (start_minute BETWEEN 0 AND 1439 AND mod(start_minute,5)=0)'),
        CheckConstraint('latest_start_minute IS NULL OR latest_start_minute BETWEEN 0 AND 1439'),
        CheckConstraint("jsonb_typeof(item_order)='array'"),
    )


class PersonalAvailability(Base):
    __tablename__ = 'recruitment_personal_availability'
    user_id = mapped_column(ForeignKey('users.id'), primary_key=True)
    revision = mapped_column(Integer, nullable=False)
    timezone = mapped_column(String(16), nullable=False)
    intervals = mapped_column(JSONB, nullable=False)
    normalized_intervals = mapped_column(JSONB, nullable=False)
    saved_at = stamp()
    __table_args__ = (CheckConstraint("revision>=1 AND timezone='Asia/Seoul'"),
                     CheckConstraint("jsonb_typeof(intervals)='array' AND jsonb_typeof(normalized_intervals)='array'"))


class AvailabilitySubmission(Base):
    __tablename__ = 'recruitment_availability_submissions'
    membership_id = mapped_column(UUID, primary_key=True)
    room_id = mapped_column(UUID, nullable=False)
    user_id = mapped_column(UUID, nullable=False)
    revision = mapped_column(Integer, nullable=False)
    source_personal_revision = mapped_column(Integer, nullable=False)
    intervals = mapped_column(JSONB, nullable=False)
    normalized_intervals = mapped_column(JSONB, nullable=False)
    submitted_at = stamp()
    __table_args__ = (
        ForeignKeyConstraint(['room_id', 'membership_id', 'user_id'], ['recruitment_memberships.room_id', 'recruitment_memberships.id', 'recruitment_memberships.user_id']),
        CheckConstraint('revision>=1 AND source_personal_revision>=1'),
        CheckConstraint("jsonb_typeof(intervals)='array' AND jsonb_typeof(normalized_intervals)='array'"),
    )


class SessionParticipation(Base):
    __tablename__ = 'recruitment_participations'
    id = pk()
    room_id = mapped_column(UUID, nullable=False)
    session_id = mapped_column(UUID, nullable=False)
    membership_id = mapped_column(UUID, nullable=False)
    user_id = mapped_column(UUID, nullable=False)
    revision = mapped_column(Integer, nullable=False)
    state = mapped_column(String(8), nullable=False)
    confirmation_state = mapped_column(String(24), nullable=False)
    confirmed_schedule_revision = mapped_column(Integer, nullable=True)
    confirmed_at = stamp(nullable=True)
    __table_args__ = (
        UniqueConstraint('session_id', 'membership_id'),
        UniqueConstraint('room_id', 'id', 'session_id', 'membership_id', 'user_id'),
        ForeignKeyConstraint(['room_id', 'session_id'], ['recruitment_sessions.room_id', 'recruitment_sessions.id']),
        ForeignKeyConstraint(['room_id', 'membership_id', 'user_id'], ['recruitment_memberships.room_id', 'recruitment_memberships.id', 'recruitment_memberships.user_id']),
        CheckConstraint("revision>=1 AND state IN ('active','ended') AND confirmation_state IN ('not_required','confirmation_pending','confirmed')"),
        CheckConstraint("(confirmation_state='confirmed' AND confirmed_at IS NOT NULL AND confirmed_schedule_revision IS NOT NULL AND confirmed_schedule_revision>=1) OR (confirmation_state<>'confirmed' AND confirmed_at IS NULL AND confirmed_schedule_revision IS NULL)"),
    )


class TimeReservation(Base):
    __tablename__ = 'recruitment_reservations'
    id = pk()
    room_id = mapped_column(UUID, nullable=False)
    participation_id = mapped_column(UUID, nullable=False)
    session_id = mapped_column(UUID, nullable=False)
    membership_id = mapped_column(UUID, nullable=False)
    user_id = mapped_column(UUID, nullable=False)
    assignment_id = mapped_column(UUID, nullable=False)
    item_id = mapped_column(UUID, nullable=False)
    round_id = mapped_column(UUID, nullable=False)
    segment_id = mapped_column(UUID, nullable=False)
    schedule_revision = mapped_column(Integer, nullable=False)
    starts_at = stamp()
    ends_at = stamp()
    released_at = stamp(nullable=True)
    released_reason = mapped_column(String(32), nullable=True)
    __table_args__ = (
        UniqueConstraint('participation_id', 'segment_id', 'schedule_revision'),
        ForeignKeyConstraint(['room_id', 'participation_id', 'session_id', 'membership_id', 'user_id'], ['recruitment_participations.room_id', 'recruitment_participations.id', 'recruitment_participations.session_id', 'recruitment_participations.membership_id', 'recruitment_participations.user_id']),
        ForeignKeyConstraint(['room_id', 'assignment_id', 'membership_id', 'user_id', 'item_id', 'round_id'], ['recruitment_assignments.room_id', 'recruitment_assignments.id', 'recruitment_assignments.membership_id', 'recruitment_assignments.user_id', 'recruitment_assignments.item_id', 'recruitment_assignments.round_id']),
        ForeignKeyConstraint(['room_id', 'segment_id', 'session_id', 'item_id', 'round_id'], ['recruitment_segments.room_id', 'recruitment_segments.id', 'recruitment_segments.session_id', 'recruitment_segments.item_id', 'recruitment_segments.round_id']),
        CheckConstraint("schedule_revision>=1 AND starts_at<ends_at AND ends_at-starts_at<=interval '24 hours'"),
        CheckConstraint('(released_at IS NULL AND released_reason IS NULL) OR (released_at IS NOT NULL AND released_reason IS NOT NULL)'),
        Index('ix_recruitment_user_active_reservations', 'user_id', 'starts_at', postgresql_where=text('released_at IS NULL')),
        Index('uq_recruitment_active_participation_segment', 'participation_id', 'segment_id', unique=True, postgresql_where=text('released_at IS NULL')),
    )


class ScheduleProposal(Base):
    __tablename__ = 'recruitment_schedule_proposals'
    id = pk()
    room_id = mapped_column(UUID, nullable=False)
    creator_membership_id = mapped_column(UUID, nullable=False)
    revision = mapped_column(Integer, nullable=False)
    proposal_plan_revision = mapped_column(Integer, nullable=False)
    created_from_plan_revision = mapped_column(Integer, nullable=False)
    state = mapped_column(String(16), nullable=False)
    created_at = stamp()
    __table_args__ = (
        UniqueConstraint('room_id', 'id'),
        ForeignKeyConstraint(['room_id', 'creator_membership_id'], ['recruitment_memberships.room_id', 'recruitment_memberships.id']),
        CheckConstraint('revision>=1 AND proposal_plan_revision>=1 AND created_from_plan_revision>=1'),
        CheckConstraint("state IN ('pending','applied','cancelled','obsolete')"),
    )


class ProposalTarget(Base):
    __tablename__ = 'recruitment_proposal_targets'
    proposal_id = mapped_column(UUID, primary_key=True)
    session_id = mapped_column(UUID, primary_key=True)
    room_id = mapped_column(UUID, nullable=False)
    base_schedule_revision = mapped_column(Integer, nullable=False)
    proposed_segments = mapped_column(JSONB, nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(['room_id', 'proposal_id'], ['recruitment_schedule_proposals.room_id', 'recruitment_schedule_proposals.id']),
        ForeignKeyConstraint(['room_id', 'session_id'], ['recruitment_sessions.room_id', 'recruitment_sessions.id']),
        CheckConstraint("base_schedule_revision>=1 AND jsonb_typeof(proposed_segments)='array'"),
    )


class ProposalResponse(Base):
    __tablename__ = 'recruitment_proposal_responses'
    proposal_id = mapped_column(UUID, primary_key=True)
    membership_id = mapped_column(UUID, primary_key=True)
    membership_generation = mapped_column(Integer, primary_key=True)
    proposal_plan_revision = mapped_column(Integer, primary_key=True)
    room_id = mapped_column(UUID, nullable=False)
    revision = mapped_column(Integer, nullable=False)
    response = mapped_column(String(8), nullable=False)
    responded_at = stamp(nullable=True)
    __table_args__ = (
        ForeignKeyConstraint(['room_id', 'proposal_id'], ['recruitment_schedule_proposals.room_id', 'recruitment_schedule_proposals.id']),
        ForeignKeyConstraint(['room_id', 'membership_id'], ['recruitment_memberships.room_id', 'recruitment_memberships.id']),
        CheckConstraint('membership_generation>=1 AND proposal_plan_revision>=1 AND revision>=1'),
        CheckConstraint("response IN ('pending','accept','reject','left')"),
        CheckConstraint("(response='pending' AND responded_at IS NULL) OR (response IN ('accept','reject') AND responded_at IS NOT NULL) OR response='left'"),
    )


class ContinuationChoice(Base):
    __tablename__ = 'recruitment_continuation_choices'
    id = pk()
    room_id = mapped_column(UUID, nullable=False)
    item_id = mapped_column(UUID, nullable=False)
    membership_id = mapped_column(UUID, nullable=False)
    user_id = mapped_column(UUID, nullable=False)
    character_id = mapped_column(ForeignKey('game_characters.id'), nullable=False)
    raid_id = mapped_column(String(64), nullable=False)
    selected_role = mapped_column(String(8), nullable=False)
    ownership_revision = mapped_column(Integer, nullable=False)
    target_cycle = mapped_column(Date, nullable=False)
    revision = mapped_column(Integer, nullable=False)
    state = mapped_column(String(8), nullable=False)
    blocked_reason = mapped_column(String(64), nullable=True)
    ended_at = stamp(nullable=True)
    __table_args__ = (
        ForeignKeyConstraint(['room_id', 'item_id', 'raid_id'], ['recruitment_items.room_id', 'recruitment_items.id', 'recruitment_items.raid_id']),
        ForeignKeyConstraint(['room_id', 'membership_id', 'user_id'], ['recruitment_memberships.room_id', 'recruitment_memberships.id', 'recruitment_memberships.user_id']),
        CheckConstraint("revision>=1 AND ownership_revision>=1 AND EXTRACT(DOW FROM target_cycle)=3 AND selected_role IN ('dealer','support')"),
        CheckConstraint("(state IN ('selected','blocked') AND ended_at IS NULL) OR (state IN ('released','replaced') AND ended_at IS NOT NULL)"),
        CheckConstraint("(state='blocked' AND blocked_reason IS NOT NULL) OR (state<>'blocked' AND blocked_reason IS NULL)"),
        Index('uq_recruitment_current_choice', 'user_id', 'character_id', 'raid_id', 'target_cycle', unique=True, postgresql_where=text('ended_at IS NULL')),
        Index('uq_recruitment_room_item_choice', 'room_id', 'user_id', 'item_id', 'target_cycle', unique=True, postgresql_where=text('ended_at IS NULL')),
    )


class OpeningEvent(Base):
    __tablename__ = 'recruitment_opening_events'
    id = pk()
    room_id = mapped_column(UUID, nullable=False)
    item_id = mapped_column(UUID, nullable=False)
    target_cycle = mapped_column(Date, nullable=False)
    mode = mapped_column(String(16), nullable=False)
    settings_revision = mapped_column(Integer, nullable=False)
    authorized_effective_at = stamp()
    search_floor_at = stamp()
    processed_at = stamp(nullable=True)
    state = mapped_column(String(16), nullable=False)
    blocked_reason = mapped_column(String(64), nullable=True)
    __table_args__ = (
        ForeignKeyConstraint(['room_id', 'item_id'], ['recruitment_items.room_id', 'recruitment_items.id']),
        UniqueConstraint('room_id', 'item_id', 'target_cycle', 'mode'),
        CheckConstraint("settings_revision>=1 AND EXTRACT(DOW FROM target_cycle)=3 AND mode IN ('scheduled_auto','manual')"),
        CheckConstraint("search_floor_at=authorized_effective_at+interval '30 minutes'"),
        CheckConstraint("mode<>'scheduled_auto' OR authorized_effective_at=((target_cycle+time '06:00') AT TIME ZONE 'Asia/Seoul')"),
        CheckConstraint("state IN ('scheduled','applied','blocked','cancelled') AND (state<>'applied' OR processed_at IS NOT NULL)"),
        CheckConstraint("(state='blocked' AND blocked_reason IS NOT NULL) OR (state<>'blocked' AND blocked_reason IS NULL)"),
        Index('uq_recruitment_applied_opening', 'room_id', 'item_id', 'target_cycle', unique=True, postgresql_where=text("state='applied'")),
    )


class RecruitmentApplication(Base):
    __tablename__ = 'recruitment_applications'
    id = pk()
    room_id = mapped_column(ForeignKey('recruitment_rooms.id'), nullable=False)
    user_id = mapped_column(ForeignKey('users.id'), nullable=False)
    revision = mapped_column(Integer, nullable=False)
    selection = mapped_column(JSONB, nullable=False)
    targets = mapped_column(JSONB, nullable=False)
    display = mapped_column(JSONB, nullable=False)
    build = mapped_column(JSONB(none_as_null=True), nullable=True)
    origin_state = mapped_column(String(16), nullable=False)
    origin_scope = mapped_column(String(8), nullable=True)
    origin_group_id = mapped_column(ForeignKey('groups.id'), nullable=True)
    state = mapped_column(String(16), nullable=False)
    created_at = stamp()
    expires_at = stamp()
    ended_at = stamp(nullable=True)
    __table_args__ = (
        CheckConstraint("revision>=1 AND jsonb_typeof(targets)='array'"),
        CheckConstraint("(origin_state='known' AND origin_scope IS NOT NULL AND origin_scope IN ('public','group') AND (origin_scope<>'group' OR origin_group_id IS NOT NULL)) OR (origin_state='legacy_unknown' AND origin_scope IS NULL AND origin_group_id IS NULL)"),
        CheckConstraint("state IN ('pending','accepted','rejected','withdrawn','expired','cancelled') AND expires_at>created_at"),
        CheckConstraint("(state='pending' AND ended_at IS NULL) OR (state<>'pending' AND ended_at IS NOT NULL)"),
        Index('uq_recruitment_pending_application', 'room_id', 'user_id', unique=True, postgresql_where=text("state='pending'")),
    )


class ItemSettings(Base):
    __tablename__ = 'recruitment_item_settings'
    item_id = mapped_column(UUID, primary_key=True)
    room_id = mapped_column(UUID, nullable=False)
    revision = mapped_column(Integer, nullable=False)
    difficulty_id = mapped_column(String(64), nullable=False)
    catalog_version = mapped_column(String(64), nullable=False)
    duration_minutes = mapped_column(Integer, nullable=True)
    duration_policy_version = mapped_column(String(64), nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(['room_id', 'item_id'], ['recruitment_items.room_id', 'recruitment_items.id']),
        CheckConstraint('revision>=1'),
        CheckConstraint('duration_minutes IS NULL OR (duration_minutes BETWEEN 10 AND 1440 AND mod(duration_minutes,5)=0)'),
    )


class SegmentDurationEvidence(Base):
    __tablename__ = 'recruitment_segment_duration_evidence'
    segment_id = mapped_column(UUID, primary_key=True)
    room_id = mapped_column(UUID, nullable=False)
    session_id = mapped_column(UUID, nullable=False)
    item_id = mapped_column(UUID, nullable=False)
    round_id = mapped_column(UUID, nullable=False)
    item_settings_revision = mapped_column(Integer, nullable=False)
    duration_policy_version = mapped_column(String(64), nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(['room_id', 'segment_id', 'session_id', 'item_id', 'round_id'],
                             ['recruitment_segments.room_id', 'recruitment_segments.id', 'recruitment_segments.session_id',
                              'recruitment_segments.item_id', 'recruitment_segments.round_id']),
        CheckConstraint('item_settings_revision>=1'),
    )


SOURCE_MODELS = (RoomSettings, ScheduleGroup, SessionBinding, ScheduleAlternative,
                 PersonalAvailability, AvailabilitySubmission, SessionParticipation,
                 TimeReservation, ScheduleProposal, ProposalTarget, ProposalResponse,
                 ContinuationChoice, OpeningEvent, RecruitmentApplication, ItemSettings, SegmentDurationEvidence)
