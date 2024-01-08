import json
from cat.log import log
from pydantic import ValidationError, BaseModel
from cat.looking_glass.prompts import MAIN_PROMPT_PREFIX
from enum import Enum
from typing import List
from langchain.prompts.few_shot import FewShotPromptTemplate
from langchain.prompts.prompt import PromptTemplate
from langchain.prompts.example_selector import SemanticSimilarityExampleSelector
from langchain.vectorstores import Qdrant
from qdrant_client.http.models import Distance, VectorParams, PointStruct
import guardrails as gd
from kor import create_extraction_chain, from_pydantic, Object, Text
# https://github.com/eyurtsev/kor
# https://www.guardrailsai.com/docs/guardrails_ai/getting_started


# Class Conversational Base Model
class CBaseModel(BaseModel):

    # Start conversation
    # (typically inside the tool that starts the intent)
    @classmethod
    def start(cls, cat):
        key = cls.__name__
        if key not in cat.working_memory.keys():
            CForm = CForm(cls, key, cat)
            cat.working_memory[key] = CForm
        CForm = cat.working_memory[key]
        CForm.check_active_form()
        response = CForm.execute_dialogue()
        return response

    '''# Stop conversation
    # (typically inside the tool that stops the intent)
    @classmethod
    def stop(cls, cat):
        key = cls.__name__
        if key in cat.working_memory.keys():
            del cat.working_memory[key]
        return'''

    # Execute the dialogue step
    # (typically inside the agent_fast_reply hook)
    @classmethod
    def dialogue(cls, cat):
        key = cls.__name__
        if key in cat.working_memory.keys():
            CForm = cat.working_memory[key]
            response = CForm.execute_dialogue()
            if response:
                return { "output": response }
        return
    
    # METHODS TO OVERRIDE
    
    # Execute final form action
    def execute_action(self):
        return self 
    
    # Allowed tools
    def allowed_tools(self, allowed_tools: List[str]) -> List[str]:
        return allowed_tools
    

# Conversational Form State
class CFormState(Enum):
    START               = 0
    ASK_INFORMATIONS    = 1
    ASK_SUMMARY         = 2


