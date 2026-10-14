from typing import Annotated
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt

Version = Annotated[StrictInt, Field(ge=1)]


class MemberSettingsOut(BaseModel):
    model_config = ConfigDict(extra='forbid')
    nice_group_auto_refresh_enabled: StrictBool
    version: Version


class MemberSettingsIn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    nice_group_auto_refresh_enabled: StrictBool
    expected_version: Version
