"""Title remains common; no fabricated room-wide group state is exposed."""
from app.game_accounts.schemas import DTO
from app.raid_rooms import cycle_wire as wire


class TitleSettings(DTO):
    title: str


class TitleContextData(wire.CommonContextData):
    current_settings: TitleSettings


class TitleContext(wire.CommonContext):
    data: TitleContextData
