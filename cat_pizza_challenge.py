from cat.mad_hatter.decorators import hook, tool
from pydantic import BaseModel, Field, ValidationError, field_validator
import enum
from typing import Dict, Optional
from cat.log import log
from .conversational_form import ConversationalForm, CFormState
import random

KEY = "pizza_challenge"

language = "Italian"

menu = {
    "Margherita": "Pomodoro, mozzarella fresca, basilico.",
    "Peperoni": "Pomodoro, mozzarella, peperoni.",
    "Romana": "Pomodoro, mozzarella, prosciutto.",
    "Quattro Formaggi": "Gorgonzola, mozzarella, parmigiano, taleggio.",
    "Capricciosa": "Pomodoro, mozzarella, prosciutto, funghi, carciofi, olive.",
    "Vegetariana": "Pomodoro, mozzarella, peperoni, cipolla, olive, melanzane.",
    "Bufalina": "Pomodoro, mozzarella di bufala, pomodorini, basilico.",
    "Diavola": "Pomodoro, mozzarella, salame piccante, peperoncino.",
    "Pescatora": "Pomodoro, mozzarella, frutti di mare (cozze, vongole, gamberi).",
    "Rucola": "Pomodoro, mozzarella, prosciutto crudo, rucola, scaglie di parmigiano."
}


# Pizza order object (from scratch implementation)
class PizzaOrder(BaseModel):

    pizza_type: str | None = None
    address: str | None = None
    phone: str | None = None
    
    @field_validator("pizza_type")
    @classmethod
    def validate_pizza_type(cls, pizza_type: str):
        log.info("VALIDATIONS")

        if pizza_type in [None, ""]:
            return

        pizza_types = list(menu.keys())

        if pizza_type not in pizza_types:
            raise ValueError(f"{pizza_type} is not present in the menù")

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


'''
# Pizza order object (for kor implementation)
class PizzaOrder(BaseModel):

    pizza_type: str = Field(
        default=None,
        description="This is the type of pizza.",
        examples=[
            ("I would like a Margherita", "Margherita"),
            ("I like Capricciosa", "Capricciosa")
        ],
    )
    address: str = Field(
        default=None,
        description="This is the address.",
        examples=[
            ("My address is via Pia 22", "via Pia 22"),
            ("I live in Via Roma 1", "Via Roma 1")
        ],
    )
    phone: str = Field(
        default=None,
        description="This is the telephone number.",
        examples=[
            ("My telephon number is 333123123", "333123123"),
            ("the number is 3493366443", "3493366443")
        ],
    )
'''    


# Get pizza menu
@tool()
def ask_menu(input, cat):
    '''What is on the menu?
    Which types of pizza do you have?
    Can I see the pizza menu?
    I want a menu'''

    log.critical("INTENT ORDER PIZZA MENU")
    # if the intent is active..
    if KEY in cat.working_memory.keys():
        # return menu
        response = "The available pizzas are the following:"
        for pizza, ingredients in menu.items():
            response += f"\n - {pizza} with the following ingredients: {ingredients}"
        return response

    return input


# Order pizza start intent
@tool(return_direct=True)
def start_order_pizza_intent(details, cat):
    '''I would like to order a pizza
    I'll take a pizza'''

    log.critical("INTENT ORDER PIZZA START")

    if KEY in cat.working_memory.keys():
        del cat.working_memory[KEY]

    # create a new conversational form, and save it in working memory
    cform = ConversationalForm(model=PizzaOrder(), cat=cat)
    #cform = ConversationalForm(model=PizzaOrder(pizza_type='', address='', phone=''), cat=cat)
    cat.working_memory[KEY] = cform

    # Execute the dialogue and return the response
    response = execute_dialogue(cform, cat)
    return response


# Acquires user information through a dialogue with the user
@hook
def agent_fast_reply(fast_reply: Dict, cat) -> Dict:

    # if the intent is active..
    if KEY in cat.working_memory.keys():        
        log.critical("INTENT ORDER PIZZA ACTIVE")
        cform = cat.working_memory[KEY]

        # Execute the dialogue and return the response
        response = execute_dialogue(cform, cat)
        return { "output": response }
        
    return fast_reply


# Execute the dialogue
def execute_dialogue(cform, cat):
    try:
        # update form from user response
        model_is_updated = cform.update_from_user_response()
        
        # if the form was updated, save it in working memory
        if model_is_updated:
            cat.working_memory[KEY] = cform

    except ValidationError as e:
        # If there was a validation problem, return the error message
        message = e.errors()[0]["msg"]
        response = cat.llm(message)
        return response

    log.warning(f"state:{cform.state}, is completed:{cform.is_completed()}")

    # Checks whether it should execute the action
    if cform.state == CFormState.ASK_SUMMARY:
        if cform.check_confirm():
            response = execute_action(cform)
            del cat.working_memory[KEY]
            return response
    
    # Checks whether the form is completed
    if cform.state == CFormState.ASK_INFORMATIONS and cform.is_completed():
        response = cform.show_summary(cat)
        return response

    # If the form is not completed, ask for missing information
    response = cform.ask_missing_information()
    return response


# Order pizza stop intent
@tool()
def stop_order_pizza_intent(input, cat):
    '''I don't want to order pizza anymore, 
    I want to give up on the order, 
    go back to normal conversation'''

    log.critical("INTENT ORDER PIZZA STOP")
        
    # if the key exists delete it
    if KEY in cat.working_memory.keys():
        del cat.working_memory[KEY]
    
    return input


# Hook the main prompt prefix
@hook()
def agent_prompt_prefix(prefix, cat) -> str:
    # if the intent is active change prompt prefix
    if KEY in cat.working_memory.keys():
        prefix = """you have to behave like a professional waiter taking orders for a pizzeria, 
        always you have to appear cordial but friendly, 
        you must use informal language with the customer;
        translating everything in {language} language.
        """
    return prefix


# Complete the action
def execute_action(cform):
    x = random.randint(0, 6)
    
    # Crea il nome del file con il formato "pizzaX.jpg"
    filename = f'pizza{x}.jpg'
    result = "<h3>PIZZA CHALLENGE - ORDER COMPLETED<h3><br>" 
    result += "<table border=0>"
    result += "<tr>"
    result += "   <td>Pizza Type</td>"
    result += f"  <td>{cform.model.pizza_type}</td>"
    result += "</tr>"
    result += "<tr>"
    result += "   <td>Address</td>"
    result += f"  <td>{cform.model.address}</td>"
    result += "</tr>"
    result += "<tr>"
    result += "   <td>Phone Number</td>"
    result += f"  <td>{cform.model.phone}</td>"
    result += "</tr>"
    result += "</table>"
    result += "<br>"                                                                                                     
    result += "Thanks for your order.. your pizza is on its way!"
    result += "<br><br>"
    result += f"<img style='width:400px' src='https://maxdam.github.io/cat-pizza-challenge/img/order/pizza{random.randint(0, 6)}.jpg'>"
    return result
