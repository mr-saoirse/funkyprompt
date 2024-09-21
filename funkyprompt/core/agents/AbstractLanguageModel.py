from abc import ABC, abstractmethod
import typing
from . import CallingContext
from pydantic import Field
from funkyprompt import LanguageModelProvider
from funkyprompt.core.agents import MessageStack, Function

class LanguageModel(ABC):

    @classmethod
    def get_provider(cls) -> LanguageModelProvider:
        return 
    
    @abstractmethod
    def get_function_call_or_stream(
        self,
        response: typing.Any,
        callback: typing.Optional[typing.Callable] = None,
        response_buffer: typing.List[typing.Any] = None,
        token_callback_action: typing.Optional[typing.Callable] = None,
    ):
        pass

    @abstractmethod
    def run(
        cls,
        messages: MessageStack,
        context: CallingContext,
        functions: typing.Optional[typing.List[Function]] = None,
    ):
        pass

    def __call__(
        cls,
        messages: MessageStack,
        context: CallingContext,
        functions: typing.Optional[typing.List[Function]] = None,
    ):
        return cls.run(context=context, messages=messages, functions=functions)
