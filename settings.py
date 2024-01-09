from pydantic import BaseModel, Field
from cat.mad_hatter.decorators import plugin

class MySettings(BaseModel):
    ask_confirm: bool = Field(
        title="ask confirm",
        default=True
    )
    auto_handle_conversation: bool = Field(
        title="auto handle conversation",
        default=True
    )

@plugin
def settings_schema():
    return MySettings.schema()
