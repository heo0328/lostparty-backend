"""Exact copied ORM metadata for the disposable 0023 legacy baseline only."""


def legacy_metadata():
    from sqlalchemy import MetaData
    from sqlalchemy import UniqueConstraint
    from app.auth import models as auth_models
    from app.game_accounts.models import models as game_models
    from app.game_accounts.models import power_success
    from app.lostark_keys import models as key_models
    from app.member_settings import models as settings_models
    from app.raid_weekly import models as weekly_models
    from app.groups import models as group_models
    from app.groups import admission_models
    from app.member_limits import models as limit_models
    from app.ownership_disputes import models as ownership_models
    from app.raid_rooms.models import models as room_models
    from app.raid_rooms.models import integrated_models
    from app.raid_rooms.models import source_models
    from app.raid_rooms.models import weekly_links
    from app.raid_rooms.models import schedule_heads
    from app.raid_rooms.models import resume_models
    # This is the legacy 0023 runtime check. Collect only its model modules,
    # independent of which future cycle models API/test collection imports.
    modules = (auth_models, game_models, key_models, settings_models, weekly_models,
        group_models, admission_models, limit_models, ownership_models, room_models,
        integrated_models, source_models, weekly_links, schedule_heads, resume_models, power_success)
    tables = {value.__table__ for module in modules for value in vars(module).values()
              if isinstance(value, type) and value.__module__ == module.__name__ and hasattr(value, '__table__')}
    metadata = MetaData()
    for table in tables:
        table.to_metadata(metadata)
    # 0031 adds this partial index; legacy retains full-history uniqueness.
    assignments = metadata.tables['recruitment_assignments']
    for index in list(assignments.indexes):
        if index.name == 'uq_recruitment_current_assignment':
            assignments.indexes.remove(index)
    # 0031 replaces 0023's full-history constraint with the partial index above.
    # Restore that constraint only on the copied legacy metadata, never live models.
    assignments.append_constraint(UniqueConstraint('round_id', 'membership_id'))
    return metadata
