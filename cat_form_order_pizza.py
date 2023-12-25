from cat.mad_hatter.decorators import tool, hook
from pydantic import field_validator, Field
from cat.log import log
from typing import Dict
from .cform import CForm
import random


class PizzaOrder(CForm):
    pizza_type: str | None = None
    address:    str | None = None
    phone:      str | None = None

    '''
    pizza_type: str | None = Field(description="The type of pizza the user wants")
    address:    str | None = Field(description="The user's address where they want the pizza to be delivered")
    phone:      str | None = Field(description="The user's telephone number for any communications")
    '''
    
    def examples(self):
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
    def execute_action(self):
        pass
    '''

    @field_validator("pizza_type")
    @classmethod
    def validate_pizza_type(cls, pizza_type: str):
        log.info("VALIDATIONS")

        if pizza_type in [None, ""]:
            return

        pizza_types = list(menu)
        if pizza_type not in pizza_types:
            raise ValueError(f"{pizza_type} is not present in the menù")


# Execute action (called when the form is completed and confirmed)
@hook
def execute_action(model: PizzaOrder):
    result = "<h3>PIZZA CHALLENGE - ORDER COMPLETED<h3><br>" 
    result += "<table border=0>"
    result += "<tr>"
    result += "   <td>Pizza Type</td>"
    result += f"  <td>{model.pizza_type}</td>"
    result += "</tr>"
    result += "<tr>"
    result += "   <td>Address</td>"
    result += f"  <td>{model.address}</td>"
    result += "</tr>"
    result += "<tr>"
    result += "   <td>Phone Number</td>"
    result += f"  <td>{model.phone}</td>"
    result += "</tr>"
    result += "</table>"
    result += "<br>"                                                                                                     
    result += "Thanks for your order.. your pizza is on its way!"
    result += "<br><br>"
    result += f"<img style='width:400px' src='https://maxdam.github.io/cat-pizza-challenge/img/order/pizza{random.randint(0, 6)}.jpg'>"
    return result


# Order pizza start intent
@tool(return_direct=True)
def start_order_pizza_intent(input, cat):
    """I would like to order a pizza
    I'll take a Margherita pizza"""
    log.critical("INTENT ORDER PIZZA START")
    return PizzaOrder.start(cat)

 
# Order pizza stop intent
@tool
def stop_order_pizza_intent(input, cat):
    """I don't want to order pizza anymore, 
    I want to give up on the order, 
    go back to normal conversation"""
    log.critical("INTENT ORDER PIZZA STOP")
    return PizzaOrder.stop(cat)


# Order pizza handle conversation
@hook
def agent_fast_reply(fast_reply: Dict, cat) -> Dict:
    return PizzaOrder.dialogue(cat)


menu = [
    "Margherita",
    "Romana",
    "Quattro Formaggi",
    "Capricciosa",
    "Bufalina",
    "Diavola"
]

# Get pizza menu
@tool()
def ask_menu(input, cat):
    """What is on the menu?
    Which types of pizza do you have?"""

    log.critical("INTENT ORDER PIZZA MENU")
    # return menu
    response = "The available pizzas are the following:"
    for pizza in menu:
        response += f"\n - {pizza}"
    return response
