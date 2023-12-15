from cat.mad_hatter.decorators import tool, hook, plugin
from pydantic import BaseModel, Field
from cat.log import log
import enum
from typing import Dict
from .cform import CForm, CFormState

# TODO settings
class MySettings(BaseModel):
    ask_confirm: bool = Field(
        title="ask confirm",
        default=True
    )


@plugin
def settings_schema():   
    return MySettings.schema()


@hook(priority=1)
def agent_fast_reply(fast_reply: Dict, cat) -> Dict:
    try:
        # Acquire models from hook
        models = []
        models = cat.mad_hatter.execute_hook("cform_set_model", models, cat=cat)
        
        # for each model ..
        for model in models:
            try:
                # Gets the key based on the model class name
                key = model.__class__.__name__

                # If the key is not present -> initialize CForm and save it in working memory
                if key not in cat.working_memory.keys():
                    
                    # Create cform and put it into working memory
                    cform = CForm(model=model, cat=cat, key=key)
                    cat.working_memory[key] = cform
                    log.critical(f'> CONFIGURED FORM {key}')
                
                else: # If the key is present -> execute dialog exchange
                    
                    # Get cform from working memory
                    cform = cat.working_memory[key]
                    
                    # Execute dialog exchange
                    response = cform.execute_dialogue()
                    return { "output": response }
                    
                    '''
                    # Manipulate dialog prompt
                    cform.return_only_prompt = True
                    response = cform.execute_dialogue()
                    if cform.state == CFormState.EXECUTE_ACTION:
                        return { "output": response }
                    else:
                        cat.working_memory["user_message_json"]["text"] = response
                    '''

            except Exception as catsBreath:
                # Cat's breath, used to start the other tools
                pass

    except Exception as hookNotImplemented:
        # The hook has not been implemented in any other plugin
        pass

    return fast_reply
