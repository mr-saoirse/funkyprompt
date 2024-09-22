# Welcome

Welcome to funkyprompt. This is a lightweight library for building agent systems by the principle of _Object Orientated Generation_.
This is a simple idea that says that we only need to focus on objects to build agentic systems. 

There are actually only two abstractions that are important for working with large language models.

1. The messages stack, a collection of messages with specific roles. The system message may be considered special in some models
2. The function stack, a list of functions often descripted in Json Schema, that can be called.

In funkyprompt both of these stacks are always treated as dynamic inside a Runner's execution loop. 
Reasoning is carried out by starting with a system prompt that is always rendered as clean Markdown and then following the trail of function calls until completion. It should be possible to activate and recruit new functions during the execution loop.

Objects are represents by Pydantic or Markdown and their is invertible mapping between these two representations. OOG requires three things;

- Top level metadata or doc string for the system level prompt
- Fields with descriptions that managed structured output
- Class methods or auxillary API methods defined for the type


Here is a trivially simple example

```python
from pydantic import Field

class TestObject(AbstractModel):
    """You are a simple agent that answers the users question with the help of functions. 
    
Please respond in a structured format with fenced json. Using the response format provided"""
             
    person: str = Field(description="A person that is of interest to the user")
    color: str = Field(description="A color that the person likes")
    object_of_color: str = Field(description="An object that is the color of the persons favorite color")
        
    @classmethod
    def favorite_color(cls, person:str):
        """
        For three people Bob, Henrik and Ursula, you can ask for the favorite color and get an answer 
        
        Args:
            person: the name of the person
        """
        
        return {
            "bob": "green",
            "henrik": "yellow",
            "ursula": "red"
        }.get(person.lower())
    
    @classmethod
    def objects_of_color(cls, color:str):
        """
        For a given color, get an object of this color
        
        Args:
            color: the color
        """
        
        return {
            "green": "turtle",
            "yellow": "cup",
            "red": "car"
        }.get(color.lower())
    
agent = Runner(TestObject)
#use GPT by default or other models like claude or gemini
Markdown(agent("Tell me about henrik",
      CallingContext(model='claude-3-5-sonnet-20240620')
     ))
```

This example illustrates that Agents are always described as pydantic objects including holding callable functions. Not shown here, the configuration can add references to external functions i.e. OpenAPI endpoints. 

## Installation

Funkyprompt is a poetry library that you can clone or install locally. Its also installable via PyPi

```bash
pip install funkyprompt
```

...TODO

