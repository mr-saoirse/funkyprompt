# https://ai.google.dev/gemini-api/docs/get-started/tutorial?lang=python

# https://ai.google.dev/gemini-api/docs/function-calling/tutorial?lang=python

# gemini-1.5-flash: our fastest multi-modal model
# gemini-1.5-pro: our most capable and intelligent multi-modal model

 
import typing
from funkyprompt.core.agents import CallingContext
from funkyprompt.core.functions import FunctionCall
from funkyprompt.core.agents import MessageStack, Function
import json
from . import LanguageModelBase
from funkyprompt import LanguageModelProvider
import google.generativeai as genai

#gemini-1.5-flash
model = "gemini-1.5-pro-exp-0827"

def _get_function_call_or_stream(
    response, message_stack:MessageStack, callback=None, response_buffer=None, token_callback_action=None
):
    """
    not implementing streaming yet
    """
    part = response.candidates[0].content.parts[0]
    
    if f := part.function_call:
        return FunctionCall(name=f.name, arguments=f.args )
         
    """is this the alternative"""
    return response.text

            

def dump_messages_for_gemini(message_stack: MessageStack, is_system: bool=False):
    """
    gemini https://github.com/google-gemini/cookbook/blob/main/quickstarts/Function_calling.ipynb
    
    """
    
    if is_system:
        return "\n\n".join([m.content for m in message_stack.messages if m.role == 'system'])
        
    data = []
    for m in message_stack.messages:
        if m.role == 'system':
            """system messages are not use in the dialogue of gemini"""
            continue
        elif m.role == 'function_call':
            """what is a function call in open ai is a user message with a tool result for gemini"""
            data.append({  'role': 'user', 'parts': [m.content]}  )
        elif m.role == 'assistant':
            data.append({  'role': 'model', 'parts': [m.content]}  )
        else:
            data.append({  'role': m.role, 'parts': [m.content]}  )
 
    return data

def unbind(f):
    from functools import partial
    s = f.__self__
    f = f.__func__
    return partial(f,s)


class GeminiModel(LanguageModelBase):

    @classmethod
    def get_provider(cls):
        return LanguageModelProvider.google
        
    def get_function_call_or_stream(
        self,
        response: typing.Any,
        callback: typing.Optional[typing.Callable] = None,
        response_buffer: typing.List[typing.Any] = None,
        token_callback_action: typing.Optional[typing.Callable] = None,
    ):
        return _get_function_call_or_stream(
            response=response,
            callback=callback,
            response_buffer=response_buffer,
            token_callback_action=token_callback_action,
        )

    def run(
        cls,
        messages: MessageStack,
        context: CallingContext,
        functions: typing.Optional[typing.List[Function]] = None,
        **kwargs
    ):
        """The run entry point for the agent model
        - calls the api
        - manages streaming
        - manages function calling
        """
        
        """google tries to be clever and handle the python functions directly but also gives option to use json https://ai.google.dev/gemini-api/docs/function-calling/tutorial?lang=python
        - we must wrap the json spec though since it forces a protobug type schema syntax ???
         - vertex api may be better to use in future since its OpenAPI spec based but it seemed easier to setup gcai with just a token (will review later)
        """
        
        model = genai.GenerativeModel(
            model_name=context.model, tools=[genai.protos.Tool( f.to_json_spec(LanguageModelProvider.google))  for f in functions] if functions else None,
            system_instruction=dump_messages_for_gemini(messages,is_system=True),
        )#.start_chat(enable_automatic_function_calling=True)

        response = model.generate_content(dump_messages_for_gemini(messages))
        
        cls.response_buffer = []
        response = _get_function_call_or_stream(
            response,
            message_stack=messages,
            callback=context.streaming_callback,
            response_buffer=cls.response_buffer,
            # token_callback_action=None,
        )

        return response

"""
may implement the vertex approach too since the function calling seems a bit more useful

import vertexai
from vertexai.generative_models import (
    Content, FunctionDeclaration, GenerationConfig, GenerativeModel, Part, Tool
)
from vertexai.preview.generative_models import (
    AutomaticFunctionCallingResponder, GenerativeModel
)

FunctionDeclaration interfaces well with json spec compared to genai.protos.Tool

"""