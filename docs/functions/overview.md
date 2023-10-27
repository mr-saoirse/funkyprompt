# Overview

All functions in `funkyprompt` must have proper _docstrings_ and _typing_ information. In the current version we assume the Google style which is compact and neat. For example

```python
def get_persons_favourite_thing_of_type(person: Person, thing_type: str) -> str:
    """
    This function returns the favourite type of thing for a supplied Person

    **Params**
        person: This a complex type that describes the person
        thing_type: The class of thing we are interested in e.g. 'color', 'food' or 'animal'

    **Returns**
        Returns information on the person's favourite thing

    **Raises**
        Exception

    """
    #dummy response - this function does not really do anything
    return "This persons favourite color is gold baby"
```

The `Person` is a pydantic object

```python
class Person(BaseModel):
    """
    This is a person
    """
    name: typing.Optional[str]
    email: str
    team: typing.Optional[str]
```

You can use your own functions and describe then as shown below.&#x20;

```python
from funkyprompt.ops.utils.inspector import describe_function
d: FunctionDescription= describe_function(get_persons_favourite_thing_of_type)
```

Calling `d.function_dict()` will provide a description in the format as used by [OpenAI functions](https://openai.com/blog/function-calling-and-other-api-updates). Note we build it in a special way e.g. adding Pydantic object schema into the descriptions.

{% hint style="info" %}
It seems nicer to add the object description into the parameter description directly but the LLM did not seem to do as well at the time of testing.
{% endhint %}

````json
{
    "name": "get_persons_favourite_thing_of_type",
    "description": "This function returns the favourite thing of type for a supplied Person\\nThe parameter [person] is a Pydantic object type described below: \\njson```<<PYDNATIC PERSON DEF>>```\\n",
    "parameters": {
        "type": "object",
        "properties": {
            "person": {
                "type": "object",
                "description": "This is a complex Pydantic type who's schema is described in the function description"
            },
            "thing": {
                "type": "string",
                "description": "The class of thing we are interested in e.g. 'color', 'food' or 'animal'"
            }
        }
    }
}
````

Here are three questions that illustrate the idea. try them for yourself (e.g. in a Jupyter notebook).&#x20;

```python
#first we ask a factual question.
#This is important to make sure the agent does not rely on functions only
import funkyprompt
from funkyprompt import agent
agent("What is the capital of Ireland")
```

Next we illustrate how import functions can supplying them allows the agent to inspect the functions along with the Pydantic arguments and understand how to call the functions

```python
from funkyprompt.ops.examples import *
from funkyprompt.ops.utils.inspector import describe_function
fns = [describe_function(get_persons_favourite_thing_of_type),
       describe_function(get_persons_action_if_you_know_favourite_type_of_thing)]
agent("What is John@gmail.com's favourite color and his most likely action?", fns)
```

The agent is able to take a reasoned approach to call one function and then pass the results to the other

Next we remove the functions `fns` that are passed in to the agent call. We do this because the `funkyprompt` interpreter has a a function lookup to use if stuck.&#x20;

We want to see that the agent will search for functions only when stuck, will find those functions, and will call those functions. With the `funkyprompt` interpret this works. This neat but not challenging for the LLM to do if we set things up right. The trick is to control parameter names etc so that selected functions are properly invoked.&#x20;

```python
agent("What is John@gmail.com's favourite color and his most likely action?")
```

In all these cases the answer to the question as setup should be

```
John@gmail.com's favourite color is gold and his most likely action is eating vanilla ice cream.
```

***

Above we crated trivially silly functions to use as basic tests. We will want to develop a good intuition before we start working with real data and bigger data. Up next we will provide some tooling to play around with function execution plans and how we visually represent them. We are getting to the heart of what `funkyprompt` is all about!
