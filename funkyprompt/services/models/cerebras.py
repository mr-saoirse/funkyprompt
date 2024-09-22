
 
"""
WIP: 
the performance of this model is not very good. part of this could be because i have not constructed the messages properly yet
but it also seems like the model is fragile anyway compared to GPT or Claude so I am not sure its worth investing in for now
"""
 
from cerebras.cloud.sdk import Cerebras
import typing
from funkyprompt.core.agents import CallingContext
from funkyprompt.core.functions import FunctionCall
from funkyprompt.core.agents import MessageStack, Function
import json
from . import LanguageModelBase
from funkyprompt import LanguageModelProvider

max_tokens = 4096
model="cerebras-llama3.1-8b"

def _get_function_call_or_stream(
    response, message_stack:MessageStack, callback=None, response_buffer=None, token_callback_action=None
):
    """
    not implementing streaming yet
    
    
    function_call = response.choices[0].message.tool_calls[0].function
    if function_call.name == "calculate_moving_average":
        arguments = json.loads(function_call.arguments)
        result = calculate_moving_average(**arguments)
        
    """
    
    if response.choices[0].finish_reason == 'tool_calls':
        fcalls = [f.function for f in response.choices[0].message.tool_calls]

        """unlike GPT i believe claude needs this continuity - side effect on the messages and not ust the function call - lets see how cerebras llama"""
        #message_stack.add_assistant_message(str(response.content))
        message_stack.add_system_message(f"I have called the functions {[f.name for f in fcalls]}")
        if len(fcalls) == 1:
            f = fcalls[0]
            return FunctionCall(name=f.name, arguments=json.loads(f.arguments) )
        else:
            return [FunctionCall(name=f.name, arguments=json.loads(f.arguments) ) for f in fcalls]
        

        
    """is this the alternative"""
    return response.choices[0].message.content

            

def dump_messages_for_cerebras_llama(message_stack: MessageStack, is_system: bool=False):
    """
    
    """
    
    raise NotImplemented("Have not implemented special message formatting for this model")

class CerebrasModel(LanguageModelBase):

    @classmethod
    def get_provider(cls):
        return LanguageModelProvider.anthropic
        
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
        client = Cerebras(
            # This is the default and can be omitted
            #api_key=os.environ.get("CEREBRAS_API_KEY"),
        )
        response = client.chat.completions.create(
            model=context.model.replace('cerebras-',''), #trick just to map providers and models
            max_tokens=max_tokens,
            tools=[f.to_json_spec(model_provider=LanguageModelProvider.cerebras) for f in functions] if functions else None,
            #try the default
            messages=messages.model_dump()
        )

        
        cls.response_buffer = []
        response = _get_function_call_or_stream(
            response,
            message_stack=messages,
            callback=context.streaming_callback,
            response_buffer=cls.response_buffer,
            # token_callback_action=None,
        )

        return response


