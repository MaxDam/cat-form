import json
from cat.log import log
from pydantic import ValidationError, BaseModel
from cat.looking_glass.prompts import MAIN_PROMPT_PREFIX
from enum import Enum
import guardrails as gd


# Class Conversational Base Model
class CBaseModel(BaseModel):

    # Start conversation
    # (typically inside the tool that starts the intent)
    @classmethod
    def start(cls, cat):
        key = cls.__name__
        if key not in cat.working_memory.keys():
            cform = CForm(cls, key, cat)
            cat.working_memory[key] = cform
        cform = cat.working_memory[key]
        cform.check_active_form()
        response = cform.execute_dialogue()
        return response


    # Stop conversation
    # (typically inside the tool that stops the intent)
    @classmethod
    def stop(cls, cat):
        key = cls.__name__
        if key in cat.working_memory.keys():
            del cat.working_memory[key]
        return


    # Execute the dialogue step
    # (typically inside the agent_fast_reply hook)
    @classmethod
    def dialogue(cls, cat):
        key = cls.__name__
        if key in cat.working_memory.keys():
            cform = cat.working_memory[key]
            response = cform.execute_dialogue()
            if response:
                return { "output": response }
        return
    
    # METHODS TO OVERRIDE
    
    # Execute final form action
    def execute_action(self):
        return self 
    

# Conversational Form State
class CFormState(Enum):
    ASK_INFORMATIONS    = 0
    ASK_SUMMARY         = 1


