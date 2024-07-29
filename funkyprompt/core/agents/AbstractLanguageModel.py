from abc import ABC, abstractmethod
import typing
from . import CallingContext


class LanguageModel(ABC):

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
        messages: typing.List[dict],
        context: CallingContext,
        functions: typing.Optional[dict] = None,
    ):
        pass

    def __call__(
        cls,
        messages: typing.List[dict],
        context: CallingContext,
        functions: typing.Optional[dict] = None,
    ):
        return cls.run(context=context, messages=messages, functions=functions)
