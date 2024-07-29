# https://cookbook.openai.com/examples/how_to_call_functions_with_chat_models


import openai
import typing
from funkyprompt.core.agents import CallingContext
from funkyprompt.core.functions import FunctionCall
import json
from . import LanguageModelBase


def _get_function_call_or_stream(
    response, callback=None, response_buffer=None, token_callback_action=None
):
    """
    This is a little bit opaque as it tries to abstract
    function calling and non-function calling for both streaming modes
    """

    def function_builder(function_call, response):
        """wrap it in our simple interface"""
        function_name = function_call.name
        function_args = function_call.arguments
        for c in response:
            if c.choices:
                c = c.choices[0].delta
                if c.function_call:
                    function_args += c.function_call.arguments
        return FunctionCall(name=function_name, arguments=json.loads(function_args))

    def content_builder(content, response):
        """
        isolate the code path where we return a generator
        """
        yield content
        for c in response:
            if not c.choices:
                """unfortunately the streaming model is a bit tricky to get the token usage out"""
                ###############################
                try:
                    token_callback_action(c)
                except:
                    raise
                ###############################
            if c.choices:
                c = c.choices[0].delta
                yield c.content

    if isinstance(response, openai.Stream):
        """this just checks the different states of messages"""
        content = ""
        for chunk in response:

            if chunk.choices:
                _chunk = chunk.choices[0].delta
                has_call = _chunk.function_call
                if has_call:
                    fb = function_builder(
                        _chunk.function_call,
                        response,
                    )
                    return fb
                elif _chunk.content:
                    """here we optionally stream to the callback"""
                    content += _chunk.content
                    if callback:
                        callback(_chunk.content)
                    if isinstance(response_buffer, list):
                        response_buffer.append(_chunk.content)
                    # we go into generator mode when there is no callback and its a stream
                    else:
                        return content_builder(_chunk.content, response)

            elif token_callback_action:
                """how we count are pennies when streaming"""
                token_callback_action(chunk)

        if isinstance(response_buffer, list):
            response_buffer.append(content)
        return content

    else:
        """not streaming mode - respecting the same interface"""
        response_message = response.choices[0].message
        function_call = response_message.function_call
        if function_call:
            return FunctionCall(
                name=function_call.name,
                arguments=json.loads(function_call.arguments),
            )
        if isinstance(response_buffer, list):
            response_buffer.append(response_message.content)

        """not streaming mode token callback"""
        if token_callback_action:
            try:
                token_callback_action(response)
            except:
                raise

        return response_message.content


class GptModel(LanguageModelBase):

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
        messages: typing.List[dict],
        context: CallingContext,
        functions: typing.Optional[dict] = None,
        **kwargs
    ):
        """The run entry point for the agent model
        - calls the api
        - manages streaming
        - manages function calling
        """

        response = openai.chat.completions.create(
            model=context.model,
            functions=(list(functions) if functions else None),
            function_call="auto" if functions else None,
            messages=messages,
            temperature=context.temperature,
            response_format=context.get_response_format(),
            stream=context.is_streaming,
            stream_options=({"include_usage": True} if context.is_streaming else None),
        )

        cls.response_buffer = []
        response = _get_function_call_or_stream(
            response,
            context.streaming_callback,
            response_buffer=cls.response_buffer,
            # token_callback_action=None,
        )

        return response
