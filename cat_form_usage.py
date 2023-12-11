from cat.mad_hatter.decorators import tool, hook, plugin
from pydantic import BaseModel, Field, ValidationError, field_validator
from cat.log import log
from typing import Dict

# Model
class PizzaOrder(BaseModel):
    pizza_type: str | None = None
    address: str | None = None
    phone: str | None = None
    
    @classmethod
    def get_prompt_examples(cls):
        return [
            {
                "sentence": "I want to order a pizza",
                "json": [None, None, None],
                "updatedJson": [None, None, None]
            },
            {
                "sentence": "I live in Via Roma 1",
                "json": ["Margherita", None, None],
                "updatedJson": ["Margherita", "Via Roma 1", None]
            }
        ]

# Hook set model  
@hook
def cform_set_model(model, cat):
    return PizzaOrder()

# Hook prompt swow summary
@hook
def cform_show_summary(prompt, cat):
    return prompt

# Hook prompt ask missing information
@hook
def cform_ask_missing_information(prompt, cat):
    return prompt

# Order pizza start intent
@tool(return_direct=True)
def start_order_pizza_intent(input, cat):
    '''I would like to order a pizza
    I'll take a pizza'''

    if "PizzaOrder" in cat.working_memory.keys():
        cform = cat.working_memory["PizzaOrder"]
        cform.start_conversation()
        return cform.execute_dialogue()
    
    return "I'm sorry but I can't order a pizza if you don't initialize my form model"

# Order pizza stop intent
@tool()
def stop_order_pizza_intent(input, cat):
    '''I don't want to order pizza anymore, 
    I want to give up on the order, 
    go back to normal conversation'''

    if "PizzaOrder" in cat.working_memory.keys():
        cform = cat.working_memory["PizzaOrder"]
        cform.stop_conversation()    
    return

# Hook for execute final action
@hook
def cform_execute_action(model, cat):
    result = "<h3>ORDER COMPLETED<h3><br>" 
    result += "<p>"
    result += f"Pizza type: {model.pizza_type}<br>"
    result += f"Address: {model.address}<br>"
    result += f"Phone number: {model.phone}"
    result += "</p>"
    return result
