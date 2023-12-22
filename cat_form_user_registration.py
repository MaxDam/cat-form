from cat.mad_hatter.decorators import tool, hook
from cat.log import log
from typing import Dict
from .cform import CForm

# CForm class
class UserRegistration(CForm):
    name:    str | None = None
    surname: str | None = None
    company: str | None = None
    email:   str | None = None

    # User registration get examples
    def get_prompt_examples(self):
        return [
            {
                "sentence": "Hello, I would register me for this service",
                "json": [None, None, None, None],
                "updatedJson": [None, None, None, None]
            },
            {
                "sentence": "Hello, my surname is Smith",
                "json": ["John", None, None, None],
                "updatedJson": ["John", "Smith", None, None]
            }
        ]
    
    # User registration set language
    def get_language(self):
        return "Italian"

    # User registration pizza execute action
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
    """I would register me for this service"""
    log.critical("INTENT USER REGISTRATION START")
    return UserRegistration.start(cat)


# Stop intent
@tool()
def stop_register_intent(input, cat):
    """I don't want to continue this registration"""
    log.critical("INTENT USER REGISTRATION STOP")
    return UserRegistration.stop(cat)    


# Order pizza handle conversation
@hook()
def agent_fast_reply(fast_reply: Dict, cat) -> Dict:
    return UserRegistration.dialogue(cat)
