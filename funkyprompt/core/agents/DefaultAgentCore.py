"""this example illustrates how "agents" are just objects with properties and functions
  some agents may not have properties 
  but properties act as a response template which will be a json response.
"""

from funkyprompt.core import AbstractModel
import typing


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
    def lookup_entity(self, keys: str | typing.List[str]) -> typing.List[dict]:
        """Given one or more entity keys, lookup the entity details

        Args:
            keys (str | typing.List[str]): a list of one or more keys

        Returns: a list of typed entities
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
