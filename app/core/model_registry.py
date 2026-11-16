"""Canonical model registry shared by migration and schema-consistency checks."""
from app.auth.models import Base
import app.game_accounts.models.provider_limits
import app.game_accounts.models.analysis
import app.game_accounts.models.models
import app.game_accounts.models.roster_presence
import app.raid_rooms.models.roster_participation
import app.member_settings.models
import app.raid_weekly.models
import app.raid_rooms.models.models
import app.raid_rooms.models.integrated_models
import app.raid_rooms.models.source_models
import app.raid_rooms.models.weekly_links
import app.raid_rooms.models.schedule_heads
import app.raid_rooms.models.resume_models
import app.raid_rooms.models.cycle_group_models
import app.raid_rooms.models.cycle_models
import app.raid_rooms.models.cycle_application_models
import app.raid_rooms.models.cycle_lifecycle_models
import app.raid_rooms.models.cycle_consent_models
import app.raid_rooms.models.cycle_planning_models
import app.raid_rooms.models.completion_correction_models
import app.raid_rooms.models.cycle_outcome_models
import app.raid_rooms.models.beta_models
import app.raid_rooms.models.membership_action_models
import app.groups.feature_models
import app.groups.models
import app.groups.admission_models
import app.member_limits.models
import app.ownership_disputes.models

metadata = Base.metadata