# Class Conversational Form
class CForm():

    def __init__(self, model_class, key, cat):
        self.state = CFormState.ASK_INFORMATIONS
        self.model_class = model_class
        self.model = model_class.model_construct()
        self.key   = key
        self.cat   = cat
        
        self.model_is_updated   = False
        self.language = self.get_language()
        self.dialog_is_skipped = True

        # Get prompt, user message and chat history
        self.prompt_prefix = self.cat.mad_hatter.execute_hook("agent_prompt_prefix", MAIN_PROMPT_PREFIX, cat=self.cat)

        self.is_valid = False
        self.errors  = []
        self.ask_for = []
    
    ### ASK INFORMATIONS ###

    # Queries the llm asking for the missing fields of the form, without memory chain
    def ask_missing_information(self) -> str:
       
        # Prompt
        prompt = f"Imagine you have to fill out a registration form and some information is missing.\n\
        Please ask to provide missing details.\n\
        In the ask_for list you can find all validation errors due to missing information.\n\
        Ask for one piece of information at a time.\n\
        Be sure to maintain a friendly and professional tone when requesting this information.\n\
        using {self.language} language.\n\n\
        ### ask_for list: {self.ask_for}"
        print(f'prompt: {prompt}')

        '''
        prompt = f"Below is are some things to ask the user for in a coversation way.\n\
        You should only ask one question at a time even if you don't get all the info.\n\
        Don't ask as a list! Don't greet the user! Don't say Hi.\n\
        Explain you need to get some info.\n\
        If the ask_for list is empty then thank them and ask how you can help them. \n\
        Ask only one question at a time\n\n\
        ### ask_for list: {self.ask_for}\n\n\
        using {self.language} language."
        '''

        response = self.cat.llm(prompt)
        return response 


    # Queries the lllm asking for the fields to be modified in the form, without a memory chain
    def ask_change_information(self) -> str:
       
        #Prompt
        prompt = f"Your form contains all the necessary information, show the summary of the data\n\
        present in the completed form and ask the user if he wants to change something.\n\
        ### form data: {self.model.model_dump()}\n\
        using the {self.language} language."
        print(f'prompt: {prompt}')

        response = self.cat.llm(prompt)
        return response 


    # Enrich the user message with missing informations
    def enrich_user_message(self):
        
        # Get user message
        user_message = self.cat.working_memory["user_message_json"]["text"]

        # Set prompt
        if len(self.ask_for) > 0:
            user_message = f"{user_message}\n\
                (Remember that you are still missing the following information to complete the form:\n\
                Missing informations: {self.ask_for})"
        else:
            user_message = f"{user_message}\n\
                (Remember that you have completed filling out the form and need user confirmation.\n\
                Form data: {self.model.model_dump()})"

        # Set user_message with the new user_message
        self.cat.working_memory["user_message_json"]["text"] = user_message

    
    # Get language
    def get_language(self):

        # Get user message
        user_message = self.cat.working_memory["user_message_json"]["text"]

        # Prompt
        language_prompt = f"Identify the language of the following message \
        and return only the language of the message, without other text.\n\
        If you can't locate it, return 'English'.\n\
        Message examples:\n\
        'Ciao, come stai?', returns: 'Italian',\n\
        'How do you go?', returns 'English',\n\
        'Bonjour a tous', returns 'French'\n\n\
        Message: '{user_message}'"
        
        # Queries the LLM and check if user is agree or not
        response = self.cat.llm(language_prompt)
        log.critical(f'Language: {response}')
        return response


    ### SUMMARIZATION ###

    # Show summary of the form to the user
    def show_summary(self, cat):
        
        # Prompt
        prompt = f"You have collected the following information from the user:\n\
        ### form data: {self.model.model_dump()}\n\n\
        Summarize the information contained in the form data.\n\
        Next, ask the user to confirm whether the information collected is correct.\n\
        Using {self.language} language."
        print(f'prompt: {prompt}')

        '''
        prompt = f"Show the summary of the data in the completed form and ask the user if they are correct.\n\
            Don't ask irrelevant questions.\n\
            Try to be precise and detailed in describing the form and what you need to know.\n\n\
            ### form data: {self.model.model_dump()}\n\n\
            using {self.language} language."
        '''
        
        # Queries the LLM
        response = self.cat.llm(prompt)
        return response


    # Check user confirm the form data
    def check_user_confirm(self) -> bool:
        
        # Get user message
        user_message = self.cat.working_memory["user_message_json"]["text"]
        
        # Confirm prompt
        confirm_prompt = f"only respond with YES if the user's message is affirmative\
        or NO if the user message is negative, do not answer the other way.\n\
        If you are unsure, answer NO.\n\n\
        ### user message: {user_message}" 
        print(f'confirm prompt: {confirm_prompt}')

        '''
        confirm_prompt = f"Given a sentence that I will now give you,\n\
        just respond with 'YES' or 'NO' depending on whether the sentence is:\n\
        - a refusal either has a negative meaning or is an intention to cancel the form (NO)\n\
        - an acceptance has a positive or neutral meaning (YES).\n\
        If you are unsure, answer 'NO'.\n\
        The sentence is as follows:\n\
        ### user message: {user_message}"
        '''
        
        # Queries the LLM and check if user is agree or not
        response = self.cat.llm(confirm_prompt)
        log.critical(f'check_user_confirm: {response}')
        confirm = "NO" not in response and "YES" in response
        
        return confirm


    ### UPDATE JSON ###

    # Updates the form with the information extracted from the user's response
    # (Return True if the model is updated)
    def update(self):

        # Extract new info
        details = self._extract_info()
        if details is None:
            return False
        
        # Remove empty values
        print("details", details)
        details = {key: value for key, value in details.items() if value not in [None, '', 'null', 'None']}

        # update form
        new_details = self.model.model_dump() | details

        # Check if there is no information in the new_model that can update the form
        if new_details == self.model.model_dump():
            return False

        # Validate new_details (raises ValidationError exception on error)
        try:
            self.ask_for = []
            self.errors  = []
            self.model.model_validate(new_details)
            self.is_valid = True
        except ValidationError as e:
            for error_message in e.errors():
                if error_message['type'] == 'missing':
                    self.ask_for.append(error_message['loc'][0])
                else:
                    self.errors.append(error_message["msg"])
                    raise e

        print("ask_for", self.ask_for)

        # Overrides the current model with the new_model
        self.model = self.model.model_construct(**new_details)

        log.critical(f'MODEL : {self.model.model_dump()}')
        return True

    # Extracted new informations from the user's response (using guardrails library)
    def _extract_info(self):
        
        # Get user message
        user_message = self.cat.working_memory["user_message_json"]["text"]
        
        # Prompt
        prompt = """
        Given the following client message, please extract information about his form.

        ${message}

        ${gr.complete_json_suffix_v2}
        """
        
        # Get json from guardrails
        guard = gd.Guard.from_pydantic(output_class=self.model_class, prompt=prompt)
        gresult = guard(self.cat._llm, prompt_params={"message": user_message})
        result = json.loads(gresult.raw_llm_output)
        return result


    ### EXECUTE DIALOGUE ###

    # Check that there is only one active form
    def check_active_form(self):
        if "_active_cforms" not in self.cat.working_memory.keys():
            self.cat.working_memory["_active_cforms"] = []
        if self.key not in self.cat.working_memory["_active_cforms"]:
            self.cat.working_memory["_active_cforms"].append(self.key)
        for key in self.cat.working_memory["_active_cforms"]:
            if key != self.key:
                self.cat.working_memory["_active_cforms"].remove(key)
                if key in self.cat.working_memory.keys():
                    del self.cat.working_memory[key]


    # Execute the dialogue step
    def execute_dialogue(self):
        
        try:
            # update form from user response
            self.model_is_updated = self.update()
            
            # (Cat's breath) Check if it's time to skip the conversation step
            if self._check_skip_conversation_step(): 
                log.critical(f'> SKIP CONVERSATION STEP {self.key}')

                # Enrich user message with missing informations and return None
                self.enrich_user_message()

                # Set dialog as skipped and return None
                self.dialog_is_skipped = True
                return None
    
        except ValidationError as e:
            # If there was a validation problem, return the error message
            message = e.errors()[0]["msg"]
            response = self.cat.llm(message)
            log.critical('> RETURN ERROR')
            return response

        # Set dialogue as unskipped
        self.dialog_is_skipped = False

        log.warning(f"state:{self.state}, is valid:{self.is_valid}")
        log.warning(f"missing informations:{self.ask_for}, errors: {self.errors}")

        # If the form is not completed, ask for missing information
        if len(self.ask_for) > 0:
            self.state  = CFormState.ASK_INFORMATIONS
            response = self.ask_missing_information()
            log.critical(f'> ASK MISSING INFORMATIONS {self.key}')
            return response
        
        # If the form is completed and state == ASK_SUMMARY ..
        if self.state in [CFormState.ASK_SUMMARY]:
            
            # Check confirm from user answer
            if self.check_user_confirm():

                # Execute action
                log.critical(f'> EXECUTE ACTION {self.key}')
                return self.execute_action()
        
        # If the form is completed and state == ASK_INFORMATIONS ..
        if self.state in [CFormState.ASK_INFORMATIONS]:
            
            # Get settings
            settings = self.cat.mad_hatter.get_plugin().load_settings()
            
            # If ask_confirm is true, show summary and ask confirmation
            if settings["ask_confirm"] is True:
                
                # Show summary
                response = self.show_summary(self.cat)

                # Change status in ASK_SUMMARY
                self.state = CFormState.ASK_SUMMARY
        
                log.critical('> SHOW SUMMARY')
                return response
            
            else: #else, execute action
                log.critical(f'> EXECUTE ACTION {self.key}')
                return self.execute_action()

        # If the form is completed, ask for missing information
        self.state  = CFormState.ASK_INFORMATIONS
        response = self.ask_change_information()
        log.critical(f'> ASK CHANGE INFORMATIONS {self.key}')
        return response
   

    # (Cat's breath) Check if should skip conversation step
    def _check_skip_conversation_step(self):

        # If the model was updated, don't skip conversation step
        if self.model_is_updated is True:
            return False
        
        # If the dialogue was previously skipped, it doesn't skip it again
        if self.dialog_is_skipped is True:
            return False

        # If the state is starded or summary, don't skip conversation step
        if self.state in [CFormState.ASK_SUMMARY]:
            return False

        # If they aren't called tools, don't skip conversation step
        num_called_tools = len(self.cat.working_memory["procedural_memories"])
        if num_called_tools == 0:
            return False
    
        # Else, skip conversation step
        return True

    # Execute action
    def execute_action(self):
        
        # Delete CForm from working memory
        del self.cat.working_memory[self.key]

        # Look for methods annotated with @hook called execute_action and with parameter model equal to the curren class
        for hook in self.cat.mad_hatter.hooks["execute_action"]:
            func = hook.function
            if hasattr(func, "__annotations__")\
            and len(func.__annotations__) > 0\
            and list(func.__annotations__.values())[0].__name__ == self.model_class.__name__:
                
                # Execute function action
                return func(self.model)

        # If not found hook -> call method execute_action in the model..
        return self.model.execute_action()
