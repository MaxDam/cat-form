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
    pizza_order_examples: str = Field(
        title="pizza order examples",
        default="[]",
        extra={"type": "TextArea"}
    )
    user_registration_examples: str = Field(
        title="user registration examples",
        default="[]",
        extra={"type": "TextArea"}
    )

@plugin
def settings_schema():
    return MySettings.schema()
