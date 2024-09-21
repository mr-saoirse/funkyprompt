 
import anthropic

# https://docs.anthropic.com/en/docs/quickstart
model = "claude-3-5-sonnet-20240620"
max_tokens = 4096

import typing
from funkyprompt.core.agents import CallingContext
from funkyprompt.core.functions import FunctionCall
from funkyprompt.core.agents import MessageStack, Function
import json
from . import LanguageModelBase
from funkyprompt import LanguageModelProvider

def _get_function_call_or_stream(
    response, message_stack:MessageStack, callback=None, response_buffer=None, token_callback_action=None
):
    """
    not implementing streaming yet
    """
    
    
    if response.stop_reason == 'tool_use':
        fcalls = [b for b in response.content if b.type =='tool_use']

        """unlike GPT i believe claude needs this continuity - side effect on the messages and not ust the function call"""
        message_stack.add_assistant_message(str(response.content))
        if len(fcalls) == 1:
            f = fcalls[0]
            return FunctionCall(name=f.name, arguments=f.input )
        else:
            return [FunctionCall(name=f.name, arguments=f.input ) for f in fcalls]
        
    """is this the alternative"""
    return response.content[0].text

            

def dump_messages_for_anthropic(message_stack: MessageStack, is_system: bool=False):
    """
    anthropic combines a single system message in the prompt
    it also alternates assistant and user messages and function responses are embedded in user messages apparently
    
    """
    
    if is_system:
        return "\n\n".join([m.content for m in message_stack.messages if m.role == 'system'])
        
    data = []
    for m in message_stack.messages:
 
        if m.role == 'system':
            """system messages are not use in the dialogue of anthropic"""
            continue
        elif m.role == 'function_call':
            """what is a function call in open ai is a user message with a tool result for anthropic"""
            data.append(
              {"role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id":m.name,
                            "content": f"Response:  {m.content}",
                        }
                    ]
              }
            )
        else:
            data.append({  'role': m.role, 'content': m.content}  )
 
    return data

class ClaudeModel(LanguageModelBase):

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
        client = anthropic.Anthropic()
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=dump_messages_for_anthropic(messages,is_system=True),
            tools=[f.to_json_spec(model_provider=LanguageModelProvider.anthropic) for f in functions] if functions else None,
            messages=dump_messages_for_anthropic(messages)
        )
        
        print(response)
        
        cls.response_buffer = []
        response = _get_function_call_or_stream(
            response,
            message_stack=messages,
            callback=context.streaming_callback,
            response_buffer=cls.response_buffer,
            # token_callback_action=None,
        )

        return response
