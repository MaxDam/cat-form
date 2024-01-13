from pydantic import ValidationError, BaseModel
from cat.mad_hatter.decorators import hook
from cat.looking_glass.prompts import MAIN_PROMPT_PREFIX, MAIN_PROMPT_SUFFIX
from cat.log import log
from typing import Dict
from enum import Enum
import json

from qdrant_client.http.models import Distance, VectorParams, PointStruct

from langchain.prompts.prompt import PromptTemplate
from langchain.output_parsers import PydanticOutputParser
import guardrails as gd #https://www.guardrailsai.com/docs/guardrails_ai/getting_started
from kor import create_extraction_chain, from_pydantic #https://github.com/eyurtsev/kor

from langchain.prompts.few_shot import FewShotPromptTemplate
from langchain.prompts.prompt import PromptTemplate
from langchain.prompts.example_selector import SemanticSimilarityExampleSelector
from langchain.vectorstores import Qdrant


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
            cform.check_active_form()
            response = cform.dialogue_action()
            return response
        cform = cat.working_memory[key]
        cform.check_active_form()
        #response = cform.dialogue_direct()
        response = cform.execute_memory_chain()
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
    def dialogue_action(cls, fast_reply, cat):
        key = cls.__name__
        if key in cat.working_memory.keys():
            cform = cat.working_memory[key]
            response = cform.dialogue_action()
            if response:
                return { "output": response }
        return
    
    # Execute the dialogue step
    # (typically inside the agent_prompt_prefix hook)
    @classmethod
    def dialogue_prefix(cls, prefix, cat):
        key = cls.__name__
        if key in cat.working_memory.keys():
            cform = cat.working_memory[key]
            return cform.dialogue_prefix(prefix)
        return prefix

    # METHODS TO OVERRIDE
    
    # Execute final form action
    def execute_action(self):
        return self.model_dump_json(indent=4)
    
    # Dialog examples
    def examples(self):
        return {}
    

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
        
        self.is_valid = False
        self.errors  = []
        self.ask_for = []

        #self.load_dialog_examples_rag()
        #self.load_confirm_examples_rag()
        

    ####################################
    ######## HANDLE ACTIVE FORM ########
    ####################################

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

    # Class method get active form
    @classmethod
    def get_active_form(cls, cat):
        if "_active_cforms" in cat.working_memory.keys():
            key = cat.working_memory["_active_cforms"][0]
            if key in cat.working_memory.keys():
                cform = cat.working_memory[key]
                return cform
        return None


    ####################################
    ######## CHECK USER CONFIRM ########
    ####################################
        
    # Check user confirm the form data
    def check_user_confirm(self) -> bool:
        
        # Get user message
        user_message = self.cat.working_memory["user_message_json"]["text"]
        
        # Confirm prompt
        confirm_prompt = f"Given a sentence that I will now give you,\n\
        just respond with 'YES' or 'NO' depending on whether the sentence is:\n\
        - a refusal either has a negative meaning or is an intention to cancel the form (NO)\n\
        - an acceptance has a positive or neutral meaning (YES).\n\
        If you are unsure, answer 'NO'.\n\n\
        The sentence is as follows:\n\
        User message: {user_message}"
        
        # Print confirm prompt
        print("*"*10)
        print("CONFIRM PROMPT:")
        print(confirm_prompt)
        print("*"*10)

        # Queries the LLM and check if user is agree or not
        response = self.cat.llm(confirm_prompt)
        log.critical(f'check_user_confirm: {response}')
        confirm = "NO" not in response and "YES" in response
        
        print("RESPONSE: " + str(confirm))
        return confirm
    

    # Load confirm examples RAG
    def load_confirm_examples_rag(self):
        
        qclient = self.cat.memory.vectors.vector_db
        self.confirm_collection = "user_confirm"
        
        # Get embedder size
        embedder_size = len(self.cat.embedder.embed_query("hello world"))

        # Create collection
        qclient.recreate_collection(
            collection_name=self.confirm_collection,
            vectors_config=VectorParams(
                size=embedder_size, 
                distance=Distance.COSINE
            )
        )

        # Load context
        examples = [ 
            {"message": "yes, they are correct",   "label": "True" },
            {"message": "ok, they are fine",       "label": "True" },
            {"message": "they seem right",         "label": "True" },
            {"message": "I think so",              "label": "True" },
            {"message": "no, we are not there",    "label": "False"},
            {"message": "wrong",                   "label": "False"},
            {"message": "they are not correct",    "label": "False"},
            {"message": "I don't think so",        "label": "False"}
        ]

        # Insert training data into index
        points = []
        for i, data in enumerate(examples):
            message = data["message"]
            label = data["label"]
            vector = self.cat.embedder.embed_query(message)
            points.append(PointStruct(id=i, vector=vector, payload={"label":label}))
            
        operation_info = qclient.upsert(
            collection_name=self.confirm_collection,
            wait=True,
            points=points,
        )
        #print(operation_info)


    # Check if user confirm the model data in RAG mode
    def check_user_confirm_rag(self) -> bool:
        
        # Get user message vector
        user_message = self.cat.working_memory["user_message_json"]["text"]
        user_message_vector = self.cat.embedder.embed_query(user_message)
        
        # Search for the vector most similar to the user message in the vector database
        qclient = self.cat.memory.vectors.vector_db
        search_results = qclient.search(
            self.confirm_collection, 
            user_message_vector, 
            with_payload=True, 
            limit=1
        )
        print(f"search_results: {search_results}")
        most_similar_label = search_results[0].payload["label"]
        
        # If the nearest distance is less than the threshold, exit intent
        return most_similar_label == "True"
    

    ####################################
    ############ UPDATE JSON ###########
    ####################################

    # Updates the form with the information extracted from the user's response
    # (Return True if the model is updated)
    def update(self):

        # Extract new info
        #details = self._extract_info_by_pydantic()
        #details = self._extract_info_by_kor()
        details = self._extract_info_by_guardrails()
        if details is None:
            return False
        
        # Clean json details
        print("details", details)
        details = self._clean_json_details(details)

        # update form
        new_details = self.model.model_dump() | details
        new_details = self._clean_json_details(new_details)
        print("new_details", new_details)

        # Check if there is no information in the new_model that can update the form
        if new_details == self.model.model_dump():
            return False

        # Validate new_details
        try:
            self.ask_for = []
            self.errors  = []
            self.model.model_validate(new_details)
            self.is_valid = True
        except ValidationError as e:
            print(f'validation error: {e}')
            # Collect ask_for and errors
            for error_message in e.errors():
                if error_message['type'] == 'missing':
                    self.ask_for.append(error_message['loc'][0])
                else:
                    self.errors.append(error_message["msg"])
                    
        # If there are errors, raise an exception
        if len(self.errors) > 0:
            return False

        # Overrides the current model with the new_model
        self.model = self.model.model_construct(**new_details)

        log.critical(f'MODEL : {self.model.model_dump()}')
        return True


    # Extracted new informations from the user's response (by pydantic)
    def _extract_info_by_pydantic(self):
        parser = PydanticOutputParser(pydantic_object=type(self.model))
        prompt = PromptTemplate(
            template="Answer the user query.\n{format_instructions}\n{query}\n",
            input_variables=["query"],
            partial_variables={"format_instructions": parser.get_format_instructions()},
        )
        log.debug(f'get_format_instructions: {parser.get_format_instructions()}')
        
        user_message = self.cat.working_memory["user_message_json"]["text"]
        _input = prompt.format_prompt(query=user_message)
        output = self.cat.llm(_input.to_string())
        log.debug(f"output: {output}")

        #user_response_json = parser.parse(output).dict()
        user_response_json = json.loads(output)
        log.debug(f'user response json: {user_response_json}')
        return user_response_json
    

    # Extracted new informations from the user's response (by kor)
    def _extract_info_by_kor(self):

        # Get user message
        user_message = self.cat.working_memory["user_message_json"]["text"]
        
        # Get schema and validator from Pydantic model
        schema, validator = from_pydantic(self.model_class)   
        chain = create_extraction_chain(
            self.cat._llm, 
            schema, 
            encoder_or_encoder_class="json", 
            validator=validator
        )
        log.debug(f"prompt: {chain.prompt.to_string(user_message)}")
        
        output = chain.run(user_message)["validated_data"]
        try:
            user_response_json = output.dict()
            log.debug(f'user response json: {user_response_json}')
            return user_response_json
        except Exception  as e:
            log.debug(f"An error occurred: {e}")
            return None
    

    # Extracted new informations from the user's response (using guardrails library)
    def _extract_info_by_guardrails(self):
        
        # Get user message
        user_message = self.cat.working_memory["user_message_json"]["text"]
        
        # Prompt
        prompt = """
        Given the following client message, please extract information about his form.

        ${message}

        ${gr.complete_json_suffix_v2}
        """
        
        # Parse message
        guard = gd.Guard.from_pydantic(output_class=self.model_class, prompt=prompt)
        gd_result = guard(self.cat._llm, prompt_params={"message": user_message})
        print(f'gd_result: {gd_result}')

        # If result is valid, return result
        if gd_result.validation_passed is True:
            result = json.loads(gd_result.raw_llm_output)
            print(f'_extract_info: {user_message} -> {result}')
            return result
        
        return {}


    # Clean json details
    def _clean_json_details(self, details):
        return {key: value for key, value in details.items() if value not in [None, '', 'None', 'null', 'lower-case']}


    # Load dialog examples for RAG
    def load_dialog_examples_rag(self):    
        self.prompt_tpl_update   = None
        self.prompt_tpl_response = None

        '''
        # Examples json format
        self.model.examples = [
            {
                "user_message": "I want to order a pizza",
                "model_before": "{}",
                "model_after":  "{}",
                "validation":   "ask_for: pizza type, address, phone; error: none",
                "response":     "What kind of pizza do you want?"
            },
            {
                "user_message": "I live in Via Roma 1",
                "model_before": "{\"pizza_type\":\"Margherita\"}",
                "model_after":  "{\"pizza_type\":\"Margherita\",\"address\":\"Via Roma 1\"}",
                "validation":   "ask_for: phone; error: none",
                "response":     "Could you give me your phone number?"
            },
            {
                "user_message": "My phone is: 123123123",
                "model_before": "{\"pizza_type\":\"Diavola\"}",
                "model_after":  "{\"pizza_type\":\"Diavola\",\"phone\":\"123123123\"}",
                "validation":   "ask_for: address; error: none",
                "response":     "Could you give me your delivery address?"
            },
            {
                "user_message": "I want a test pizza",
                "model_before": "{\"phone\":\"123123123\"}",
                "model_after":  "{\"pizza_type\":\"test\", \"phone\":\"123123123\"}",
                "validation":   "ask_for: address; error: pizza_type test is not present in the menu",
                "response":     "Pizza type is not a valid pizza"
            }
        ]
        '''

        # If no examples are available, return
        if not self.model.examples:
            return

        # Create example selector
        example_selector = SemanticSimilarityExampleSelector.from_examples(
            self.model.examples, self.cat.embedder, Qdrant, k=1, location=':memory:'
        )

        # Create promptTemplate from examples_selector and example_update_model_prompt
        self.prompt_tpl_update = FewShotPromptTemplate(
            example_selector = example_selector,
            example_prompt   = PromptTemplate(
                input_variables = ["user_message", "model_before", "model_after"],
                template = "User Message: {user_message}\nModel: {model_before}\nUpdated Model: {model_after}"
            ),
            suffix = "Question: {input}",
            input_variables = ["input"]
        )
        #print(self.prompt_tpl_update.format(input="<user question>"))

        # Create promptTemplate from examples_selector and example_response_prompt
        self.prompt_tpl_response = FewShotPromptTemplate(
            example_selector = example_selector,
            example_prompt   = PromptTemplate(
                input_variables = ["validation", "response"],
                template = "Validation: {validation}\nResponse: {response}"
            ),
            suffix = "Validation: {input}",
            input_variables = ["input"]
        )
        #print(self.prompt_tpl_response.format(input="<pydantic validation result>"))


    ####################################
    ######### EXECUTE DIALOGUE #########
    ####################################
    
    # Execute the dialogue step
    def dialogue_action(self):
        log.critical("dialogue_action")
        log.warning(f" state: {self.state}, valid: {self.is_valid}")

        #self.cat.working_memory["episodic_memories"] = []

        # If the form is valid and ask_confirm is False, execute action directly
        settings = self.cat.mad_hatter.get_plugin().load_settings()
        if self.is_valid and settings["ask_confirm"] is False:
            log.warning("> EXECUTE ACTION")
            del self.cat.working_memory[self.key]   
            return self.model.execute_action()
        
        # Check user confirm
        if self.is_valid and self.state == CFormState.ASK_SUMMARY:
            if self.check_user_confirm():
                log.warning("> EXECUTE ACTION")
                del self.cat.working_memory[self.key]   
                return self.model.execute_action()
            else:
                log.warning("> STATE=ASK_INFORMATIONS")
                self.state = CFormState.ASK_INFORMATIONS
                
        # Switch in user ask confirm
        if self.is_valid and self.state == CFormState.ASK_INFORMATIONS:
            self.state = CFormState.ASK_SUMMARY
            log.warning("> STATE=ASK_SUMMARY")
            return None

        # update model from user response
        self.update()
        log.warning("> UPDATE")
        return None
    

    # execute dialog prompt prefix
    def dialogue_prefix(self, prompt_prefix):
        log.critical("dialogue_prefix")

        # Get class fields descriptions
        class_descriptions = []
        for key, value in self.model_class.model_fields.items():
            class_descriptions.append(f"{key}: {value.description}")
        
        # Formatted texts
        formatted_model_class = ", ".join(class_descriptions)
        formatted_model       = ", ".join([f"{key}: {value}" for key, value in self.model.model_dump().items()])
        formatted_ask_for     = ", ".join(self.ask_for)
        formatted_errors      = ", ".join(self.errors)

        # Set prompt
        if not self.is_valid:
            prompt = \
                f"Your goal is to have the user fill out a form containing the following fields:\n\
                {formatted_model_class}\n\n\
                you have currently collected the following values:\n\
                {formatted_model}\n\n"

            if len(self.errors) > 0:
                prompt += \
                    f"and in the validation you got the following errors:\n\
                    {formatted_errors}\n\n"

            if len(self.ask_for) > 0:    
                prompt += \
                    f"and the following fields are still missing:\n\
                    {formatted_ask_for}\n\n"
                
            prompt += \
                f"ask the user to give you the necessary information."
        else:
            prompt = f"Your goal is to have the user fill out a form containing the following fields:\n\
                {formatted_model_class}\n\n\
                you have collected all the available data:\n\
                {formatted_model}\n\n\
                show the user the data and ask them to confirm that it is correct.\n"

        # Print prompt prefix
        print("*"*10)
        print("PROMPT PREFIX:")
        print(prompt)
        print("*"*10)

        # Set user_message with the new user_message
        #self.cat.working_memory["user_message_json"]["text"] = prompt
        return prompt


    # execute dialog direct (combines the previous two methods)
    def dialogue_direct(self):
        response = self.dialogue_action()
        if not response:
            user_message = self.cat.working_memory["user_message_json"]["text"]
            prompt_prefix = self.cat.mad_hatter.execute_hook("agent_prompt_prefix", MAIN_PROMPT_PREFIX, cat=self.cat)
            prompt_prefix = self.dialogue_prefix(prompt_prefix)
            prompt = f"{prompt_prefix}\n\n\
                User message: {user_message}\n\
                AI:"
            response = self.cat.llm(prompt)
        return response
    

    # Execute memory chain
    def execute_memory_chain(self):
        agent_input   = self.cat.agent_manager.format_agent_input(self.cat.working_memory)
        agent_input   = self.cat.mad_hatter.execute_hook("before_agent_starts", agent_input, cat=self.cat)
        agent_input["tools_output"] = ""
        prompt_prefix = self.cat.mad_hatter.execute_hook("agent_prompt_prefix", MAIN_PROMPT_PREFIX, cat=self.cat)
        prompt_prefix = self.dialogue_prefix(prompt_prefix)
        prompt_suffix = self.cat.mad_hatter.execute_hook("agent_prompt_suffix", MAIN_PROMPT_SUFFIX, cat=self.cat)
        response = self.cat.agent_manager.execute_memory_chain(agent_input, prompt_prefix, prompt_suffix, self.cat)
        return response.get("output")
    

############################################################
######### HOOKS FOR AUTOMATIC HANDLE CONVERSATION ##########
############################################################

@hook
def agent_fast_reply(fast_reply: Dict, cat) -> Dict:
    settings = cat.mad_hatter.get_plugin().load_settings()
    if settings["auto_handle_conversation"] is True:
        cform = CForm.get_active_form(cat)
        if cform:
            return cform.model.dialogue_action(fast_reply, cat)
    return fast_reply

@hook
def agent_prompt_prefix(prefix, cat) -> str:
    settings = cat.mad_hatter.get_plugin().load_settings()
    if settings["auto_handle_conversation"] is True:
        cform = CForm.get_active_form(cat)
        if cform:
            return cform.model.dialogue_prefix(prefix, cat)
    return prefix