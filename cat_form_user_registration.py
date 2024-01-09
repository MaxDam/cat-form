from cat.mad_hatter.decorators import tool, hook
from cat.log import log
from typing import Dict
from .cform_v3 import CBaseModel
from pydantic import Field


class UserRegistration(CBaseModel):
    
    name:    str = Field(description="Name of the user who wants to register")
    surname: str = Field(description="Surname of the user who wants to register")
    company: str = Field(description="Company where the user who wants to register works")
    email:   str = Field(description="Email of the user who wants to register")

    def execute_action(self):
        result = "<h3>You have registered<h3><br>" 
        result += "<table border=0>"
        result += "<tr>"
        result += "   <td>Name</td>"
        result += f"  <td>{self.name}</td>"
        result += "</tr>"
        result += "<tr>"
        result += "   <td>Surname</td>"
        result += f"  <td>{self.surname}</td>"
        result += "</tr>"
        result += "<tr>"
        result += "   <td>Company</td>"
        result += f"  <td>{self.company}</td>"
        result += "</tr>"
        result += "<tr>"
        result += "   <td>Email</td>"
        result += f"  <td>{self.email}</td>"
        result += "</tr>"
        result += "</table>"
        return result


# Start intent
@tool(return_direct=True)
def start_register_intent(input, cat):
    """I would register the user for the service"""
    log.critical("INTENT USER REGISTRATION START")
    return UserRegistration.start(cat)


# Stop intent
@tool
def stop_register_intent(input, cat):
    """I don't want to continue this user registration"""
    log.critical("INTENT USER REGISTRATION STOP")
    return UserRegistration.stop(cat)


# User registration handle conversation
@hook
def agent_fast_reply(fast_reply: Dict, cat) -> Dict:
    return UserRegistration.dialogue_action(fast_reply, cat)

@hook
def agent_prompt_prefix(prefix, cat) -> str:
    return UserRegistration.dialogue_prefix(prefix, cat)
