
# Cat Conversational Form

the cat knows how to collect the data you need in a conversational way!


<img src="./img/thumb.jpg" width=400>

[![awesome plugin](https://custom-icon-badges.demolab.com/static/v1?label=&message=awesome+plugin&color=383938&style=for-the-badge&logo=cheshire_cat_ai)](https://)  


## Usage

### 1) Prepare the pydantic model which extends CForm class
```python 
class MyModel(CForm):
    field1: str | None = None
    field2: str | None = None
    #...
    
```

### 2) Implement get prompt example annotation method
```python 
@cform(MyModel)
def get_prompt_examples():
    return [ 
        {
            "sentence":    "# sentence",
            "json":        [# initial attributes],
            "updatedJson": [# updated attributes]
        },
        {
            "sentence":    "# sentence",
            "json":        [# initial attributes],
            "updatedJson": [# updated attributes]
        }
        #...
    ]
```

### 3) Implement execute action annotation method
```python 
@cform(MyModel)
def execute_action(cat, model):
    # execute action
    return # action output
```

### 4) Implement tool intent start
```python 
@tool(return_direct=True)
def intent_start(model, cat):
    ''' <docString> '''
    return MyModel.start(cat)
```

### 5) Implement tool intent stop
```python 
@tool(return_direct=True)
def intent_stop(model, cat):
    ''' <docString> '''
    return MyModel.stop(cat)
```

### 6) Implement agent_fast_reply for dialog exchange
```python 
@hook()
def agent_fast_reply(fast_reply: Dict, cat) -> Dict:
    return MyModel.dialogue(cat)
```