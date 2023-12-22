import json
from cat.log import log
from pydantic import ValidationError, BaseModel
from cat.looking_glass.stray_cat import StrayCat
from cat.looking_glass.prompts import MAIN_PROMPT_PREFIX
from enum import Enum

# Conversational Form State
class CFormState(Enum):
    STARTED             = 0    
    ASK_INFORMATIONS    = 1
    ASK_SUMMARY         = 2


# Class Conversational Form
class CForm(BaseModel):

    _state :            CFormState
    _key :              str
    _cat :              StrayCat
    _model_is_updated : bool
    _language :         str
    _prompt_prefix :    str
    _ask_for :          []
    _is_completed       : bool
    
    def __init__(self, key, cat):
        super().__init__()
        self._state = CFormState.STARTED
        self._key = key
        self._cat = cat
        
        self._model_is_updated   = False
        self._language = self.get_language()
    
        # Get prompt, user message and chat history
        self._prompt_prefix = self._cat.mad_hatter.execute_hook("agent_prompt_prefix", MAIN_PROMPT_PREFIX, cat=self._cat)
        

    # Get model fields
    def get_model(self):
        return self.dict(exclude={"_.*"})
    
    
    # Fill list of empty form's fields
    def _check_what_fields_are_empty(self):
        ask_for = []
        
        for field, value in self.get_model().items():
            if value in [None, "", 0]:
                ask_for.append(f'{field}')

        self._ask_for = ask_for
        self._is_completed = not self._ask_for


    ### ASK INFORMATIONS ###

    # Queries the llm asking for the missing fields of the form, without memory chain
    def ask_missing_information(self) -> str:
       
        ''' OLD PROMPT
        prompt = f"Below is are some things to ask the user for in a coversation way.\n\
        You should only ask one question at a time even if you don't get all the info.\n\
        Don't ask as a list! Don't greet the user! Don't say Hi.\n\
        Explain you need to get some info.\n\
        If the ask_for list is empty then thank them and ask how you can help them. \n\
        Ask only one question at a time\n\n\
        ### ask_for list: {self._ask_for}\n\n\
        using {self._language} language."'''

        # Prompt
        prompt = f"Imagine you have to fill out a registration form and some information is missing.\n\
        Please ask to provide missing details. Missing information can be found in the ask_for list.\n\
        Example:\n\
        if ask_for list is provided by [name, address]\n\
        ask: may I know your name?\n\
        Ask for one piece of information at a time.\n\
        Be sure to maintain a friendly and professional tone when requesting this information.\n\
        using {self._language} language.\n\n\
        ### ask_for list: {self._ask_for}"
        print(f'prompt: {prompt}')

        response = self._cat.llm(prompt)
        return response 


    # Queries the lllm asking for the fields to be modified in the form, without a memory chain
    def ask_change_information(self) -> str:
       
        #Prompt
        prompt = f"Your form contains all the necessary information, show the summary of the data\n\
        present in the completed form and ask the user if he wants to change something.\n\
        ### form data: {self.get_model()}\n\
        using the {self._language} language."
        print(f'prompt: {prompt}')

        response = self._cat.llm(prompt)
        return response 


    ### SUMMARIZATION ###

    # Show summary of the form to the user
    def show_summary(self, cat):
        
        ''' OLD PROMPT
        prompt = f"Show the summary of the data in the completed form and ask the user if they are correct.\n\
            Don't ask irrelevant questions.\n\
            Try to be precise and detailed in describing the form and what you need to know.\n\n\
            ### form data: {self.get_model()}\n\n\
            using {self._language} language."'''
        
        # Prompt
        prompt = f"You have collected the following information from the user:\n\
        ### form data: {self.get_model()}\n\n\
        Summarize the information contained in the form data.\n\
        Next, ask the user to confirm whether the information collected is correct.\n\
        Using {self._language} language."
        print(f'prompt: {prompt}')

        # Queries the LLM
        response = self._cat.llm(prompt)
        return response


    # Check user confirm the form data
    def check_user_confirm(self) -> bool:
        
        # Get user message
        user_message = self._cat.working_memory["user_message_json"]["text"]
        
        ''' OLD PROMPT
        prompt = f"only respond with YES if the user's message is affirmative\
        or NO if the user message is negative, do not answer the other way.\n\n\
        ### user message: {user_message}"'''

        # Confirm prompt
        confirm_prompt = f"Given a sentence that I will now give you,\n\
        just respond with 'true' or 'false' depending on whether the sentence is:\n\
        - a refusal either has a negative meaning or is an intention to cancel the form (false)\n\
        - an acceptance has a positive or neutral meaning (true).\n\
        If you are unsure, answer 'false'.\n\
        The sentence is as follows:\n\
        ### user message: {user_message}"
        print(f'confirm prompt: {confirm_prompt}')

        # Queries the LLM and check if user is agree or not
        response = self._cat.llm(confirm_prompt)
        log.critical(f'check_user_confirm: {response}')
        #confirm = "YES" in response
        confirm = "true" in response
        
        return confirm


    ### UPDATE JSON ###

    # Updates the form with the information extracted from the user's response
    # (Return True if the model is updated)
    def update_from_user_response(self):

        # Extract new info
        user_response_json = self._extract_info()
        if user_response_json is None:
            return False
        
        # Gets a new_model with the new fields filled in
        new_model = self.get_model()
        for k, v in user_response_json.items():
            if v not in [None, ""]:
                new_model[k] = v

        # Check if there is no information in the new_model that can update the form
        if new_model == self.get_model():
            return False

        # Validate new_model (raises ValidationError exception on error)
        #self.model_validate_json(**new_model)
        #TODO NON FUNZIONA, da verififare perchè

        # Overrides the current model with the new_model
        for k, v in new_model.items():
            setattr(self, k, v)

        log.critical(f'MODEL : {self.get_model()}')
        return True


    # Extracted new informations from the user's response (from sratch)
    def _extract_info(self):
        user_message = self._cat.working_memory["user_message_json"]["text"]
        prompt = self._get_pydantic_prompt(user_message)
        #print(f'prompt: {prompt}')
        json_str = self._cat.llm(prompt)
        user_response_json = json.loads(json_str)
        return user_response_json


    # return pydantic prompt based from examples
    def _get_pydantic_prompt(self, message):
        lines = []
        
        prompt_examples = self.get_prompt_examples()
        for example in prompt_examples:
            lines.append(f"Sentence: {example['sentence']}")
            lines.append(f"JSON: {self._format_prompt_json(example['json'])}")
            lines.append(f"Updated JSON: {self._format_prompt_json(example['updatedJson'])}")
            lines.append("\n")

        result = "Update the following JSON with information extracted from the Sentence:\n\n"
        result += "\n".join(lines)
        result += f"Sentence: {message}\nJSON:{json.dumps(self.get_model(), indent=4)}\nUpdated JSON:"
        return result


    # format json for prompt
    def _format_prompt_json(self, values):
        #attributes = list(self.get_model().__annotations__.keys())
        attributes = list(self.get_model().keys())
        data_dict = dict(zip(attributes, values))
        return json.dumps(data_dict, indent=4)


    ### EXECUTE DIALOGUE ###

    # Check that there is only one active form
    def set_active_form(self):
        if "_active_cforms" not in self._cat.working_memory.keys():
            self._cat.working_memory["_active_cforms"] = []
        if self._key not in self._cat.working_memory["_active_cforms"]:
            self._cat.working_memory["_active_cforms"].append(self._key)
        for key in self._cat.working_memory["_active_cforms"]:
            if key != self._key:
                self._cat.working_memory["_active_cforms"].remove(key)
                if key in self._cat.working_memory.keys():
                    del self._cat.working_memory[key]


    # Execute the dialogue step
    def execute_dialogue(self):
        
        try:
            # update form from user response
            self._model_is_updated = self.update_from_user_response()
            
            # Fill the information it should ask the user based on the fields that are still empty
            self._check_what_fields_are_empty()
            log.warning(f'MISSING INFORMATIONS: {self._ask_for}')
            
            # (Cat's breath) Check if it's time to skip the conversation step
            if self._check_skip_conversation_step(): 
                log.critical(f'> SKIP CONVERSATION STEP {self._key}')
                #TODO Aggiungere al messaggio utente alcune informazioni per comunicare al llm come comportarsi
                #self._cat.working_memory["user_message_json"]["text"] = "..."
                return None

        except ValidationError as e:
            # If there was a validation problem, return the error message
            message = e.errors()[0]["msg"]
            response = self._cat.llm(message)
            log.critical('> RETURN ERROR')
            return response

        log.warning(f"state:{self._state}, is completed:{self._is_completed}")

        # If the form is not completed, ask for missing information
        if not self._is_completed:
            self._state  = CFormState.ASK_INFORMATIONS
            response = self.ask_missing_information()
            log.critical(f'> ASK MISSING INFORMATIONS {self._key}')
            return response

        # If the form is completed and state = ASK_SUMMARY ..
        if self._state in [CFormState.ASK_SUMMARY]:
            
            # Check confirm from user answer
            if self.check_user_confirm():

                # Execute action
                log.critical(f'> EXECUTE ACTION {self._key}')
                return self.execute_action()
        
        # If the form is completed and state in STARTED or ASK_INFORMATIONS ..
        if self._state in [CFormState.STARTED, CFormState.ASK_INFORMATIONS]:
            
            # Get settings
            settings = self._cat.mad_hatter.get_plugin().load_settings()
            
            # If ask_confirm is true, show summary and ask confirmation
            if settings["ask_confirm"] is True:
                
                # Show summary
                response = self.show_summary(self._cat)

                # Change status in ASK_SUMMARY
                self._state = CFormState.ASK_SUMMARY
        
                log.critical('> SHOW SUMMARY')
                return response
            
            else: #else, execute action
                log.critical(f'> EXECUTE ACTION {self._key}')
                return self.execute_action()

        # If the form is completed, ask for missing information
        self._state  = CFormState.ASK_INFORMATIONS
        response = self.ask_change_information()
        log.critical(f'> ASK CHANGE INFORMATIONS {self._key}')
        return response
   

    # (Cat's breath) Check if should skip conversation step
    def _check_skip_conversation_step(self):

        # If the model was updated, don't skip conversation step
        if self._model_is_updated is True:
            return False
        
        # If the state is starded or summary, don't skip conversation step
        if self._state in [CFormState.STARTED, CFormState.ASK_SUMMARY]:
            return False

        # If they aren't called tools, don't skip conversation step
        num_called_tools = len(self._cat.working_memory["procedural_memories"])
        if num_called_tools == 0:
            return False
    
        # Else, skip conversation step
        return True


    # METHODS TO OVERRIDE

    # Execute final form action
    def execute_action(self):
        result = self.get_model().json()
        del self._cat.working_memory[self._key]
        return result

    # Get prompt examples
    def get_prompt_examples(self):
        return []
    
    # Get language
    def get_language():
        return "English"


    # CLASS METHODS
    
    # Start conversation
    @classmethod
    def start(cls, cat):
        key = cls.__name__
        if key not in cat.working_memory.keys():
            cform = cls(key, cat)
            cat.working_memory[key] = cform
        cform = cat.working_memory[key]
        cform.set_active_form()
        response = cform.execute_dialogue()
        return response


    # Stop conversation
    @classmethod
    def stop(cls, cat):
        key = cls.__name__
        if key in cat.working_memory.keys():
            del cat.working_memory[key]
        return


    # Execute the dialogue step
    @classmethod
    def dialogue(cls, cat):
        key = cls.__name__
        if key in cat.working_memory.keys():
            cform = cat.working_memory[key]
            response = cform.execute_dialogue()
            if response:
                return { "output": response }
        return
