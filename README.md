
# Cat Conversational Form

the cat knows how to collect the data you need in a conversational way!


<img src="./img/thumb.jpg" width=400>

[![awesome plugin](https://custom-icon-badges.demolab.com/static/v1?label=&message=awesome+plugin&color=383938&style=for-the-badge&logo=cheshire_cat_ai)](https://)  


## Usage

### 1) Prepare the pydantic model which extends CBaseModel class
```python 
class MyModel(CBaseModel):
    field1: str = Field(description="...", default="...")
    field2: str = Field(description="...")
    #...
    
	# Implement execute action overriding method
    def execute_action(self):
        # execute action
        return # action output
```

### 2) Implement tool intent start
```python 
@tool(return_direct=True)
def intent_start(input, cat):
    ''' <docString> '''
    return MyModel.start(cat)
```

### 3) Implement tool intent stop
```python 
@tool
def intent_stop(input, cat):
    ''' <docString> '''
    return MyModel.stop(cat)
```

### 4) Implement agent_fast_reply & agent_prompt_prefix for dialog exchange
### (not necessary if the auto handle conversation setting is true)
```python 
@hook
def agent_fast_reply(fast_reply: Dict, cat) -> Dict:
    return MyModel.dialogue_action(fast_reply, cat)

@hook
def agent_prompt_prefix(prefix, cat) -> str:
    return MyModel.dialogue_prefix(prefix, cat)
```