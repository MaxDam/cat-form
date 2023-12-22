from pydantic import BaseModel, Field
from cat.mad_hatter.decorators import plugin

class MySettings(BaseModel):
    ask_confirm: bool = Field(
        title="ask confirm",
        default=True
    )

@plugin
def settings_schema():
    return MySettings.schema()
