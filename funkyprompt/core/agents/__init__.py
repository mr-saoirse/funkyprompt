GPT_MINI = "gpt-4o-mini"

DEFAULT_MODEL =   "gpt-4o-2024-08-06"


from funkyprompt.core.functions.Function import Function, FunctionCall
from .CallingContext import CallingContext, ApiCallingContext
from .DefaultAgentCore import DefaultAgentCore, AgentBuilder
from .AbstractLanguageModel import LanguageModel
from .MessageStack import MessageStack
from .Plan import Plan
from .FunctionManager import FunctionManager
from .Runner import Runner
from .QueryClassifier import QueryClassifier




def ask_gpt_mini(question:str, prompt:str):
    """
    ask mini a question - this is a convenience method
    """
    
    from funkyprompt.core.agents.MessageStack import MessageStack, SystemMessage, UserMessage
    from funkyprompt.core import AbstractEntity
    messages= [
            SystemMessage(content=prompt),
            UserMessage(content=question)
        ]
     
    from funkyprompt.services.models.gpt import GptModel
    
    model = GptModel()
    return model(messages=MessageStack(messages=messages, model=AbstractEntity), 
                 context=CallingContext(prefer_json=True, model=GPT_MINI))