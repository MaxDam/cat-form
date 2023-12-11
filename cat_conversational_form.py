from cat.mad_hatter.decorators import tool, hook, plugin
from pydantic import BaseModel, Field, ValidationError, field_validator
from datetime import datetime, date
from cat.log import log
import enum
from typing import Dict, Optional
from .c_form import CForm, CFormState
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
            cform = CForm(model=model, cat=cat, key=key)
            cat.working_memory[cform.key] = cform
            #TODO: check if the model is changed, and in this case delete previous key and create a new CForm
    except Exception as e:
        log.debug(f"{e}")
        
    return fast_reply
