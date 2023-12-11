from cat.mad_hatter.decorators import tool, hook, plugin
from pydantic import BaseModel, Field, ValidationError, field_validator
from datetime import datetime, date
from cat.log import log
import enum
from typing import Dict, Optional
from .cform import CForm, CFormState
import random

# TODO
class MySettings(BaseModel):
    required_int: int
    optional_int: int = 69
    required_str: str
    optional_str: str = "meow"
    required_date: date
    optional_date: date = 1679616000

@plugin
def settings_schema():   
    return MySettings.schema()


@hook(priority=1)
def agent_fast_reply(fast_reply: Dict, cat) -> Dict:
    try:
        model = cat.mad_hatter.execute_hook("cform_set_model", None, cat=cat)
        key = model.__class__.__name__
        if key not in cat.working_memory.keys():
            # If the key is not present -> initialize CForm and save it in working memory
            cform = CForm(model=model, cat=cat, key=key)
            cat.working_memory[key] = cform
        else:
            # If the key is present and form is active -> execute dialog exchange
            cform = cat.working_memory[key]
            if cform.is_active():
                response = cform.execute_dialogue()
                return { "output": response }
    except Exception as e:
        pass

    return fast_reply
