import app.lostark_keys.models
from alembic import context
from app.auth.models import Base
import app.game_accounts.models
import app.member_settings.models
import app.raid_weekly.models
import app.raid_rooms.models
import app.raid_rooms.integrated_models
import app.raid_rooms.source_models
import app.raid_rooms.weekly_links
import app.raid_rooms.schedule_heads
import app.raid_rooms.resume_models
import app.raid_rooms.cycle_models
import app.raid_rooms.cycle_application_models
import app.raid_rooms.cycle_lifecycle_models
import app.raid_rooms.cycle_consent_models
import app.raid_rooms.cycle_planning_models
import app.raid_rooms.cycle_outcome_models
import app.raid_rooms.beta_models
import app.raid_rooms.membership_action_models
import app.game_accounts.power_success
import app.groups.models
import app.groups.admission_models
import app.member_limits.models
import app.ownership_disputes.models
from app.core.database import engine

if context.is_offline_mode():
    context.configure(dialect_name="postgresql", target_metadata=Base.metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    with engine().connect() as connection:
        context.configure(connection=connection, target_metadata=Base.metadata)
        with context.begin_transaction():
            context.run_migrations()
