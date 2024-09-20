"""this example illustrates how "agents" are just objects with properties and functions
  some agents may not have properties 
  but properties act as a response template which will be a json response.
"""

from funkyprompt.core import AbstractModel, AbstractContentModel, AbstractEntity
import typing
from pydantic import Field
import os
import requests
        
"""for testing we always have a single function api but in theory other apis could be registered"""
FP_API_ROOT = f"https://{os.environ.get('FP_API')}"
openapi_spec_uri = f'{FP_API_ROOT}/openapi.json'


AGENT_CORE_DESCRIPTION = """
As a funkyprompt agent you are responsible for calling 
provided functions to answer the users question.
The default agent core contains basic bootstrapping functions. 

An example use case would be to ask questions about 
named entities which can be loaded from the store. 
Once loaded, these entities provide not only details 
but references to other functions that can be called. 
This can be used to allows agent workflows to multi-hop.

Furthermore, a help function can be used for general planning 
over all known functions in a function registry.
These functions are loaded on demand into the runners for use by LLMs.

Image description functions points to some multimodal applications.

`Funkyprompt` uses the following key principles;
- it treats the dynamic parts of agents i.e. the runner as a simple shell (<200 lines of code)
- the runner outsources two stateful jobs i. the message stack (simple list of dicts) and ii. the function stack
- it then treats agents as "declarative" using a object orientated generation paradigm
- objects contains methods and fields as well as metadata. these are the agent prompts/guidance
- objects also provide a response schema if relevant to guide json agent response formats 
   - Note: the implies the response format, functions, goals and general "prompting" are all encapsulated in a single Pydantic object
- functions can be infinitely searched and the function stack can be dynamical managed in context

By treating agents as simple object types which provide rich semantics and access to encapsulated functions
`funkyprompt` allows for complex agent systems to be built in a lightweight and intuitive way

"""


class DefaultAgentCore(AbstractModel):
    """Agents in `funkyprompt` are declarative things.
    They do not do anything except expose metadata and functions.
    Runners are used to manage the comms with LLMS
    and the basic workflow - there is only one workflow in `funkyprompt`.
    This default type for use in the runner - contains basic functions.
    This minimal agent is quite powerful because it can bootstrap RAG/search.
    """

    # ideas
    # it may be that not providing a format results in default plain text / markdown

    class Config:
        name: str = "agent"
        namespace: str = "core"
        description: str = AGENT_CORE_DESCRIPTION

    @classmethod
    def describe_images(self, images: typing.List[str], question: str = None) -> dict:
        """describe a set of using the default LLM and an optional prompt/question

        Args:
            images (typing.List[str]): the images in uri format or Pil Image format
            question (str): the question to ask about the images - optional, a default prompt will be used
        """
        pass

    @classmethod
    def funky_prompt_codebase(self, questions: str):
        """ask questions about the codebase aka library

        Args:
            questions (str): provide one or more questions to ask
        """
        from funkyprompt.core import load_entities

        print(f"funky_prompt_codebase/{questions=}")

        return {"questions": questions, "the following entities exist": load_entities()}


class AgentBuilder(AbstractContentModel):
    """Use to create agents which are basically markdown agents in funkyprompt"""
    class Config:
        name: str='agent'
        namespace: str = 'core'
        as_json: bool = True
        description = f"""
        Your job is to create the agent template using the information provided. 
        You can use an openapi json for an API {openapi_spec_uri} and the user will provide a list of tasks they would like to be able to perform using an agent. 
        Please include a list to only the functions that will help the user in their task
      
        - you can use a function to lookup the openapi json spec
        - You will be provided with an agent name and namespace  - if no namespace is given use `public`. make sure to snake case the name as <namespace>.<agent_name>. Choose a suitable name if none is given defaulting to just the name of the entity in question
        - you should provide a detailed description of the agent in the content field
        
        """
        
    functions_markdown: str = Field(description="bullet list of markdown formatted functions using the hyperlink format including verb prefix - [verb:endpoint](https://domain.com/prefix/docs#/[Tag]/operationid) based on the OpenAPI.Json provided ")
    structured_response_markdown: str

           
    @classmethod
    def get_openapi_json_schema(cls,context:str=None):
        """get the openapi json schema
        
        **Args**
            context: optional context to choose a schema
        """

        spec = requests.get(openapi_spec_uri)
        return spec.json()
    
    def instantiate_markdown_agent(self) -> AbstractContentModel:
        """
        we are explicit about create an abstract model/entity from the markdown
        """
        markdown = self.get_instance_model_as_prompt()            
        model = AbstractContentModel.create_model_from_markdown( markdown=markdown) 
        return model
        
    #this is to allow a path to test a loaded instance but the correct thing to 
    #do would be explicit about creating a markdown agent from the loaded instance
    def get_instance_model_as_prompt(cls):
        """
        override the cls method?
        """
        
        print(cls)
        
        return f"""
# {cls.name}

{cls.content}

## Structured Response Types

{cls.structured_response_markdown}

## Available Functions

{cls.functions_markdown}

        """
        