
# Cat Conversational Form

the cat knows how to collect the data you need in a conversational way!


<img src="./img/thumb.jpg" width=400>

[![awesome plugin](https://custom-icon-badges.demolab.com/static/v1?label=&message=awesome+plugin&color=383938&style=for-the-badge&logo=cheshire_cat_ai)](https://)  


## Usage

### 1) Prepare the pydantic model which extends CForm class
```python 
class MyModel(CForm):
    field1: str = Field(description="...", default="...")
    field2: str = Field(description="...")
    #...
    
	# Implement execute action overriding method
    def execute_action(self):
        # execute action
        return # action output
```

### 2) Implement execute action annotation method
```python 
@hook
def execute_action(model: MyModel):
    # execute action
    return # action output
```

### 3) Implement tool intent start
```python 
@tool(return_direct=True)
def intent_start(model, cat):
    ''' <docString> '''
    return MyModel.start(cat)
```

### 4) Implement tool intent stop
```python 
@tool
def intent_stop(model, cat):
    ''' <docString> '''
    return MyModel.stop(cat)
```

### 5) Implement agent_fast_reply for dialog exchange
```python 
@hook
def agent_fast_reply(fast_reply: Dict, cat) -> Dict:
    return MyModel.dialogue(cat)
```