from pydantic import BaseModel, Field
from cat.mad_hatter.decorators import plugin
from enum import Enum

class JsonExtractorType(Enum):
    a: str  = 'langchain'
    b: str  = 'kor'
    c: str  = 'guardrails'
    d: str  = 'from examples'
    
class MySettings(BaseModel):
    json_extractor: JsonExtractorType = Field(
        title="json extractor",
        default="guardrails"
    )
    strict: bool = Field(
        title="strict",
        default=False
    )
    ask_confirm: bool = Field(
        title="ask confirm",
        default=True
    )
    use_rag_confirm: bool = Field(
        title="use rag for confirm",
        default=False
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
    auto_handle_conversation: bool = Field(
        title="auto handle conversation",
        default=True
    )
    
@plugin
def settings_schema():
    return MySettings.schema()
