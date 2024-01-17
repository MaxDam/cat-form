
# Cat Conversational Form

the cat knows how to collect the data you need in a conversational way!


<img src="./img/thumb.jpg" width=400>

[![awesome plugin](https://custom-icon-badges.demolab.com/static/v1?label=&message=awesome+plugin&color=383938&style=for-the-badge&logo=cheshire_cat_ai)](https://)  


## Usage

### 1) Prepare the pydantic model which extends CBaseModel class
```python 
class PizzaOrder(CBaseModel):
    pizza_type: str = Field(description="...", default="...")
    address:    str = Field(description="...")
    phone:      str = Field(description="...")
    #...
    
    # Implement execute action overriding method
    def execute_action(self, cat):
        # execute action
        return # action output
    
    # Implement examples method	
    def examples(self, cat):
        return [
            {
                "user_message": "My phone is: 123123123",
                "model_before": "{\"pizza_type\":\"Diavola\"}",
                "model_after":  "{\"pizza_type\":\"Diavola\",\"phone\":\"123123123\"}",
                "validation":   "ask_for: address; error: none",
                "response":     "Could you give me your delivery address?"
            },
            #...
        ]
```

### 2) Implement tool intent start
```python 
@tool(return_direct=True)
def intent_start(input, cat):
    ''' <docString> '''
    return PizzaOrder.start(cat)
```

### 3) Implement tool intent stop
```python 
@tool
def intent_stop(input, cat):
    ''' <docString> '''
    return PizzaOrder.stop(cat)
```

### 4) Implement agent_fast_reply & agent_prompt_prefix for dialog exchange
### (not necessary if the auto handle conversation setting is true)
```python 
@hook
def agent_fast_reply(fast_reply: Dict, cat) -> Dict:
    return PizzaOrder.dialogue_action(fast_reply, cat)

@hook
def agent_prompt_prefix(prefix, cat) -> str:
    return PizzaOrder.dialogue_prefix(prefix, cat)
```

## Flow
<img src="./schema/cat-form.jpg" width=400>


### if you also want to extend the standard behavior of the module you have to do it this way
```python
# Extend CForm class
class MyForm(CForm):
    def __init__(self, model_class, key, cat):
        print("MyForm constructor")
        super().__init__(model_class, key, cat)
    
    def check_user_confirm(self) -> bool:
        print("MyForm check_user_confirm")
        return super().check_user_confirm() 
    
    def user_message_to_json(self):
        print("MyForm user_message_to_json")
        return super().user_message_to_json()
    
    def model_merge(self, json_details):
        print("MyForm model_merge")
        return super().model_merge(json_details)
        
    def model_validate(self, model):
        print("MyForm model_validate")
        return super().model_validate(model)

    #...


@tool(return_direct=True)
def intent_start(input, cat):
    ''' <docString> '''
    return PizzaOrder.start(cat, form=MyForm)
```