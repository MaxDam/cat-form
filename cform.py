import json
from cat.log import log
from pydantic import ValidationError
from cat.looking_glass.prompts import MAIN_PROMPT_PREFIX
from enum import Enum

# Conversational Form State
class CFormState(Enum):
    STOPPED             = 0     
    ASK_INFORMATIONS    = 1
    ASK_SUMMARY         = 2
    EXECUTE_ACTION      = 3


# Class Conversational Form
class CForm:

    def __init__(self, model, cat, key):
        self.state = CFormState.STOPPED
        self.model = model
        self.cat = cat
        self.key = key


    # Start conversation
    def start_conversation(self):
        self.state  = CFormState.ASK_INFORMATIONS
        self._set_active_form()
        return self.execute_dialogue()


    # Stop conversation
    def stop_conversation(self):
        self.state = CFormState.STOPPED
        
        # Delete form from working memory
        # del self.cat.working_memory[self.key]


    # Check if the dialog is active
    def is_active(self):
        is_active = True
        if self.state == CFormState.STOPPED:
            is_active = False
        return is_active
    

    # Check if the form is completed
    def is_completed(self):
        for k,v in self.model.model_dump().items():
            if v in [None, ""]:
                return False
        return True
    

    # Check that there is only one active form
    def _set_active_form(self):
        if "_active_cforms" not in self.cat.working_memory.keys():
            self.cat.working_memory["_active_cforms"] = []
        if self.key not in self.cat.working_memory["_active_cforms"]:
            self.cat.working_memory["_active_cforms"].append(self.key)
        for key in self.cat.working_memory["_active_cforms"]:
            if key != self.key:
                self.cat.working_memory["_active_cforms"].remove(key)
                if key in self.cat.working_memory.keys():
                    self.cat.working_memory[key].state = CFormState.STOPPED


    # Queries the llm asking for the missing fields of the form, without memory chain
    def ask_missing_information(self) -> str:
       
        # Gets the information it should ask the user based on the fields that are still empty
        ask_for = self._check_what_is_empty()

        # Get prompt
        prefix = self.cat.mad_hatter.execute_hook("agent_prompt_prefix", '', cat=self.cat)
        if hasattr(type(self.model), 'prompt_prefix'):
            prefix = type(self.model).prompt_prefix()

        # Get user message and chat history
        user_message = self.cat.working_memory["user_message_json"]["text"]
        chat_history = self.cat.agent_manager.agent_prompt_chat_history(
            self.cat.working_memory["history"]
        )
        
        ## Conversation until now:{chat_history}
        
        # Prompt
        prompt = f"""{prefix}
        Create a question for the user, 
        below are some things to ask the user in a conversational and confidential way.
        You should only ask one question at a time even if you don't get all the information
        don't ask how to list! Don't say hello to the user! Don't say hi.
        Explain that you need some information. If the ask_for list is empty, thank them and ask how you can help them.
        ### ask_for list: {ask_for}
        - Human: {user_message}
        - AI: """

        log.warning(f'MISSING INFORMATIONS: {ask_for}')
        response = self.cat.llm(prompt)

        return response 


    # Return list of empty form's fields
    def _check_what_is_empty(self):
        ask_for = []
        for field, value in self.model.model_dump().items():
            if value in [None, "", 0]:
                ask_for.append(f'{field}')
        return ask_for


    # Show summary of the form to the user
    def show_summary(self, cat):
        prefix = self.cat.mad_hatter.execute_hook("agent_prompt_prefix", MAIN_PROMPT_PREFIX, cat=self.cat)
        user_message = self.cat.working_memory["user_message_json"]["text"]
        chat_history = self.cat.agent_manager.agent_prompt_chat_history(
            self.cat.working_memory["history"]
        )
        
        # Prompt
        prompt = f"""show the summary of the data in the completed form and ask the user if they are correct. 
        Don't ask irrelevant questions. 
        Try to be precise and detailed in describing the form and what you need to know.
        ### form data: {self.model}
        ## Conversation until now:{chat_history}
        - Human: {user_message}
        - AI: """

        # Change status
        self.state = CFormState.ASK_SUMMARY

        # Queries the LLM
        response = self.cat.llm(prompt)
        log.debug(f'show_summary: {response}')
        return response


    # Check user confirm the form data
    def check_confirm(self) -> bool:
        user_message = self.cat.working_memory["user_message_json"]["text"]
        
        # Prompt
        prompt = f"""
        respond with either YES if the user's message is affirmative 
        or NO if the user's message is not affirmative
        - Human: {user_message}
        - AI: """

        # Queries the LLM and check if user is agree or not
        response = self.cat.llm(prompt)
        log.debug(f'check_confirm: {response}')
        confirm = "YES" in response
        
        # If confirmed change status
        if confirm:
            self.state = CFormState.EXECUTE_ACTION

        return confirm


    # Updates the form with the information extracted from the user's response
    # (Return True if the model is updated)
    def update_from_user_response(self):

        # Extract new info
        user_response_json = self._extract_info()
        if user_response_json is None:
            return False

        # Gets a new_model with the new fields filled in
        non_empty_details = {k: v for k, v in user_response_json.items() if v not in [None, ""]}
        new_model = self.model.copy(update=non_empty_details)

        # Check if there is no information in the new_model that can update the form
        if new_model.model_dump() == self.model.model_dump():
            return False

        # Validate new_model (raises ValidationError exception on error)
        self.model.model_validate(new_model.model_dump())

        # Overrides the current model with the new_model
        self.model = self.model.model_construct(**new_model.model_dump())
        #print(f'updated model:\n{self.model.model_dump_json(indent=4)}')
        log.critical(f'MODEL : {self.model.model_dump_json()}')
        return True


    # Extracted new informations from the user's response (from sratch)
    def _extract_info(self):
        user_message = self.cat.working_memory["user_message_json"]["text"]
        prompt = self._get_pydantic_prompt(user_message)
        log.debug(f"prompt: {prompt}")
        json_str = self.cat.llm(prompt)
        user_response_json = json.loads(json_str)
        log.debug(f'user response json:\n{user_response_json}')
        return user_response_json


    # return pydantic prompt based from examples
    def _get_pydantic_prompt(self, message):
        lines = []
        # If exists class method for examples ..
        if hasattr(type(self.model), 'get_prompt_examples'):
            prompt_examples = type(self.model).get_prompt_examples()
            for example in prompt_examples:
                lines.append(f"Sentence: {example['sentence']}")
                lines.append(f"JSON: {self._format_prompt_json(example['json'])}")
                lines.append(f"Updated JSON: {self._format_prompt_json(example['updatedJson'])}")
                lines.append("\n")

        result = "Update the following JSON with information extracted from the Sentence:\n\n"
        result += "\n".join(lines)
        result += f"Sentence: {message}\nJSON:{json.dumps(self.model.dict(), indent=4)}\nUpdated JSON:"
        return result


    # format json for prompt
    def _format_prompt_json(self, values):
        attributes = list(self.model.__annotations__.keys())
        data_dict = dict(zip(attributes, values))
        return json.dumps(data_dict, indent=4)


    # Execute the dialogue step
    def execute_dialogue(self):
        try:
            # update form from user response
            model_is_updated = self.update_from_user_response()
            
            # if the form was updated, save it in working memory
            if model_is_updated:
                self.cat.working_memory[ self.key] = self

        except ValidationError as e:
            # If there was a validation problem, return the error message
            message = e.errors()[0]["msg"]
            response = self.cat.llm(message)
            log.critical('> RETURN ERROR')
            return response

        log.warning(f"state:{self.state}, is completed:{self.is_completed()}")

        # Checks whether it should execute the action
        if self.state == CFormState.ASK_SUMMARY:
            if self.check_confirm():
                
                # Execute action
                log.critical('> EXECUTE ACTION')
                return self.execute_action()
        
        # Checks whether the form is completed
        if self.state == CFormState.ASK_INFORMATIONS and self.is_completed():
            
            # Get settings
            settings = self.cat.mad_hatter.get_plugin().load_settings()
            
            # If ask_confirt is true, show summary and ask confirmation
            if settings["ask_confirm"] is True:
                response = self.show_summary(self.cat)
                log.critical('> SHOW SUMMARY')
                return response
            else: #else, execute action
                log.critical('> EXECUTE ACTION')
                return self.execute_action()

        # If the form is not completed, ask for missing information
        response = self.ask_missing_information()
        log.critical('> ASK MISSING INFORMATIONS')
        return response
   

    # Execute final form action
    def execute_action(self):
        if hasattr(type(self.model), 'execute_action'):
            result = type(self.model).execute_action(self.model)
        else:
            result = self.model.json()
        
        del self.cat.working_memory[self.key]

        return result
