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

# Hook for execute final action
@hook
def cform_execute_action(cform, cat):
    result = "<h3>ORDER COMPLETED<h3><br>" 
    result += "<p>"
    result += f"Pizza type: {cform.model.pizza_type}<br>"
    result += f"Address: {cform.model.address}<br>"
    result += f"Phone number: {cform.model.phone}"
    result += "</p>"
    return result


# Order pizza start intent
@tool(return_direct=True)
def start_order_pizza_intent(details, cat):
    '''I would like to order a pizza
    I'll take a pizza'''

    log.critical("INTENT ORDER PIZZA START")
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

    log.critical("INTENT ORDER PIZZA STOP")     
    if "PizzaOrder" in cat.working_memory.keys():
        cform = cat.working_memory["PizzaOrder"]
        cform.stop_conversation()    
    return

# Hook user interactions
@hook
def agent_fast_reply(fast_reply: Dict, cat) -> Dict:

    if "PizzaOrder" in cat.working_memory.keys():
        cform = cat.working_memory["PizzaOrder"]
        if cform.isActive():
            response = cform.execute_dialogue()
            return { "output": response }
            
    return fast_reply
