import app.lostark_keys.models
from alembic import context
from app.auth.models import Base
import app.game_accounts.models
import app.member_settings.models
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