# Class Conversational Form
class CForm():

    def __init__(self, model_class, key, cat):
        self.state = CFormState.START
        self.model_class = model_class
        self.model = model_class.model_construct()
        self.key   = key
        self.cat   = cat
        
        self.language = self.get_language()
        
        # Get prompt, user message and chat history
        self.prompt_prefix = self.cat.mad_hatter.execute_hook("agent_prompt_prefix", MAIN_PROMPT_PREFIX, cat=self.cat)

        self.is_valid = False
        self.errors  = []
        self.ask_for = []

        # Get embedder_size
        self.embedder_size = len(self.cat.embedder.embed_query("hello world")) #1536

        # Load examples
        self.load_confirm_examples()
        self.load_exit_intent_examples()
    
        # Test scan model methods
        self.scan_model_methods()


    ### ASK INFORMATIONS ###

    # Queries the llm asking for the missing fields of the form, without memory chain
    def ask_missing_informations(self) -> str:
       
        # Prompt
        prompt = f"Imagine you have to fill out a registration form and some information is missing.\n\
        Please ask to provide missing details.\n\
        In the ask_for list you can find all validation errors due to missing information.\n\
        Ask for one piece of information at a time.\n\
        Be sure to maintain a friendly and professional tone when requesting this information.\n\
        using {self.language} language.\n\n\
        ### ask_for list: {self.ask_for}"
        print(f'prompt: {prompt}')

        response = self.cat.llm(prompt)
        return response 


    # Queries the lllm asking for the fields to be modified in the form, without a memory chain
    def ask_change_informations(self) -> str:
       
        #Prompt
        prompt = f"Your form contains all the necessary information, show the summary of the data\n\
        present in the completed form and ask the user if he wants to change something.\n\
        ### form data: {self.model.model_dump()}\n\
        using the {self.language} language."
        print(f'prompt: {prompt}')

        response = self.cat.llm(prompt)
        return response 
    

    # Notification error to user
    def notification_error(self) -> str:
        error_message = self.errors[0]
        response = self.cat.llm(error_message)
        return response


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

        # Queries the LLM
        response = self.cat.llm(prompt)
        return response


    # Load confirm examples
    def load_confirm_examples(self):
        
        qclient = self.cat.memory.vectors.vector_db
        self.confirm_collection = "user_confirm"
        
        # Create collection
        qclient.recreate_collection(
            collection_name=self.confirm_collection,
            vectors_config=VectorParams(
                size=self.embedder_size, 
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


    # Check if user confirm the model data
    def check_user_confirm(self) -> bool:
        
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


    ### UPDATE JSON ###

    # Updates the form with the information extracted from the user's response
    # (Return True if the model is updated)
    def update(self):

        # Extract new info
        details = self._extract_info_by_kor()
        #details = self._extract_info_by_guardrails()
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
            raise Exception(f"there are errors in the form: {self.errors}")

        # Overrides the current model with the new_model
        self.model = self.model.model_construct(**new_details)

        log.critical(f'MODEL : {self.model.model_dump()}')
        return True

    
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


    ### EXECUTE DIALOGUE ###

    # Check that there is only one active form
    def check_active_form(self):
        if "_active_CForms" not in self.cat.working_memory.keys():
            self.cat.working_memory["_active_CForms"] = []
        if self.key not in self.cat.working_memory["_active_CForms"]:
            self.cat.working_memory["_active_CForms"].append(self.key)
        for key in self.cat.working_memory["_active_CForms"]:
            if key != self.key:
                self.cat.working_memory["_active_CForms"].remove(key)
                if key in self.cat.working_memory.keys():
                    del self.cat.working_memory[key]


    # Execute the dialogue step
    def execute_dialogue(self):
        
        '''# If there are other tools to invoke skip the dialogue step
        if len(self.allowed_tools()) > 0:
            log.critical(f'> SKIP DIALOG {self.key}')
            return None'''
        
        # Check if the user want to exit the intent
        if self.state not in [CFormState.START] and self.check_exit_intent():
            log.critical(f'> Exit Intent {self.key}')
            del self.cat.working_memory[self.key]
            return None

        # If the form is valid and state == ASK_SUMMARY and user has confirmed, execute action
        if self.is_valid and self.state in [CFormState.ASK_SUMMARY] and self.check_user_confirm():            
            log.critical(f'> EXECUTE ACTION {self.key}')
            return self.execute_action()
        
        try:
            # update model from user response
            model_is_updated = self.update()
            
        except Exception as e:
            # If there was a validation problem, return error
            log.critical(f'> RETURN ERROR {e}')
            return self.notification_error()

        log.warning(f"state:{self.state}, is valid:{self.is_valid}")
        log.warning(f"missing informations:{self.ask_for}, errors: {self.errors}")

        # If the form is not valid, ask for missing information
        if not self.is_valid:
            self.state  = CFormState.ASK_INFORMATIONS
            response = self.ask_missing_informations()
            log.critical(f'> ASK MISSING INFORMATIONS {self.key}')
            return response

        # If ask_confirm is False, execute action directly
        settings = self.cat.mad_hatter.get_plugin().load_settings()
        if settings["ask_confirm"] is False:
            return self.execute_action()
            
        # If state == ASK_INFORMATIONS, Show summary
        if self.state in [CFormState.ASK_INFORMATIONS]:            
            response = self.show_summary(self.cat)
            self.state = CFormState.ASK_SUMMARY
            log.critical('> SHOW SUMMARY')
            return response
        
        # Else: ask for change information
        self.state  = CFormState.ASK_INFORMATIONS
        response = self.ask_change_informations()
        log.critical(f'> ASK CHANGE INFORMATIONS {self.key}')
        return response


    ### OTHER METHODS ###

    # Get prompt template from examples context
    def get_prompt_template(self, examples):

        # Create example selector
        example_selector = SemanticSimilarityExampleSelector.from_examples(
            examples, self.cat.embedder, Qdrant, k=1, location=':memory:'
        )

        # Create example prompt
        example_prompt = PromptTemplate(
            input_variables=["question", "answer"], 
            template="Question: {question}\n{answer}"
        )

        # Create promptTemplate from examples_selector and example_prompt
        prompt_template = FewShotPromptTemplate(
            example_selector=example_selector, 
            example_prompt=example_prompt,
            suffix="Question: {input}", 
            input_variables=["input"]
        )

        return prompt_template


    # Get allowed tools
    def allowed_tools(self):
        # filter only allowed tools in procedural memory
        recalled_tools = self.cat.working_memory["procedural_memories"]
        tool_names = [t[0].metadata["name"] for t in recalled_tools]
        log.critical(f"tools chiamati: {len(tool_names)}")
        allowed_tool_names = self.model.allowed_tools(tool_names)
        filtered_tool_names = [t for t in tool_names if t in allowed_tool_names]
        log.critical(f"tools permessi: {len(filtered_tool_names)}")
        allowed_tools = [i for i in self.cat.mad_hatter.tools if i.name in filtered_tool_names]
        #self.cat.working_memory["procedural_memories"] = allowed_tools
        return allowed_tools


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
    
    
    # Load exit intent examples
    def load_exit_intent_examples(self):
        
        qclient = self.cat.memory.vectors.vector_db
        self.exit_intent_collection = "exit_intent"
        
        # Create collection
        qclient.recreate_collection(
            collection_name=self.exit_intent_collection,
            vectors_config=VectorParams(
                size=self.embedder_size, 
                distance=Distance.COSINE
            )
        )
        
        # Load context
        examples = [ 
            {"message": "I would like to exit the module"                   },
            {"message": "I no longer want to continue filling out the form" },
            {"message": "You go out"                                        },
            {"message": "Return to normal conversation"                     },
            {"message": "Stop and go out"                                   }
        ]

        # Insert training data into index
        points = []
        for i, data in enumerate(examples):
            message = data["message"]
            vector = self.cat.embedder.embed_query(message)
            points.append(PointStruct(id=i, vector=vector, payload={}))
            
        operation_info = qclient.upsert(
            collection_name=self.exit_intent_collection,
            wait=True,
            points=points,
        )
        #print(operation_info)


    # Check if the user wants to exit the intent
    def check_exit_intent(self) -> bool:
        
        # Get user message vector
        user_message = self.cat.working_memory["user_message_json"]["text"]
        user_message_vector = self.cat.embedder.embed_query(user_message)
        
        # Search for the vector most similar to the user message in the vector database and get distance
        qclient = self.cat.memory.vectors.vector_db
        search_results = qclient.search(
            self.exit_intent_collection, 
            user_message_vector, 
            with_payload=False, 
            limit=1
        )
        print(f"search_results: {search_results}")
        nearest_score = search_results[0].score
        
        # If the nearest score is less than the threshold, exit intent
        threshold = 0.9
        return nearest_score >= threshold


    def scan_model_methods(self):
        # Cycle through all methods of the object model
        for method_name in dir(self.model):
            # Check if method name starts with "lookup_"
            if method_name.startswith('lookup_'):
                # Get the method
                method = getattr(self.model, method_name)
                
                # Get the method docstring
                docstring = method.__doc__
                
                # Print result
                print("-" * 30)
                print(f"Method name: {method_name}")
                print(f"Docstring: {docstring}")
                print("-" * 30)

                # Convert docstring to examples json array
                lines = [line.strip() for line in docstring.strip().split('\n') if line.strip()]
                examples = [{"message": line} for line in lines]
                print(f"examples: {examples}")
