from cat.mad_hatter.decorators import tool, hook
from pydantic import field_validator, Field
from cat.log import log
from typing import Dict, List
from .cform_v3 import CBaseModel
import random


class PizzaOrder(CBaseModel):
    
    pizza_type: str = Field(
        #default = None,
        description = "The type of pizza",
        examples = [
            ("I would like a Capricciosa pizza,", "Capricciosa"),
            ("Margherita is my favorite", "Margherita")
        ])
    
    address: str = Field(
        #default = None,
        description = "The user's address",
        examples = [
            ("My address is via Libertà 21 in Rome,", "via Libertà 21, Rome"),
            ("I live in Corso Italia 34", "Corso Italia 34")
        ])
    
    phone: str = Field(
        #default = None,
        description = "The user's telephone number",
        examples = [
            ("033234534 ", "033234534"),
            ("my number is 08234453", "08234453"),
            ("For any communications 567493423", "567493423")
        ])

    '''
    @field_validator("pizza_type")
    @classmethod
    def validate_pizza_type(cls, pizza_type: str):
        log.critical(f"Validating pizza type: {pizza_type}")
        if pizza_type not in [None, ""] and pizza_type not in list(menu):
            raise ValueError(f"{pizza_type} is not present in the menù")

        return
    '''

    def execute_action(self):
        result = "<h3>PIZZA CHALLENGE - ORDER COMPLETED<h3><br>" 
        result += "<table border=0>"
        result += "<tr>"
        result += "   <td>Pizza Type</td>"
        result += f"  <td>{self.model.pizza_type}</td>"
        result += "</tr>"
        result += "<tr>"
        result += "   <td>Address</td>"
        result += f"  <td>{self.model.address}</td>"
        result += "</tr>"
        result += "<tr>"
        result += "   <td>Phone Number</td>"
        result += f"  <td>{self.model.phone}</td>"
        result += "</tr>"
        result += "</table>"
        result += "<br>"                                                                                                     
        result += "Thanks for your order.. your pizza is on its way!"
        result += "<br><br>"
        result += f"<img style='width:400px' src='https://maxdam.github.io/cat-pizza-challenge/img/order/pizza{random.randint(0, 6)}.jpg'>"
        return result

    def lookup_ask_menu(self):
        """
        What is on the menu?
        Which types of pizza do you have?
        Could you show me a menu?
        """

        log.critical("LOOKUP ASK MENU")
        return self.cat.llm(f"The available pizzas are the following: " + menu)


'''@hook
def execute_action(model: PizzaOrder):
    pass'''


# Order pizza start intent
@tool(return_direct=True)
def start_order_pizza_intent(input, cat):
    """I would like to order a pizza
    I'll take a Margherita pizza"""
    log.critical("INTENT ORDER PIZZA START")
    return PizzaOrder.start(cat)

 
'''# Order pizza stop intent
@tool
def stop_order_pizza_intent(input, cat):
    """I don't want to order pizza anymore, 
    I want to give up on the order, 
    go back to normal conversation"""
    log.critical("INTENT ORDER PIZZA STOP")
    return PizzaOrder.stop(cat)'''


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
