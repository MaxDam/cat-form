# Cat Conversational Form

the cat knows how to collect the data you need in a conversational way!

You can see an example implementation here:

https://github.com/MaxDam/cat-form-order-pizza


<img src="./img/thumb.jpg" width=400>

[![awesome plugin](https://custom-icon-badges.demolab.com/static/v1?label=&message=awesome+plugin&color=383938&style=for-the-badge&logo=cheshire_cat_ai)](https://)  


## Usage

This hook is used to set the module instance
<pre>
<code>
@hook
def cform_set_model(model, cat):
    return <instance of module>
</code>
</pre>

This hook allows you to manipulate the 
prompt to request missing information
<pre>
<code>	
@hook
def cform_ask_missing_information(prompt, cat):
	#...
    return prompt
</code>
</pre>
	
This hook allows you to manipulate 
the prompt to ask for user confirmation
<pre>
<code>
@hook
def cform_show_summary(prompt, cat):
	#...
    return prompt
</code>
</pre>

This Hook is called when the form is filled out 
and user confirmation is obtained
<pre>
<code>
@hook
def cform_execute_action(model, cat):
	return result
</code>
</pre>
